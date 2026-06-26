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
