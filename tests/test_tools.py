"""Tool-layer tests — driver/hardware fully mocked, no LiDAR required."""

import pytest

from lidar_mcp.tools import lidar_tools
from lidar_mcp.ydlidar_driver import ScanPoint, ScanResult


@pytest.fixture(autouse=True)
def _no_lidar_env(monkeypatch):
    monkeypatch.delenv("LIDAR_PORT", raising=False)
    monkeypatch.delenv("LIDAR_BAUD", raising=False)


async def test_ports_operation_lists_detected(monkeypatch):
    monkeypatch.setattr(
        lidar_tools, "list_ports", lambda: [{"port": "COM3", "description": "CP210x"}]
    )
    result = await lidar_tools.lidar_scan(operation="ports")
    assert result["success"] is True
    assert result["data"]["ports"][0]["port"] == "COM3"
    assert "message" in result


async def test_unknown_operation_lists_valid_ops():
    result = await lidar_tools.lidar_scan(operation="bogus")
    assert result["success"] is False
    assert "ports" in result["data"]["valid_operations"]


async def test_status_without_port_returns_candidates(monkeypatch):
    monkeypatch.setattr(lidar_tools, "list_ports", lambda: [{"port": "COM3"}])
    result = await lidar_tools.lidar_scan(operation="status")
    assert result["success"] is False
    assert result["data"]["ports"] == [{"port": "COM3"}]


async def test_scan_without_port_explains_setup():
    result = await lidar_tools.lidar_scan(operation="scan")
    assert result["success"] is False
    assert "LIDAR_PORT" in result["message"]


async def test_status_error_path_uses_helper(monkeypatch):
    monkeypatch.setenv("LIDAR_PORT", "COM3")

    def _boom(port):
        raise ConnectionError("unplugged")

    monkeypatch.setattr(lidar_tools, "probe_port", _boom)
    result = await lidar_tools.lidar_scan(operation="status")
    assert result["success"] is False
    assert result["message"].startswith("status failed")


async def test_scan_error_path_uses_helper(monkeypatch):
    monkeypatch.setenv("LIDAR_PORT", "COM3")

    def _boom(port, baud=None):
        raise ConnectionError("no device")

    monkeypatch.setattr(lidar_tools, "connect", _boom)
    result = await lidar_tools.lidar_scan(operation="scan")
    assert result["success"] is False
    assert result["message"].startswith("scan failed")


async def test_stream_start_points_to_sse():
    result = await lidar_tools.lidar_scan(operation="stream_start")
    assert result["success"] is False
    assert "SSE" in result["message"]


async def test_shutdown_schedules_exit(monkeypatch):
    calls = []
    monkeypatch.setattr(lidar_tools.os, "_exit", lambda code: calls.append(code))

    async def _no_sleep(delay):
        return None

    monkeypatch.setattr(lidar_tools.asyncio, "sleep", _no_sleep)
    result = await lidar_tools.lidar_shutdown(reason="test")
    assert result == {
        "success": True,
        "message": "Shutdown scheduled",
        "reason": "test",
    }
    # Await the scheduled task directly (the test's own sleep is also mocked).
    tasks = list(lidar_tools._shutdown_tasks)
    assert len(tasks) == 1
    await tasks[0]
    assert calls == [0]


async def test_health_card_without_port_mentions_env(monkeypatch):
    monkeypatch.setattr(lidar_tools, "list_ports", lambda: [])
    result = await lidar_tools.show_lidar_health_card()
    assert "LIDAR_PORT" in result["content"]


class _FakeSer:
    def close(self):
        pass


def _two_points():
    return [
        ScanPoint(quality=90, angle_deg=0.0, distance_mm=450.0, is_sync=True, is_valid=True),
        ScanPoint(quality=0, angle_deg=1.0, distance_mm=0.0, is_sync=False, is_valid=False),
    ]


def _mock_live_scan(monkeypatch, points):
    monkeypatch.setenv("LIDAR_PORT", "COM3")
    monkeypatch.setattr(lidar_tools, "connect", lambda port, baud=None: _FakeSer())
    monkeypatch.setattr(lidar_tools, "stream_stop", lambda ser: None)
    monkeypatch.setattr(
        lidar_tools,
        "scan_once",
        lambda ser, timeout_s=2.0: ScanResult(
            points=points, point_count=len(points), duration_ms=12.0
        ),
    )


@pytest.fixture()
def _data_dir(tmp_path, monkeypatch):
    d = tmp_path / "scans"
    monkeypatch.setenv("LIDAR_DATA_DIR", str(d))
    return d


