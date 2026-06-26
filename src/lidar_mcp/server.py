from fastmcp import FastMCP

from lidar_mcp.tools import lidar_scan, show_lidar_health_card

mcp = FastMCP(
    "lidar-mcp",
    instructions="YDLIDAR USB LiDAR control — scan, stream, status, health",
    version="0.1.0",
)

mcp.tool()(lidar_scan)
mcp.tool()(show_lidar_health_card)
