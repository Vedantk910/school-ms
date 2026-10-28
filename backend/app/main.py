"""FastAPI application factory for School-MS."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import create_all
from app.routers import (
    admin, ai, attendance, auth, comms, events, exams, fees,
    library, staff, students, timetable, transport,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Dev convenience: ensure schema exists. Production uses Alembic in compose.
    create_all()
    # Keep create_all-built DBs migration-consistent (stamp head if unmanaged).
    from app.db import engine
    from app.migrate import ensure_schema
    try:
        ensure_schema(engine)
    except Exception:
        pass  # never block startup on the stamp
    yield


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(students.router, prefix="/api/v1")
    app.include_router(attendance.router, prefix="/api/v1")
    app.include_router(fees.router, prefix="/api/v1")
    app.include_router(exams.router, prefix="/api/v1")
    app.include_router(events.router, prefix="/api/v1")
    app.include_router(transport.router, prefix="/api/v1")
    app.include_router(library.router, prefix="/api/v1")
    app.include_router(staff.router, prefix="/api/v1")
    app.include_router(timetable.router, prefix="/api/v1")
    app.include_router(comms.router, prefix="/api/v1")
    app.include_router(ai.router, prefix="/api/v1")
    app.include_router(admin.router, prefix="/api/v1")

    @app.get("/healthz", tags=["meta"])
    def healthz() -> dict:
        return {"status": "ok", "app": settings.app_name}

    return app


app = create_app()
