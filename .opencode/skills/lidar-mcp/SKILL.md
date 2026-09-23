---
name: lidar-mcp
description: YDLIDAR USB LiDAR sensor control — scan, stream, status, health card
---

# lidar-mcp

YDLIDAR USB LiDAR (X2/X4/G1/G4/S series) on serial `LIDAR_PORT`. SSE default port 11075.

## Before starting work

- `lidar_scan(operation="ports")` to find the sensor; `lidar_scan(operation="scan")` for a 360-degree sweep.
- `show_lidar_health_card()` for the Prefab summary.

## At end of work

- Run `uv run ruff check src/`, `uv run pyright src/`, `uv run pytest tests/ -q`.
- Never change the SSE port without updating `WEBAPP_PORTS.md`.
