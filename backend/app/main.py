import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import init_db
from app.core.scheduler import start_scheduler, stop_scheduler, collect_and_parse_job
from app.api import health, requests, errors, dashboard, integration

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting LogAnalyzer...")
    init_db()

    # 초기 수집 실행
    await collect_and_parse_job()

    start_scheduler()
    logger.info("LogAnalyzer started successfully")

    yield

    logger.info("Shutting down LogAnalyzer...")
    stop_scheduler()
    logger.info("LogAnalyzer shut down")


settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

cors_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(requests.router, prefix="/api", tags=["requests"])
app.include_router(errors.router, prefix="/api", tags=["errors"])
app.include_router(dashboard.router, prefix="/api", tags=["dashboard"])
app.include_router(integration.router, prefix="/api", tags=["integration"])
