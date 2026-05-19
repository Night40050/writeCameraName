"""
core/robot_hand.py
==================
Serial interface to the ESP32-powered robotic hand.

The ESP32 Arduino firmware (mano/MANOOOO.ino) listens at 115200 baud and
executes sign-language sequences for every received word or individual letter.

Usage
-----
    from core.robot_hand import RobotHand

    hand = RobotHand()          # auto-detects COM port
    hand.connect()
    hand.send_text("DANIEL")    # sends "DANIEL\\n" to the ESP32
    hand.close()
"""

from __future__ import annotations

import glob
import logging
import sys
from typing import Optional

import serial
import serial.tools.list_ports

import config

logger = logging.getLogger("airsign.robot_hand")

# ── Keywords used by find_esp32_port() to identify ESP32 boards ───────────────
_ESP32_KEYWORDS = [
    "esp32",        # native USB descriptor on ESP32-C3 / ESP32-S3, etc.
    "Silicon Labs", # CP2102 / CP2104 — most common ESP32-S2/S3 adapter
    "FTDI",         # FT232R — official ESP32 dev-kits
    "CH340",        # cheap USB-to-serial (ESP32-WROOM boards)
    "WCH",          # CH340 / CH341G — vendor name "wch.cn"
    "Espressif",    # Espressif Systems native USB CDC
    "CP210",        # generic CP210x family
]


