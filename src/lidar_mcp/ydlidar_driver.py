"""Raw serial protocol driver for YDLIDAR USB LiDAR sensors.

Communicates over USB CDC ACM (virtual serial port). The protocol is
documented in the YDLIDAR SDK2 manual: packet-framed binary with CRC16.

Supported models: X2, X4, G1, G4, S2, S4, S2B, S4B (any YDLIDAR using
the standard SDK2 protocol).
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Any

import serial
import serial.tools.list_ports

# -- Protocol constants --

CMD_STOP = 0x65
CMD_SCAN = 0x60
CMD_FORCE_SCAN = 0x61
CMD_DEVICE_INFO = 0xA0
CMD_HEALTH = 0x90

RESP_DESCRIPTOR_HEADER = bytes([0xA5, 0x5A])
RESP_TYPE_DEVICE_INFO = 0x04
RESP_TYPE_HEALTH = 0x06
RESP_TYPE_SCAN = 0x81

# Default baud rates by model tier
BAUD_X2 = 115200
BAUD_X4 = 230400
BAUD_G4 = 500000
BAUD_SERIES = 230400


# -- Data models --


@dataclass
class LidarDeviceInfo:
    model: int = 0
    firmware_minor: int = 0
    firmware_major: int = 0
    hardware: int = 0
    serial: str = ""

    @property
    def model_name(self) -> str:
        names = {
            1: "X2",
            2: "X4",
            3: "X1",
            4: "G1",
            5: "G4",
            6: "S2",
            7: "S4",
            8: "S2B",
            9: "S4B",
            10: "T1",
            11: "G1",
            12: "G4",
            13: "G6",
            14: "TX8",
            15: "TX20",
            16: "G6",
        }
        return names.get(self.model, f"Unknown({self.model})")


@dataclass
class LidarHealth:
    status: int = 0
    error_code: int = 0

    @property
    def status_text(self) -> str:
        return {0: "good", 1: "warning", 2: "error"}.get(self.status, "unknown")


@dataclass
class ScanPoint:
    quality: int = 0
    angle_deg: float = 0.0
    distance_mm: float = 0.0
    is_sync: bool = False
    is_valid: bool = False


@dataclass
class ScanResult:
    points: list[ScanPoint] = field(default_factory=list)
    point_count: int = 0
    duration_ms: float = 0.0


# -- CRC16-Modbus --

_CRC16_TABLE = [
    0x0000,
    0xCC01,
    0xD801,
    0x1400,
    0xF001,
    0x3C00,
    0x2800,
    0xE401,
    0xA001,
    0x6C00,
    0x7800,
    0xB401,
    0x5000,
    0x9C01,
    0x8801,
    0x4400,
]


def _crc16(data: bytes) -> int:
    crc = 0
    for b in data:
        crc = (crc >> 4) ^ _CRC16_TABLE[(crc ^ (b & 0xF)) & 0x0F]
        crc = (crc >> 4) ^ _CRC16_TABLE[(crc ^ ((b >> 4) & 0xF)) & 0x0F]
    return crc


# -- Serial I/O helpers --


def _read_strict(ser: serial.Serial, n: int) -> bytes:
    data = ser.read(n)
    if len(data) < n:
        raise ConnectionError(
            f"Short read: wanted {n} bytes, got {len(data)}. Check LiDAR connection and baud rate."
        )
    return data


def _send_cmd(ser: serial.Serial, cmd: int) -> None:
    ser.write(bytes([0xA5, cmd]))


def _read_descriptor(ser: serial.Serial) -> tuple[int, int, int]:
    """Read the 7-byte response descriptor. Returns (length, resp_type, crc)."""
    header = _read_strict(ser, 2)
    if header != RESP_DESCRIPTOR_HEADER:
        raise ConnectionError(
            f"Bad response header: {header.hex()} "
            f"(expected a5 5a). LiDAR may be in use or unresponsive."
        )
    length_low = _read_strict(ser, 1)[0]
    length_high = _read_strict(ser, 1)[0]
    resp_type = _read_strict(ser, 1)[0]
    crc = struct.unpack("<H", _read_strict(ser, 2))[0]
    length = (length_high << 8) | length_low
    return length, resp_type, crc


def _read_response_data(ser: serial.Serial, length: int) -> bytes:
    data = _read_strict(ser, length)
    return data


# -- Public API --


def list_ports() -> list[dict[str, str]]:
    """List serial ports that look like YDLIDAR devices."""
    candidates = []
    for p in serial.tools.list_ports.comports():
        desc = (p.description or "").lower()
        if "cp210" in desc or "ch340" in desc or "silicon" in desc or "usb serial" in desc:
            candidates.append({"port": p.device, "description": p.description, "vid_pid": p.hwid})
    return candidates or [
        {"port": p.device, "description": p.description, "vid_pid": p.hwid}
        for p in serial.tools.list_ports.comports()
    ]


def probe_port(port: str, baud: int = BAUD_X4) -> dict[str, Any]:
    """Probe a serial port to see if a YDLIDAR is connected.

    Tries to get device info and health. Returns success/failure with
    meaningful error messages.
    """
    for test_baud in [BAUD_X4, BAUD_X2, BAUD_G4, BAUD_SERIES]:
        try:
            with serial.Serial(port, test_baud, timeout=1) as ser:
                ser.flushInput()
                ser.flushOutput()
                try:
                    info = _get_device_info(ser)
                    health = _get_health(ser)
                    return {
                        "success": True,
                        "port": port,
                        "baud": test_baud,
                        "device": {
                            "model": info.model,
                            "model_name": info.model_name,
                            "firmware": f"v{info.firmware_major}.{info.firmware_minor}",
                            "hardware": info.hardware,
                            "serial": info.serial,
                        },
                        "health": {
                            "status": health.status_text,
                            "error_code": health.error_code,
                        },
                    }
                except ConnectionError:
                    continue
        except serial.SerialException as e:
            return {
                "success": False,
                "port": port,
                "error": f"Cannot open port: {e}",
            }

    return {
        "success": False,
        "port": port,
        "error": "No YDLIDAR detected on this port",
        "hint": "Verify: (1) LiDAR is plugged in, (2) correct port, "
        "(3) no other process claims the serial device",
    }


def connect(port: str, baud: int | None = None) -> serial.Serial:
    """Open serial connection to the LiDAR.

    If baud is None, auto-detects by trying common rates.
    """
    if baud is not None:
        ser = serial.Serial(port, baud, timeout=1)
        ser.flushInput()
        ser.flushOutput()
        return ser

    for test_baud in [BAUD_X4, BAUD_X2, BAUD_G4, BAUD_SERIES]:
        try:
            ser = serial.Serial(port, test_baud, timeout=1)
        except serial.SerialException:
            continue
        try:
            ser.flushInput()
            ser.flushOutput()
            _send_cmd(ser, CMD_STOP)
            import time

            time.sleep(0.1)
            _get_device_info(ser)
            return ser
        except (ConnectionError, serial.SerialException):
            try:
                ser.close()
            except serial.SerialException:
                pass
            continue

    raise ConnectionError(
        f"Could not connect to YDLIDAR on {port} at any baud rate "
        f"(tried {BAUD_X2}, {BAUD_X4}, {BAUD_G4}, {BAUD_SERIES})"
    )


def _get_device_info(ser: serial.Serial) -> LidarDeviceInfo:
    _send_cmd(ser, CMD_DEVICE_INFO)
    length, resp_type, crc = _read_descriptor(ser)
    if resp_type != RESP_TYPE_DEVICE_INFO:
        raise ConnectionError(f"Expected device info response (0x04), got 0x{resp_type:02x}")
    if length < 5:
        raise ConnectionError(f"Device info too short: {length} bytes")
    data = _read_response_data(ser, length)

    model = data[0]
    fm_minor = data[1]
    fm_major = data[2]
    hw = data[3]
    serial_bytes = data[4 : 4 + 16] if len(data) >= 20 else data[4:]
    serial_str = serial_bytes.rstrip(b"\x00").decode("ascii", errors="replace")

    return LidarDeviceInfo(model, fm_minor, fm_major, hw, serial_str)


def _get_health(ser: serial.Serial) -> LidarHealth:
    _send_cmd(ser, CMD_HEALTH)
    length, resp_type, crc = _read_descriptor(ser)
    if resp_type != RESP_TYPE_HEALTH:
        raise ConnectionError(f"Expected health response (0x06), got 0x{resp_type:02x}")
    data = _read_response_data(ser, length)
    status = data[0] if len(data) > 0 else 2
    error_code = struct.unpack("<H", data[1:3])[0] if len(data) >= 3 else 0
    return LidarHealth(status, error_code)


def scan_once(ser: serial.Serial, timeout_s: float = 2.0) -> ScanResult:
    """Perform a single 360-degree scan and return all points.

    Sends a scan command, reads all points until a full rotation is captured
    (detected by the sync flag on each point).
    """
    import time

    ser.timeout = max(0.1, timeout_s / 10)

    _send_cmd(ser, CMD_STOP)
    time.sleep(0.05)
    ser.flushInput()

    _send_cmd(ser, CMD_SCAN)
    length, resp_type, crc = _read_descriptor(ser)
    if resp_type != RESP_TYPE_SCAN:
        raise ConnectionError(f"Expected scan response (0x81), got 0x{resp_type:02x}")

    points: list[ScanPoint] = []
    start_time = time.time()
    synced_once = False
    sync_count = 0

    while time.time() - start_time < timeout_s:
        raw = _read_strict(ser, 5)
        quality_byte = raw[0]
        angle_raw = struct.unpack("<H", raw[1:3])[0]
        dist_raw = struct.unpack("<H", raw[3:5])[0]

        is_sync = bool(quality_byte & 0x80)
        quality = quality_byte & 0x7F
        angle_deg = angle_raw / 64.0
        distance_mm = dist_raw / 4.0
        is_valid = quality > 0 and dist_raw > 0

        point = ScanPoint(
            quality=quality,
            angle_deg=angle_deg,
            distance_mm=distance_mm,
            is_sync=is_sync,
            is_valid=is_valid,
        )

        if is_sync:
            sync_count += 1
            if synced_once and sync_count >= 2:
                break
            synced_once = True

        points.append(point)

    duration = (time.time() - start_time) * 1000
    return ScanResult(points=points, point_count=len(points), duration_ms=duration)


def stream_start(ser: serial.Serial) -> None:
    """Start continuous scan streaming."""
    _send_cmd(ser, CMD_STOP)
    import time

    time.sleep(0.05)
    ser.flushInput()
    _send_cmd(ser, CMD_SCAN)
    length, resp_type, crc = _read_descriptor(ser)
    if resp_type != RESP_TYPE_SCAN:
        raise ConnectionError(f"Expected scan response (0x81), got 0x{resp_type:02x}")


def stream_read_point(ser: serial.Serial) -> ScanPoint | None:
    """Read a single scan point from an active stream."""
    raw = _read_strict(ser, 5)
    quality_byte = raw[0]
    angle_raw = struct.unpack("<H", raw[1:3])[0]
    dist_raw = struct.unpack("<H", raw[3:5])[0]

    return ScanPoint(
        quality=quality_byte & 0x7F,
        angle_deg=angle_raw / 64.0,
        distance_mm=dist_raw / 4.0,
        is_sync=bool(quality_byte & 0x80),
        is_valid=(quality_byte & 0x7F) > 0 and dist_raw > 0,
    )


def stream_stop(ser: serial.Serial) -> None:
    """Stop scan streaming."""
    _send_cmd(ser, CMD_STOP)
