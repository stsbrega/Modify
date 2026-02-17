import logging

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.mod import Mod
from app.models.modlist import Modlist, ModlistEntry
from app.models.game import Game
from app.schemas.modlist import DownloadRequest, DownloadStatus
from app.services.download_manager import DownloadManager, DownloadTask

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory download managers per modlist
_download_managers: dict[str, DownloadManager] = {}


@router.post("/start", response_model=list[DownloadStatus])
async def start_downloads(
    request: DownloadRequest,
    db: AsyncSession = Depends(get_db),
):
    ml_id = str(request.modlist_id)

    # Load modlist with entries
    modlist = await db.get(Modlist, request.modlist_id)
    if not modlist:
        raise HTTPException(status_code=404, detail="Modlist not found")

    # Get game info for nexus domain
    game = await db.get(Game, modlist.game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    # Load entries with mod details
    query = (
        select(ModlistEntry, Mod)
        .outerjoin(Mod, ModlistEntry.mod_id == Mod.id)
        .where(ModlistEntry.modlist_id == request.modlist_id)
    )
    if request.mod_ids:
        query = query.where(ModlistEntry.mod_id.in_(request.mod_ids))

    result = await db.execute(query)

    # Create download manager
    manager = DownloadManager()
    statuses = []

    for entry, mod in result.all():
        if not mod or not mod.nexus_mod_id:
            continue

        task = DownloadTask(
            mod_id=mod.id,
            name=mod.name,
            game_domain=game.nexus_domain,
            nexus_mod_id=mod.nexus_mod_id,
        )
        manager.add_task(task)
        statuses.append(
            DownloadStatus(
                mod_id=mod.id,
                name=mod.name,
                status="pending",
                progress=0.0,
            )
        )

    _download_managers[ml_id] = manager

    # Start downloads in background (non-blocking)
    import asyncio
    asyncio.create_task(manager.start_downloads())

    return statuses


@router.get("/{modlist_id}/status", response_model=list[DownloadStatus])
async def get_download_status(modlist_id: str):
    manager = _download_managers.get(modlist_id)
    if not manager:
        return []

    return [
        DownloadStatus(
            mod_id=task.mod_id,
            name=task.name,
            status=task.status,
            progress=task.progress,
            error=task.error,
        )
        for task in manager.get_status()
    ]


@router.websocket("/{modlist_id}/ws")
async def download_websocket(websocket: WebSocket, modlist_id: str):
    """WebSocket endpoint for real-time download progress updates."""
    await websocket.accept()

    import asyncio

    try:
        while True:
            manager = _download_managers.get(modlist_id)
            if manager:
                statuses = [
                    {
                        "mod_id": task.mod_id,
                        "name": task.name,
                        "status": task.status,
                        "progress": task.progress,
                        "error": task.error,
                    }
                    for task in manager.get_status()
                ]
                await websocket.send_json({"type": "progress", "data": statuses})

                # Check if all downloads are complete
                all_done = all(
                    t.status in ("complete", "failed") for t in manager.get_status()
                )
                if all_done and manager.get_status():
                    await websocket.send_json({"type": "complete", "data": statuses})
                    break
            else:
                await websocket.send_json({"type": "waiting", "data": []})

            await asyncio.sleep(1)

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for modlist {modlist_id}")
