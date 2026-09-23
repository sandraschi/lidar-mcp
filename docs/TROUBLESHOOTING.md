# Troubleshooting

## "No LiDAR port" error
**Cause**: LIDAR_PORT not set, or port wrong
**Fix**: Run `lidar_scan(operation="ports")` to list available ports. Set `LIDAR_PORT` env var.

## "Bad response header"
**Cause**: Wrong port, wrong baud, or device not a YDLIDAR
**Fix**: Verify the LiDAR is plugged in (LED should be spinning). Check port name. Try different USB cable — some cables are power-only.

## "Short read" / timeout when scanning
**Cause**: USB buffer overrun, or LiDAR motor stalled
**Fix**: Use a USB 3.0 port or a powered USB hub. On Windows, check USB selective suspend is disabled for the LiDAR.

## Scan returns all zero distances
**Cause**: LiDAR motor not spinning, or object too close (< detection range)
**Fix**: Check the motor is spinning (you should hear/feel it). Minimum range is ~12–20 cm depending on model.

## "Port in use" / permission denied
**Cause**: Another process claims the serial port
**Fix**: Close serial monitors, Arduino IDE, ROS serial nodes, or previous MCP sessions.

## Port shows in list but scan fails
**Cause**: Wrong baud rate, or motor not started
**Fix**: Try all common baud rates manually via `LIDAR_BAUD`. Some models need a power cycle after USB plug-in.

## Server doesn't appear in Claude Desktop
**Cause**: Config JSON malformed, or uv not in PATH
**Fix**: Validate JSON. Run `uv --version` from terminal.

## Web UI shows "Backend unreachable"
**Cause**: API not running, or browser on another host without LAN route
**Fix**: Run `start.ps1` (or `just serve-web`) and wait for the readiness poll.
From another machine use the Pi's Tailscale/LAN IP — CORS allows LAN + 100.x.

## Chat says "No local LLM detected"
**Cause**: No Ollama/LM Studio/vLLM running
**Fix**: Install Ollama (Settings page one-click, or winget), pull a model,
or paste a cloud key in Settings. Keys live server-side only.

## Companion "unreachable" on Raspbot Link
**Cause**: yahboom-mcp backend (10892) not running
**Fix**: Start yahboom-mcp. The page degrades — LiDAR pages keep working.
