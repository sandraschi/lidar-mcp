"""Server registration smoke test — tools import and register cleanly."""

from lidar_mcp import main as lidar_main  # noqa: F401 — import coverage
from lidar_mcp.server import mcp


async def test_server_registers_three_tools():
    tools = await mcp.list_tools()
    assert {t.name for t in tools} == {"lidar_scan", "show_lidar_health_card", "lidar_shutdown"}