async def test_scan_success_returns_point_cloud(monkeypatch):
    _mock_live_scan(monkeypatch, _two_points())
    result = await lidar_tools.lidar_scan(operation="scan")
    assert result["success"] is True
    assert result["data"]["point_count"] == 2
    assert result["data"]["valid_count"] == 1
    assert result["data"]["points"][0]["angle_deg"] == 0.0


async def test_health_card_success_summarises_scan(monkeypatch):
    _mock_live_scan(monkeypatch, _two_points())
    monkeypatch.setattr(
        lidar_tools,
        "scan_once",
        lambda ser, timeout_s=2.0: ScanResult(
            points=[
                ScanPoint(
                    quality=90, angle_deg=0.0, distance_mm=450.0, is_sync=True, is_valid=True
                ),
                ScanPoint(
                    quality=80, angle_deg=180.0, distance_mm=900.0, is_sync=False, is_valid=True
                ),
            ],
            point_count=2,
            duration_ms=12.0,
        ),
    )
    result = await lidar_tools.show_lidar_health_card()
    assert "2 points (2 valid)" in result["content"]
    assert "450-900 mm" in result["content"]


async def test_save_persists_scan_with_note(monkeypatch, _data_dir):
    _mock_live_scan(monkeypatch, _two_points())
    result = await lidar_tools.lidar_scan(operation="save", note="door open")
    assert result["success"] is True
    scan_id = result["data"]["scan_id"]
    assert (_data_dir / f"{scan_id}.json").exists()
    assert result["data"]["valid_count"] == 1


async def test_scans_lists_saved(monkeypatch, _data_dir):
    _mock_live_scan(monkeypatch, _two_points())
    await lidar_tools.lidar_scan(operation="save", note="first")
    await lidar_tools.lidar_scan(operation="save", note="second")
    result = await lidar_tools.lidar_scan(operation="scans")
    assert result["success"] is True
    assert len(result["data"]["scans"]) == 2
    assert {s["note"] for s in result["data"]["scans"]} == {"first", "second"}


async def test_map_svg_from_saved_scan(monkeypatch, _data_dir):
    _mock_live_scan(monkeypatch, _two_points())
    saved = await lidar_tools.lidar_scan(operation="save")
    result = await lidar_tools.lidar_scan(
        operation="map", source=saved["data"]["scan_id"], format="svg"
    )
    assert result["success"] is True
    assert result["data"]["svg"].startswith("<svg")
    assert "closest:" in result["data"]["svg"]


async def test_map_grid_shape_and_occupancy(monkeypatch, _data_dir):
    _mock_live_scan(monkeypatch, _two_points())
    saved = await lidar_tools.lidar_scan(operation="save")
    result = await lidar_tools.lidar_scan(
        operation="map", source=saved["data"]["scan_id"], format="grid", grid_size=10
    )
    grid = result["data"]["grid"]
    assert grid["grid_size"] == 10
    assert len(grid["rows"]) == 10
    assert grid["occupied_count"] == 1  # only one valid point in fixture
    assert grid["bbox"] is not None


async def test_map_rejects_bad_format_and_grid():
    bad_fmt = await lidar_tools.lidar_scan(operation="map", format="png")
    assert bad_fmt["success"] is False
    bad_grid = await lidar_tools.lidar_scan(operation="map", grid_size=500)
    assert bad_grid["success"] is False
    unknown = await lidar_tools.lidar_scan(operation="map", source="scan-nope")
    assert unknown["success"] is False
    assert "Unknown scan id" in unknown["message"]


async def test_map_live_requires_port():
    result = await lidar_tools.lidar_scan(operation="map", source="live")
    assert result["success"] is False
    assert "LIDAR_PORT" in result["message"]


async def test_diff_detects_moved_obstacle(monkeypatch, _data_dir):
    _mock_live_scan(
        monkeypatch,
        [ScanPoint(quality=90, angle_deg=0.0, distance_mm=500.0, is_sync=True, is_valid=True)],
    )
    scan_a = (await lidar_tools.lidar_scan(operation="save"))["data"]["scan_id"]
    _mock_live_scan(
        monkeypatch,
        [ScanPoint(quality=90, angle_deg=0.0, distance_mm=2000.0, is_sync=True, is_valid=True)],
    )
    scan_b = (await lidar_tools.lidar_scan(operation="save"))["data"]["scan_id"]
    result = await lidar_tools.lidar_scan(operation="diff", scan_a=scan_a, scan_b=scan_b)
    assert result["success"] is True
    assert result["data"]["changed_count"] >= 1
    assert result["data"]["changed"][0]["delta_mm"] == pytest.approx(1500.0)


async def test_diff_requires_both_ids():
    result = await lidar_tools.lidar_scan(operation="diff", scan_a="scan-x")
    assert result["success"] is False
    assert "scan_a and scan_b" in result["message"]
