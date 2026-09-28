"""FastAPI application entrypoint.

Wires together config, logging, the database, and all routers. Also
exposes /api/system/health as a liveness endpoint for the API itself --
distinct from the network health checks the app runs against monitored
hosts (see routers/checks.py for those).
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.logging_config import get_logger, setup_logging
from app.routers import alerts, checks, dashboard, hosts, scans

setup_logging(level=settings.log_level, json_format=settings.log_json)
logger = get_logger("dashboard.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up: ensuring database schema exists")
    init_db()
    yield
    logger.info("Shutting down")


app = FastAPI(
    title="Network Troubleshooting & Security Dashboard",
    description=(
        "Authorized-only network diagnostics, Nmap-based service discovery, "
        "and issue detection for hosts you own or are explicitly authorized "
        "to test. See /docs for interactive API documentation."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(hosts.router)
app.include_router(checks.router)
app.include_router(scans.router)
app.include_router(alerts.router)
app.include_router(dashboard.router)


@app.get("/api/system/health", tags=["system"])
def system_health() -> dict[str, str]:
    """Liveness check for the API process itself."""
    return {"status": "ok"}
