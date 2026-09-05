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

---

## lidar_shutdown — Self-Termination

Gracefully shuts down the server process (fleet self-termination contract).
Schedules `os._exit(0)` after 0.5 s so the in-flight response flushes.

```
lidar_shutdown()
lidar_shutdown(reason="robot packed up for the night")
```

Returns `{"success": true, "message": "Shutdown scheduled", "reason": ...}`.
Annotated DESTRUCTIVE (readOnlyHint false).

---

## Map experiments — save / scans / map / diff

Persisted scans live in `data/scans/scan-YYYYMMDD-HHMMSS.json`
(`LIDAR_DATA_DIR` overrides the location, e.g. in tests).

```
lidar_scan(operation="save", note="door open")   # live scan + persist, returns scan_id
lidar_scan(operation="scans")                    # list saved scans (id, time, counts, note)
lidar_scan(operation="map", source="live", format="svg")
lidar_scan(operation="map", source="scan-20260906-120000", format="both", grid_size=100)
lidar_scan(operation="diff", scan_a="...", scan_b="...", tolerance_mm=150)
```

- **map**: `source="live"` scans now, or pass a saved id. `format` is
  `svg` (polar plot, 0 deg up, closest return circled red), `grid`
  (top-down occupancy grid, `grid_size` 8–200, `range_max_mm=0` auto-scales),
  or `both`.
- **diff**: per-sector minimum-range comparison (`sector_deg` default 5,
  `tolerance_mm` default 150 guards noise). Reports changed/gained/lost
  sectors sorted by delta — door opened, furniture moved, person walked by.
