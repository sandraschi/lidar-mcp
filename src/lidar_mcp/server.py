from pathlib import Path

from fastmcp import FastMCP
from fastmcp.server.providers.skills import SkillsDirectoryProvider

from lidar_mcp.tools import lidar_scan, lidar_shutdown, show_lidar_health_card

_READ_ONLY = {"readonly": True}
_DESTRUCTIVE = {"readOnlyHint": False, "destructiveHint": True, "idempotentHint": False}

_DIALOGIC_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "success": {"type": "boolean"},
        "message": {"type": "string"},
        "data": {"type": "object"},
    },
    "required": ["success", "message"],
}

mcp = FastMCP(
    "lidar-mcp",
    instructions="YDLIDAR USB LiDAR control - scan, stream, status, health",
    version="0.4.0",
)

mcp.tool(annotations=_READ_ONLY, output_schema=_DIALOGIC_SCHEMA)(lidar_scan)
mcp.tool(annotations=_READ_ONLY)(show_lidar_health_card)
mcp.tool(annotations=_DESTRUCTIVE, output_schema=_DIALOGIC_SCHEMA)(lidar_shutdown)

_skills_dir = Path(__file__).resolve().parents[2] / ".opencode" / "skills"
if _skills_dir.is_dir():
    mcp.add_provider(SkillsDirectoryProvider(roots=[_skills_dir]))


@mcp.resource("lidar://status")
def lidar_status_resource() -> str:
    """Live LiDAR server status as JSON (no secrets, booleans only).

    ## Return Format
    JSON string: {"configured": bool, "ports": {...}, "version": str}

    ## Examples
    Read lidar://status before scanning to check LIDAR_PORT is set.
    """
    import json
    import os

    try:
        from importlib.metadata import version

        ver = version("lidar-mcp")
    except Exception:
        ver = "0.0.0"
    return json.dumps(
        {
            "configured": bool(os.environ.get("LIDAR_PORT", "")),
            "ports": {"sse": 11075, "api": 11228, "web": 11227},
            "version": ver,
        }
    )


@mcp.prompt(
    name="room_scan_workflow",
    description="Step-by-step LiDAR room survey: ports, status, scan, save, map, diff.",
    tags={"lidar", "workflow", "onboarding"},
)
def room_scan_workflow(scenario: str = "single") -> str:
    """Return a room-scan workflow prompt for the requested scenario.

    ## Return Format
    Plain-text numbered tool plan.

    ## Examples
    room_scan_workflow(scenario="single")
    room_scan_workflow(scenario="compare")
    room_scan_workflow(scenario="map")
    """
    base = (
        "You have access to lidar-mcp tools. "
        'Use lidar_scan(operation="ports") to find the sensor; '
        'lidar_scan(operation="status") for device health; '
        'lidar_scan(operation="scan") for a single 360-degree sweep; '
        "show_lidar_health_card() for a rich in-chat scan summary."
    )
    modes = {
        "single": (
            "\n\nScenario: single scan.\n"
            '1. lidar_scan(operation="ports")\n'
            '2. lidar_scan(operation="status")\n'
            '3. lidar_scan(operation="scan", timeout_s=3.0)\n'
            "4. Narrate: closest object, room shape, valid ratio."
        ),
        "compare": (
            "\n\nScenario: what moved.\n"
            '1. lidar_scan(operation="save", note="before")\n'
            '2. Rearrange the room, then lidar_scan(operation="save", note="after")\n'
            '3. lidar_scan(operation="diff", scan_a="<before>", scan_b="<after>")\n'
            "4. Report changed sectors with distances."
        ),
        "map": (
            "\n\nScenario: room map.\n"
            '1. lidar_scan(operation="save", note="map pose")\n'
            '2. lidar_scan(operation="map", source="<scan_id>", format="both")\n'
            "3. Describe the polar plot and occupancy grid in plain language."
        ),
    }
    return base + modes.get(scenario, modes["single"])
