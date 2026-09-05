from fastmcp import FastMCP

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
    version="0.2.0",
)

mcp.tool(annotations=_READ_ONLY, output_schema=_DIALOGIC_SCHEMA)(lidar_scan)
mcp.tool(annotations=_READ_ONLY)(show_lidar_health_card)
mcp.tool(annotations=_DESTRUCTIVE, output_schema=_DIALOGIC_SCHEMA)(lidar_shutdown)
