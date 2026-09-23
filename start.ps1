param([switch]$Headless, [switch]$NoBrowser)
$ErrorActionPreference = "Stop"
$ScriptRoot = Split-Path -Parent $PSCommandPath
$ApiPort = 11217

# Zombie-clear the web backend port before binding.
Get-NetTCPConnection -LocalPort $ApiPort -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }

$env:LIDAR_API_PORT = "$ApiPort"

Write-Host "Starting lidar-mcp web backend on port $ApiPort..." -ForegroundColor Cyan
$job = Start-Job -ScriptBlock {
    Set-Location $using:ScriptRoot
    uv run python -m lidar_mcp.webapp
}

try {
    # Backend readiness: TCP poll (not a fixed sleep).
    $ready = $false
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Seconds 1
        if (Get-NetTCPConnection -LocalPort $ApiPort -ErrorAction SilentlyContinue) { $ready = $true; break }
        if ($job.State -ne "Running") { throw "Backend job exited early. Check: uv run python -m lidar_mcp.webapp" }
    }
    if (-not $ready) { throw "Backend did not bind port $ApiPort within 30 s." }
    Write-Host "Backend ready: http://127.0.0.1:$ApiPort" -ForegroundColor Green
    if (-not $NoBrowser) { Start-Process "http://127.0.0.1:$ApiPort" }
    Write-Host "Press Ctrl+C to stop." -ForegroundColor Cyan
    Wait-Job $job | Out-Null
}
finally {
    Stop-Job $job -ErrorAction SilentlyContinue | Out-Null
    Remove-Job $job -Force -ErrorAction SilentlyContinue | Out-Null
}
