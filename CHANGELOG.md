# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.0] - 2026-07-14

### Added
- Initial release: FastMCP 3.4+ server for YDLIDAR USB LiDAR sensors (X2/X4/G1/G4/S series)
- `lidar_scan` portmanteau tool with 5 operations: ports, status, scan, stream_start/stop/read
- `show_lidar_health_card` Prefab UI card with scan statistics
- Raw SDK2 serial protocol driver (ydlidar_driver.py): CRC16, auto-baud detect, sync-delta scan
- Dual transport: stdio (default) and SSE on port 11074
- Documentation: README, INSTALL, CONFIGURATION, DEVELOPMENT, TOOLS, TROUBLESHOOTING
- llms.txt + llms-full.txt for LLM discovery
- glama.json for MCP registry
