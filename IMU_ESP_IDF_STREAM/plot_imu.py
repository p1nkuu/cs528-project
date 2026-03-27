#!/usr/bin/env python3
"""
Real-time IMU plotter for MPU6050 streamed from an ESP32.

Expected serial line format (ESP_LOGI):
  I (ticks) mpu6050 stream: AX:0.123 AY:-0.456 AZ:9.789 | GX:1.23 GY:-0.45 GZ:0.67 | T:25.30 C

Usage:
  python plot_imu.py                        # auto-detects port
  python plot_imu.py --port /dev/tty.usbserial-11130
  python plot_imu.py --port /dev/tty.usbserial-11130 --baud 115200 --window 5
"""

import argparse
import re
import sys
import threading
import time
from collections import deque

import matplotlib
# matplotlib.use("TkAgg")          # change to "Qt5Agg" if TkAgg is unavailable
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import serial
import serial.tools.list_ports

# ── Configuration ────────────────────────────────────────────────────────────
BAUD_RATE    = 115200
WINDOW_SEC   = 5      # seconds of history to display
SAMPLE_HZ    = 100    # expected sample rate (used only for buffer sizing)
DELAY = 1/SAMPLE_HZ     # time between samples (for simple position estimation)

# Regex that matches both raw ESP_LOGI lines and plain printed lines
# Updated Regex: more robust against ESP_LOGI headers
LINE_RE = re.compile(
    r"AX:(?P<ax>[-\d.]+)\s+AY:(?P<ay>[-\d.]+)\s+AZ:(?P<az>[-\d.]+)"
    r".*?"  # Matches anything in between (like the | pipe)
    r"GX:(?P<gx>[-\d.]+)\s+GY:(?P<gy>[-\d.]+)\s+GZ:(?P<gz>[-\d.]+)"
    r".*?"
    r"T:(?P<t>[-\d.]+)"
)

# ── Colour palette ────────────────────────────────────────────────────────────
C = {
    "bg":     "#0f1117",
    "panel":  "#1a1d27",
    "grid":   "#2a2d3a",
    "ax":     "#4fc3f7",   # blue  – accel X
    "ay":     "#81d4fa",   # light blue  – accel Y
    "az":     "#b3e5fc",   # pale blue   – accel Z
    "gx":     "#f48fb1",   # pink  – gyro X
    "gy":     "#f06292",   # rose  – gyro Y
    "gz":     "#e91e63",   # deep rose   – gyro Z
    "x":    "#ff8a65",   # light orange  – position X
    "y":    "#ff7043",   # orange  – position Y
    "z":    "#ff5722",   # deep orange  – position Z
    "temp":   "#ffcc02",   # gold  – temperature
    "text":   "#e0e0e0",
    "title":  "#ffffff",
}


def find_port() -> str:
    """Auto-detect the first USB-serial port."""
    ports = serial.tools.list_ports.comports()
    usb = [p for p in ports if "usb" in p.device.lower() or "usbserial" in p.device.lower()]
    if usb:
        return usb[0].device
    if ports:
        return ports[0].device
    print("[ERROR] No serial ports found. Plug in your ESP32 or specify --port.", file=sys.stderr)
    sys.exit(1)


def parse_line(line: str):
    """Return (ax, ay, az, gx, gy, gz, temp) floats or None."""
    m = LINE_RE.search(line)
    if m:
        return tuple(float(m.group(k)) for k in ("ax", "ay", "az", "gx", "gy", "gz", "t"))
    return None


