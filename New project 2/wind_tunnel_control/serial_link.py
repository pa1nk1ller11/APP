"""Threaded serial communication with the Arduino Mega."""

from __future__ import annotations

from dataclasses import dataclass
import queue
import threading
import time
from typing import Optional

import serial

from .data import TunnelReading, parse_tunnel_reading


@dataclass(frozen=True)
class SerialEvent:
    kind: str
    text: str = ""
    reading: Optional[TunnelReading] = None


class SerialLink:
    """Small wrapper that keeps serial I/O off the Tkinter main thread."""

    def __init__(self, port: str, baud_rate: int, event_queue: "queue.Queue[SerialEvent]"):
        self.port = port
        self.baud_rate = baud_rate
        self.event_queue = event_queue
        self._stop_event = threading.Event()
        self._serial_lock = threading.Lock()
        self._serial: Optional[serial.Serial] = None
        self._thread = threading.Thread(target=self._run, name="wind-tunnel-serial", daemon=True)

    def start(self) -> None:
        self._thread.start()

    def close(self) -> None:
        self._stop_event.set()
        with self._serial_lock:
            if self._serial and self._serial.is_open:
                self._serial.close()
        self._thread.join(timeout=2.0)

    def send_command(self, command: str) -> None:
        clean_command = command.strip()
        if not clean_command:
            return

        payload = f"{clean_command}\n".encode("ascii", errors="ignore")
        with self._serial_lock:
            if not self._serial or not self._serial.is_open:
                raise RuntimeError("Not connected to the Arduino.")
            self._serial.write(payload)

    def _run(self) -> None:
        try:
            with serial.Serial(
                self.port,
                self.baud_rate,
                timeout=0.2,
                write_timeout=1.0,
            ) as serial_port:
                with self._serial_lock:
                    self._serial = serial_port

                self.event_queue.put(SerialEvent("status", f"Connected to {self.port}"))
                time.sleep(2.0)  # Arduino boards usually reset when the port opens.

                while not self._stop_event.is_set():
                    raw_line = serial_port.readline()
                    if not raw_line:
                        continue

                    line = raw_line.decode("utf-8", errors="replace").strip()
                    if not line:
                        continue

                    reading = parse_tunnel_reading(line)
                    if reading is None:
                        self.event_queue.put(SerialEvent("line", line))
                    else:
                        self.event_queue.put(SerialEvent("reading", line, reading))

        except serial.SerialException as exc:
            self.event_queue.put(SerialEvent("error", str(exc)))
        finally:
            with self._serial_lock:
                self._serial = None
            self.event_queue.put(SerialEvent("closed", "Disconnected"))
