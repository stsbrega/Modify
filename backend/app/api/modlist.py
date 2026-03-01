import asyncio
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.game import Game
from app.models.mod import Mod
from app.models.modlist import Modlist, ModlistEntry, ModlistKnowledgeFlag
from app.models.playstyle import Playstyle
from app.models.playstyle_mod import PlaystyleMod
from app.models.user import User
from app.schemas.modlist import (
    ExportModEntry, ModEntry, ModlistExportResponse,
    ModlistGenerateRequest, ModlistResponse, UserKnowledgeFlag,
)
from app.services.generation import (
    TIER_MIN_VRAM,
    generate_modlist as run_generation, GenerationResult, is_version_compatible,
)
from app.services.nexus_client import NexusModsClient
from app.api.deps import get_current_user, get_current_user_optional

logger = logging.getLogger(__name__)

router = APIRouter()


def _entry_to_schema(entry: ModlistEntry) -> ModEntry:
    """Convert a DB ModlistEntry to the API schema, using denormalized fields."""
    return ModEntry(
        mod_id=entry.mod_id,
        nexus_mod_id=entry.nexus_mod_id,
        name=entry.name or "Unknown",
        author=entry.author,
        summary=entry.summary,
        reason=entry.reason,
        load_order=entry.load_order,
        is_patch=entry.is_patch,
        patches_mods=entry.patches_mods,
        compatibility_notes=entry.compatibility_notes,
    )


def _flag_to_schema(flag: ModlistKnowledgeFlag) -> UserKnowledgeFlag:
    return UserKnowledgeFlag(
        mod_a=flag.mod_a_name,
        mod_b=flag.mod_b_name,
        issue=flag.issue,
        severity=flag.severity,
    )


async def save_modlist_to_db(
    db: AsyncSession,
    request: ModlistGenerateRequest,
    result: GenerationResult,
    user_id: uuid.UUID | None = None,
) -> Modlist:
    """Save a generation result to the database.

    Creates the Modlist, ModlistEntry rows, and ModlistKnowledgeFlag rows.
    Returns the saved Modlist with its generated UUID.

    This helper is used by both the legacy synchronous endpoint and the
    new background-task generation flow.
    """
    modlist = Modlist(
        game_id=request.game_id,
        playstyle_id=request.playstyle_id,
        gpu_model=request.gpu,
        cpu_model=request.cpu,
        ram_gb=request.ram_gb,
        vram_mb=request.vram_mb,
        llm_provider=result.llm_provider,
        user_id=user_id,
    )
    db.add(modlist)
    await db.flush()

    for i, mod_data in enumerate(result.entries):
        entry = ModlistEntry(
            modlist_id=modlist.id,
            nexus_mod_id=mod_data.get("nexus_mod_id"),
            mod_id=mod_data.get("mod_id"),
            name=mod_data.get("name", "Unknown"),
            author=mod_data.get("author"),
            summary=mod_data.get("summary"),
            reason=mod_data.get("reason"),
            load_order=mod_data.get("load_order", i + 1),
            enabled=True,
            download_status="pending",
            is_patch=mod_data.get("is_patch", False),
            patches_mods=mod_data.get("patches_mods"),
        )
        db.add(entry)

    for flag_data in result.knowledge_flags:
        flag = ModlistKnowledgeFlag(
            modlist_id=modlist.id,
            mod_a_name=flag_data["mod_a"],
            mod_b_name=flag_data["mod_b"],
            issue=flag_data["issue"],
            severity=flag_data.get("severity", "warning"),
        )
        db.add(flag)

    await db.commit()
    return modlist