class SerialReader(threading.Thread):
    """Background thread that fills shared deques from the serial port."""

    def __init__(self, port: str, baud: int, buf_size: int):
        super().__init__(daemon=True)
        self.port     = port
        self.baud     = baud
        self.buf_size = buf_size
        self.lock     = threading.Lock()

        self.x   = deque(maxlen=buf_size)
        self.x.append(0.0)  # initial position
        self.y    = deque(maxlen=buf_size)
        self.y.append(0.0)  # initial position
        self.z    = deque(maxlen=buf_size)
        self.z.append(0.0)  # initial position
        self.d_t  = 0
        
        self.cursor_x = 0.0
        self.cursor_y = 0.0
        self.friction = 0.95 # Helps bring the "pen" to a stop


        self.t    = deque(maxlen=buf_size)
        self.ax   = deque(maxlen=buf_size)
        self.ay   = deque(maxlen=buf_size)
        self.az   = deque(maxlen=buf_size)
        self.gx   = deque(maxlen=buf_size)
        self.gy   = deque(maxlen=buf_size)
        self.gz   = deque(maxlen=buf_size)
        self.temp = deque(maxlen=buf_size)

        self.connected = False
        self.status    = "Connecting…"

    def run(self):
        while True:
            try:
                with serial.Serial(self.port, self.baud, timeout=1) as ser:
                    self.connected = True
                    self.status    = f"Connected  {self.port}  @{self.baud} baud"
                    t0 = time.perf_counter()
                    while True:
                        raw = ser.readline()
                        try:
                            line = raw.decode("utf-8", errors="replace").strip()
                        except Exception:
                            continue
                        parsed = parse_line(line)
                        if parsed is None:
                            continue
                        ax, ay, az, gx, gy, gz, temp = parsed

                        # self.x.append(self.x[-1] + (DELAY**2) * ax)
                        # self.y.append(self.y[-1]  + (DELAY ** 2) * ay)
                        # self.z.append(self.z[-1] + (DELAY ** 2) * (az - 9.8)) # remove gravity

                        self.cursor_x = (self.cursor_x + gx * 0.01) * self.friction
                        self.cursor_y = (self.cursor_y + gy * 0.01) * self.friction

                        now = time.perf_counter() - t0
                        with self.lock:
                            self.x.append(self.cursor_x)
                            self.y.append(self.cursor_y)   
                            self.z.append(gz)                          
                            self.t.append(now)
                            self.ax.append(ax);   self.ay.append(ay);   self.az.append(az)
                            self.gx.append(gx);   self.gy.append(gy);   self.gz.append(gz)
                            self.temp.append(temp)
            except serial.SerialException as e:
                self.connected = False
                self.status    = f"Disconnected — {e}  (retrying…)"
                time.sleep(2)

    def snapshot(self):
        """Thread-safe copy of all buffers."""
        with self.lock:
            return (
                list(self.t),
                list(self.ax), list(self.ay), list(self.az),
                list(self.gx), list(self.gy), list(self.gz),
                list(self.temp), list(self.x), list(self.y), list(self.z)
            )


def style_axes(ax, ylabel, ylim=None):
    ax.set_facecolor(C["panel"])
    ax.tick_params(colors=C["text"], labelsize=8)
    ax.yaxis.label.set_color(C["text"])
    ax.xaxis.label.set_color(C["text"])
    ax.set_ylabel(ylabel, fontsize=9)
    for spine in ax.spines.values():
        spine.set_edgecolor(C["grid"])
    ax.grid(True, color=C["grid"], linewidth=0.5, linestyle="--")
    if ylim:
        ax.set_ylim(*ylim)


