# Per-repo fleet start config for lidar-mcp
# Ports were allocated by fleet-gate/allocate.py (2026-10-03): 11217/11218
# collided with raspberrypi-mcp. SSE on 11075 unchanged.
@{
    Name         = 'lidar-mcp'
    BackendPort  = 11228
    FrontendPort = 11227
    HealthPath   = '/api/health'
    WebRoot      = 'webapp'
    Backend = @{
        Kind          = 'uvicorn'
        UvicornTarget = 'lidar_mcp.webapp:app'
        SyncExtras    = @('dev')
        Env           = @{ LIDAR_API_PORT = '11228'; LIDAR_WEB_PORT = '11227' }
    }
    Frontend = @{
        Kind           = 'vite-npm'
        PackageManager = 'npm'
        PortEnvVar     = 'VITE_PORT'
        ApiTargetEnv   = 'VITE_API_TARGET'
    }
}
