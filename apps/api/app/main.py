from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine
from app.config import settings
from app.auth import require_authenticated
from app.models.base import Base
from app.pipeline.queue import start_workers, stop_workers, set_pipeline_runner
from app.pipeline.runner import run_pipeline

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    set_pipeline_runner(run_pipeline)
    logger.info("AVCE API starting with USE_MOCKS=%s", settings.USE_MOCKS)
    await start_workers(num_workers=2)
    yield
    await stop_workers()


def create_app() -> FastAPI:
    app = FastAPI(
        title="AVCE API",
        description="ADA Visual Compliance Engine",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from app.routers import videos, jobs, captions, compliance, segments, export, auth
    protected = [Depends(require_authenticated)]
    app.include_router(auth.router)
    app.include_router(videos.router, dependencies=protected)
    app.include_router(jobs.router, dependencies=protected)
    app.include_router(captions.router, dependencies=protected)
    app.include_router(compliance.router, dependencies=protected)
    app.include_router(segments.router, dependencies=protected)
    app.include_router(export.router, dependencies=protected)

    @app.get("/health")
    def health_check():
        return {"status": "ok", "use_mocks": settings.USE_MOCKS}

    return app


app = create_app()
