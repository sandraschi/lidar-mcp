"""YDLIDAR LiDAR tools — portmanteau pattern."""

from __future__ import annotations

import os
from typing import Any

from fastmcp import Context

from lidar_mcp.ydlidar_driver import (
    connect,
    list_ports,
    probe_port,
    scan_once,
    stream_stop,
)


def _get_port() -> str:
    return os.environ.get("LIDAR_PORT", "")


def _get_baud() -> int:
    return int(os.environ.get("LIDAR_BAUD", "0"))


async def lidar_scan(
    operation: str,
    ctx: Context = None,
    port: str = "",
    timeout_s: float = 3.0,
) -> dict[str, Any]:
    """Unified control for YDLIDAR USB LiDAR sensors.

    [RATIONALE] Consolidates all LiDAR operations (status, scan, stream,
    port discovery) into one portmanteau tool so agents don't need 6 separate
    tools for a simple USB sensor.

    Operations:
    - status: Device info, firmware, health, connected ports
    - scan: Single 360-degree scan, returns point cloud
    - stream_start: Begin continuous scan streaming
    - stream_read: Read one scan point from active stream
    - stream_stop: Stop continuous streaming
    - ports: List available serial ports (auto-detect LiDARs)

    ## Return Format
    {"success": bool, "message": str, "data": {...}}

    ## Examples
    lidar_scan(operation="status")
    lidar_scan(operation="scan", timeout_s=3.0)
    lidar_scan(operation="ports")
    """
    resolved_port = port or _get_port()

    if operation == "ports":
        ports = list_ports()
        return {
            "success": True,
            "message": f"Found {len(ports)} serial ports",
            "data": {"ports": ports},
        }

    if operation == "status":
        if not resolved_port:
            ports = list_ports()
            return {
                "success": False,
                "message": "No LiDAR port specified. Set LIDAR_PORT env var or use detected ports:",
                "data": {"ports": ports},
            }
        try:
            result = probe_port(resolved_port)
            return result
        except Exception as e:
            return {"success": False, "message": f"Status check failed: {e}", "data": {}}

    if operation == "scan":
        if not resolved_port:
            return {"success": False, "message": "No LiDAR port set. Use operation='ports' to find it "
                                                  "or set LIDAR_PORT env var.", "data": {}}
        try:
            baud = _get_baud() or None
            ser = connect(resolved_port, baud=baud)
            try:
                result = scan_once(ser, timeout_s=timeout_s)
                valid = [p for p in result.points if p.is_valid]
                return {
                    "success": True,
                    "message": f"Scan complete: {result.point_count} points "
                               f"({len(valid)} valid) in {result.duration_ms:.0f} ms",
                    "data": {
                        "point_count": result.point_count,
                        "valid_count": len(valid),
                        "duration_ms": result.duration_ms,
                        "points": [
                            {
                                "angle_deg": round(p.angle_deg, 2),
                                "distance_mm": round(p.distance_mm, 1),
                                "quality": p.quality,
                                "is_valid": p.is_valid,
                                "is_sync": p.is_sync,
                            }
                            for p in result.points
                        ],
                    },
                }
            finally:
                stream_stop(ser)
                ser.close()
        except Exception as e:
            return {"success": False, "message": f"Scan failed: {e}", "data": {}}

    if operation == "stream_start":
        return {"success": False, "message": "Streaming via stdio MCP is not recommended. "
                                              "Use scan (single capture) or connect via HTTP SSE "
                                              "for persistent stream access.", "data": {}}

    return {
        "success": False,
        "message": f"Unknown operation: {operation}",
        "data": {"valid_operations": ["status", "scan", "stream_start", "stream_read",
                                       "stream_stop", "ports"]},
    }


async def show_lidar_health_card(ctx: Context = None) -> Any:
    """Show a rich Prefab card with LiDAR status and scan data.

    ## Return Format
    PrefabApp card or plain-text fallback.

    ## Examples
    show_lidar_health_card()
    """
    port = _get_port()

    if not port:
        ports = list_ports()
        from prefab_ui import PrefabApp
        from prefab_ui.components import Div, Heading, Text

        app = PrefabApp(title="YDLIDAR — No Port")
        Heading("No LiDAR configured")
        Div()
        Text(f"Set LIDAR_PORT env var. Detected serial ports: {len(ports)}")
        return {
            "content": "Set LIDAR_PORT env var to use the LiDAR health card.",
            "structured_content": app,
        }

    try:
        baud = _get_baud() or None
        ser = connect(port, baud=baud)
        try:
            from prefab_ui import PrefabApp
            from prefab_ui.components import Badge, Div, Heading, Row

            scan = scan_once(ser, timeout_s=2.0)
            valid = [p for p in scan.points if p.is_valid]
            dists = [p.distance_mm for p in valid]
            min_dist = min(dists) if dists else 0
            max_dist = max(dists) if dists else 0

            app = PrefabApp(title="YDLIDAR LiDAR")
            Heading("Scan Summary")
            Div()
            Badge(f"{scan.point_count} points", color="blue")
            Badge(f"{len(valid)} valid", color="green")
            Div()
            Row(label="Min distance", value=f"{min_dist:.0f} mm")
            Row(label="Max distance", value=f"{max_dist:.0f} mm")
            Row(label="Duration", value=f"{scan.duration_ms:.0f} ms")
            Row(label="Port", value=port)

            text = (f"LiDAR scan: {scan.point_count} points ({len(valid)} valid), "
                    f"range {min_dist:.0f}–{max_dist:.0f} mm on {port}")
            return {"content": text, "structured_content": app}
        finally:
            stream_stop(ser)
            ser.close()
    except Exception as e:
        from prefab_ui import PrefabApp
        from prefab_ui.components import Div, Text

        app = PrefabApp(title="YDLIDAR — Error")
        app.add(Div())
        app.add(Text(str(e)))
        return {"content": f"LiDAR error: {e}", "structured_content": app}
