import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.api import specs, games, modlist, downloads, settings
from app.config import get_settings
from app.database import engine, async_session, Base

logger = logging.getLogger(__name__)

app_settings = get_settings()


async def init_db():
    """Create tables and seed data if empty."""
    from app.models import Game  # noqa: F811 — ensure all models are imported
    import app.models  # noqa: F401 — register all models with Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created/verified.")

    async with async_session() as session:
        result = await session.execute(select(Game).limit(1))
        if result.scalar_one_or_none() is None:
            logger.info("Database empty — running seed...")
            from app.seeds.run_seed import main as run_seed
            await run_seed()
            logger.info("Seed complete.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await init_db()
    except Exception:
        logger.exception("Database init failed — app will start without data")
    yield


app = FastAPI(
    title="Modify API",
    description="AI-powered video game mod manager API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in app_settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(specs.router, prefix="/api/specs", tags=["specs"])
app.include_router(games.router, prefix="/api/games", tags=["games"])
app.include_router(modlist.router, prefix="/api/modlist", tags=["modlist"])
app.include_router(downloads.router, prefix="/api/downloads", tags=["downloads"])
app.include_router(settings.router, prefix="/api/settings", tags=["settings"])


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "app": app_settings.app_name}
