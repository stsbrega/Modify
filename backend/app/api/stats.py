import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.modlist import Modlist
from app.models.game import Game
from app.schemas.stats import StatsResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=StatsResponse)
async def get_stats(db: AsyncSession = Depends(get_db)):
    """Public stats for the landing page."""
    try:
        modlist_result = await db.execute(select(func.count()).select_from(Modlist))
        modlists_generated = modlist_result.scalar_one()

        games_result = await db.execute(select(func.count()).select_from(Game))
        games_supported = games_result.scalar_one()

        return StatsResponse(
            modlists_generated=modlists_generated,
            games_supported=games_supported,
        )
    except Exception as e:
        logger.exception("Failed to query stats")
        raise HTTPException(
            status_code=503, detail=f"Database unavailable: {type(e).__name__}"
        )