class RobotHand:
    """Non-blocking serial wrapper for the ESP32 robotic-hand controller.

    All writes are non-blocking (OS-level ``write_timeout`` + ``timeout`` on the
    underlying :class:`serial.Serial` object).  If the ESP32 is not connected the
    error is caught, logged, and **no exception propagates** to the caller — the
    AirSign main loop continues uninterrupted.

    Parameters
    ----------
    port:
        Explicit serial port path (e.g. ``"COM3"``).  Takes priority over
        auto-detection and ``config.SERIAL_PORT``.
    baudrate:
        Baud rate (default: ``config.SERIAL_BAUDRATE``).
    timeout:
        Read / write timeout in seconds (default: ``config.SERIAL_TIMEOUT``).
    auto_detect:
        When *True* and no explicit *port* is given, call
        :meth:`find_esp32_port` to identify the ESP32 adapter before
        falling back to the generic first-available-port scanner.
    """

    def __init__(
        self,
        port: Optional[str] = None,
        baudrate: int = config.SERIAL_BAUDRATE,
        timeout: float = config.SERIAL_TIMEOUT,
        auto_detect: bool = True,
    ) -> None:
        self._port   = port
        self._baudrate = baudrate
        self._timeout  = timeout
        self._auto_detect = auto_detect
        self._serial: Optional[serial.Serial] = None
        self._autodetected: bool = False

    # ── public helpers ─────────────────────────────────────────────────────────

    def connect(self) -> bool:
        """Open the serial connection.

        The port is resolved through :meth:`_resolve_port`, honouring the
        priority order: explicit *port* → *config.SERIAL_PORT* →
        ESP32-aware auto-detection → first-available port.

        Returns
        -------
        bool
            ``True`` if the port opened successfully; ``False`` otherwise.
            When ``False``, the robot-hand subsystem is considered disabled
            and subsequent calls to :meth:`send_text` will be no-ops.
        """
        port = self._resolve_port()
        if not port:
            logger.warning(
                "RobotHand: no suitable serial port found — "
                "robot hand disabled."
            )
            return False

        try:
            self._serial = serial.Serial(
                port=port,
                baudrate=self._baudrate,
                timeout=self._timeout,
                write_timeout=self._timeout,
            )
            # Give the ESP32 a moment to settle after DTR/RTS toggle
            import time as _time
            _time.sleep(0.5)
            self._serial.reset_input_buffer()
            self._serial.reset_output_buffer()
            logger.info(
                "RobotHand: connected to %s @ %d baud", port, self._baudrate
            )
            return True

        except (serial.SerialException, OSError) as exc:
            logger.warning(
                "RobotHand: could not open %s (%s) — robot hand disabled.",
                port,
                exc,
            )
            self._serial = None
            return False

    def send_text(self, text: str) -> bool:
        """Send *text* to the ESP32.

        The content is converted to ``str.upper().strip()``, then a trailing
        newline is appended before transmission.  This matches the Arduino
        firmware's ``Serial.readStringUntil('\\n')`` line parser.

        Parameters
        ----------
        text:
            Plain-text string to be spelled by the robotic hand (ASCII Latin).

        Returns
        -------
        bool
            ``True`` if all bytes were successfully written;
            ``False`` if the port is unavailable, the write timed out, or a
            serial error occurred.  In every failure case a warning is logged
            and the instance is marked **disconnected** so subsequent calls
            return ``False`` immediately.
        """
        if self._serial is None or not self._serial.is_open:
            logger.debug(
                "RobotHand: send_text() called while port is closed — ignoring."
            )
            return False

        payload = text.upper().strip() + "\n"
        try:
            written = self._serial.write(payload.encode("ascii", errors="ignore"))
            logger.debug(
                "RobotHand: queued %d bytes → %r", written, payload.strip()
            )
            return written == len(payload)

        except serial.SerialTimeoutException:
            logger.error(
                "RobotHand: write timed out — command dropped: %r", payload
            )
            return False

        except serial.SerialException as exc:
            logger.error("RobotHand: serial error while sending: %s", exc)
            self._close_silent()
            return False

    def close(self) -> None:
        """Gracefully shut down the serial connection (idempotent)."""
        self._close_silent()
        logger.info("RobotHand: serial port closed.")

    # ── optional stdout forwarding from ESP32 ──────────────────────────────────

    def available(self) -> int:
        """Return the number of bytes waiting in the input buffer (0 if closed)."""
        if self._serial and self._serial.is_open:
            return self._serial.in_waiting
        return 0

    def read_line(self) -> Optional[str]:
        """Read one line from the ESP32 (non-blocking). Returns ``None`` on EOL."""
        if self._serial and self._serial.is_open:
            raw = self._serial.readline()
            if raw:
                return raw.decode("ascii", errors="replace").strip()
        return None

    # ── dunder ─────────────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        port_info = (
            self._serial.port if (self._serial and self._serial.is_open)
            else "<closed>"
        )
        return f"RobotHand(port={port_info!r}, baudrate={self._baudrate})"

    def __enter__(self) -> "RobotHand":
        self.connect()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    # ── ESP32-aware port detection ─────────────────────────────────────────────

    @classmethod
    def find_esp32_port(
        cls,
        keywords: Optional[list[str]] = None,
    ) -> Optional[str]:
        """Scan all available serial ports and return the first one whose
        manufacturer, product descriptor, or hardware-ID string contains any
        keyword associated with ESP32 or common USB-to-serial adapters used
        with ESP32 boards.

        Detection heuristics
        --------------------
        The port is considered an ESP32 candidate when **any** of the
        following strings (case-insensitive substring match) is found in the
        port's description, manufacturer name, or hardware-ID:

        * ``esp32``, ``Espressif`` — ESP32 native USB CDC
        * ``Silicon Labs`` — Silicon Labs CP2102 / CP2104 adapter
        * ``FTDI`` — FT232R / FTDI-based adapters
        * ``CH340``, ``WCH`` — CH340 / CH341 USB-to-serial (widespread on
          ESP32-WROOM-32 dev-kits from Asia)

        Parameters
        ----------
        keywords:
            Override the default keyword list.  Each string must appear as a
            case-insensitive substring of the serial port's description,
            manufacturer, or hardware-ID.

        Returns
        -------
        Optional[str]
            The device path (e.g. ``"COM5"`` or ``"/dev/ttyUSB0"``) of the
            first matching port, or ``None`` if ports were found but none
            matched the ESP32 signature.

        Raises
        ------
        RuntimeError
            If *no* serial port is available at all — the caller can catch
            this and proceed with the ESP32 treated as unplugged.
        """
        kw = [k.lower() for k in (keywords or _ESP32_KEYWORDS)]
        all_ports = list(serial.tools.list_ports.comports())

        if not all_ports:
            raise RuntimeError(
                "RobotHand.find_esp32_port: no serial devices are connected "
                "to this computer.  Check USB — the ESP32 may be unplugged."
            )

        for p in all_ports:
            desc   = (p.description or "").lower()
            mfr    = (p.manufacturer or "").lower()
            hwid   = (p.hwid or "").lower()
            device = p.device or ""

            if any(k in desc for k in kw) \
               or any(k in mfr for k in kw) \
               or any(k in hwid for k in kw):
                logger.info(
                    "RobotHand.find_esp32_port: ✅ ESP32 at %s "
                    "(manufacturer=%s, description=%s)",
                    device,
                    p.manufacturer or "<unknown>",
                    p.description or "<unknown>",
                )
                return device

        # Nothing matched an ESP32 signature — log all candidates for the user
        candidates = [p.device for p in all_ports if p.device]
        logger.warning(
            "RobotHand.find_esp32_port: no ESP32 found among %d port(s): %s",
            len(candidates),
            candidates,
        )
        return None

    # ── private internals ──────────────────────────────────────────────────────

    def _close_silent(self) -> None:
        """Close the port without emitting a log line — used for error recovery."""
        if self._serial:
            try:
                self._serial.close()
            except Exception:
                pass
        self._serial = None

    def _resolve_port(self) -> Optional[str]:
        """Return the serial port path to use, honouring the priority order:

        1. Explicit *port* argument passed to the constructor.
        2. ``config.SERIAL_PORT`` (must be a non-empty string).
        3. :meth:`find_esp32_port` when ``auto_detect=True``.
        4. Generic first-available port scan (``_auto_detect_port``) as the
           absolute fallback when ``auto_detect`` is ``False``.

        Returns
        -------
        Optional[str]
            Resolved port path, or ``None`` when no suitable port was found.
        """
        # 1. Explicit constructor argument
        if self._port:
            return self._port

        # 2. config.py override
        configured = config.SERIAL_PORT
        if configured:
            return configured

        # 3. ESP32-aware auto-detection
        if self._auto_detect:
            try:
                esp_port = RobotHand.find_esp32_port()
                if esp_port:
                    self._autodetected = True
                    return esp_port
                # Ports exist but none matched an ESP32 signature
                logger.warning(
                    "RobotHand._resolve_port: no ESP32 detected among available "
                    "ports — the robot hand will remain disabled.  Set an "
                    "explicit port via config.SERIAL_PORT or the constructor."
                )
                return None
            except RuntimeError as exc:
                # No port at all — treat as "ESP32 unplugged"
                logger.warning(
                    "RobotHand._resolve_port: %s — robot hand disabled.", exc
                )
                return None

        # 4. Last resort: first available serial port
        return RobotHand._auto_detect_port()

    @staticmethod
    def _auto_detect_port() -> Optional[str]:
        """Return the first available serial port (generic fallback scan).

        .. warning::
            This method does not check for ESP32 identity — it returns
            whichever port ``serial.tools.list_ports`` reports first.  Use
            :meth:`find_esp32_port` for ESP32-aware detection.
        """
        ports = [p.device for p in serial.tools.list_ports.comports() if p.device]

        if not ports:
            logger.warning(
                "RobotHand._auto_detect_port: no serial devices found."
            )
            return None

        logger.debug("RobotHand._auto_detect_port: candidates: %s", ports)
        return ports[0]


