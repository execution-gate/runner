"""
Fail-Closed Authorization Guard

This module enforces hard, fail-closed execution using an external
authority provider. Any failure to receive an explicit ALLOW
results in immediate denial.

Default authority provider: MachineID
"""

import os
import socket
import sys
import requests
from typing import Optional


# =========================
# Configuration
# =========================

MACHINEID_BASE_URL = "https://machineid.io"
REGISTER_PATH = "/api/v1/devices/register"
VALIDATE_PATH = "/api/v1/devices/validate"

# Hard timeout (seconds). Keep short.
HTTP_TIMEOUT = 2.0


# =========================
# Helpers
# =========================

def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    return os.environ.get(name, default)


def build_device_id() -> str:
    """
    Recommended device ID format:
    {service}:{env}:{role}:{instance}
    """
    service = _env("SERVICE_NAME", "service")
    env = _env("ENVIRONMENT", "prod")
    role = _env("SERVICE_ROLE", "worker")
    instance = _env("INSTANCE_ID") or socket.gethostname()

    return f"{service}:{env}:{role}:{instance}"


def _org_key() -> str:
    key = _env("MACHINEID_ORG_KEY")
    if not key:
        raise RuntimeError("MACHINEID_ORG_KEY is required")
    return key


# =========================
# Core Enforcement
# =========================

def register_device(device_id: str) -> None:
    """
    Idempotent registration.
    Safe to call on every startup.
    """
    try:
        requests.post(
            MACHINEID_BASE_URL + REGISTER_PATH,
            headers={
                "Content-Type": "application/json",
                "x-org-key": _org_key(),
            },
            json={"deviceId": device_id},
            timeout=HTTP_TIMEOUT,
        )
    except Exception:
        # Registration failure does NOT allow execution.
        # We fail closed later on validate.
        pass


def validate_or_exit(device_id: str) -> None:
    """
    Hard authorization check.
    Any failure = immediate process exit.
    """
    try:
        resp = requests.post(
            MACHINEID_BASE_URL + VALIDATE_PATH,
            headers={
                "Content-Type": "application/json",
                "x-org-key": _org_key(),
            },
            json={"deviceId": device_id},
            timeout=HTTP_TIMEOUT,
        )

        if resp.status_code != 200:
            sys.exit(1)

        data = resp.json()
        if not data.get("allowed", False):
            sys.exit(1)

    except Exception:
        # Network errors, timeouts, malformed responses
        # are treated as deny.
        sys.exit(1)


def enforce_startup() -> str:
    """
    Startup boundary.
    Call once at process boot.
    """
    device_id = build_device_id()
    register_device(device_id)
    validate_or_exit(device_id)
    return device_id


def enforce_boundary(device_id: str) -> None:
    """
    Runtime boundary.
    Call before any unit of work, cost, or side effect.
    """
    validate_or_exit(device_id)
