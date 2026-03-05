"""Main generation pipeline orchestrator.

Contains the phased agentic generation loop and the legacy two-phase fallback.
"""

import logging
from typing import Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.provider import LLMProvider, LLMProviderFactory
from app.models.compatibility import CompatibilityRule
from app.models.game import Game
from app.models.mod import Mod
from app.models.mod_build_phase import ModBuildPhase
from app.models.playstyle import Playstyle
from app.models.playstyle_mod import PlaystyleMod
from app.schemas.modlist import ModlistGenerateRequest
from app.services.nexus_client import NexusModsClient
from app.services.tier_classifier import classify_hardware_tier

from .exceptions import PauseGeneration
from .handlers import build_phase1_handlers, build_phase2_handlers, emit
from .prompts import (
    LEGACY_DISCOVERY_PROMPT,
    LEGACY_PATCH_REVIEW_PROMPT,
    build_hardware_context,
    build_patch_phase_prompt,
    build_phase_prompt,
    build_phase_user_msg,
    classify_error,
)
from .session import GenerationResult, GenerationSession
from .tools import PHASE1_TOOLS, PHASE2_TOOLS
from .version import TIER_MIN_VRAM, VERSION_NOTES, is_version_compatible

logger = logging.getLogger(__name__)

# VRAM budget percentages by hardware tier
_TIER_VRAM_PCT = {"low": 0.60, "mid": 0.70, "high": 0.80, "ultra": 0.85}


def _build_provider_list(request: ModlistGenerateRequest) -> list[LLMProvider]:
    """Build ordered list of LLM providers to try from request credentials."""
    providers: list[LLMProvider] = []
    for cred in request.llm_credentials:
        try:
            providers.append(
                LLMProviderFactory.create_from_request(
                    cred.provider, cred.api_key,
                    base_url=cred.base_url, model=cred.model,
                )
            )
        except ValueError:
            logger.warning(f"Skipping unknown provider: {cred.provider}")

    if not providers:
        providers.append(LLMProviderFactory.create())

    return providers


def _compute_budgets(
    request: ModlistGenerateRequest,
) -> tuple[dict, int, int]:
    """Compute hardware tier, VRAM budget, and storage budget from request."""
    user_vram = request.vram_mb or 6144
    tier_info = classify_hardware_tier(
        gpu=request.gpu, vram_mb=request.vram_mb,
        cpu=request.cpu, ram_gb=request.ram_gb,
        cpu_cores=request.cpu_cores, cpu_speed_ghz=request.cpu_speed_ghz,
    )
    vram_budget = int(user_vram * _TIER_VRAM_PCT.get(tier_info["tier"], 0.75))
    available_storage = request.available_storage_gb or 50
    storage_budget_gb = max(10, int(available_storage * 0.80))
    return tier_info, vram_budget, storage_budget_gb


