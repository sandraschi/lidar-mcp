set windows-shell := ["powershell.exe", "-NoProfile", "-Command"]

default: serve

# Run in stdio mode (Claude Desktop)
serve:
    uv run python -m lidar_mcp.main

# Run in HTTP/SSE mode on port 11075
serve-http:
    $env:MCP_PORT = "11075"; $env:MCP_HOST = "127.0.0.1"; uv run python -m lidar_mcp.main

# Run tests (hardware-mocked, no LiDAR required)
test:
    uv run pytest tests/ -q

# Verify server imports and tool registration
check:
    uv run python -c "import lidar_mcp; print('OK')"

# Lint
lint:
    uv run ruff check src/

# Format
fmt:
    uv run ruff format src/

# Install dependencies
install:
    uv sync

# Clean cache and artifacts
clean:
    Remove-Item -Recurse -Force __pycache__, .ruff_cache -ErrorAction SilentlyContinue

# Run web backend (FastAPI on 11217, serves SPA when built)
serve-web:
    $env:LIDAR_API_PORT = "11217"; uv run python -m lidar_mcp.webapp

# Install webapp deps (bun, fleet standard)
web-install:
    Push-Location webapp; bun install; Pop-Location

# Build webapp (tsc + vite; Tailwind CSS gate: dist CSS must exceed 5 kB)
web-build:
    Push-Location webapp; bun run build; Pop-Location

# Full gates: python lint + types + tests, frontend types + lint
gates:
    uv run ruff check src/ tests/; uv run ruff format src/ tests/ --check; uv run pyright src/; uv run pytest tests/ -q; Push-Location webapp; bun run check; bunx @biomejs/biome check src/; Pop-Location

# Bootstrap: install dev deps + pre-commit hook
bootstrap:
    uv sync --group dev
    uv run pre-commit install
    Write-Host "Pre-commit hooks installed." -ForegroundColor Green