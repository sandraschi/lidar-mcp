"""YDLIDAR LiDAR tools - portmanteau pattern."""

from __future__ import annotations

import asyncio
import datetime
import html
import json
import logging
import math
import os
import re
from pathlib import Path
from typing import Any

from fastmcp import Context

from lidar_mcp.ydlidar_driver import (
    ScanPoint,
    ScanResult,
    connect,
    list_ports,
    probe_port,
    scan_once,
    stream_stop,
)

logger = logging.getLogger(__name__)

# Keep references to scheduled shutdown tasks so the event loop does not GC them.
_shutdown_tasks: set = set()


def _error_response(operation: str, exc: BaseException) -> dict[str, Any]:
    """Shared error shape with auto-logged traceback (fleet Pattern 3)."""
    logger.exception("lidar %s failed", operation)
    return {"success": False, "message": f"{operation} failed: {exc}", "data": {}}


def _get_port() -> str:
    return os.environ.get("LIDAR_PORT", "")


def _get_baud() -> int:
    return int(os.environ.get("LIDAR_BAUD", "0"))


_SCAN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
_MAX_SVG_POINTS = 1440
_MAX_GRID = 200


def _scans_dir() -> Path:
    """Directory for persisted scans (LIDAR_DATA_DIR overrides for tests)."""
    override = os.environ.get("LIDAR_DATA_DIR", "")
    path = Path(override) if override else Path(__file__).resolve().parents[3] / "data" / "scans"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _scan_file(scan_id: str) -> Path:
    if not _SCAN_ID_RE.match(scan_id):
        raise ValueError(f"Invalid scan id: {scan_id!r}")
    return _scans_dir() / f"{scan_id}.json"


def _point_to_dict(p: ScanPoint) -> dict[str, Any]:
    return {
        "angle_deg": round(p.angle_deg, 2),
        "distance_mm": round(p.distance_mm, 1),
        "quality": p.quality,
        "is_valid": p.is_valid,
        "is_sync": p.is_sync,
    }


def _capture(resolved_port: str, timeout_s: float) -> ScanResult:
    """Single live capture with guaranteed serial cleanup."""
    baud = _get_baud() or None
    ser = connect(resolved_port, baud=baud)
    try:
        return scan_once(ser, timeout_s=timeout_s)
    finally:
        try:
            stream_stop(ser)
        finally:
            ser.close()


def _save_scan(result: ScanResult, port: str, note: str) -> dict[str, Any]:
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    scan_id = f"scan-{stamp}"
    suffix = 1
    while _scan_file(scan_id).exists():
        suffix += 1
        scan_id = f"scan-{stamp}-{suffix}"
    payload = {
        "scan_id": scan_id,
        "saved_at": datetime.datetime.now(datetime.UTC).isoformat(),
        "port": port,
        "note": note,
        "point_count": result.point_count,
        "valid_count": sum(1 for p in result.points if p.is_valid),
        "duration_ms": result.duration_ms,
        "points": [_point_to_dict(p) for p in result.points],
    }
    _scan_file(scan_id).write_text(json.dumps(payload), encoding="utf-8")
    logger.info("Saved scan %s (%d points)", scan_id, result.point_count)
    return payload


def _load_scan(scan_id: str) -> dict[str, Any]:
    path = _scan_file(scan_id)
    if not path.exists():
        known = sorted(p.stem for p in _scans_dir().glob("scan-*.json"))
        raise ValueError(
            f"Unknown scan id: {scan_id!r}. Known: {known or 'none yet — use save first'}"
        )
    return json.loads(path.read_text(encoding="utf-8"))