async def generate_modlist(
    db: AsyncSession,
    request: ModlistGenerateRequest,
    event_callback: Callable[[dict], None] | None = None,
    nexus_api_key: str | None = None,
    resume_from_phase: int | None = None,
    resume_session: GenerationSession | None = None,
) -> GenerationResult:
    """Generate a modlist using the phased agentic pipeline.

    Iterates through game-specific build phases from the DB. Each phase runs
    its own LLM tool-calling loop with focused prompts. The final phase always
    handles compatibility patches.

    Args:
        db: Database session
        request: Generation request with hardware info, playstyle, credentials
        event_callback: Optional callback for real-time event streaming
        nexus_api_key: API key for Nexus Mods
        resume_from_phase: If resuming, which phase number to start from
        resume_session: If resuming, the restored GenerationSession
    """
    game = await db.get(Game, request.game_id)
    playstyle = await db.get(Playstyle, request.playstyle_id)
    if not game or not playstyle:
        raise ValueError("Invalid game or playstyle ID")

    game_version = request.game_version
    tier_info, vram_budget, storage_budget_gb = _compute_budgets(request)
    version_notes = VERSION_NOTES.get(game_version or "", "No specific version selected.")
    hardware_context = build_hardware_context(request, tier_info, vram_budget, storage_budget_gb)

    # Load ordered phases for this game
    result = await db.execute(
        select(ModBuildPhase)
        .where(ModBuildPhase.game_id == request.game_id)
        .order_by(ModBuildPhase.phase_number)
    )
    phase_list = result.scalars().all()

    # If no phases in DB, fall back to legacy two-phase pipeline
    if not phase_list:
        return await _generate_legacy(db, request, event_callback, nexus_api_key=nexus_api_key)

    providers_to_try = _build_provider_list(request)

    # Create or restore Nexus client and session
    nexus = NexusModsClient(api_key=nexus_api_key)

    # Validate Nexus API key before running phases of empty searches
    try:
        nexus_user = await nexus.validate_key()
        logger.info("Nexus API key validated: user=%s premium=%s",
                     nexus_user.get("name"), nexus_user.get("is_premium"))
        emit(event_callback, "nexus_validated", {
            "username": nexus_user.get("name", ""),
            "is_premium": nexus_user.get("is_premium", False),
        })
    except Exception as e:
        logger.error("Nexus API key validation failed: %s", e)
        emit(event_callback, "error", {
            "message": f"Nexus API key is invalid or expired: {e}",
        })
        raise ValueError(f"Nexus API key validation failed: {e}")

    if resume_session:
        session = resume_session
        session.nexus = nexus
    else:
        session = GenerationSession(game_domain=game.nexus_domain, nexus=nexus)

    total_phases = len(phase_list)
    last_successful_provider = providers_to_try[0]
    # Permanent failure types — these providers won't recover mid-generation
    _PERMANENT_ERRORS = {"auth_error", "token_limit"}
    exhausted_providers: set[str] = set()

    # ── Phased generation loop ──
    for phase in phase_list:
        if resume_from_phase and phase.phase_number < resume_from_phase:
            continue

        is_patch_phase = (phase.phase_number == phase_list[-1].phase_number)

        emit(event_callback, "phase_start", {
            "phase": phase.name,
            "number": phase.phase_number,
            "total_phases": total_phases,
            "is_patch_phase": is_patch_phase,
        })

        # Build the provider order for this phase:
        # 1. Last successful provider first (likely to keep working)
        # 2. Skip permanently-exhausted providers
        phase_providers = [
            p for p in providers_to_try
            if p.get_model_name() not in exhausted_providers
        ]
        if not phase_providers:
            raise PauseGeneration(
                reason="All LLM providers are exhausted",
                phase_number=phase.phase_number,
                phase_name=phase.name,
                session_snapshot=session.to_snapshot(),
            )
        # Move last successful provider to front
        if last_successful_provider in phase_providers:
            phase_providers.remove(last_successful_provider)
            phase_providers.insert(0, last_successful_provider)

        phase_succeeded = False
        provider_errors: list[str] = []

        for i, llm in enumerate(phase_providers):
            try:
                session.finalized = False

                if is_patch_phase:
                    system_prompt = build_patch_phase_prompt(
                        phase, game, game_version, session, total_phases,
                    )
                    user_msg = "Review the modlist above for compatibility patches."
                    tools = PHASE2_TOOLS
                    handlers = build_phase2_handlers(session, event_callback)
                else:
                    system_prompt = build_phase_prompt(
                        phase, game, playstyle, game_version, version_notes,
                        hardware_context, session, total_phases,
                    )
                    user_msg = build_phase_user_msg(phase, playstyle, game, game_version)
                    tools = PHASE1_TOOLS
                    handlers = build_phase1_handlers(session, event_callback)

                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_msg},
                ]

                logger.info(
                    f"Phase {phase.phase_number}/{total_phases}: {phase.name} "
                    f"(provider: {llm.get_model_name()})"
                )

                await llm.generate_with_tools(
                    messages=messages,
                    tools=tools,
                    tool_handlers=handlers,
                    max_iterations=phase.max_mods * 3 + 10,
                    on_text=lambda text: emit(
                        event_callback, "thinking", {"text": text[:200]}
                    ),
                )

                phase_succeeded = True
                last_successful_provider = llm
                session.completed_phases.append(phase.phase_number)

                if not session.finalized:
                    logger.warning(
                        f"Phase {phase.phase_number} ({phase.name}) ended without "
                        f"finalize() — LLM may have hit max iterations or stopped early"
                    )

                emit(event_callback, "phase_complete", {
                    "phase": phase.name,
                    "number": phase.phase_number,
                    "mod_count": len(session.modlist),
                    "patch_count": len(session.patches),
                })

                logger.info(
                    f"Phase {phase.phase_number} complete: "
                    f"{len(session.modlist)} mods, {len(session.patches)} patches"
                )
                break

            except Exception as e:
                error_type, friendly = classify_error(llm, e)
                logger.warning(
                    f"Provider {llm.get_model_name()} failed on phase "
                    f"{phase.phase_number} ({error_type}): {e}"
                )
                provider_errors.append(friendly)

                # Mark permanently-failed providers so we skip them on future phases
                if error_type in _PERMANENT_ERRORS:
                    exhausted_providers.add(llm.get_model_name())
                    logger.info(
                        f"Provider {llm.get_model_name()} marked as exhausted "
                        f"({error_type}) — will not retry on future phases"
                    )

                emit(event_callback, "provider_error", {
                    "provider": llm.get_model_name(),
                    "type": error_type,
                    "message": friendly,
                })

                remaining = [
                    p for p in phase_providers[i + 1:]
                    if p.get_model_name() not in exhausted_providers
                ]
                if remaining:
                    emit(event_callback, "provider_switch", {
                        "from_provider": llm.get_model_name(),
                        "to_provider": remaining[0].get_model_name(),
                    })

                continue

        if not phase_succeeded:
            error_summary = "; ".join(provider_errors)
            raise PauseGeneration(
                reason=error_summary,
                phase_number=phase.phase_number,
                phase_name=phase.name,
                session_snapshot=session.to_snapshot(),
            )

    # ── All phases complete ──
    all_entries = session.modlist + session.patches
    return GenerationResult(
        entries=all_entries,
        knowledge_flags=session.knowledge_flags,
        llm_provider=last_successful_provider.get_model_name(),
    )


