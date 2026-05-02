"""Tkinter desktop UI for controlling the wind tunnel."""

from __future__ import annotations

import queue
import tkinter as tk
from tkinter import messagebox, ttk

from serial.tools import list_ports

from .data import TunnelReading
from .serial_link import SerialEvent, SerialLink


class WindTunnelApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()

        self.title("Wind Tunnel Control")
        self.geometry("900x640")
        self.minsize(760, 560)

        self._events: "queue.Queue[SerialEvent]" = queue.Queue()
        self._link: SerialLink | None = None
        self._port_by_label: dict[str, str] = {}

        self._status_var = tk.StringVar(value="Disconnected")
        self._port_var = tk.StringVar()
        self._baud_var = tk.StringVar(value="9600")
        self._speed_var = tk.DoubleVar(value=0)
        self._speed_text_var = tk.StringVar(value="0%")

        self._wind_var = tk.StringVar(value="--")
        self._temperature_var = tk.StringVar(value="--")
        self._dynamic_pressure_var = tk.StringVar(value="--")
        self._static_pressure_var = tk.StringVar(value="--")

        self._control_widgets: list[tk.Widget] = []

        self._configure_style()
        self._build_ui()
        self.refresh_ports()
        self._set_connected_state(False)

        self.after(100, self._poll_events)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        style.configure("Title.TLabel", font=("Segoe UI", 18, "bold"))
        style.configure("Section.TLabel", font=("Segoe UI", 11, "bold"))
        style.configure("Readout.TLabel", font=("Segoe UI", 16, "bold"))
        style.configure("Danger.TButton", font=("Segoe UI", 10, "bold"))

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        header = ttk.Frame(self, padding=(18, 16, 18, 8))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)

        ttk.Label(header, text="Wind Tunnel Control", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(header, textvariable=self._status_var).grid(row=0, column=1, sticky="e")

        body = ttk.Frame(self, padding=18)
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(0, weight=0)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(1, weight=1)

        connection = ttk.LabelFrame(body, text="Connection", padding=12)
        connection.grid(row=0, column=0, sticky="new", padx=(0, 14))
        connection.columnconfigure(1, weight=1)

        ttk.Label(connection, text="Port").grid(row=0, column=0, sticky="w", pady=4)
        self._port_combo = ttk.Combobox(connection, textvariable=self._port_var, width=32)
        self._port_combo.grid(row=0, column=1, sticky="ew", pady=4)
        ttk.Button(connection, text="Refresh", command=self.refresh_ports).grid(row=0, column=2, padx=(8, 0), pady=4)

        ttk.Label(connection, text="Baud").grid(row=1, column=0, sticky="w", pady=4)
        self._baud_combo = ttk.Combobox(
            connection,
            textvariable=self._baud_var,
            values=("9600", "115200", "460800"),
            width=12,
        )
        self._baud_combo.grid(row=1, column=1, sticky="w", pady=4)

        self._connect_button = ttk.Button(connection, text="Connect", command=self.connect)
        self._connect_button.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        self._disconnect_button = ttk.Button(connection, text="Disconnect", command=self.disconnect)
        self._disconnect_button.grid(row=2, column=1, sticky="ew", padx=(8, 0), pady=(10, 0))

        controls = ttk.LabelFrame(body, text="Fan Control", padding=12)
        controls.grid(row=1, column=0, sticky="new", padx=(0, 14), pady=(14, 0))
        controls.columnconfigure(0, weight=1)

        button_row = ttk.Frame(controls)
        button_row.grid(row=0, column=0, sticky="ew")
        button_row.columnconfigure((0, 1), weight=1)

        on_button = ttk.Button(button_row, text="Fan On", command=lambda: self._send("ON"))
        on_button.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        off_button = ttk.Button(button_row, text="Fan Off", command=self.emergency_stop, style="Danger.TButton")
        off_button.grid(row=0, column=1, sticky="ew", padx=(6, 0))

        ttk.Label(controls, text="Speed").grid(row=1, column=0, sticky="w", pady=(16, 2))
        speed_row = ttk.Frame(controls)
        speed_row.grid(row=2, column=0, sticky="ew")
        speed_row.columnconfigure(0, weight=1)

        speed_scale = ttk.Scale(
            speed_row,
            from_=0,
            to=100,
            variable=self._speed_var,
            command=self._on_speed_changed,
        )
        speed_scale.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        ttk.Label(speed_row, textvariable=self._speed_text_var, width=5).grid(row=0, column=1)

        set_speed_button = ttk.Button(controls, text="Set Speed", command=self.set_speed)
        set_speed_button.grid(row=3, column=0, sticky="ew", pady=(12, 0))

        manual = ttk.LabelFrame(body, text="Manual Command", padding=12)
        manual.grid(row=2, column=0, sticky="new", padx=(0, 14), pady=(14, 0))
        manual.columnconfigure(0, weight=1)

        self._manual_command_var = tk.StringVar()
        manual_entry = ttk.Entry(manual, textvariable=self._manual_command_var)
        manual_entry.grid(row=0, column=0, sticky="ew")
        manual_entry.bind("<Return>", lambda _event: self.send_manual_command())
        manual_button = ttk.Button(manual, text="Send", command=self.send_manual_command)
        manual_button.grid(row=0, column=1, padx=(8, 0))

        self._control_widgets.extend(
            [on_button, off_button, speed_scale, set_speed_button, manual_entry, manual_button]
        )

        readouts = ttk.LabelFrame(body, text="Live Readings", padding=12)
        readouts.grid(row=0, column=1, rowspan=2, sticky="nsew")
        readouts.columnconfigure((0, 1), weight=1)

        self._add_readout(readouts, 0, 0, "Wind Speed", self._wind_var, "m/s")
        self._add_readout(readouts, 0, 1, "Temperature", self._temperature_var, "deg C")
        self._add_readout(readouts, 1, 0, "Dynamic Pressure", self._dynamic_pressure_var, "Pa")
        self._add_readout(readouts, 1, 1, "Static Pressure", self._static_pressure_var, "Pa")

        log_frame = ttk.LabelFrame(body, text="Serial Log", padding=12)
        log_frame.grid(row=2, column=1, sticky="nsew", pady=(14, 0))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self._log = tk.Text(log_frame, height=9, wrap="word", state="disabled")
        self._log.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self._log.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self._log.configure(yscrollcommand=scrollbar.set)

    def _add_readout(
        self,
        parent: ttk.Frame,
        row: int,
        column: int,
        label: str,
        variable: tk.StringVar,
        unit: str,
    ) -> None:
        frame = ttk.Frame(parent, padding=10)
        frame.grid(row=row, column=column, sticky="nsew", padx=6, pady=6)
        frame.columnconfigure(0, weight=1)
        ttk.Label(frame, text=label, style="Section.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(frame, textvariable=variable, style="Readout.TLabel").grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Label(frame, text=unit).grid(row=2, column=0, sticky="w")

    def refresh_ports(self) -> None:
        current_port = self._selected_port()
        self._port_by_label.clear()

        labels = []
        for port in list_ports.comports():
            label = f"{port.device} - {port.description}"
            self._port_by_label[label] = port.device
            labels.append(label)

        self._port_combo["values"] = labels
        if current_port:
            self._port_var.set(current_port)
        elif labels:
            self._port_var.set(labels[0])
        elif not self._port_var.get():
            self._port_var.set("COM6")

    def connect(self) -> None:
        if self._link is not None:
            return

        port = self._selected_port()
        if not port:
            messagebox.showerror("Missing port", "Choose or type a COM port first.")
            return

        try:
            baud_rate = int(self._baud_var.get())
        except ValueError:
            messagebox.showerror("Invalid baud rate", "Baud rate must be a number.")
            return

        self._set_status(f"Connecting to {port}...")
        self._link = SerialLink(port, baud_rate, self._events)
        self._link.start()
        self._connect_button.configure(state="disabled")
        self._disconnect_button.configure(state="normal")

    def disconnect(self) -> None:
        if self._link is None:
            return
        self._set_status("Disconnecting...")
        self._link.close()
        self._link = None
        self._set_connected_state(False)

    def emergency_stop(self) -> None:
        self._speed_var.set(0)
        self._speed_text_var.set("0%")
        self._send("OFF")

    def set_speed(self) -> None:
        speed = round(self._speed_var.get())
        self._send(str(speed))

    def send_manual_command(self) -> None:
        command = self._manual_command_var.get().strip()
        if not command:
            return
        self._send(command)
        self._manual_command_var.set("")

    def _send(self, command: str) -> None:
        if self._link is None:
            messagebox.showwarning("Not connected", "Connect to the Arduino before sending commands.")
            return

        try:
            self._link.send_command(command)
        except RuntimeError as exc:
            messagebox.showerror("Serial error", str(exc))
        else:
            self._append_log(f"> {command}")

    def _selected_port(self) -> str:
        selected = self._port_var.get().strip()
        return self._port_by_label.get(selected, selected)

    def _on_speed_changed(self, _value: str) -> None:
        self._speed_text_var.set(f"{round(self._speed_var.get())}%")

    def _poll_events(self) -> None:
        try:
            while True:
                event = self._events.get_nowait()
                self._handle_event(event)
        except queue.Empty:
            pass
        finally:
            self.after(100, self._poll_events)

    def _handle_event(self, event: SerialEvent) -> None:
        if event.kind == "status":
            self._set_status(event.text)
            self._set_connected_state(True)
        elif event.kind == "reading" and event.reading:
            self._update_readings(event.reading)
            self._append_log(event.text)
        elif event.kind == "line":
            self._append_log(event.text)
        elif event.kind == "error":
            self._append_log(f"ERROR: {event.text}")
            self._set_status("Serial error")
            self._link = None
            self._set_connected_state(False)
        elif event.kind == "closed":
            if self._link is not None:
                self._set_status(event.text)
            self._link = None
            self._set_connected_state(False)

    def _update_readings(self, reading: TunnelReading) -> None:
        if reading.wind_speed_mps is None:
            self._wind_var.set("n/a")
        else:
            self._wind_var.set(f"{reading.wind_speed_mps:.2f}")

        self._temperature_var.set(f"{reading.temperature_c:.1f}")
        self._dynamic_pressure_var.set(f"{reading.dynamic_pressure_pa:.1f}")
        self._static_pressure_var.set(f"{reading.static_pressure_pa:.1f}")

    def _append_log(self, line: str) -> None:
        self._log.configure(state="normal")
        self._log.insert("end", f"{line}\n")
        self._log.see("end")
        self._log.configure(state="disabled")

    def _set_status(self, text: str) -> None:
        self._status_var.set(text)

    def _set_connected_state(self, connected: bool) -> None:
        state = "normal" if connected else "disabled"
        for widget in self._control_widgets:
            widget.configure(state=state)

        self._connect_button.configure(state="disabled" if connected else "normal")
        self._disconnect_button.configure(state="normal" if connected else "disabled")
        if not connected:
            self._set_status("Disconnected")

    def _on_close(self) -> None:
        self.disconnect()
        self.destroy()


def main() -> None:
    app = WindTunnelApp()
    app.mainloop()
