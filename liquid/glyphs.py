# SPDX-License-Identifier: GPL-3.0-only
"""Pear — menü çubuğu glifleri (tek renk, elle çizilmiş; macOS 26 SF Symbols benzeri)."""
import math
import os

import cairo
import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk  # noqa: E402

from .core import design

PEAR_ICON = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "branding", "pear.png")


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


class Glyph(Gtk.DrawingArea):
    """Menü çubuğu ikonu: light=True → beyaz (koyu duvar kâğıdı), False → siyah."""

    def __init__(self, kind, width):
        super().__init__()
        self.kind, self.state, self.light = kind, None, True
        self._brand = cairo.ImageSurface.create_from_png(PEAR_ICON) if kind == "pear" else None
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
        if k == "pear":
            # Kullanıcının sağladığı logonun alfa kanalı; renk menü çubuğuna uyar.
            size = 18
            cr.save()
            cr.translate((wd - size) / 2, cy - size / 2)
            cr.scale(size / self._brand.get_width(), size / self._brand.get_height())
            src()
            cr.mask_surface(self._brand, 0, 0)
            cr.restore()
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
