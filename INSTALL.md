# Installing lidar-mcp

## Prerequisites

| Tool | Purpose | Install |
|------|---------|---------|
| Claude Desktop | Required MCP host | [download](https://claude.ai/download) |
| Git | Clone repo (Options C/D) | `winget install Git.Git` |
| Python + uv | Run server (Options C/D) | `winget install astral-sh.uv` |
| YDLIDAR sensor | LiDAR hardware | See Buying Guide in `llms-full.txt` |

## Option A — Plug and Play (Recommended)

1. Plug the YDLIDAR into a USB port
2. Find the port: `lidar_scan(operation="ports")`
3. Set `LIDAR_PORT` in the Claude Desktop config (see Option C)
4. Done

## Option B — mcpb CLI

Not yet available. Coming in a future release.

## Option C — Manual Configuration

1. Clone:
```bash
git clone https://github.com/sandraschi/lidar-mcp
cd lidar-mcp
```

2. Install deps:
```bash
uv sync
```

3. Add to `%APPDATA%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "lidar": {
      "command": "uv",
      "args": ["--directory", "C:\\path\\to\\lidar-mcp",
               "run", "python", "-m", "lidar_mcp.main"],
      "env": { "PYTHONUNBUFFERED": "1", "LIDAR_PORT": "COM3" }
    }
  }
}
```

4. Restart Claude Desktop

## Option D — Developer Mode

See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).

## Verify Installation

Open Claude and say:
> "Scan with the LiDAR."

You should see a point cloud with angles and distances. If you get "no port",
check `LIDAR_PORT` is set correctly.
