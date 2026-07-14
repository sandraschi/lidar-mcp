from fastmcp import FastMCP

from lidar_mcp.tools import lidar_scan, show_lidar_health_card

_READ_ONLY = {"readonly": True}

mcp = FastMCP(
    "lidar-mcp",
    instructions="YDLIDAR USB LiDAR control — scan, stream, status, health",
    version="0.1.0",
)

mcp.tool(annotations=_READ_ONLY)(lidar_scan)
mcp.tool(annotations=_READ_ONLY)(show_lidar_health_card)
