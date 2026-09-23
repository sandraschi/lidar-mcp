"""Robot companion registry for the Raspbot Link page and Mapper poses.

One-hop, fail-soft cross-connects per FLEET_CROSSCONNECT_STANDARD.md: the
web backend probes a companion's own health endpoint with a short timeout.
A dead companion degrades its page section, never the LiDAR core.

yahboom-mcp (Raspbot) is live. norirobotics-mcp (Nori A3) is a declared
placeholder — probed only once its backend contract lands.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)

PROBE_TIMEOUT_S = 2.5

COMPANIONS: list[dict[str, Any]] = [
    {
        "id": "yahboom",
        "label": "Yahboom Raspbot",
        "repo": "yahboom-mcp",
        "health_url": "http://127.0.0.1:10892/api/v1/health",
        "dashboard_url": "http://127.0.0.1:10893",
        "mount": "YDLIDAR on mast, scan plane horizontal",
        "status": "live",
    },
    {
        "id": "norirobotics",
        "label": "Nori Robotics A3",
        "repo": "norirobotics-mcp",
        "health_url": "http://127.0.0.1:11970/api/health",
        "dashboard_url": "http://127.0.0.1:11971",
        "mount": "undecided — cross-connect lands later",
        "status": "planned",
    },
]


def list_companions() -> list[dict[str, Any]]:
    """Registry shape without probing (fast, always available)."""
    return [dict(c) for c in COMPANIONS]


async def probe_companion(client: httpx.AsyncClient, companion_id: str) -> dict[str, Any]:
    """Probe one companion. Never raises — offline is a result, not an error."""
    spec = next((c for c in COMPANIONS if c["id"] == companion_id), None)
    if spec is None:
        return {"success": False, "message": f"Unknown companion: {companion_id}", "data": {}}
    if spec["status"] == "planned":
        return {
            "success": True,
            "message": f"{spec['label']} cross-connect is planned, not wired yet",
            "data": {"online": False, "planned": True, "spec": spec},
        }
    started = time.perf_counter()
    try:
        resp = await client.get(spec["health_url"], timeout=PROBE_TIMEOUT_S)
        latency_ms = round((time.perf_counter() - started) * 1000, 1)
        online = resp.status_code < 500
        try:
            detail = resp.json()
        except ValueError:
            detail = {"raw": resp.text[:2000]}
        return {
            "success": True,
            "message": f"{spec['label']} {'online' if online else 'unhealthy'} "
            f"({latency_ms:.0f} ms)",
            "data": {"online": online, "latency_ms": latency_ms, "detail": detail, "spec": spec},
        }
    except httpx.HTTPError as exc:
        logger.info("Companion %s unreachable: %s", companion_id, exc)
        return {
            "success": True,
            "message": f"{spec['label']} unreachable — is its backend running?",
            "data": {"online": False, "latency_ms": None, "detail": {"error": str(exc)[:300]}},
        }
