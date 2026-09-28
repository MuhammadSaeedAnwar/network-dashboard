"""Running and listing network diagnostic checks for a host."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.logging_config import get_logger
from app.models import Alert, HealthCheck, Host
from app.schemas import HealthCheckResponse, RunChecksResponse
from app.services import issue_detection
from app.services.network_checks import run_standard_checks

router = APIRouter(prefix="/api/hosts/{host_id}/checks", tags=["checks"])
logger = get_logger("dashboard.checks")


@router.post("/run", response_model=RunChecksResponse)
def run_checks(host_id: int, db: Session = Depends(get_db)) -> RunChecksResponse:
    host = db.get(Host, host_id)
    if host is None:
        raise HTTPException(status_code=404, detail="Host not found")

    results = run_standard_checks(
        address=host.address,
        http_url=host.expected_http_url,
        ping_count=settings.ping_count,
        ping_timeout_seconds=settings.ping_timeout_seconds,
        http_timeout_seconds=settings.http_timeout_seconds,
        traceroute_timeout_seconds=settings.traceroute_timeout_seconds,
    )

    stored: list[HealthCheck] = []
    for r in results:
        record = HealthCheck(
            host_id=host.id,
            check_type=r.check_type,
            target=r.target,
            success=r.success,
            status=r.status,
            detail=r.detail,
            latency_ms=r.latency_ms,
        )
        db.add(record)
        stored.append(record)

    latency_threshold = host.latency_warning_ms or settings.ping_latency_warning_ms
    drafts = issue_detection.alerts_from_health_checks(results, latency_threshold)
    for draft in drafts:
        db.add(Alert(host_id=host.id, source="health_check", severity=draft.severity, message=draft.message))

    db.commit()
    for record in stored:
        db.refresh(record)

    logger.info(f"Ran {len(results)} checks for host_id={host_id}, {len(drafts)} alerts raised")
    return RunChecksResponse(
        host_id=host.id,
        results=[HealthCheckResponse.model_validate(r) for r in stored],
        alerts_raised=len(drafts),
    )


@router.get("", response_model=list[HealthCheckResponse])
def list_checks(host_id: int, limit: int = 50, db: Session = Depends(get_db)) -> list[HealthCheck]:
    host = db.get(Host, host_id)
    if host is None:
        raise HTTPException(status_code=404, detail="Host not found")

    return list(
        db.execute(
            select(HealthCheck)
            .where(HealthCheck.host_id == host_id)
            .order_by(HealthCheck.checked_at.desc())
            .limit(limit)
        ).scalars()
    )
