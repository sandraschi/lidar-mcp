# lidar-mcp

Turn a $30 YDLIDAR USB sensor into an AI-controllable 2D laser scanner — get
point clouds, device health, and live streaming, all through MCP.

```
Plug in a YDLIDAR X4/G4/S2 → talk to it from Claude:
  "scan the room and tell me what distances you see"
  "show me the LiDAR health card"
  "what's the closest object?"
```

## How It Works

YDLIDAR sensors (X2, X4, G1, G4, S2, S4, S2B, S4B) are 2D time-of-flight
LiDARs that communicate over USB serial using a standard packet protocol.
They do 360-degree sweeps at 5–12 Hz, returning distance readings at each
angle step. This server wraps that protocol for AI agents.

## Features

- Single 360-degree scan with angle/distance/quality per point
- Device info and health (temperature, error codes)
- Serial port auto-detection for YDLIDAR devices
- Rich Prefab card with point cloud summary (min/max distance, valid count)
- All over a $30–$80 USB sensor — no ROS, no Python SDK, no compilation

## Quick Install

```json
{
  "mcpServers": {
    "lidar": {
      "command": "uv",
      "args": ["--directory", "C:\\path\\to\\lidar-mcp", "run",
               "python", "-m", "lidar_mcp.main"],
      "env": { "PYTHONUNBUFFERED": "1", "LIDAR_PORT": "COM3" }
    }
  }
}
```

Plug in the LiDAR, find its port with `lidar_scan(operation="ports")`,
add to `claude_desktop_config.json`, restart. See [INSTALL.md](INSTALL.md).

## What You Can Do

```
"Find my LiDAR port."
"Scan once and show me the data."
"Show the LiDAR health card."
"What's the minimum distance in the current scan?"
```

## Fleet Ecosystem

| Layer | Repo | What it provides | Hardware |
|-------|------|-----------------|----------|
| **LiDAR** | **lidar-mcp** (you are here) | 2D point clouds, device status | YDLIDAR X2/X4/G4/S2 ($30–80) |
| **Robot** | [yahboom-mcp](https://github.com/sandraschi/yahboom-mcp) | Obstacle avoidance, motor control | Yahboom ROS robot |
| **Simulation** | [ros-mcp](https://github.com/sandraschi/ros-mcp) | ROS 2 bridge, node graph | ROS 2 Humble |

`lidar-mcp` exposes raw scan data. `yahboom-mcp` consumes it for obstacle
avoidance. `ros-mcp` bridges it into a full ROS 2 ecosystem.

## Documentation

| Doc | Contents |
|-----|----------|
| [Installation](INSTALL.md) | All install methods, prerequisites |
| [Configuration](docs/CONFIGURATION.md) | Env vars (LIDAR_PORT, etc.) |
| [Tool Reference](docs/TOOLS.md) | Full tool list with examples |
| [Troubleshooting](docs/TROUBLESHOOTING.md) | Common issues |
| [Full Reference](llms-full.txt) | YDLIDAR hardware tech doc |

## Requirements

- Python 3.12+ with `uv`
- YDLIDAR X2, X4, G1, G4, S2, S4, S2B, or S4B LiDAR ($30–80 on AliExpress/Amazon)
- USB port (USB 2.0 minimum, USB 3.0 recommended for G4/S2 high-rate modes)

## License

MIT
