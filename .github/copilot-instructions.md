# lidar-mcp — Copilot Instructions

YDLIDAR USB LiDAR MCP server (FastMCP 3.4+, stdio-first, SSE on 11075).

- Find the sensor: `lidar_scan(operation="ports")`, single sweep:
  `lidar_scan(operation="scan")`, card: `show_lidar_health_card()`.
- `LIDAR_PORT` env var (e.g. COM3) is required for status/scan.
- Checks: `uv run ruff check src/`, `uv run pytest tests/ -q`.
- Never change the SSE port without updating `WEBAPP_PORTS.md`.