# ── Module-level singleton ─────────────────────────────────────────────────────
# Every module that imports this instance shares exactly one RobotHand instance,
# so there is never more than one open serial connection at a time.

_robot_hand_instance: Optional[RobotHand] = None
_robot_hand_connected: bool = False


def get_robot_hand(
    port: Optional[str] = None,
    baudrate: int = config.SERIAL_BAUDRATE,
    auto_detect: bool = True,
) -> RobotHand:
    """Return (and lazily create) the global :class:`RobotHand` singleton.

    Parameters
    ----------
    port:
        Override the port name on the very first call.  Subsequent calls
        ignore this parameter and return the already-created instance.
    baudrate:
        Baud-rate override on first call; ignored on subsequent calls.
    auto_detect:
        Enable ESP32-aware port auto-detection on first call (see
        :meth:`RobotHand.find_esp32_port`); ignored on subsequent calls.

    Returns
    -------
    RobotHand
        The module-level singleton instance, always the same object within the
        same Python process.
    """
    global _robot_hand_instance, _robot_hand_connected

    if _robot_hand_instance is None:
        _robot_hand_instance = RobotHand(
            port=port,
            baudrate=baudrate,
            auto_detect=auto_detect,
        )
        _robot_hand_connected = _robot_hand_instance.connect()

    return _robot_hand_instance
