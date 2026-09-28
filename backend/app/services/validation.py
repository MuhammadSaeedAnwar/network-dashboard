"""Validation for scan/diagnostic targets.

This module is the project's main safety boundary for the "only scan what
you're authorized to touch" requirement. It enforces:

1. A target must be a single host (IP or hostname) -- never a CIDR range,
   wildcard, or list. This bounds the blast radius of a mistake: you can
   register and scan one box at a time, never "10.0.0.0/8".
2. The string must match a strict IP or hostname pattern. Nmap and other
   tools are always invoked with argv lists (never shell=True and never a
   user string interpolated into a shell command), so this isn't primarily
   an injection defense -- it's a defense against typos/mistakes turning
   into scans of something unintended (e.g. a stray space or flag-looking
   string being misread as a target).

Authorization itself (the "do you actually own this host" question) is
enforced at the API layer via the two required boolean acknowledgments in
schemas.py -- this module cannot verify real-world ownership, and neither
can any piece of software; it can only make it structurally hard to scan
something without deliberately saying "yes, I'm authorized" twice.
"""

from __future__ import annotations

import ipaddress
import re

_HOSTNAME_RE = re.compile(
    r"^(?=.{1,253}$)(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))*$"
)


class ValidationError(ValueError):
    """Raised when a target fails safety validation."""


def validate_single_target(address: str) -> str:
    """Validate that `address` is a single IP address or hostname.

    Returns the (trimmed) address on success, raises ValidationError
    otherwise. Never raises on a legitimate single host -- only rejects
    ranges, wildcards, and malformed input.
    """
    address = address.strip()
    if not address:
        raise ValidationError("Target address cannot be empty.")

    if "/" in address:
        raise ValidationError(
            "CIDR ranges are not allowed. This tool only supports scanning "
            "a single, individually-authorized host at a time."
        )

    if any(char in address for char in [" ", ";", "|", "&", "$", "`", "\n", "\r", "*"]):
        raise ValidationError("Target address contains characters that are not allowed.")

    # Try as an IP address first (covers both IPv4 and IPv6).
    try:
        ipaddress.ip_address(address)
        return address
    except ValueError:
        pass

    # Fall back to hostname validation.
    if _HOSTNAME_RE.match(address):
        return address

    raise ValidationError(
        f"'{address}' is not a valid single IP address or hostname."
    )
