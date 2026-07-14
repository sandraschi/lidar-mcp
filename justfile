default: serve

# Run in stdio mode (Claude Desktop)
serve:
    uv run python -m lidar_mcp.main

# Run in HTTP/SSE mode on port 11074
serve-http:
    $env:MCP_PORT = "11074"; $env:MCP_HOST = "127.0.0.1"; uv run python -m lidar_mcp.main

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
