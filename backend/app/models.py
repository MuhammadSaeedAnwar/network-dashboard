"""ORM models: hosts, health checks, scans, ports, alerts."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Host(Base):
    __tablename__ = "hosts"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Authorization gate #1: a host cannot be created without this being
    # explicitly true. See services/validation.py and the README security
    # section for the full authorization design.
    authorized: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Optional expectations used by issue detection.
    expected_ports: Mapped[list[int] | None] = mapped_column(JSON, nullable=True)
    expected_http_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    latency_warning_ms: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    health_checks: Mapped[list["HealthCheck"]] = relationship(
        back_populates="host", cascade="all, delete-orphan", order_by="HealthCheck.checked_at.desc()"
    )
    scans: Mapped[list["Scan"]] = relationship(
        back_populates="host", cascade="all, delete-orphan", order_by="Scan.started_at.desc()"
    )
    alerts: Mapped[list["Alert"]] = relationship(
        back_populates="host", cascade="all, delete-orphan", order_by="Alert.raised_at.desc()"
    )


class HealthCheck(Base):
    __tablename__ = "health_checks"

    id: Mapped[int] = mapped_column(primary_key=True)
    host_id: Mapped[int] = mapped_column(ForeignKey("hosts.id", ondelete="CASCADE"))
    check_type: Mapped[str] = mapped_column(String(20))  # ping|dns|tcp|http|traceroute
    target: Mapped[str] = mapped_column(String(255))
    success: Mapped[bool] = mapped_column(Boolean)
    status: Mapped[str] = mapped_column(String(20))  # ok|warning|critical|unknown
    detail: Mapped[str] = mapped_column(Text)
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    host: Mapped[Host] = relationship(back_populates="health_checks")


class Scan(Base):
    __tablename__ = "scans"

    id: Mapped[int] = mapped_column(primary_key=True)
    host_id: Mapped[int] = mapped_column(ForeignKey("hosts.id", ondelete="CASCADE"))
    target: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20))  # running|completed|failed
    top_ports: Mapped[int] = mapped_column(Integer)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    host: Mapped[Host] = relationship(back_populates="scans")
    ports: Mapped[list["Port"]] = relationship(back_populates="scan", cascade="all, delete-orphan")


class Port(Base):
    __tablename__ = "ports"

    id: Mapped[int] = mapped_column(primary_key=True)
    scan_id: Mapped[int] = mapped_column(ForeignKey("scans.id", ondelete="CASCADE"))
    port_number: Mapped[int] = mapped_column(Integer)
    protocol: Mapped[str] = mapped_column(String(10))  # tcp|udp
    state: Mapped[str] = mapped_column(String(20))  # open|closed|filtered
    service_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    service_product: Mapped[str | None] = mapped_column(String(200), nullable=True)
    service_version: Mapped[str | None] = mapped_column(String(100), nullable=True)

    scan: Mapped[Scan] = relationship(back_populates="ports")


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    host_id: Mapped[int] = mapped_column(ForeignKey("hosts.id", ondelete="CASCADE"))
    source: Mapped[str] = mapped_column(String(20))  # health_check|scan
    severity: Mapped[str] = mapped_column(String(20))  # warning|critical
    message: Mapped[str] = mapped_column(Text)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    raised_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    host: Mapped[Host] = relationship(back_populates="alerts")
