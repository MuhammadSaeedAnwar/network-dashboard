"""Optional, best-effort packet capture summary via tshark.

This is intentionally the most restricted piece of the project:
  - Disabled by default (ENABLE_PACKET_CAPTURE=false in .env).
  - Only ever captures traffic to/from one already-authorized host
    (BPF filter "host <ip>"), never a general capture.
  - Fixed duration and packet-count ceiling from config -- never
    user-controlled per request.
  - Requires the tshark binary and (on most systems) elevated
    privileges/capabilities to open a capture interface; if either is
    missing, this reports "unavailable" rather than failing loudly,
    matching the rest of the toolkit's graceful-degradation pattern.

It produces a coarse protocol breakdown only (counts by top-level
protocol), not packet contents -- this is meant to demonstrate the
integration exists and is safely bounded, not to be a Wireshark
replacement.
"""

from __future__ import annotations

import shutil
import subprocess
from collections import Counter
from dataclasses import dataclass, field


@dataclass
class CaptureSummary:
    available: bool
    protocol_counts: dict[str, int] = field(default_factory=dict)
    packet_count: int = 0
    detail: str = ""


def tshark_available() -> bool:
    return shutil.which("tshark") is not None


def capture_summary(
    target_ip: str,
    interface: str,
    duration_seconds: int,
    max_packets: int,
) -> CaptureSummary:
    if not tshark_available():
        return CaptureSummary(available=False, detail="tshark is not installed on this system.")

    cmd = [
        "tshark",
        "-i", interface,
        "-a", f"duration:{duration_seconds}",
        "-c", str(max_packets),
        "-f", f"host {target_ip}",
        "-T", "fields",
        "-e", "frame.protocols",
    ]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=duration_seconds + 15
        )
    except subprocess.TimeoutExpired:
        return CaptureSummary(available=False, detail="tshark capture timed out.")
    except PermissionError:
        return CaptureSummary(
            available=False,
            detail="Permission denied opening a capture interface (tshark usually needs root or CAP_NET_RAW).",
        )

    if result.returncode != 0:
        return CaptureSummary(
            available=False,
            detail=f"tshark exited with code {result.returncode}: {result.stderr.strip()[:300]}",
        )

    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    counts: Counter[str] = Counter()
    for line in lines:
        protocols = line.split(":")
        top_protocol = protocols[-1] if protocols else "unknown"
        counts[top_protocol] += 1

    return CaptureSummary(
        available=True,
        protocol_counts=dict(counts),
        packet_count=len(lines),
        detail=f"Captured {len(lines)} packets to/from {target_ip} over {duration_seconds}s.",
    )
