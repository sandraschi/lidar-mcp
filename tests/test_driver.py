"""Driver unit tests — pure protocol logic, hardware fully mocked."""

import struct

import pytest
import serial

from lidar_mcp import ydlidar_driver as drv


def test_crc16_modbus_check_value():
    # Standard Modbus check: CRC16 of b"123456789" is 0xBB3D.
    assert drv._crc16(b"123456789") == 0xBB3D
    assert drv._crc16(b"") == 0x0000


def test_model_names():
    assert drv.LidarDeviceInfo(model=2).model_name == "X4"
    assert drv.LidarDeviceInfo(model=5).model_name == "G4"
    assert drv.LidarDeviceInfo(model=99).model_name == "Unknown(99)"


def test_health_text():
    assert drv.LidarHealth(status=0).status_text == "good"
    assert drv.LidarHealth(status=1).status_text == "warning"
    assert drv.LidarHealth(status=2).status_text == "error"
    assert drv.LidarHealth(status=9).status_text == "unknown"


class _FakePort:
    def __init__(self, device, description, hwid=""):
        self.device = device
        self.description = description
        self.hwid = hwid


def test_list_ports_prefers_lidar_candidates(monkeypatch):
    ports = [
        _FakePort("COM1", "Communications Port"),
        _FakePort("COM3", "Silicon Labs CP210x USB to UART Bridge"),
    ]
    monkeypatch.setattr(drv.serial.tools.list_ports, "comports", lambda: ports)
    found = drv.list_ports()
    assert [p["port"] for p in found] == ["COM3"]


def test_list_ports_falls_back_to_all(monkeypatch):
    ports = [_FakePort("COM1", "Communications Port")]
    monkeypatch.setattr(drv.serial.tools.list_ports, "comports", lambda: ports)
    assert [p["port"] for p in drv.list_ports()] == ["COM1"]


class _RaisingSerial:
    def __init__(self, *args, **kwargs):
        raise serial.SerialException("port busy")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_probe_port_reports_unopenable(monkeypatch):
    monkeypatch.setattr(drv.serial, "Serial", _RaisingSerial)
    result = drv.probe_port("COM9")
    assert result["success"] is False
    assert "Cannot open port" in result["error"]


def test_connect_raises_after_all_bauds_fail(monkeypatch):
    monkeypatch.setattr(drv.serial, "Serial", _RaisingSerial)
    with pytest.raises(ConnectionError, match="Could not connect"):
        drv.connect("COM9")


def _point_bytes(quality: int, angle_deg: float, dist_mm: float) -> bytes:
    angle_raw = int(angle_deg * 64)
    dist_raw = int(dist_mm * 4)
    return bytes([quality & 0xFF]) + struct.pack("<H", angle_raw) + struct.pack("<H", dist_raw)


class _CannedSerial:
    """Feeds a canned byte stream; records writes."""

    def __init__(self, stream: bytes):
        self._stream = stream
        self.written = b""
        self.timeout = 1

    def write(self, data: bytes) -> int:
        self.written += data
        return len(data)

    def read(self, n: int) -> bytes:
        chunk, self._stream = self._stream[:n], self._stream[n:]
        return chunk

    def flushInput(self):
        pass

    def flushOutput(self):
        pass

    def close(self):
        pass


def _descriptor(resp_type: int) -> bytes:
    return bytes([0xA5, 0x5A, 0x00, 0x00, resp_type, 0x00, 0x00])


def test_scan_once_parses_rotation():
    stream = (
        _descriptor(drv.RESP_TYPE_SCAN)
        + _point_bytes(0x80 | 90, 0.0, 450.0)  # sync: rotation start
        + _point_bytes(85, 1.0, 1230.0)
        + _point_bytes(0, 2.0, 0.0)  # quality 0 -> invalid
        + _point_bytes(0x80 | 88, 3.0, 900.0)  # second sync ends scan
    )
    ser = _CannedSerial(stream)
    result = drv.scan_once(ser, timeout_s=2.0)
    assert result.point_count == 3
    assert ser.written.startswith(bytes([0xA5, drv.CMD_STOP]))
    first, second, third = result.points
    assert first.is_sync and first.is_valid
    assert first.angle_deg == pytest.approx(0.0)
    assert first.distance_mm == pytest.approx(450.0)
    assert second.angle_deg == pytest.approx(1.0)
    assert not third.is_valid  # quality 0 with zero distance
    assert result.duration_ms >= 0


def test_scan_once_rejects_wrong_response():
    ser = _CannedSerial(_descriptor(drv.RESP_TYPE_HEALTH))
    with pytest.raises(ConnectionError, match="Expected scan response"):
        drv.scan_once(ser, timeout_s=1.0)


def test_stream_stop_sends_stop():
    ser = _CannedSerial(b"")
    drv.stream_stop(ser)
    assert ser.written == bytes([0xA5, drv.CMD_STOP])