def _render_svg(points: list[dict[str, Any]], range_max_mm: float, title: str) -> str:
    """Polar plot: 0 deg up, clockwise. Valid returns cyan, closest red."""
    size, c = 800, 400
    scale = 370.0 / range_max_mm
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}">',
        f'<rect width="{size}" height="{size}" fill="#09090b"/>',
    ]
    ring = 1000.0
    while ring < range_max_mm:
        r = ring * scale
        out.append(
            f'<circle cx="{c}" cy="{c}" r="{r:.1f}" fill="none" stroke="#27272a" stroke-width="1"/>'
            f'<text x="{c + 4}" y="{c - r - 4}" fill="#71717a" font-size="16">{ring / 1000:.0f} m</text>'
        )
        ring += 1000.0
    out.append(
        f'<line x1="{c - 370}" y1="{c}" x2="{c + 370}" y2="{c}" stroke="#27272a"/>'
        f'<line x1="{c}" y1="{c - 370}" x2="{c}" y2="{c + 370}" stroke="#27272a"/>'
    )
    closest: dict[str, Any] | None = None
    shown = 0
    for p in points:
        if not p["is_valid"] or shown >= _MAX_SVG_POINTS:
            continue
        a = math.radians(p["angle_deg"])
        r = p["distance_mm"] * scale
        x, y = c + r * math.sin(a), c - r * math.cos(a)
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.2" fill="#22d3ee"/>')
        shown += 1
        if closest is None or p["distance_mm"] < closest["distance_mm"]:
            closest = {"distance_mm": p["distance_mm"], "x": x, "y": y, "angle": p["angle_deg"]}
    out.append(f'<circle cx="{c}" cy="{c}" r="5" fill="#fafafa"/>')
    if closest is not None:
        out.append(
            f'<circle cx="{closest["x"]:.1f}" cy="{closest["y"]:.1f}" r="6" fill="none" '
            f'stroke="#f43f5e" stroke-width="2"/>'
            f'<text x="{c - 360}" y="{c + 360}" fill="#f43f5e" font-size="18">closest: '
            f"{closest['distance_mm']:.0f} mm @ {closest['angle']:.1f} deg</text>"
        )
    out.append(
        f'<text x="{c - 360}" y="{c - 348}" fill="#e4e4e7" font-size="20">{html.escape(title)}</text>'
    )
    out.append("</svg>")
    return "".join(out)


def _occupancy_grid(
    points: list[dict[str, Any]], grid_size: int, range_max_mm: float
) -> dict[str, Any]:
    """Coarse top-down grid (+y forward, row 0 = far edge). Cells: '1' occupied."""
    cell = (2 * range_max_mm) / grid_size
    occ: set[tuple[int, int]] = set()
    for p in points:
        if not p["is_valid"]:
            continue
        a = math.radians(p["angle_deg"])
        ix = int((p["distance_mm"] * math.sin(a) + range_max_mm) / cell)
        iy = int((range_max_mm - p["distance_mm"] * math.cos(a)) / cell)
        if 0 <= ix < grid_size and 0 <= iy < grid_size:
            occ.add((iy, ix))
    rows = [
        "".join("1" if (iy, ix) in occ else "0" for ix in range(grid_size))
        for iy in range(grid_size)
    ]
    xs = [ix for _, ix in occ]
    ys = [iy for iy, _ in occ]
    return {
        "grid_size": grid_size,
        "cell_mm": round(cell, 1),
        "range_max_mm": range_max_mm,
        "occupied_count": len(occ),
        "bbox": (
            {"row_min": min(ys), "row_max": max(ys), "col_min": min(xs), "col_max": max(xs)}
            if occ
            else None
        ),
        "rows": rows,
    }


