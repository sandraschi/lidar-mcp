# lidar-mcp

FastMCP 3.4+ server for YDLIDAR USB LiDAR sensors (X2/X4/G1/G4/S series).

## Quick Start
```powershell
uv run python -m lidar_mcp.main          # stdio (Claude Desktop)
set MCP_PORT=11074 && uv run python -m lidar_mcp.main  # SSE
```

## Port
- SSE: 11074

## Tools
- `lidar_scan` — portmanteau: ports, status, scan, stream_start/stop/read
- `show_lidar_health_card` — Prefab card with scan point stats

## Docs
- [README](README.md), [INSTALL](INSTALL.md), [TOOLS](docs/TOOLS.md)
- [CHANGELOG](CHANGELOG.md), [AGENTS](AGENTS.md)

## Required Config
- `LIDAR_PORT` env var (e.g. COM3 or /dev/ttyUSB0)
