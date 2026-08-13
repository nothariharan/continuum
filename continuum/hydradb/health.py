"""HydraDB readiness and failure diagnostics."""

from __future__ import annotations

import urllib.error
import urllib.request
from dataclasses import dataclass

from neo4j.exceptions import AuthError, ClientError, ServiceUnavailable

from .client import HydraDBClient
from .config import HydraDBConfig


@dataclass(frozen=True)
class HealthStatus:
    reachable: bool
    ready: bool
    authenticated: bool
    queryable: bool
    message: str


def readiness_check(config: HydraDBConfig) -> bool:
    try:
        with urllib.request.urlopen(config.admin_ready_url, timeout=3) as response:
            return 200 <= response.status < 300
    except (urllib.error.URLError, TimeoutError):
        return False


def readiness_message(config: HydraDBConfig) -> str:
    try:
        with urllib.request.urlopen(config.admin_ready_url, timeout=3) as response:
            if 200 <= response.status < 300:
                return "HydraDB is ready"
            return f"HydraDB is not ready (admin endpoint returned HTTP {response.status})"
    except urllib.error.URLError as exc:
        reason = getattr(exc, "reason", exc)
        return f"HydraDB is not running or admin endpoint is unreachable: {reason}"
    except TimeoutError:
        return "HydraDB is not ready: admin readiness request timed out"


def diagnose(config: HydraDBConfig | None = None) -> HealthStatus:
    config = config or HydraDBConfig.from_env()
    ready = readiness_check(config)
    if not ready:
        return HealthStatus(False, False, False, False, readiness_message(config))
    try:
        with HydraDBClient(config) as client:
            client.health_check()
        return HealthStatus(True, True, True, True, "HydraDB is reachable, ready, authenticated, and queryable")
    except AuthError as exc:
        return HealthStatus(True, True, False, False, f"HydraDB authentication failure: {exc}")
    except ClientError as exc:
        return HealthStatus(True, True, True, False, f"HydraDB database/namespace or query failure: {exc}")
    except ServiceUnavailable as exc:
        return HealthStatus(True, True, False, False, f"HydraDB connection refused: {exc}")


def main() -> int:
    status = diagnose()
    print(status.message)
    return 0 if status.reachable and status.ready and status.authenticated and status.queryable else 1


if __name__ == "__main__":
    raise SystemExit(main())