def _sector_minima(points: list[dict[str, Any]], sector_deg: float) -> list[float | None]:
    n = max(1, int(round(360.0 / sector_deg)))
    width = 360.0 / n
    minima: list[float | None] = [None] * n
    for p in points:
        if not p["is_valid"]:
            continue
        idx = int(p["angle_deg"] // width) % n
        if minima[idx] is None or p["distance_mm"] < minima[idx]:  # type: ignore[operator]
            minima[idx] = p["distance_mm"]
    return minima


async def lidar_scan(
    operation: str,
    ctx: Context = None,
    port: str = "",
    timeout_s: float = 3.0,
    source: str = "live",
    format: str = "both",
    grid_size: int = 100,
    range_max_mm: float = 0.0,
    scan_a: str = "",
    scan_b: str = "",
    sector_deg: float = 5.0,
    tolerance_mm: float = 150.0,
    note: str = "",
) -> dict[str, Any]:
    """Unified control for YDLIDAR USB LiDAR sensors.

    [RATIONALE] Consolidates all LiDAR operations (status, scan, stream,
    port discovery, persistence, mapping, diffing) into one portmanteau tool
    so agents don't need 6 separate tools for a simple USB sensor.

    Operations:
    - status: Device info, firmware, health, connected ports
    - scan: Single 360-degree scan, returns point cloud
    - stream_start: Begin continuous scan streaming
    - stream_read: Read one scan point from active stream
    - stream_stop: Stop continuous streaming
    - ports: List available serial ports (auto-detect LiDARs)
    - save: Live scan persisted to data/scans/ (repeatable experiments)
    - scans: List persisted scans (id, time, counts, note)
    - map: Polar SVG plot and/or occupancy grid, live or from a saved id
    - diff: Per-sector range change between two saved scans

    Map/diff params: source="live" or a saved scan id; format="svg"|"grid"|"both";
    grid_size 8-200; range_max_mm=0 auto-scales; tolerance_mm guards noise.

    ## Return Format
    {"success": bool, "message": str, "data": {...}}

    ## Examples
    lidar_scan(operation="status")
    lidar_scan(operation="scan", timeout_s=3.0)
    lidar_scan(operation="ports")
    lidar_scan(operation="save", note="door open")
    lidar_scan(operation="scans")
    lidar_scan(operation="map", source="live", format="svg")
    lidar_scan(operation="diff", scan_a="scan-20260906-120000", scan_b="scan-20260906-120500")
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
            return _error_response("status", e)

    if operation == "scan":
        if not resolved_port:
            return {
                "success": False,
                "message": "No LiDAR port set. Use operation='ports' to find it "
                "or set LIDAR_PORT env var.",
                "data": {},
            }
        try:
            result = _capture(resolved_port, timeout_s)
            valid = [p for p in result.points if p.is_valid]
            return {
                "success": True,
                "message": f"Scan complete: {result.point_count} points "
                f"({len(valid)} valid) in {result.duration_ms:.0f} ms",
                "data": {
                    "point_count": result.point_count,
                    "valid_count": len(valid),
                    "duration_ms": result.duration_ms,
                    "points": [_point_to_dict(p) for p in result.points],
                },
            }
        except Exception as e:
            return _error_response("scan", e)

    if operation == "save":
        if not resolved_port:
            return {
                "success": False,
                "message": "No LiDAR port set. Use operation='ports' to find it "
                "or set LIDAR_PORT env var.",
                "data": {},
            }
        try:
            payload = _save_scan(_capture(resolved_port, timeout_s), resolved_port, note)
            return {
                "success": True,
                "message": f"Saved {payload['scan_id']}: {payload['point_count']} points "
                f"({payload['valid_count']} valid)",
                "data": payload,
            }
        except Exception as e:
            return _error_response("save", e)

    if operation == "scans":
        try:
            items = []
            for path in sorted(_scans_dir().glob("scan-*.json"), reverse=True):
                doc = json.loads(path.read_text(encoding="utf-8"))
                items.append(
                    {
                        "scan_id": doc.get("scan_id", path.stem),
                        "saved_at": doc.get("saved_at", ""),
                        "note": doc.get("note", ""),
                        "point_count": doc.get("point_count", 0),
                        "valid_count": doc.get("valid_count", 0),
                    }
                )
            return {
                "success": True,
                "message": f"Found {len(items)} saved scans",
                "data": {"scans": items},
            }
        except Exception as e:
            return _error_response("scans", e)

    if operation == "map":
        if format not in ("svg", "grid", "both"):
            return {
                "success": False,
                "message": f"Unknown format: {format!r}. Use svg, grid, or both.",
                "data": {"valid_formats": ["svg", "grid", "both"]},
            }
        if not 8 <= grid_size <= _MAX_GRID:
            return {
                "success": False,
                "message": f"grid_size must be 8-{_MAX_GRID}, got {grid_size}.",
                "data": {},
            }
        try:
            if source == "live":
                if not resolved_port:
                    return {
                        "success": False,
                        "message": "No LiDAR port set. Use source=<scan_id> for saved scans "
                        "or set LIDAR_PORT env var.",
                        "data": {},
                    }
                result = _capture(resolved_port, timeout_s)
                points = [_point_to_dict(p) for p in result.points]
                label = f"live scan on {resolved_port}"
            else:
                doc = _load_scan(source)
                points = doc["points"]
                label = f"{source} ({doc.get('note', 'no note')})"
            valid_dists = [p["distance_mm"] for p in points if p["is_valid"]]
            auto_max = max(valid_dists) if valid_dists else 4000.0
            span = range_max_mm or max(auto_max * 1.1, 1000.0)
            data: dict[str, Any] = {
                "source": source,
                "point_count": len(points),
                "valid_count": len(valid_dists),
                "range_max_mm": round(span, 1),
            }
            if format in ("svg", "both"):
                data["svg"] = _render_svg(points, span, label)
            if format in ("grid", "both"):
                data["grid"] = _occupancy_grid(points, grid_size, span)
            return {
                "success": True,
                "message": f"Map ready: {len(valid_dists)} valid points over "
                f"{span / 1000:.1f} m ({label})",
                "data": data,
            }
        except Exception as e:
            return _error_response("map", e)

    if operation == "diff":
        if not scan_a or not scan_b:
            return {
                "success": False,
                "message": "diff needs scan_a and scan_b ids (see operation='scans').",
                "data": {},
            }
        try:
            mins_a = _sector_minima(_load_scan(scan_a)["points"], sector_deg)
            mins_b = _sector_minima(_load_scan(scan_b)["points"], sector_deg)
            width = 360.0 / len(mins_a)
            changed, gained, lost = [], 0, 0
            for i, (da, db) in enumerate(zip(mins_a, mins_b, strict=True)):
                if da is None and db is None:
                    continue
                if da is None or db is None:
                    gained, lost = (gained + 1, lost) if da is None else (gained, lost + 1)
                    changed.append(
                        {
                            "sector_deg": round(i * width, 1),
                            "scan_a_mm": da,
                            "scan_b_mm": db,
                            "delta_mm": None,
                        }
                    )
                elif abs(db - da) > tolerance_mm:
                    changed.append(
                        {
                            "sector_deg": round(i * width, 1),
                            "scan_a_mm": round(da, 1),
                            "scan_b_mm": round(db, 1),
                            "delta_mm": round(db - da, 1),
                        }
                    )
            changed.sort(
                key=lambda c: abs(c["delta_mm"]) if c["delta_mm"] is not None else float("inf"),
                reverse=True,
            )
            return {
                "success": True,
                "message": f"{len(changed)}/{len(mins_a)} sectors changed "
                f"(>{tolerance_mm:.0f} mm; +{gained} appeared, -{lost} cleared)",
                "data": {
                    "scan_a": scan_a,
                    "scan_b": scan_b,
                    "sector_deg": width,
                    "tolerance_mm": tolerance_mm,
                    "changed_count": len(changed),
                    "changed": changed[:36],
                },
            }
        except Exception as e:
            return _error_response("diff", e)

    if operation == "stream_start":
        return {
            "success": False,
            "message": "Streaming via stdio MCP is not recommended. "
            "Use scan (single capture) or connect via HTTP SSE "
            "for persistent stream access.",
            "data": {},
        }

    return {
        "success": False,
        "message": f"Unknown operation: {operation}",
        "data": {
            "valid_operations": [
                "status",
                "scan",
                "stream_start",
                "stream_read",
                "stream_stop",
                "ports",
                "save",
                "scans",
                "map",
                "diff",
            ]
        },
    }


async def lidar_shutdown(reason: str = "operator requested shutdown") -> dict[str, Any]:
    """Gracefully shut down the lidar-mcp server process.

    Schedules an orderly exit after a short delay so in-flight responses can
    flush. The owning process (uvicorn daemon or stdio client) reaps it.

    ## Return Format
    {"success": bool, "message": str, "reason": str}

    ## Examples
    lidar_shutdown()
    lidar_shutdown(reason="robot packed up for the night")
    """

    async def _schedule_exit() -> None:
        await asyncio.sleep(0.5)
        os._exit(0)

    logger.warning("Shutdown requested via lidar_shutdown: %s", reason)
    task = asyncio.create_task(_schedule_exit())
    _shutdown_tasks.add(task)
    task.add_done_callback(_shutdown_tasks.discard)
    return {"success": True, "message": "Shutdown scheduled", "reason": reason}


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

        app = PrefabApp(title="YDLIDAR - No Port")
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

            text = (
                f"LiDAR scan: {scan.point_count} points ({len(valid)} valid), "
                f"range {min_dist:.0f}-{max_dist:.0f} mm on {port}"
            )
            return {"content": text, "structured_content": app}
        finally:
            stream_stop(ser)
            ser.close()
    except Exception as e:
        from prefab_ui import PrefabApp
        from prefab_ui.components import Div, Text

        app = PrefabApp(title="YDLIDAR - Error")
        app.add(Div())
        app.add(Text(str(e)))
        return {"content": f"LiDAR error: {e}", "structured_content": app}
