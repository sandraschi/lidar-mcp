# Tool Reference

## lidar_scan — Portmanteau LiDAR Control

All LiDAR operations go through this single portmanteau tool.

### Operations

| operation | Parameters | Description |
|-----------|-----------|-------------|
| `ports` | — | List all serial ports, auto-detect LiDAR candidates |
| `status` | `port` | Device info, firmware version, health, error codes |
| `scan` | `port`, `timeout_s` | Single 360-degree scan, returns full point cloud |
| `stream_start` | `port` | Begin continuous scan streaming (SSE mode only) |
| `stream_stop` | `port` | Stop streaming |

### Return Format (scan)

```json
{
  "success": true,
  "message": "Scan complete: 812 points (723 valid) in 352 ms",
  "data": {
    "point_count": 812,
    "valid_count": 723,
    "duration_ms": 352.1,
    "points": [
      {"angle_deg": 0.0, "distance_mm": 450.2, "quality": 85, "is_valid": true, "is_sync": true},
      {"angle_deg": 0.5, "distance_mm": 1230.1, "quality": 92, "is_valid": true, "is_sync": false},
      ...
    ]
  }
}
```

### Examples

```
lidar_scan(operation="ports")
lidar_scan(operation="status")
lidar_scan(operation="scan", timeout_s=4.0)
```

### Point Quality Reference

| Quality | Meaning |
|---------|---------|
| 0 | Invalid/noise — discard this point |
| 1–50 | Low — likely scatter or edge case |
| 51–100 | Normal — solid return |
| 101–127 | Strong — retroreflector or very close object |

is_sync=true marks the start of a new 360-degree rotation.

---

## show_lidar_health_card — Prefab Status Card

Renders a rich in-chat card with LiDAR status and last scan summary.

```
show_lidar_health_card()
```

Displays: total points, valid count, min/max distance, scan duration.
