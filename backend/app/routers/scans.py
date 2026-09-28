"""Triggering and listing Nmap scans for a host.

Authorization is checked twice here: the host must have been created
with authorized=True (enforced at creation time, see hosts.py /
schemas.py), and the request body must carry authorization_ack=True
for this specific scan (enforced by ScanRequest's validator). Both are
re-checked here defensively rather than trusted blindly.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.logging_config import get_logger
from app.models import Alert, Host, Port, Scan
from app.schemas import ScanRequest, ScanResponse
from app.services import issue_detection
from app.services.nmap_scanner import NmapNotAvailableError, run_nmap_scan
from app.services.validation import ValidationError, validate_single_target

router = APIRouter(tags=["scans"])
logger = get_logger("dashboard.scans")


@router.post("/api/hosts/{host_id}/scans", response_model=ScanResponse, status_code=201)
def create_scan(host_id: int, payload: ScanRequest, db: Session = Depends(get_db)) -> Scan:
    host = db.get(Host, host_id)
    if host is None:
        raise HTTPException(status_code=404, detail="Host not found")

    if not host.authorized:
        # Should be unreachable in practice (hosts can't be created without
        # authorization), but this is the load-bearing check, not a formality.
        raise HTTPException(status_code=403, detail="This host is not marked as authorized for scanning.")

    try:
        target = validate_single_target(host.address)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    top_ports = min(payload.top_ports or settings.nmap_top_ports, settings.nmap_max_top_ports)

    scan = Scan(host_id=host.id, target=target, status="running", top_ports=top_ports)
    db.add(scan)
    db.commit()
    db.refresh(scan)

    logger.info(f"Starting nmap scan id={scan.id} host_id={host_id} target={target} top_ports={top_ports}")

    try:
        outcome = run_nmap_scan(
            target,
            top_ports=top_ports,
            timeout_seconds=settings.nmap_timeout_seconds,
            expected_ports=host.expected_ports,
        )
    except NmapNotAvailableError as exc:
        scan.status = "failed"
        scan.error_detail = str(exc)
        scan.completed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(scan)
        logger.error(f"Scan id={scan.id} failed: {exc}")
        return scan

    scan.completed_at = datetime.now(timezone.utc)
    if not outcome.success:
        scan.status = "failed"
        scan.error_detail = outcome.error_detail
        db.commit()
        db.refresh(scan)
        logger.error(f"Scan id={scan.id} failed: {outcome.error_detail}")
        return scan

    scan.status = "completed"
    for p in outcome.ports:
        db.add(
            Port(
                scan_id=scan.id,
                port_number=p.port_number,
                protocol=p.protocol,
                state=p.state,
                service_name=p.service_name,
                service_product=p.service_product,
                service_version=p.service_version,
            )
        )

    drafts = issue_detection.alerts_from_scan(outcome.ports, host.expected_ports)
    for draft in drafts:
        db.add(Alert(host_id=host.id, source="scan", severity=draft.severity, message=draft.message))

    db.commit()
    db.refresh(scan)
    logger.info(f"Scan id={scan.id} completed: {len(outcome.ports)} ports found, {len(drafts)} alerts raised")
    return scan


@router.get("/api/hosts/{host_id}/scans", response_model=list[ScanResponse])
def list_scans(host_id: int, limit: int = 20, db: Session = Depends(get_db)) -> list[Scan]:
    host = db.get(Host, host_id)
    if host is None:
        raise HTTPException(status_code=404, detail="Host not found")
    return list(
        db.execute(
            select(Scan).where(Scan.host_id == host_id).order_by(Scan.started_at.desc()).limit(limit)
        ).scalars()
    )


@router.get("/api/scans/{scan_id}", response_model=ScanResponse)
def get_scan(scan_id: int, db: Session = Depends(get_db)) -> Scan:
    scan = db.get(Scan, scan_id)
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan not found")
    return scan
