
"""
Fail-Closed Authorization Guard

This module enforces hard, fail-closed execution using an external
authority provider. Any failure to receive an explicit allowed:true
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


def _log(msg: str) -> None:
    # Minimal ops visibility (neutral, no marketing)
    sys.stderr.write(msg + "\n")
    sys.stderr.flush()


def _hard_exit() -> None:
    # OS-level termination (cannot be caught by try/except)
    os._exit(1)


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
        _log("authorization guard: missing MACHINEID_ORG_KEY")
        _hard_exit()
    return key


# =========================
# Core Enforcement
# =========================

def register_device(device_id: str) -> None:
    """
    Idempotent registration.
    Safe to call on every startup.

    Registration failure does NOT allow execution.
    We fail closed later on validate, but we log for visibility.
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
        _log("authorization guard: registration failed (non-fatal; validate will gate)")


def validate_or_exit(device_id: str) -> None:
    """
    Hard authorization check.
    Any failure = immediate termination (fail closed).
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

        # Fail closed on non-200
        if resp.status_code != 200:
            _log(f"authorization guard: validate failed (http {resp.status_code})")
            _hard_exit()

        # Fail closed on malformed / non-JSON
        try:
            data = resp.json()
        except Exception:
            _log("authorization guard: validate failed (non-json response)")
            _hard_exit()

        allowed = data.get("allowed", None)
        if allowed is not True:
            # Canonical audit fields (if present)
            code = data.get("code", "UNKNOWN")
            request_id = data.get("request_id", "UNKNOWN")
            _log(f"authorization guard: denied (code={code}, request_id={request_id})")
            _hard_exit()

        # Allowed -> continue
        return

    except Exception as e:
        # Network errors, timeouts, malformed responses are treated as deny.
        _log(f"authorization guard: validate unreachable ({type(e).__name__})")
        _hard_exit()


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
