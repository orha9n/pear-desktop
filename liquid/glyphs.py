"""Liquid — menü çubuğu glifleri (tek renk, elle çizilmiş; macOS 26 SF Symbols benzeri)."""
import math
import os
import subprocess

import cairo
from gi.repository import Gtk

from .core import design

# Elma logosu (özgür çizim, 0..100 kutusunda)
_APPLE = [
    ("M", 67.6, 53.1), ("C", 67.5, 43.9, 75.1, 39.5, 75.5, 39.3), ("C", 71.2, 33.0, 64.6, 32.2, 62.2, 32.1),
    ("C", 56.6, 31.5, 51.3, 35.4, 48.4, 35.4), ("C", 45.6, 35.4, 41.3, 32.2, 36.7, 32.3),
    ("C", 30.7, 32.4, 25.1, 35.8, 22.0, 41.2), ("C", 15.7, 52.1, 20.4, 68.2, 26.5, 77.0),
    ("C", 29.5, 81.3, 33.1, 86.1, 37.7, 85.9), ("C", 42.2, 85.7, 43.9, 83.0, 49.3, 83.0),
    ("C", 54.7, 83.0, 56.2, 85.9, 60.9, 85.8), ("C", 65.7, 85.7, 68.7, 81.5, 71.6, 77.1),
    ("C", 75.0, 72.2, 76.4, 67.4, 76.5, 67.1), ("C", 76.4, 67.1, 67.7, 63.8, 67.6, 53.1), ("Z",),
    ("M", 58.7, 26.0), ("C", 61.2, 23.0, 62.9, 18.8, 62.4, 14.6), ("C", 58.8, 14.8, 54.5, 17.0, 51.9, 20.0),
    ("C", 49.6, 22.6, 47.6, 26.9, 48.1, 31.0), ("C", 52.1, 31.3, 56.2, 29.0, 58.7, 26.0), ("Z",),
]


def apple_path(cr, x, y, size):
    s = size / 100.0
    for op in _APPLE:
        if op[0] == "M":
            cr.move_to(x + op[1] * s, y + op[2] * s)
        elif op[0] == "C":
            cr.curve_to(x + op[1] * s, y + op[2] * s, x + op[3] * s, y + op[4] * s, x + op[5] * s, y + op[6] * s)
        else:
            cr.close_path()


def battery_state():
    base = "/sys/class/power_supply"
    cap, status, ac = None, "", False
    try:
        for d in sorted(os.listdir(base)):
            p = os.path.join(base, d)
            typ = open(os.path.join(p, "type")).read().strip()
            if typ == "Battery" and cap is None:
                cap = int(open(os.path.join(p, "capacity")).read())
                status = open(os.path.join(p, "status")).read().strip()
            elif typ == "Mains":
                ac = open(os.path.join(p, "online")).read().strip() == "1"
    except Exception:
        pass
    return cap, status, ac


def wifi_state():
    """(radyo açık, bağlı SSID, sinyal 0..100)"""
    def run(cmd):
        try:
            return subprocess.run(cmd, capture_output=True, text=True, timeout=3).stdout
        except Exception:
            return ""
    on = run(["nmcli", "radio", "wifi"]).strip().lower().startswith("en")
    for line in run(["env", "LC_ALL=C.UTF-8", "nmcli", "-t", "-f", "ACTIVE,SSID,SIGNAL", "dev", "wifi",
                     "list", "--rescan", "no"]).splitlines():
        a, _, rest = line.partition(":")
        ssid, _, sig = rest.rpartition(":")
        if a == "yes" and ssid:
            return on, ssid.replace("\\:", ":"), int(sig or 0)
    return on, "", 0


