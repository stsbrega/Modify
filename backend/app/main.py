import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select, text

from app.api import specs, games, modlist, downloads, settings, auth, stats
from app.config import get_settings
from app.database import engine, async_session, Base

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app_settings = get_settings()

# Track whether DB init succeeded
_db_ready = False


async def init_db():
    """Create tables and seed data if empty."""
    global _db_ready
    from app.models import Game  # noqa: F811 — ensure all models are imported
    import app.models  # noqa: F401 — register all models with Base

    # Log connection info (mask password)
    db_url = str(engine.url)
    masked = db_url.split("@")[-1] if "@" in db_url else db_url
    logger.info(f"Connecting to database: ...@{masked}")

    async with engine.begin() as conn:
        # Test raw connectivity first
        await conn.execute(text("SELECT 1"))
        logger.info("Database connection successful.")
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created/verified.")

    async with async_session() as session:
        result = await session.execute(select(Game).limit(1))
        if result.scalar_one_or_none() is None:
            logger.info("Database empty — running seed...")
            from app.seeds.run_seed import main as run_seed
            await run_seed()
            logger.info("Seed complete.")

    _db_ready = True


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

# Parse CORS origins and log them
cors_origins = [o.strip() for o in app_settings.cors_origins.split(",") if o.strip()]
logger.info(f"CORS origins: {cors_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled error on {request.method} {request.url.path}")
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {type(exc).__name__}"},
    )


app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(specs.router, prefix="/api/specs", tags=["specs"])
app.include_router(games.router, prefix="/api/games", tags=["games"])
app.include_router(modlist.router, prefix="/api/modlist", tags=["modlist"])
app.include_router(downloads.router, prefix="/api/downloads", tags=["downloads"])
app.include_router(settings.router, prefix="/api/settings", tags=["settings"])
app.include_router(stats.router, prefix="/api/stats", tags=["stats"])


@app.get("/api/health")
async def health_check():
    db_status = "unknown"
    if _db_ready:
        try:
            async with async_session() as session:
                await session.execute(text("SELECT 1"))
            db_status = "connected"
        except Exception as e:
            db_status = f"error: {type(e).__name__}"
    else:
        db_status = "init_failed"

    return {
        "status": "ok",
        "app": app_settings.app_name,
        "db_ready": _db_ready,
        "db_status": db_status,
    }
