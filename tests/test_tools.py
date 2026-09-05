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


async def test_scan_success_returns_point_cloud(monkeypatch):
    monkeypatch.setenv("LIDAR_PORT", "COM3")
    monkeypatch.setattr(lidar_tools, "connect", lambda port, baud=None: _FakeSer())
    monkeypatch.setattr(lidar_tools, "stream_stop", lambda ser: None)
    points = [
        ScanPoint(quality=90, angle_deg=0.0, distance_mm=450.0, is_sync=True, is_valid=True),
        ScanPoint(quality=0, angle_deg=1.0, distance_mm=0.0, is_sync=False, is_valid=False),
    ]
    monkeypatch.setattr(
        lidar_tools,
        "scan_once",
        lambda ser, timeout_s=2.0: ScanResult(points=points, point_count=2, duration_ms=12.0),
    )
    result = await lidar_tools.lidar_scan(operation="scan")
    assert result["success"] is True
    assert result["data"]["point_count"] == 2
    assert result["data"]["valid_count"] == 1
    assert result["data"]["points"][0]["angle_deg"] == 0.0


async def test_health_card_success_summarises_scan(monkeypatch):
    monkeypatch.setenv("LIDAR_PORT", "COM3")
    monkeypatch.setattr(lidar_tools, "connect", lambda port, baud=None: _FakeSer())
    monkeypatch.setattr(lidar_tools, "stream_stop", lambda ser: None)
    points = [
        ScanPoint(quality=90, angle_deg=0.0, distance_mm=450.0, is_sync=True, is_valid=True),
        ScanPoint(quality=80, angle_deg=180.0, distance_mm=900.0, is_sync=False, is_valid=True),
    ]
    monkeypatch.setattr(
        lidar_tools,
        "scan_once",
        lambda ser, timeout_s=2.0: ScanResult(points=points, point_count=2, duration_ms=12.0),
    )
    result = await lidar_tools.show_lidar_health_card()
    assert "2 points (2 valid)" in result["content"]
    assert "450-900 mm" in result["content"]
