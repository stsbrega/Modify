"""Prompt builders for the generation pipeline.

Constructs system prompts and user messages for each build phase,
including hardware context, playstyle focus, and methodology injection.
"""

import logging

from app.knowledge import get_methodology_context
from app.llm.provider import LLMProvider
from app.models.game import Game
from app.models.mod_build_phase import ModBuildPhase
from app.models.playstyle import Playstyle
from app.schemas.modlist import ModlistGenerateRequest

from .session import GenerationSession
from .version import VERSION_NOTES

logger = logging.getLogger(__name__)


def build_phase_prompt(
    phase: ModBuildPhase,
    game: Game,
    playstyle: Playstyle,
    game_version: str | None,
    version_notes: str,
    hardware_context: str,
    session: GenerationSession,
    total_phases: int,
) -> str:
    """Build a focused system prompt for a single build phase."""

    mods_so_far = ""
    if session.modlist:
        mods_so_far = "\n\nMODS ALREADY IN YOUR MODLIST (from earlier phases — do NOT re-add these):\n"
        mods_so_far += "\n".join(
            f"  {i+1}. {m['name']} (Nexus ID: {m['nexus_mod_id']})"
            for i, m in enumerate(session.modlist)
        )

    if phase.is_playstyle_driven:
        playstyle_context = f"""
PLAYSTYLE FOCUS: {playstyle.name}
The user wants a {playstyle.name} experience. Your mod choices in this phase should
directly support this playstyle. Prioritize mods that enhance the {playstyle.name} feel."""
    else:
        playstyle_context = f"""
PLAYSTYLE: {playstyle.name} (for context — this phase is not heavily playstyle-driven,
but keep the overall experience in mind)."""

    methodology_context = get_methodology_context(game.slug, phase.phase_number)

    return f"""You are an expert {game.name} mod curator working on Phase {phase.phase_number}/{total_phases}: "{phase.name}".

GAME: {game.name} ({game_version or "Unknown"} edition)
{version_notes}

{hardware_context}

{playstyle_context}
{methodology_context}

── PHASE {phase.phase_number}: {phase.name} ──
{phase.description}

SEARCH GUIDANCE:
{phase.search_guidance}

RULES FOR THIS PHASE:
{phase.rules}

{f"EXAMPLE MODS (for reference — verify these exist and are current before adding):{chr(10)}{phase.example_mods}" if phase.example_mods else ""}
{mods_so_far}

INSTRUCTIONS:
1. Search for mods using varied, specific terms related to this phase's focus.
2. Use get_mod_details to read about a mod BEFORE adding it. Check:
   - Compatibility with {game_version or "the user's"} game version
   - Performance impact relative to the user's hardware
   - Whether it actually fits this phase's purpose
3. Add up to {phase.max_mods} mods for this phase (fewer is fine if quality is high).
4. Set load_order based on the mod's position within this phase.
5. Call finalize() when you are done with this phase."""


def build_patch_phase_prompt(
    phase: ModBuildPhase,
    game: Game,
    game_version: str | None,
    session: GenerationSession,
    total_phases: int,
) -> str:
    """Build system prompt for the final compatibility patches phase."""
    modlist_summary = "\n".join(
        f"  {i+1}. {m['name']} (Nexus ID: {m['nexus_mod_id']}) — {m.get('reason', '')}"
        for i, m in enumerate(session.modlist)
    )

    methodology_context = get_methodology_context(game.slug, phase.phase_number)

    return f"""You are reviewing a {game.name} ({game_version or "Unknown"} edition) modlist for compatibility.

This is Phase {phase.phase_number}/{total_phases}: "{phase.name}".
{methodology_context}

THE MODLIST TO REVIEW:
{modlist_summary}

{phase.search_guidance}

RULES:
{phase.rules}

PROCESS:
1. For each potential conflict pair, FIRST use get_mod_description to check if the
   mod page mentions patches or compatibility notes.
2. If the description doesn't mention a patch, use search_patches to search Nexus.
3. If you find a patch, use add_patch with correct load_order (patches load AFTER the mods they patch).
4. If a patch is NEEDED but doesn't exist, use flag_user_knowledge to alert the user.

IMPORTANT:
- Not every mod pair needs a patch. Only flag genuine conflicts.
- Framework mods (SKSE, Address Library, etc.) don't need patches with each other.
- Focus on mods that edit the same game systems.
- Call finalize_review when done."""


def build_phase_user_msg(
    phase: ModBuildPhase,
    playstyle: Playstyle,
    game: Game,
    game_version: str | None,
) -> str:
    """Build the user message that kicks off a phase."""
    if phase.is_playstyle_driven:
        return (
            f"Build the {phase.name} section of a {playstyle.name} modlist for "
            f"{game.name} ({game_version or 'any version'}). "
            f"Focus on mods that enhance the {playstyle.name} experience."
        )
    return (
        f"Build the {phase.name} section of a modlist for "
        f"{game.name} ({game_version or 'any version'})."
    )


