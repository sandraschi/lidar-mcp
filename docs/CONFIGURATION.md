# Configuration

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LIDAR_PORT` | — | Serial port of the LiDAR (e.g. COM3, /dev/ttyUSB0). **Required.** |
| `LIDAR_BAUD` | auto | Override baud rate. Auto-detected if omitted. Common values: 115200 (X2), 230400 (X4), 500000 (G4). |
| `MCP_PORT` | — | Set to `11075` for SSE/HTTP mode (omit for stdio) |

## Setting Variables

In `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "lidar": {
      "command": "uv",
      "args": ["--directory", "C:\\path\\to\\lidar-mcp",
               "run", "python", "-m", "lidar_mcp.main"],
      "env": {
        "LIDAR_PORT": "COM3",
        "LIDAR_BAUD": "230400"
      }
    }
  }
}
```

## Finding the Port

Run `lidar_scan(operation="ports")` to list all serial ports. YDLIDAR
sensors typically show as CP210x, CH340, or Silicon Labs USB UART.
