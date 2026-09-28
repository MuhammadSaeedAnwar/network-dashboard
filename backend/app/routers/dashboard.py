"""Aggregated dashboard overview endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Alert, HealthCheck, Host, Scan
from app.schemas import DashboardSummary

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def dashboard_summary(db: Session = Depends(get_db)) -> DashboardSummary:
    hosts = db.execute(select(Host)).scalars().all()

    counts = {"ok": 0, "warning": 0, "critical": 0, "unknown": 0}
    for host in hosts:
        latest_check = db.execute(
            select(HealthCheck)
            .where(HealthCheck.host_id == host.id)
            .order_by(HealthCheck.checked_at.desc())
            .limit(1)
        ).scalar_one_or_none()
        status = latest_check.status if latest_check else "unknown"
        counts[status] = counts.get(status, 0) + 1

    open_alerts = db.execute(
        select(func.count()).select_from(Alert).where(Alert.resolved.is_(False))
    ).scalar_one()

    total_scans = db.execute(select(func.count()).select_from(Scan)).scalar_one()

    return DashboardSummary(
        total_hosts=len(hosts),
        hosts_ok=counts.get("ok", 0),
        hosts_warning=counts.get("warning", 0),
        hosts_critical=counts.get("critical", 0),
        hosts_unknown=counts.get("unknown", 0),
        open_alerts=open_alerts,
        total_scans=total_scans,
    )