def build_hardware_context(
    request: ModlistGenerateRequest,
    tier_info: dict,
    vram_budget: int,
    storage_budget_gb: int,
) -> str:
    """Build the hardware context block for system prompts."""
    return f"""USER HARDWARE:
- GPU: {request.gpu or "Unknown"} ({request.vram_mb or 6144}MB VRAM)
- CPU: {request.cpu or "Unknown"}
- RAM: {request.ram_gb or "Unknown"}GB
- Available disk space: {request.available_storage_gb or 50}GB (budget: {storage_budget_gb}GB)
- VRAM budget: {vram_budget}MB
- Hardware tier: {tier_info["tier"]}"""


def classify_error(llm: LLMProvider, e: Exception) -> tuple[str, str]:
    """Classify an exception into (error_type, friendly_message).

    Returns:
        error_type: machine-readable error classification
        friendly: human-readable message for the frontend
    """
    error_msg = str(e)
    model_name = llm.get_model_name()

    if "rate" in error_msg.lower() or "429" in error_msg:
        return "rate_limit", f"{model_name}: Rate limited — too many requests"
    if "auth" in error_msg.lower() or "401" in error_msg or ("invalid" in error_msg.lower() and "key" in error_msg.lower()):
        return "auth_error", f"{model_name}: Invalid API key"
    if "quota" in error_msg.lower() or "insufficient" in error_msg.lower() or "billing" in error_msg.lower():
        return "token_limit", f"{model_name}: Quota exceeded or billing issue"
    if "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
        return "timeout", f"{model_name}: Request timed out"
    if "connect" in error_msg.lower() or "network" in error_msg.lower():
        return "connection", f"{model_name}: Connection failed"
    if "token" in error_msg.lower() and ("limit" in error_msg.lower() or "max" in error_msg.lower()):
        return "token_limit", f"{model_name}: Token limit exceeded"

    error_type_name = type(e).__name__
    return "unknown", f"{model_name}: {error_type_name} — {error_msg[:120]}"


# ──────────────────────────────────────────────
# Legacy two-phase prompts (used when no DB phases exist)
# ──────────────────────────────────────────────

LEGACY_DISCOVERY_PROMPT = """You are an expert video game mod curator for {game_name} ({game_version} edition).

USER HARDWARE:
- GPU: {gpu} ({vram_mb}MB VRAM)
- CPU: {cpu}
- RAM: {ram_gb}GB
- Available disk space: {available_storage_gb}GB (budget: {storage_budget_gb}GB)
- VRAM budget: {vram_budget}MB

PLAYSTYLE: {playstyle}

{version_notes}

YOUR TASK: Build a high-quality modlist by searching Nexus Mods. Follow these rules:

1. Search for mods using varied, specific terms — don't use one generic search.
   Good: "texture overhaul", "combat mechanics", "weather effects", "UI improvements"
   Bad: "best mods", "popular mods"

2. DON'T just pick the most popular mods. Use both "endorsements" and "updated" sort orders.
   Newer mods with fewer endorsements can be excellent — evaluate them on merit.

3. Use get_mod_details to read about a mod BEFORE adding it. Check for:
   - Compatibility with the user's game version
   - Performance impact relative to the user's hardware
   - Whether it actually fits the requested playstyle

4. Stay within the storage budget ({storage_budget_gb}GB) and VRAM budget ({vram_budget}MB).
   Estimate sizes: texture packs 1-4GB, gameplay mods <100MB, overhauls 500MB-2GB.

5. Set load_order correctly — essential framework mods first (SKSE, USSEP, etc.), then overhauls, then patches/tweaks last.

6. Call finalize() when you're satisfied with the list. Aim for 15-30 mods depending on the playstyle."""

LEGACY_PATCH_REVIEW_PROMPT = """You are reviewing a modlist for {game_name} ({game_version} edition) for compatibility issues.

THE MODLIST:
{modlist_summary}

YOUR TASK: Check each mod for compatibility patches needed with other mods in this list.

PROCESS (follow this order for each potential conflict):
1. FIRST: Use get_mod_description to check if the mod page mentions patches or compatibility.
   Mod authors often list required patches or link to them directly.
2. SECOND: If the description doesn't mention a patch, use search_patches to search Nexus.
   Search with terms like "ModA ModB patch" or "ModA compatibility".
3. If you find a patch mod, use add_patch to add it with the correct load_order (patches load AFTER the mods they patch).
4. If a patch is NEEDED but doesn't exist, use flag_user_knowledge to alert the user.
   This is important for future AI patch generation.

IMPORTANT:
- Not every mod pair needs a patch. Only flag genuine conflicts.
- Common framework mods (SKSE, Address Library, etc.) don't need patches with each other.
- Focus on mods that edit the same game systems (e.g., two combat mods, or a texture mod + ENB).
- Call finalize_review when done."""