class Glyph(Gtk.DrawingArea):
    """Menü çubuğu ikonu: light=True → beyaz (koyu duvar kâğıdı), False → siyah."""

    def __init__(self, kind, width):
        super().__init__()
        self.kind, self.state, self.light = kind, None, True
        self.set_size_request(width, design.BAR_H - 6)
        self.connect("draw", self.draw)

    def _fg(self, a=1.0):
        return (1, 1, 1, 0.96 * a) if self.light else (0, 0, 0, 0.86 * a)

    def draw(self, w, cr):
        wd, ht = self.get_allocated_width(), self.get_allocated_height()
        cy = ht / 2
        # hafif gölge (beyaz glif açık duvar kâğıdında okunsun) → önce gölge, sonra glif
        passes = [((0, 0, 0, 0.28), 0.8), (None, 0)] if self.light else [(None, 0)]
        for col, dy in passes:
            cr.save()
            cr.translate(0, dy)
            self._paint(cr, wd, ht, cy, col)
            cr.restore()
        return False

    def _paint(self, cr, wd, ht, cy, col):
        def src(a=1.0):
            if col is not None:
                cr.set_source_rgba(col[0], col[1], col[2], col[3] * a)
            else:
                cr.set_source_rgba(*self._fg(a))
        k = self.kind
        if k == "apple":
            s = 17
            apple_path(cr, (wd - s) / 2, cy - s / 2 - 0.5, s)
            src()
            cr.fill()
        elif k == "battery":
            cap, status, ac = self.state or (100, "", False)
            lvl = max(0, min(100, cap if cap is not None else 100))
            bw, bh, x = 25, 12, (wd - 28) / 2
            y = cy - bh / 2
            # macOS 26: dolu kapsül; kalan kısım soluk
            design.rrect(cr, x, y, bw, bh, 4)
            src(0.35)
            cr.fill()
            cr.save()
            design.rrect(cr, x, y, bw, bh, 4)
            cr.clip()
            cr.rectangle(x, y, bw * lvl / 100, bh)
            if lvl <= 20 and not ac and col is None:
                cr.set_source_rgba(*design.RED, 1)
            else:
                src()
            cr.fill()
            cr.restore()
            design.rrect(cr, x + bw + 1.4, cy - 2.2, 2.2, 4.4, 1.1)    # uç
            src(0.45)
            cr.fill()
            if status == "Charging" and col is None:                   # şarj şimşeği (oyuk)
                cr.set_operator(cairo.OPERATOR_CLEAR)
                bx = x + bw / 2
                cr.move_to(bx + 1.6, y + 1.2)
                cr.line_to(bx - 3.2, cy + 1)
                cr.line_to(bx - 0.2, cy + 1)
                cr.line_to(bx - 1.6, y + bh - 1.2)
                cr.line_to(bx + 3.2, cy - 1)
                cr.line_to(bx + 0.2, cy - 1)
                cr.close_path()
                cr.fill()
                cr.set_operator(cairo.OPERATOR_OVER)
        elif k == "wifi":
            on, ssid, sig = self.state or (True, "x", 100)
            bars = 0 if not (on and ssid) else (1 if sig < 34 else 2 if sig < 67 else 3)
            cx, by = wd / 2, cy + 5.8
            cr.set_line_cap(cairo.LINE_CAP_ROUND)
            for i, r in ((1, 4.2), (2, 8.0), (3, 11.8)):
                cr.new_sub_path()
                cr.arc(cx, by, r, math.radians(228), math.radians(312))
                cr.set_line_width(2.1)
                src(1.0 if bars >= i else 0.3)
                cr.stroke()
            design.circle(cr, cx, by - 0.6, 1.4)
            src(1.0 if bars >= 1 else 0.3)
            cr.fill()
        elif k == "spotlight":
            cr.set_line_width(1.8)
            cr.arc(wd / 2 - 1.2, cy - 1.2, 5.0, 0, 2 * math.pi)
            src()
            cr.stroke()
            cr.set_line_width(2.2)
            cr.set_line_cap(cairo.LINE_CAP_ROUND)
            cr.move_to(wd / 2 + 2.6, cy + 2.6)
            cr.line_to(wd / 2 + 6.0, cy + 6.0)
            cr.stroke()
        elif k == "cc":
            x = (wd - 16) / 2
            for row, knob in ((cy - 3.8, 1), (cy + 3.8, 0)):
                design.rrect(cr, x + 0.7, row - 3.0, 14.6, 6.0, 3.0)
                cr.set_line_width(1.4)
                src()
                cr.stroke()
                design.circle(cr, x + (12.3 if knob else 3.7), row, 2.2)
                cr.fill()