@router.post("/generate", response_model=ModlistResponse)
async def generate_modlist(
    request: ModlistGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    """Legacy synchronous generation endpoint (backward compatible)."""
    game = await db.get(Game, request.game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    playstyle = await db.get(Playstyle, request.playstyle_id)
    if not playstyle:
        raise HTTPException(status_code=404, detail="Playstyle not found")

    result: GenerationResult | None = None
    generation_error: str | None = None
    try:
        result = await run_generation(db, request)
    except Exception as e:
        generation_error = str(e)
        logger.error(f"LLM generation failed ({type(e).__name__}): {e}")

    use_fallback = result is None or not result.entries
    user_id = current_user.id if current_user else None

    if not use_fallback:
        modlist = await save_modlist_to_db(db, request, result, user_id)
        entry_result = await db.execute(
            select(ModlistEntry)
            .where(ModlistEntry.modlist_id == modlist.id)
            .order_by(ModlistEntry.load_order)
        )
        entries_schema = [_entry_to_schema(e) for e in entry_result.scalars().all()]
        knowledge_flags_schema = [
            UserKnowledgeFlag(
                mod_a=f["mod_a"], mod_b=f["mod_b"],
                issue=f["issue"], severity=f.get("severity", "warning"),
            )
            for f in result.knowledge_flags
        ]
    else:
        fallback_mods = await _fallback_modlist(
            db, request.playstyle_id, request.vram_mb, request.game_version
        )
        modlist = Modlist(
            game_id=request.game_id,
            playstyle_id=request.playstyle_id,
            gpu_model=request.gpu,
            cpu_model=request.cpu,
            ram_gb=request.ram_gb,
            vram_mb=request.vram_mb,
            llm_provider="fallback",
            user_id=user_id,
        )
        db.add(modlist)
        await db.flush()

        entries_schema = []
        for i, mod_data in enumerate(fallback_mods):
            entry = ModlistEntry(
                modlist_id=modlist.id,
                mod_id=mod_data.get("mod_id"),
                name=mod_data.get("name", "Unknown"),
                author=mod_data.get("author"),
                summary=mod_data.get("summary"),
                reason=mod_data.get("reason"),
                load_order=mod_data.get("load_order", i + 1),
                enabled=True,
                download_status="pending",
            )
            db.add(entry)
            entries_schema.append(_entry_to_schema(entry))

        await db.commit()
        knowledge_flags_schema = []

    return ModlistResponse(
        id=modlist.id,
        game_id=request.game_id,
        playstyle_id=request.playstyle_id,
        entries=entries_schema,
        llm_provider=modlist.llm_provider,
        user_knowledge_flags=knowledge_flags_schema,
        used_fallback=use_fallback,
        generation_error=generation_error,
    )


async def _fallback_modlist(
    db: AsyncSession, playstyle_id: int, user_vram_mb: int | None,
    game_version: str | None = None,
) -> list[dict]:
    """Fallback: return curated mods from DB when LLM is unavailable."""
    vram = user_vram_mb or 6144

    result = await db.execute(
        select(Mod, PlaystyleMod)
        .join(PlaystyleMod, Mod.id == PlaystyleMod.mod_id)
        .where(PlaystyleMod.playstyle_id == playstyle_id)
        .order_by(PlaystyleMod.priority.desc())
    )

    mods = []
    for i, (mod, pm) in enumerate(result.all()):
        if not is_version_compatible(mod.game_version_support, game_version):
            continue
        min_vram = TIER_MIN_VRAM.get(pm.hardware_tier_min or "low", 0)
        if vram >= min_vram:
            mods.append({
                "mod_id": mod.id,
                "name": mod.name,
                "author": mod.author,
                "summary": mod.summary,
                "reason": f"Curated mod (priority: {pm.priority})",
                "load_order": i + 1,
            })

    return mods


@router.get("/mine", response_model=list[ModlistResponse])
async def get_my_modlists(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all modlists for the current user."""
    result = await db.execute(
        select(Modlist)
        .where(Modlist.user_id == current_user.id)
        .order_by(Modlist.created_at.desc())
    )
    modlists = result.scalars().all()

    responses = []
    for ml in modlists:
        entry_result = await db.execute(
            select(ModlistEntry)
            .where(ModlistEntry.modlist_id == ml.id)
            .order_by(ModlistEntry.load_order)
        )
        entries = [_entry_to_schema(e) for e in entry_result.scalars().all()]

        flag_result = await db.execute(
            select(ModlistKnowledgeFlag)
            .where(ModlistKnowledgeFlag.modlist_id == ml.id)
        )
        flags = [_flag_to_schema(f) for f in flag_result.scalars().all()]

        responses.append(
            ModlistResponse(
                id=ml.id,
                game_id=ml.game_id,
                playstyle_id=ml.playstyle_id,
                entries=entries,
                llm_provider=ml.llm_provider,
                user_knowledge_flags=flags,
            )
        )

    return responses


@router.delete("/{modlist_id}", status_code=204)
async def delete_modlist(
    modlist_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a modlist owned by the current user."""
    try:
        ml_uuid = uuid.UUID(modlist_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid modlist ID")

    modlist = await db.get(Modlist, ml_uuid)
    if not modlist:
        raise HTTPException(status_code=404, detail="Modlist not found")

    if modlist.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your modlist")

    await db.execute(
        delete(ModlistKnowledgeFlag).where(ModlistKnowledgeFlag.modlist_id == ml_uuid)
    )
    await db.execute(
        delete(ModlistEntry).where(ModlistEntry.modlist_id == ml_uuid)
    )
    await db.delete(modlist)
    await db.commit()


@router.get("/{modlist_id}/export", response_model=ModlistExportResponse)
async def export_modlist(
    modlist_id: str,
    nexus_api_key: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Export modlist for MO2 plugin with optional file_id resolution.

    If nexus_api_key is provided, resolves the primary file_id for each
    mod via the Nexus Mods API. Otherwise, entries are returned without
    file_ids — the plugin can resolve them locally.
    """
    try:
        ml_uuid = uuid.UUID(modlist_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid modlist ID")

    modlist = await db.get(Modlist, ml_uuid)
    if not modlist:
        raise HTTPException(status_code=404, detail="Modlist not found")

    game = await db.get(Game, modlist.game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    entry_result = await db.execute(
        select(ModlistEntry)
        .where(ModlistEntry.modlist_id == ml_uuid)
        .order_by(ModlistEntry.load_order)
    )
    db_entries = entry_result.scalars().all()

    # Optionally resolve file_ids via Nexus API
    file_id_map: dict[int, int | None] = {}
    if nexus_api_key:
        client = NexusModsClient(nexus_api_key)

        async def resolve_file_id(nexus_mod_id: int) -> tuple[int, int | None]:
            try:
                files = await client.get_mod_files(game.nexus_domain, nexus_mod_id)
                if files:
                    primary = next((f for f in files if f.get("isPrimary")), files[0])
                    return nexus_mod_id, primary.get("fileId")
            except Exception:
                logger.warning(f"Failed to resolve file_id for mod {nexus_mod_id}")
            return nexus_mod_id, None

        nexus_ids = [e.nexus_mod_id for e in db_entries if e.nexus_mod_id]
        results = await asyncio.gather(
            *(resolve_file_id(mid) for mid in nexus_ids)
        )
        file_id_map = dict(results)

    entries = [
        ExportModEntry(
            nexus_mod_id=e.nexus_mod_id,
            file_id=file_id_map.get(e.nexus_mod_id) if e.nexus_mod_id else None,
            name=e.name or "Unknown",
            author=e.author,
            load_order=e.load_order,
            is_patch=e.is_patch,
            patches_mods=e.patches_mods,
        )
        for e in db_entries
    ]

    return ModlistExportResponse(
        id=modlist.id,
        game_domain=game.nexus_domain,
        game_name=game.name,
        mod_count=len(entries),
        entries=entries,
    )


@router.get("/{modlist_id}", response_model=ModlistResponse)
async def get_modlist(modlist_id: str, db: AsyncSession = Depends(get_db)):
    """Get a previously generated modlist by ID."""
    try:
        ml_uuid = uuid.UUID(modlist_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid modlist ID")

    modlist = await db.get(Modlist, ml_uuid)
    if not modlist:
        raise HTTPException(status_code=404, detail="Modlist not found")

    # Load entries — use denormalized fields directly
    entry_result = await db.execute(
        select(ModlistEntry)
        .where(ModlistEntry.modlist_id == ml_uuid)
        .order_by(ModlistEntry.load_order)
    )
    entries = [_entry_to_schema(e) for e in entry_result.scalars().all()]

    # Load knowledge flags
    flag_result = await db.execute(
        select(ModlistKnowledgeFlag)
        .where(ModlistKnowledgeFlag.modlist_id == ml_uuid)
    )
    flags = [_flag_to_schema(f) for f in flag_result.scalars().all()]

    return ModlistResponse(
        id=modlist.id,
        game_id=modlist.game_id,
        playstyle_id=modlist.playstyle_id,
        entries=entries,
        llm_provider=modlist.llm_provider,
        user_knowledge_flags=flags,
        used_fallback=modlist.llm_provider == "fallback",
    )
