param([switch]$Headless, [switch]$NoBrowser)
$ErrorActionPreference = "Stop"
$ScriptRoot = Split-Path -Parent $PSCommandPath
$Port = 11075

Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }

$env:MCP_PORT = "$Port"
$env:MCP_HOST = "127.0.0.1"

Write-Host "Starting lidar-mcp on port $Port..." -ForegroundColor Cyan
uv run python -m lidar_mcp.main
