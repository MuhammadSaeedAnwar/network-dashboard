"""Listing and resolving alerts raised by health checks and scans."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.logging_config import get_logger
from app.models import Alert
from app.schemas import AlertResponse

router = APIRouter(prefix="/api/alerts", tags=["alerts"])
logger = get_logger("dashboard.alerts")


@router.get("", response_model=list[AlertResponse])
def list_alerts(
    host_id: int | None = None,
    resolved: bool | None = None,
    severity: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> list[Alert]:
    stmt = select(Alert)
    if host_id is not None:
        stmt = stmt.where(Alert.host_id == host_id)
    if resolved is not None:
        stmt = stmt.where(Alert.resolved.is_(resolved))
    if severity is not None:
        stmt = stmt.where(Alert.severity == severity)
    stmt = stmt.order_by(Alert.raised_at.desc()).limit(limit)
    return list(db.execute(stmt).scalars())


@router.post("/{alert_id}/resolve", response_model=AlertResponse)
def resolve_alert(alert_id: int, db: Session = Depends(get_db)) -> Alert:
    alert = db.get(Alert, alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.resolved = True
    db.commit()
    db.refresh(alert)
    logger.info(f"Alert resolved: id={alert_id}")
    return alert
