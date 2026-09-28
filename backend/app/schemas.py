"""Pydantic schemas for request validation and API responses."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.services.validation import ValidationError, validate_single_target


# ---------- Hosts ----------

class HostCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    address: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    expected_ports: list[int] | None = None
    expected_http_url: str | None = None
    latency_warning_ms: float | None = Field(None, gt=0)
    authorized_confirmation: bool = Field(
        ...,
        description=(
            "Must be true. By setting this you confirm you own this host or "
            "have explicit written authorization to test it."
        ),
    )

    @field_validator("address")
    @classmethod
    def validate_address(cls, v: str) -> str:
        try:
            validate_single_target(v)
        except ValidationError as exc:
            raise ValueError(str(exc)) from exc
        return v

    @field_validator("expected_ports")
    @classmethod
    def validate_ports(cls, v: list[int] | None) -> list[int] | None:
        if v is None:
            return v
        for port in v:
            if not (0 < port <= 65535):
                raise ValueError(f"Invalid port number: {port}")
        return v

    @field_validator("authorized_confirmation")
    @classmethod
    def must_confirm_authorization(cls, v: bool) -> bool:
        if v is not True:
            raise ValueError(
                "authorized_confirmation must be true. This tool may only be used against "
                "hosts you own or are explicitly authorized to test."
            )
        return v


class HostResponse(BaseModel):
    id: int
    name: str
    address: str
    description: str | None
    authorized: bool
    expected_ports: list[int] | None
    expected_http_url: str | None
    latency_warning_ms: float | None
    created_at: datetime

    model_config = {"from_attributes": True}


class HostSummary(HostResponse):
    """Host plus a rollup of its latest status, for the dashboard list view."""

    latest_status: str  # ok|warning|critical|unknown
    latest_latency_ms: float | None
    open_port_count: int | None
    open_alert_count: int
    last_checked_at: datetime | None


# ---------- Health checks ----------

class HealthCheckResponse(BaseModel):
    id: int
    host_id: int
    check_type: str
    target: str
    success: bool
    status: str
    detail: str
    latency_ms: float | None
    checked_at: datetime

    model_config = {"from_attributes": True}


class RunChecksResponse(BaseModel):
    host_id: int
    results: list[HealthCheckResponse]
    alerts_raised: int


# ---------- Scans ----------

class ScanRequest(BaseModel):
    top_ports: int | None = Field(None, gt=0, le=1000)
    authorization_ack: bool = Field(
        ...,
        description=(
            "Must be true for every scan request. Confirms you are authorized "
            "to run this scan against this specific host, right now."
        ),
    )

    @field_validator("authorization_ack")
    @classmethod
    def must_ack(cls, v: bool) -> bool:
        if v is not True:
            raise ValueError(
                "authorization_ack must be true for every scan. You must confirm "
                "authorization each time a scan is run, not just when the host was added."
            )
        return v


class PortResponse(BaseModel):
    id: int
    port_number: int
    protocol: str
    state: str
    service_name: str | None
    service_product: str | None
    service_version: str | None

    model_config = {"from_attributes": True}


class ScanResponse(BaseModel):
    id: int
    host_id: int
    target: str
    status: str
    top_ports: int
    error_detail: str | None
    started_at: datetime
    completed_at: datetime | None
    ports: list[PortResponse] = []

    model_config = {"from_attributes": True}


# ---------- Alerts ----------

class AlertResponse(BaseModel):
    id: int
    host_id: int
    source: str
    severity: str
    message: str
    resolved: bool
    raised_at: datetime

    model_config = {"from_attributes": True}


# ---------- Dashboard ----------

class DashboardSummary(BaseModel):
    total_hosts: int
    hosts_ok: int
    hosts_warning: int
    hosts_critical: int
    hosts_unknown: int
    open_alerts: int
    total_scans: int
