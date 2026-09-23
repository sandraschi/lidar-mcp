# Onboarding — lidar-mcp

First-timer path from sealed box to first scan, on PC or Raspberry Pi.

## What this is for

YDLIDAR USB LiDAR (X2/X4/G1/G4/S series) as an AI-readable sensor: scans,
maps, and robot linkage. You need the module (~$30-80), a USB port, and
this repo. No ROS, no SDK, no account, no money beyond the hardware.

## PC first run (Windows)

1. `git clone https://github.com/sandraschi/lidar-mcp && cd lidar-mcp`
2. `uv sync` (Python 3.12+ via uv)
3. Plug the LiDAR into a **direct USB port** (no hub for first test).
4. Device Manager → Ports → note `COMx`. Motor should spin.
5. Copy `.env.example` to `.env`, set `LIDAR_PORT=COMx`.
6. `.\start.ps1` → browser opens the Console → Status → Scan once.

## Webapp path (no Claude needed)

1. `cd webapp && bun install && bun run build && cd ..`
2. `.\start.ps1` — API 11217 serves the SPA.
3. If the UI says "Backend unreachable", the readiness poll failed: run
   `uv run python -m lidar_mcp.webapp` manually and read the error.

## Raspberry Pi path (Raspbot mast)

1. Pi OS 64-bit, `uv` installed, repo cloned to `~/lidar-mcp`.
2. `uv sync` (pure Python + pyserial — no compilation).
3. Plug LiDAR into the Pi (`/dev/ttyUSB0` typically), set `LIDAR_PORT`.
4. `uv run python -m lidar_mcp.webapp` (or wire an NSSM/systemd unit later).
5. From your laptop: `http://<pi-tailscale-ip>:11217` (CORS allows LAN + 100.x).
6. Raspbot Link page probes yahboom-mcp when the robot stack is up.

## Pitfalls

- **Power first**: thin/long cables stall the motor. Short shielded cable, ≤2 m.
- **COM held open**: close Arduino IDE / serial monitors / old sessions.
- **Glass is invisible** (785 nm IR passes through) — quality 0 is physics.
- **Chat needs an LLM**: Settings → install Ollama (one click) or paste a
  cloud key. Cloud keys stay in `data/llm_keys.json` (0600) or env.

## Sanity check

Console → Scan once → several hundred points, majority valid → Save with a
note → Library shows it → Diff Lab compares two. All green = onboarded.
