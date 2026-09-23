# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.4.0] - 2026-09-24

### Added (webapp)
- FastAPI web backend on 11217 (frontend dev 11218): scan/map/diff/status,
  dashboard, tools/skills/logs, LLM proxy (local discovery + cloud keys),
  robot companion probes (yahboom live, norirobotics planned), POST /shutdown
- SOTA SPA: Dashboard, Console, Scope, Mapper (pose-tagged stitching, not SLAM),
  Raspbot Link (obstacle guard + honest E-STOP), Diff Lab, PTZ 3D capture,
  Scan Library, Tools, Skills, Apps, Chat, API Docs, Settings, Help, Logs
- `start.ps1` runs the web stack (zombie-clear, TCP readiness poll, browser);
  `just serve-web/web-install/web-build/gates` recipes

## [Unreleased]

### Fixed
- `show_lidar_health_card` rebuilt against the installed prefab-ui API
  (`PrefabApp(view=...)`, `Heading(content=...)`, `Text` rows): the old
  `Row(label=, value=)` kwargs and `app.add()` calls raised at runtime, and
  the no-port branch returned an empty card
- `ydlidar_driver` uses `reset_input_buffer/output_buffer` instead of the
  deprecated `flushInput/flushOutput` aliases (pyserial 3.5+ canonical names)
- `lidar_scan` / `show_lidar_health_card` type `ctx` as `Context | None`

### Added
- `pyright` + `pre-commit` in dev deps; `.git/hooks/pre-commit` materialised;
  CI runs a `pyright src/` typecheck step (0 errors)
- Session context injection for OpenCode (`.opencode/skills/lidar-mcp/SKILL.md`)
  and Antigravity (`.agents/skills/config.json`)

## [0.3.0] - 2026-09-06

### Added
- Map-experiment operations on `lidar_scan`: `save` (persist with note),
  `scans` (list), `map` (polar SVG + occupancy grid, live or saved id),
  `diff` (per-sector change with noise tolerance)
- 8 new mocked tests (30 total, ~79% coverage)

## [0.2.0] - 2026-09-06

### Fixed
- SSE default port moved 11074 → 11075 (11074 is registered to sysinternals-mcp
  in WEBAPP_PORTS.md; lidar-mcp had no registry entry)
- `connect()` auto-baud loop crashed with UnboundLocalError when the serial
  constructor itself raised; now skips to the next baud rate (found by mocked
  hardware test)

### Added
- `lidar_shutdown` self-termination tool (fleet os._exit pattern, DESTRUCTIVE)
- Hardware-mocked test suite: 22 tests, 75% coverage, `--cov-fail-under=70`
- Module logger + `_error_response` helper with traceback auto-logging
- `output_schema` on dialogic tools, T20 print-ban in ruff select
- CI (windows-latest: ruff, format check, pytest), pre-commit config,
  renovate.json
- Session context injection: `.cursorrules` section, `.windsurfrules`,
  `.claude-plugin`, `.github/copilot-instructions.md`
- `just test` recipe; `uv.lock` now committed (was gitignored)

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
