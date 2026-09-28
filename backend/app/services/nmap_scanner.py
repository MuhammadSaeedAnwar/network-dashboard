"""Nmap integration: runs a basic TCP service-discovery scan against a
single, already-validated, already-authorized target and parses the
XML output.

Deliberately excluded, by design (see README security section):
  - OS fingerprinting (-O)
  - Aggressive/vuln scripts (--script vuln, -A)
  - SYN scanning (-sS) -- uses -sT (TCP connect) so it never needs root
  - UDP scanning (-sU) -- much slower and noisier, out of scope here
  - Any user-supplied flags -- the argv list is fully fixed by this code

This is a "safe/basic service discovery scan" as scoped in the project
brief, not a general-purpose Nmap wrapper.
"""

from __future__ import annotations

import shutil
import subprocess
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field


class NmapNotAvailableError(RuntimeError):
    """Raised when the nmap binary isn't installed on this system."""


@dataclass
class ParsedPort:
    port_number: int
    protocol: str
    state: str
    service_name: str | None
    service_product: str | None
    service_version: str | None


@dataclass
class ScanOutcome:
    success: bool
    ports: list[ParsedPort] = field(default_factory=list)
    error_detail: str | None = None


def nmap_available() -> bool:
    return shutil.which("nmap") is not None


def run_nmap_scan(
    target: str,
    top_ports: int,
    timeout_seconds: int,
    expected_ports: list[int] | None = None,
) -> ScanOutcome:
    """Run Nmap top-port discovery and optionally verify expected ports.

    The target must already have passed validate_single_target(). For Docker
    local testing, loopback targets are mapped to the host gateway so Nmap
    scans the machine hosting the containers rather than the backend itself.
    """
    if not nmap_available():
        raise NmapNotAvailableError(
            "nmap is not installed on this system. Install it with "
            "'sudo apt install nmap' (see README)."
        )

    scan_target = "host.docker.internal" if target in {"127.0.0.1", "localhost"} else target

    def run_command(cmd: list[str]) -> ScanOutcome:
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout_seconds
            )
        except subprocess.TimeoutExpired:
            return ScanOutcome(
                success=False,
                error_detail=f"nmap scan timed out after {timeout_seconds}s",
            )

        if result.returncode != 0:
            return ScanOutcome(
                success=False,
                error_detail=(
                    f"nmap exited with code {result.returncode}: "
                    f"{result.stderr.strip()[:500]}"
                ),
            )

        try:
            ports = _parse_xml(result.stdout)
        except ET.ParseError as exc:
            return ScanOutcome(
                success=False,
                error_detail=f"Failed to parse nmap XML output: {exc}",
            )

        return ScanOutcome(success=True, ports=ports)

    top_cmd = [
        "nmap", "-sT", "-T3", "--top-ports", str(top_ports),
        "-oX", "-", scan_target,
    ]
    top_outcome = run_command(top_cmd)

    if not top_outcome.success:
        return top_outcome

    if not expected_ports:
        return top_outcome

    unique_expected = sorted(set(expected_ports))
    expected_cmd = [
        "nmap", "-sT", "-T3",
        "-p", ",".join(str(port) for port in unique_expected),
        "-oX", "-", scan_target,
    ]
    expected_outcome = run_command(expected_cmd)

    if not expected_outcome.success:
        return expected_outcome

    merged: dict[tuple[str, int], ParsedPort] = {
        (port.protocol, port.port_number): port
        for port in top_outcome.ports
    }
    for port in expected_outcome.ports:
        merged[(port.protocol, port.port_number)] = port

    return ScanOutcome(success=True, ports=list(merged.values()))


def _parse_xml(xml_text: str) -> list[ParsedPort]:
    root = ET.fromstring(xml_text)
    ports: list[ParsedPort] = []

    for host_el in root.findall("host"):
        ports_el = host_el.find("ports")
        if ports_el is None:
            continue
        for port_el in ports_el.findall("port"):
            port_number = int(port_el.get("portid", "0"))
            protocol = port_el.get("protocol", "tcp")

            state_el = port_el.find("state")
            state = state_el.get("state", "unknown") if state_el is not None else "unknown"

            service_el = port_el.find("service")
            service_name = service_el.get("name") if service_el is not None else None
            service_product = service_el.get("product") if service_el is not None else None
            service_version = service_el.get("version") if service_el is not None else None

            ports.append(
                ParsedPort(
                    port_number=port_number,
                    protocol=protocol,
                    state=state,
                    service_name=service_name,
                    service_product=service_product,
                    service_version=service_version,
                )
            )

    return ports