async def _generate_legacy(
    db: AsyncSession,
    request: ModlistGenerateRequest,
    event_callback: Callable[[dict], None] | None = None,
    nexus_api_key: str | None = None,
) -> GenerationResult:
    """Legacy two-phase pipeline for games without DB-defined phases."""
    game = await db.get(Game, request.game_id)
    playstyle = await db.get(Playstyle, request.playstyle_id)
    if not game or not playstyle:
        raise ValueError("Invalid game or playstyle ID")

    game_version = request.game_version
    tier_info, vram_budget, storage_budget_gb = _compute_budgets(request)
    version_notes = VERSION_NOTES.get(game_version or "", "No specific version selected.")

    nexus = NexusModsClient(api_key=nexus_api_key)
    session = GenerationSession(game_domain=game.nexus_domain, nexus=nexus)

    providers_to_try = _build_provider_list(request)

    discovery_prompt = LEGACY_DISCOVERY_PROMPT.format(
        game_name=game.name,
        game_version=game_version or "Unknown",
        gpu=request.gpu or "Unknown",
        cpu=request.cpu or "Unknown",
        ram_gb=request.ram_gb or "Unknown",
        vram_mb=request.vram_mb or 6144,
        available_storage_gb=request.available_storage_gb or 50,
        storage_budget_gb=storage_budget_gb,
        vram_budget=vram_budget,
        playstyle=playstyle.name,
        version_notes=version_notes,
    )

    provider_errors: list[str] = []
    for i, llm in enumerate(providers_to_try):
        try:
            session.modlist.clear()
            session.patches.clear()
            session.knowledge_flags.clear()
            session.description_cache.clear()
            session.finalized = False

            logger.info(f"Trying provider {i+1}/{len(providers_to_try)}: {llm.get_model_name()}")

            emit(event_callback, "phase_start", {
                "phase": "Discovery",
                "number": 1,
                "total_phases": 2,
            })

            messages = [
                {"role": "system", "content": discovery_prompt},
                {"role": "user", "content": f"Build a {playstyle.name} modlist for {game.name} ({game_version or 'any version'})."},
            ]

            await llm.generate_with_tools(
                messages=messages,
                tools=PHASE1_TOOLS,
                tool_handlers=build_phase1_handlers(session, event_callback),
                max_iterations=20,
                on_text=lambda text: emit(
                    event_callback, "thinking", {"text": text[:200]}
                ),
            )

            emit(event_callback, "phase_complete", {
                "phase": "Discovery",
                "number": 1,
                "mod_count": len(session.modlist),
            })

            if session.modlist:
                modlist_summary = "\n".join(
                    f"{i+1}. {m['name']} (Nexus ID: {m['nexus_mod_id']}) — {m.get('reason', '')}"
                    for i, m in enumerate(session.modlist)
                )

                patch_prompt = LEGACY_PATCH_REVIEW_PROMPT.format(
                    game_name=game.name,
                    game_version=game_version or "Unknown",
                    modlist_summary=modlist_summary,
                )

                session.finalized = False

                emit(event_callback, "phase_start", {
                    "phase": "Patch Review",
                    "number": 2,
                    "total_phases": 2,
                })

                await llm.generate_with_tools(
                    messages=[
                        {"role": "system", "content": patch_prompt},
                        {"role": "user", "content": "Review the modlist above for compatibility patches."},
                    ],
                    tools=PHASE2_TOOLS,
                    tool_handlers=build_phase2_handlers(session, event_callback),
                    max_iterations=15,
                    on_text=lambda text: emit(
                        event_callback, "thinking", {"text": text[:200]}
                    ),
                )

                emit(event_callback, "phase_complete", {
                    "phase": "Patch Review",
                    "number": 2,
                    "mod_count": len(session.modlist),
                    "patch_count": len(session.patches),
                })

            all_entries = session.modlist + session.patches
            return GenerationResult(
                entries=all_entries,
                knowledge_flags=session.knowledge_flags,
                llm_provider=llm.get_model_name(),
            )

        except Exception as e:
            _, friendly = classify_error(llm, e)
            logger.warning(f"Provider {llm.get_model_name()} failed: {e}")
            provider_errors.append(friendly)
            continue

    error_summary = "; ".join(provider_errors) if provider_errors else "No LLM provider available"
    raise RuntimeError(error_summary)


