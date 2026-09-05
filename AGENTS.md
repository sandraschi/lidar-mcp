# lidar-mcp — Agent Context

FastMCP 3.4+ server for YDLIDAR USB LiDAR sensors (X2/X4/G1/G4/S series).

## Quick Start
```powershell
uv run python -m lidar_mcp.main          # stdio mode (Claude Desktop)
uv run python -m lidar_mcp.main          # SSE mode (MCP_PORT=11075)
uv run ruff check src/                   # Lint
```

## Ports
- MCP SSE: 11075 (when MCP_PORT is set)
- Default: stdio

## Tools (3)
| Tool | Description |
|------|-------------|
| `lidar_scan` | Portmanteau: ports, status, scan, stream_start/stop/read |
| `show_lidar_health_card` | Prefab card with scan stats (point count, quality, distances) |
| `lidar_shutdown` | Graceful self-termination (DESTRUCTIVE) |

## Architecture
```
server.py → tools/lidar_tools.py → ydlidar_driver.py → USB Serial → YDLIDAR
```

## Code Rules
- Ruff linting (default selectors, line length 120)
- READ_ONLY annotation on all tools (LiDAR reads, no mutations)
- No bare `except: pass` in driver code
