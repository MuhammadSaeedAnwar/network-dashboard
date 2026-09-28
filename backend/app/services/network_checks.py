"""Network diagnostics: DNS, ping, TCP port, HTTP, traceroute.

External commands (ping, traceroute) always use a fixed argv list via
subprocess -- never shell=True, never a string-built command -- so a
target string can never be interpreted as shell syntax.
"""

from __future__ import annotations

import shutil
import socket
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass


@dataclass
class CheckResult:
    check_type: str
    target: str
    success: bool
    status: str  # ok|warning|critical|unknown
    detail: str
    latency_ms: float | None


def check_dns(hostname: str) -> CheckResult:
    start = time.monotonic()
    try:
        socket.gethostbyname(hostname)
        elapsed_ms = (time.monotonic() - start) * 1000
        return CheckResult("dns", hostname, True, "ok", f"Resolved in {elapsed_ms:.1f} ms", elapsed_ms)
    except socket.gaierror as exc:
        return CheckResult("dns", hostname, False, "critical", f"DNS resolution failed: {exc}", None)


def check_ping(host: str, count: int = 3, timeout_seconds: int = 2) -> CheckResult:
    if shutil.which("ping") is None:
        return CheckResult("ping", host, False, "unknown", "'ping' binary not available on this system", None)

    cmd = ["ping", "-c", str(count), "-W", str(timeout_seconds), host]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_seconds * count + 5)
    except subprocess.TimeoutExpired:
        return CheckResult("ping", host, False, "critical", f"ping to {host} timed out", None)

    latency_ms = _parse_avg_latency(result.stdout)
    if result.returncode == 0:
        return CheckResult("ping", host, True, "ok", f"{count} packets sent, host reachable", latency_ms)
    return CheckResult(
        "ping", host, False, "critical",
        f"Host unreachable (exit code {result.returncode}): {result.stderr.strip() or result.stdout.strip()}",
        None,
    )


def _parse_avg_latency(ping_output: str) -> float | None:
    for line in ping_output.splitlines():
        if "min/avg/max" in line and "=" in line:
            try:
                stats = line.split("=")[1].strip().split()[0]
                return float(stats.split("/")[1])
            except (IndexError, ValueError):
                continue
    return None


def check_tcp_port(host: str, port: int, timeout_seconds: float = 3.0) -> CheckResult:
    label = f"{host}:{port}"
    start = time.monotonic()
    try:
        with socket.create_connection((host, port), timeout=timeout_seconds):
            elapsed_ms = (time.monotonic() - start) * 1000
            return CheckResult("tcp", label, True, "ok", f"Connected in {elapsed_ms:.1f} ms", elapsed_ms)
    except (socket.timeout, ConnectionRefusedError, OSError) as exc:
        return CheckResult("tcp", label, False, "critical", f"Could not connect: {exc}", None)


def check_http(url: str, expected_status: int = 200, timeout_seconds: float = 5.0) -> CheckResult:
    start = time.monotonic()
    try:
        req = urllib.request.Request(url, method="GET", headers={"User-Agent": "network-dashboard-healthcheck/1.0"})
        with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
            elapsed_ms = (time.monotonic() - start) * 1000
            status_code = resp.getcode()
            if status_code == expected_status:
                return CheckResult("http", url, True, "ok", f"HTTP {status_code} in {elapsed_ms:.1f} ms", elapsed_ms)
            return CheckResult(
                "http", url, False, "warning",
                f"Unexpected status {status_code}, expected {expected_status}", elapsed_ms,
            )
    except urllib.error.HTTPError as exc:
        return CheckResult("http", url, False, "warning", f"HTTP error {exc.code}: {exc.reason}", None)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return CheckResult("http", url, False, "critical", f"Request failed: {exc}", None)


def check_traceroute(host: str, timeout_seconds: int = 10) -> CheckResult:
    binary = shutil.which("traceroute") or shutil.which("tracepath")
    if binary is None:
        return CheckResult(
            "traceroute", host, False, "unknown",
            "Neither 'traceroute' nor 'tracepath' is installed on this system", None,
        )
    cmd = [binary, host]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_seconds)
        hop_count = max(0, len(result.stdout.strip().splitlines()) - 1)
        return CheckResult(
            "traceroute", host, result.returncode == 0,
            "ok" if result.returncode == 0 else "warning",
            f"{hop_count} hops recorded" if result.returncode == 0 else result.stderr.strip(),
            None,
        )
    except subprocess.TimeoutExpired:
        return CheckResult(
            "traceroute", host, False, "warning", f"traceroute timed out after {timeout_seconds}s", None
        )


def run_standard_checks(
    address: str,
    http_url: str | None,
    ping_count: int,
    ping_timeout_seconds: int,
    http_timeout_seconds: int,
    traceroute_timeout_seconds: int,
) -> list[CheckResult]:
    """Run the standard diagnostic set for a host: dns, ping, and
    optionally an http check if the host has an expected_http_url."""
    results = [
        check_dns(address),
        check_ping(address, count=ping_count, timeout_seconds=ping_timeout_seconds),
        check_traceroute(address, timeout_seconds=traceroute_timeout_seconds),
    ]
    if http_url:
        results.append(check_http(http_url, timeout_seconds=http_timeout_seconds))
    return results
