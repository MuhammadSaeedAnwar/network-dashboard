"""Turns raw diagnostic/scan results into alert-worthy findings.

Kept intentionally simple (no dedupe window, no escalation, no
auto-resolve) -- documented as a limitation in the README rather than
half-built here.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.services.network_checks import CheckResult
from app.services.nmap_scanner import ParsedPort


@dataclass
class AlertDraft:
    severity: str  # warning|critical
    message: str


def alerts_from_health_checks(
    results: list[CheckResult], latency_warning_ms: float
) -> list[AlertDraft]:
    drafts: list[AlertDraft] = []

    for r in results:
        if r.check_type == "dns" and not r.success:
            drafts.append(AlertDraft("critical", f"DNS resolution failed for {r.target}: {r.detail}"))

        elif r.check_type == "ping":
            if not r.success:
                drafts.append(AlertDraft("critical", f"Host {r.target} is unreachable: {r.detail}"))
            elif r.latency_ms is not None and r.latency_ms > latency_warning_ms:
                drafts.append(
                    AlertDraft(
                        "warning",
                        f"High latency to {r.target}: {r.latency_ms:.1f} ms (threshold {latency_warning_ms:.0f} ms)",
                    )
                )

        elif r.check_type == "http" and not r.success:
            severity = "critical" if r.status == "critical" else "warning"
            drafts.append(AlertDraft(severity, f"HTTP health check failed for {r.target}: {r.detail}"))

    return drafts


def alerts_from_scan(
    ports: list[ParsedPort], expected_ports: list[int] | None
) -> list[AlertDraft]:
    """Compare scan results against a host's expected port allow-list.

    Only runs the "unexpected port" and "expected port missing" checks
    when the host actually has an expected_ports list configured --
    without one, there's no baseline to compare against, so nothing is
    flagged (this is intentional: it avoids false positives on hosts the
    user hasn't characterized yet).
    """
    drafts: list[AlertDraft] = []
    open_ports = [p for p in ports if p.state == "open"]
    open_port_numbers = {p.port_number for p in open_ports}

    if expected_ports is not None:
        expected_set = set(expected_ports)

        missing = expected_set - open_port_numbers
        for port in sorted(missing):
            drafts.append(AlertDraft("critical", f"Expected port {port} was not found open in the latest scan."))

        unexpected = open_port_numbers - expected_set
        for port in sorted(unexpected):
            match = next((p for p in open_ports if p.port_number == port), None)
            service = f" ({match.service_name})" if match and match.service_name else ""
            drafts.append(AlertDraft("warning", f"Unexpected open port {port}{service} found in latest scan."))

    return drafts