def main():
    parser = argparse.ArgumentParser(description="Real-time MPU6050 plotter")
    parser.add_argument("--port",   default=None,      help="Serial port (auto-detected if omitted)")
    parser.add_argument("--baud",   default=BAUD_RATE,  type=int, help=f"Baud rate (default {BAUD_RATE})")
    parser.add_argument("--window", default=WINDOW_SEC, type=float, help=f"Plot window in seconds (default {WINDOW_SEC})")
    args = parser.parse_args()

    port     = args.port or find_port()
    baud     = args.baud
    window   = args.window
    buf_size = int(window * SAMPLE_HZ * 2)   # 2× safety margin

    print(f"[INFO] Opening  {port}  at {baud} baud …")
    reader = SerialReader(port, baud, buf_size)
    reader.start()

    # ── Figure layout ─────────────────────────────────────────────────────────
    plt.style.use("dark_background")
    fig = plt.figure(figsize=(13, 8), facecolor=C["bg"])
    fig.canvas.manager.set_window_title("MPU6050 — Real-Time Stream")

    gs = gridspec.GridSpec(3, 1, figure=fig, hspace=0.45,
                           left=0.08, right=0.97, top=0.90, bottom=0.08)

    ax_acc  = fig.add_subplot(gs[0])
    ax_gyro = fig.add_subplot(gs[1])
    ax_pos = fig.add_subplot(gs[2])

    style_axes(ax_acc,  "Acceleration (g)")
    style_axes(ax_gyro, "Angular rate (°/s)")
    style_axes(ax_pos,  "Position (m)")

    # Title + status bar
    suptitle = fig.suptitle("MPU6050  Real-Time Stream  — 100 Hz",
                             color=C["title"], fontsize=13, fontweight="bold")
    status_txt = fig.text(0.5, 0.005, reader.status,
                          ha="center", fontsize=8, color="#888888")

    # Legend handles (empty lines animated later)
    la_x, = ax_acc.plot([], [], color=C["ax"], lw=1.2, label="Accel X")
    la_y, = ax_acc.plot([], [], color=C["ay"], lw=1.2, label="Accel Y")
    la_z, = ax_acc.plot([], [], color=C["az"], lw=1.2, label="Accel Z")

    lg_x, = ax_gyro.plot([], [], color=C["gx"], lw=1.2, label="Gyro X")
    lg_y, = ax_gyro.plot([], [], color=C["gy"], lw=1.2, label="Gyro Y")
    lg_z, = ax_gyro.plot([], [], color=C["gz"], lw=1.2, label="Gyro Z")

    # lt,   = ax_temp.plot([], [], color=C["temp"], lw=1.5, label="Temperature")

    # Legend handles for Position (Air Drawing)
    lp_x, = ax_pos.plot([], [], color=C["x"], lw=1.5, label="Pos X (Yaw)")
    lp_y, = ax_pos.plot([], [], color=C["y"], lw=1.5, label="Pos Y (Pitch)")
    lp_z, = ax_pos.plot([], [], color=C["z"], lw=1.5, label="Pos Z (Roll)")


    for a, lines in [(ax_acc,  [la_x, la_y, la_z]),
                     (ax_gyro, [lg_x, lg_y, lg_z]),
                    #  (ax_temp, [lt]),
                     (ax_pos,  [lp_x, lp_y, lp_z])]:
        leg = a.legend(handles=lines, loc="upper left", fontsize=7,
                       facecolor=C["panel"], edgecolor=C["grid"],
                       labelcolor=C["text"])


    # Live numeric readouts
    def readout(ax, x, y, text=""):
        return ax.text(1.001, y, text, transform=ax.transAxes,
                       color=C["text"], fontsize=7.5, va="center",
                       fontfamily="monospace")

    ro_ax = readout(ax_acc,  1, 0.83)
    ro_ay = readout(ax_acc,  1, 0.50)
    ro_az = readout(ax_acc,  1, 0.17)
    ro_gx = readout(ax_gyro, 1, 0.83)
    ro_gy = readout(ax_gyro, 1, 0.50)
    ro_gz = readout(ax_gyro, 1, 0.17)
    ro_px = readout(ax_pos,  1, 0.83)
    ro_py = readout(ax_pos,  1, 0.50)
    ro_pz = readout(ax_pos,  1, 0.17)


    def update(_):
        # Unpack the snapshot from the thread-safe reader
        t, ax_, ay_, az_, gx_, gy_, gz_, tmp, px_, py_, pz_ = reader.snapshot()

        if len(t) < 2:
            return

        t_now = t[-1]
        t_lo  = t_now - window

        # Helper to slice data to the visible time window
        def trim(xs, ts):
            return [x for x, ti in zip(xs, ts) if ti >= t_lo]

        # Shared time vectors for the X-axis
        tv = [ti for ti in t if ti >= t_lo]

        # Slice all data series
        axv = trim(ax_, t); ayv = trim(ay_, t); azv = trim(az_, t)
        gxv = trim(gx_, t); gyv = trim(gy_, t); gzv = trim(gz_, t)
        pxv = trim(px_, t); pyv = trim(py_, t); pzv = trim(pz_, t)
        tmpv = trim(tmp, t)

        # Update line data for all plots
        la_x.set_data(tv, axv); la_y.set_data(tv, ayv); la_z.set_data(tv, azv)
        lg_x.set_data(tv, gxv); lg_y.set_data(tv, gyv); lg_z.set_data(tv, gzv)
        lp_x.set_data(tv, pxv); lp_y.set_data(tv, pyv); lp_z.set_data(tv, pzv)
        # lt.set_data(tv, tmpv) # Uncomment if you use the temp plot

        # Synchronize X-axis limits for scrolling effect
        for a in (ax_acc, ax_gyro, ax_pos):
            a.set_xlim(t_lo, t_now)

        # Auto-scale Y-axis for each plot based on visible data
        def auto_ylim(ax, *series):
            vals = [v for s in series for v in s]
            if vals:
                lo, hi = min(vals), max(vals)
                pad = max((hi - lo) * 0.15, 0.05)
                ax.set_ylim(lo - pad, hi + pad)

        auto_ylim(ax_acc, axv, ayv, azv)
        auto_ylim(ax_gyro, gxv, gyv, gzv)
        auto_ylim(ax_pos, pxv, pyv, pzv)

        # Update live numeric readouts on the right side
        if ax_:
            ro_ax.set_text(f"AX {ax_[-1]:+7.3f}")
            ro_ay.set_text(f"AY {ay_[-1]:+7.3f}")
            ro_az.set_text(f"AZ {az_[-1]:+7.3f}")
            ro_gx.set_text(f"GX {gx_[-1]:+7.2f}")
            ro_gy.set_text(f"GY {gy_[-1]:+7.2f}")
            ro_gz.set_text(f"GZ {gz_[-1]:+7.2f}")
            ro_px.set_text(f"PX {px_[-1]:+7.3f}")
            ro_py.set_text(f"PY {py_[-1]:+7.3f}")
            ro_pz.set_text(f"PZ {pz_[-1]:+7.3f}")
        status_txt.set_text(reader.status)

    from matplotlib.animation import FuncAnimation
    ani = FuncAnimation(fig, update, interval=50, blit=False, cache_frame_data=False)

    plt.show()


if __name__ == "__main__":
    main()
