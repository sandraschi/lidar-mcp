# Development Setup

## Tools Required

```bash
# Windows (winget)
winget install astral-sh.uv
winget install Git.Git
winget install Casey.Just

# Verify
uv --version
git --version
just --version
```

## Setup

```bash
git clone https://github.com/sandraschi/lidar-mcp
cd lidar-mcp
uv sync
```

## Common Tasks

```bash
just serve       # Run in stdio mode
just serve-http  # Run in SSE/HTTP mode on port 11075
just check       # Verify imports and tool registration
```

## Project Structure

```
src/lidar_mcp/
├── __init__.py
├── server.py              # FastMCP app
├── main.py                # Entry point, dual transport
├── ydlidar_driver.py      # Raw serial protocol for YDLIDAR
└── tools/
    ├── __init__.py
    └── lidar_tools.py      # Portmanteau tool + Prefab card
```

## Protocol Reference

The YDLIDAR SDK2 protocol is a binary packet format over USB CDC ACM:

- Command: `0xA5` + command_byte
- Response descriptor: `0xA5 0x5A` + length(2) + type(1) + CRC16(2)
- Scan point data: 5 bytes per point (quality + angle + distance)
- CRC16-Modbus over all data bytes

See `ydlidar_driver.py` for the full implementation — it's a pure Python
implementation with no C++ dependencies.
