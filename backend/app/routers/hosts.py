"""CRUD for monitored hosts."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.logging_config import get_logger
from app.models import Alert, HealthCheck, Host, Scan
from app.schemas import HostCreate, HostResponse, HostSummary

router = APIRouter(prefix="/api/hosts", tags=["hosts"])
logger = get_logger("dashboard.hosts")


@router.post("", response_model=HostResponse, status_code=201)
def create_host(payload: HostCreate, db: Session = Depends(get_db)) -> Host:
    host = Host(
        name=payload.name,
        address=payload.address,
        description=payload.description,
        authorized=True,  # only reachable if HostCreate's validator already accepted `True`
        expected_ports=payload.expected_ports,
        expected_http_url=payload.expected_http_url,
        latency_warning_ms=payload.latency_warning_ms,
    )
    db.add(host)
    db.commit()
    db.refresh(host)
    logger.info(f"Host created: id={host.id} address={host.address}")
    return host


@router.get("", response_model=list[HostSummary])
def list_hosts(db: Session = Depends(get_db)) -> list[HostSummary]:
    hosts = db.execute(select(Host)).scalars().all()
    summaries: list[HostSummary] = []

    for host in hosts:
        latest_check = db.execute(
            select(HealthCheck)
            .where(HealthCheck.host_id == host.id)
            .order_by(HealthCheck.checked_at.desc())
            .limit(1)
        ).scalar_one_or_none()

        latest_scan = db.execute(
            select(Scan)
            .where(Scan.host_id == host.id, Scan.status == "completed")
            .order_by(Scan.started_at.desc())
            .limit(1)
        ).scalar_one_or_none()

        open_port_count = None
        if latest_scan is not None:
            open_port_count = sum(1 for p in latest_scan.ports if p.state == "open")

        open_alert_count = db.execute(
            select(func.count()).select_from(Alert).where(Alert.host_id == host.id, Alert.resolved.is_(False))
        ).scalar_one()

        summaries.append(
            HostSummary(
                id=host.id,
                name=host.name,
                address=host.address,
                description=host.description,
                authorized=host.authorized,
                expected_ports=host.expected_ports,
                expected_http_url=host.expected_http_url,
                latency_warning_ms=host.latency_warning_ms,
                created_at=host.created_at,
                latest_status=latest_check.status if latest_check else "unknown",
                latest_latency_ms=latest_check.latency_ms if latest_check else None,
                open_port_count=open_port_count,
                open_alert_count=open_alert_count,
                last_checked_at=latest_check.checked_at if latest_check else None,
            )
        )

    return summaries


@router.get("/{host_id}", response_model=HostResponse)
def get_host(host_id: int, db: Session = Depends(get_db)) -> Host:
    host = db.get(Host, host_id)
    if host is None:
        raise HTTPException(status_code=404, detail="Host not found")
    return host


@router.delete("/{host_id}", status_code=204)
def delete_host(host_id: int, db: Session = Depends(get_db)) -> None:
    host = db.get(Host, host_id)
    if host is None:
        raise HTTPException(status_code=404, detail="Host not found")
    db.delete(host)
    db.commit()
    logger.info(f"Host deleted: id={host_id}")