async def build_rag_context(
    db: AsyncSession, playstyle_id: int, user_vram_mb: int,
    game_version: str | None = None,
) -> str:
    """Build context string from database for LLM."""
    result = await db.execute(
        select(Mod, PlaystyleMod)
        .join(PlaystyleMod, Mod.id == PlaystyleMod.mod_id)
        .where(PlaystyleMod.playstyle_id == playstyle_id)
    )
    rows = result.all()

    context_lines = []
    for mod, pm in rows:
        if not is_version_compatible(mod.game_version_support, game_version):
            continue
        min_vram = TIER_MIN_VRAM.get(pm.hardware_tier_min or "low", 0)
        if user_vram_mb >= min_vram:
            impact = mod.performance_impact or "unknown"
            vram = f"{mod.vram_requirement_mb}MB VRAM" if mod.vram_requirement_mb else "N/A"
            ver = f" | Version: {mod.game_version_support}" if mod.game_version_support != "all" else ""
            context_lines.append(
                f"- ID:{mod.id} | {mod.name} by {mod.author} | "
                f"Impact: {impact} | VRAM: {vram} | "
                f"Priority: {pm.priority}{ver} | {mod.summary or ''}"
            )

    mod_ids = [mod.id for mod, _ in rows]
    if mod_ids:
        compat_result = await db.execute(
            select(CompatibilityRule).where(CompatibilityRule.mod_id.in_(mod_ids))
        )
        rules = compat_result.scalars().all()
        if rules:
            context_lines.append("\nCompatibility Rules:")
            for rule in rules:
                context_lines.append(
                    f"- Mod {rule.mod_id} {rule.rule_type} Mod {rule.related_mod_id}"
                    + (f" | Note: {rule.notes}" if rule.notes else "")
                )

    return "\n".join(context_lines) if context_lines else "No mod data available yet."
