# SPDX-License-Identifier: GPL-3.0-only
"""Pear — macOS tam ekranı: yeşil düğme, menü çubuğunun altına yerleşen pencere, başlık şeridi.

macOS'ta yeşil düğme pencereyi tam ekrana alır ama pencere menü çubuğunun ÜSTÜNE çıkmaz: menü
çubuğunun şeridi düz açık/koyu renge döner, pencere onun altından ekranın en altına (dock'un alanı
dahil) uzanır; dock gizlenir ve fare en alta gelince belirir. Başlığa çift tıklama ise "doldurur"
(= büyütme).

xfwm4'te yeşil (M) düğme yalnızca büyütür ve davranışı temadan değiştirilemez. Bu yüzden büyütme
durumu değiştiği anda fare imleci pencerenin trafik ışığı bölgesindeyse değişiklik geri alınır ve
pencere "macOS tam ekranına" alınır: istemci alanı (0, BAR_H)–(genişlik, yükseklik); xfwm4 başlık
çubuğu opak menü çubuğunun arkasında kalır. Kendi düğmelerini çizen kenarlıksız uygulamalarda
(Claude gibi) ☐ düğmesi de aynı bölgede olduğundan yeşil düğme gibi davranır.

Uygulamanın kendi tam ekranı (video, F11 → _NET_WM_STATE_FULLSCREEN) ayrıdır: xfwm4 onu DOCK
pencerelerin ALTINDA bıraktığından çubuk ve dock saydam/tıklanamaz yapılır, başlık şeridi en üstte açılır.

Durum $XDG_RUNTIME_DIR/liquid/fullscreen.json'da (bar yeniden başlarsa ve dock okusun diye).
Wnck.Window nesneleri SAKLANMAZ — yalnızca XID.
"""
import json
import os
import subprocess
import time

import cairo
import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("Wnck", "3.0")
gi.require_version("PangoCairo", "1.0")
from gi.repository import Gtk, Gdk, GLib, Pango, PangoCairo, Wnck  # noqa: E402

from .core import design, daemon  # noqa: E402

MAX = Wnck.WindowState.MAXIMIZED_HORIZONTALLY | Wnck.WindowState.MAXIMIZED_VERTICALLY
# trafik ışığı bölgesi (çerçevenin sol üstünden): MacTahoe xfwm4'te düğmeler 10–82 px, GTK CSD
# pencerelerde görünmez gölge payı da eklenir
ZONE_W, ZONE_H = 140, 70
POLL_MS = 100
STATE = os.path.join(daemon.RUN, "fullscreen.json")
_MASK = Wnck.WindowMoveResizeMask.X | Wnck.WindowMoveResizeMask.Y | \
    Wnck.WindowMoveResizeMask.WIDTH | Wnck.WindowMoveResizeMask.HEIGHT


def pointer():
    _, x, y = Gdk.Display.get_default().get_default_seat().get_pointer().get_position()
    return x, y


def load_state():
    try:
        with open(STATE) as f:
            return {int(k): v for k, v in json.load(f).items()}
    except Exception:
        return {}


def mode_of(screen, state=None):
    """Etkin pencerenin tam ekran türü: "x" (uygulamanın kendi tam ekranı), "mac" (yeşil düğme), None."""
    w = screen.get_active_window()
    if w is None or w.get_window_type() != Wnck.WindowType.NORMAL:
        return None
    if w.is_fullscreen():
        return "x"
    return "mac" if w.get_xid() in (load_state() if state is None else state) else None


def set_hidden(win, hidden, input_region=None):
    """Çubuk/dock'u gizle ya da göster: haritadan kaldırmadan saydam ve tıklanamaz yap."""
    win.set_opacity(0.0 if hidden else 1.0)
    win.input_shape_combine_region(cairo.Region() if hidden else input_region)


def _gtk_extents(xid):
    """GTK CSD pencerelerin görünmez gölge payı (sol, sağ, üst, alt)."""
    out = subprocess.run(["xprop", "-id", str(xid), "-notype", "_GTK_FRAME_EXTENTS"],
                         capture_output=True, text=True).stdout
    try:
        return tuple(int(v) for v in out.split("=", 1)[1].split(","))[:4]
    except Exception:
        return 0, 0, 0, 0


def _frame(w):
    """xfwm4 çerçeve kalınlığı (sol, üst, sağ, alt); kenarlıksız pencerede 0."""
    fx, fy, fw, fh = w.get_geometry()
    cx, cy, cw, ch = w.get_client_window_geometry()
    return cx - fx, cy - fy, fx + fw - cx - cw, fy + fh - cy - ch


def _place(w, x, y, cw, ch):
    """İstemci alanını (x, y, cw, ch) yap. xfwm4, _NET_MOVERESIZE_WINDOW konumuna çerçeve kalınlığını
    BİR KEZ DAHA ekliyor (ölçüldü: istek + kenar = çerçeve) → istek = istemci − 2 × kenar."""
    left, top, right, bottom = _frame(w)
    w.set_geometry(Wnck.WindowGravity.NORTHWEST, _MASK, x - 2 * left, y - 2 * top,
                   cw + left + right, ch + top + bottom)


class Watcher:
    """Tam ekran türünü (mode_of) izler; değişince on_change(mode) çağrılır. on_green verilirse
    (yalnızca bar) yeşil düğme tıklamaları on_green(xid, maximized_now) olarak bildirilir."""

    def __init__(self, screen, on_change, on_green=None, mode=mode_of):
        self.screen, self.on_change, self.on_green, self.mode = screen, on_change, on_green, mode
        self.active = "?"
        self.hist = {}            # xid -> [(zaman, (x, y, w, h))] son birkaç çerçeve geometrisi
        self.quiet = {}           # xid -> bu zamana kadar kendi tetiklediğimiz değişiklikleri yok say
        for w in screen.get_windows():
            self._hook(w)
        screen.connect("window-opened", lambda s, w: self._hook(w))
        screen.connect("window-closed", lambda s, w: self._forget(w.get_xid()))
        screen.connect("active-window-changed", lambda *_: GLib.idle_add(self.check))
        GLib.idle_add(self.check)

    def _hook(self, w):
        xid = w.get_xid()
        w.connect("state-changed", lambda ww, ch, new: self._state(xid, ww, ch, new))
        if self.on_green:
            self._geom(xid, w)
            w.connect("geometry-changed", lambda ww: self._geom(xid, ww))

    def _forget(self, xid):
        self.hist.pop(xid, None)
        self.quiet.pop(xid, None)
        GLib.idle_add(self.check)

    def check(self):
        m = self.mode(self.screen)
        if m != self.active:
            self.active = m
            self.on_change(m)
        return False

    def mute(self, xid, secs=1.0):
        self.quiet[xid] = time.monotonic() + secs

    # ---------- yeşil düğme ----------
    def _geom(self, xid, w):
        h = self.hist.setdefault(xid, [])
        h.append((time.monotonic(), tuple(w.get_geometry())))
        del h[:-4]

    def _state(self, xid, w, changed, new):
        if changed & Wnck.WindowState.FULLSCREEN:
            GLib.idle_add(self.check)
        if not self.on_green or not (changed & MAX) or w.get_window_type() != Wnck.WindowType.NORMAL:
            return
        now = time.monotonic()
        if now < self.quiet.get(xid, 0):
            return
        # durum değişmeden ÖNCEKİ geometri: geometry-changed, state-changed'den önce de gelebilir
        hist = self.hist.get(xid) or []
        older = [g for t, g in hist if t <= now - 0.12]
        if not hist:
            return
        gx, gy, _, _ = older[-1] if older else hist[0][1]
        px, py = pointer()
        green = gx <= px <= gx + ZONE_W and gy <= py <= gy + ZONE_H
        GLib.idle_add(self.on_green, xid, bool(new & MAX), green)


class MacFullscreen:
    """Yeşil düğme tam ekranı (bar sürecinde). strut(on) çubuğun üst şerit ayırmasını açar/kapatır:
    xfwm4 başlık çubuğunu ayrılmış şeridin altına sokmaz → yerleştirme anında kısa süre kaldırılır."""

    def __init__(self, bar_h, geometry, strut, on_change):
        self.bar_h, self.geometry, self.strut, self.on_change = bar_h, geometry, strut, on_change
        self.state = {x: v for x, v in load_state().items() if Wnck.Window.get(x) is not None}
        self.watcher = None
        self._save()

    def _save(self):
        try:
            os.makedirs(daemon.RUN, exist_ok=True)
            with open(STATE, "w") as f:
                json.dump({str(k): v for k, v in self.state.items()}, f)
        except Exception:
            pass
        pid = daemon.running("dock")                      # dock yeniden kontrol etsin
        if pid:
            try:
                os.kill(pid, 12)                          # SIGUSR2
            except Exception:
                pass
        self.on_change()

    def active(self, xid):
        return xid in self.state

    def toggle(self, xid):
        (self.exit if xid in self.state else self.enter)(xid)

    def enter(self, xid, was_max=None):
        w = Wnck.Window.get(xid)
        if w is None or w.get_window_type() != Wnck.WindowType.NORMAL or xid in self.state:
            return
        if w.is_fullscreen():
            w.set_fullscreen(False)
        if was_max is None:
            was_max = w.is_maximized()
        if self.watcher:
            self.watcher.mute(xid, 1.5)
        if w.is_maximized():
            w.unmaximize()
        # büyütmeden çıkış uygulansın, sonra şimdiki (normal) boyutu kaydet ve yerleştir
        GLib.timeout_add(150, self._enter2, xid, was_max)

    def _enter2(self, xid, was_max):
        w = Wnck.Window.get(xid)
        if w is None:
            return False
        self.state[xid] = {"geom": list(w.get_client_window_geometry()), "max": was_max}
        mx, my, mw, mh = self.geometry
        gl, gr, gt, gb = _gtk_extents(xid)
        target = (mx - gl, my + self.bar_h - gt, mw + gl + gr, mh - self.bar_h + gt + gb)
        # xfwm4 başlık çubuğunu çubuğun ayırdığı şeridin altına sokmaz → yalnızca başlığı/gölgesi
        # şeride taşan pencerelerde şeridi kısa süre kaldır. Kenarlıksız pencerelerde (Claude) KALDIRMA:
        # çalışma alanı değişince Electron kendi sınırlarını yeniden uygulayıp pencereyi y=0'a kaydırıyordu.
        lift = _frame(w)[1] + gt > 0
        if lift:
            self.strut(False)
        _place(w, *target)
        if lift:
            GLib.timeout_add(400, lambda: (self.strut(True), False)[1])
        GLib.timeout_add(700, self._verify, xid, target, 2)
        w.activate(Gtk.get_current_event_time() or 0)
        self._save()
        return False

    def _verify(self, xid, target, tries):
        """Uygulama (Electron vb.) yerleştirmeden sonra kendi sınırlarını uygularsa yeniden yerleştir."""
        w = Wnck.Window.get(xid)
        if w is None or xid not in self.state or tries <= 0:
            return False
        if tuple(w.get_client_window_geometry()) != target:
            lift = _frame(w)[1] > 0
            if lift:
                self.strut(False)
            _place(w, *target)
            if lift:
                GLib.timeout_add(400, lambda: (self.strut(True), False)[1])
            GLib.timeout_add(700, self._verify, xid, target, tries - 1)
        return False

    def exit(self, xid):
        st = self.state.pop(xid, None)
        w = Wnck.Window.get(xid)
        if st is not None and w is not None:
            if self.watcher:
                self.watcher.mute(xid, 1.5)
            x, y, cw, ch = st["geom"]
            _place(w, x, y, cw, ch)
            if st.get("max"):
                GLib.timeout_add(150, lambda: (w.maximize() if Wnck.Window.get(xid) else None, False)[1])
        self._save()

    def forget(self, xid):
        if self.state.pop(xid, None) is not None:
            self._save()


class TitleStrip(Gtk.Window):
    """Tam ekranda fare menü çubuğu bölgesine gelince açılan başlık şeridi (macOS): trafik ışıkları +
    pencere adı. Kırmızı kapatır, yeşil tam ekrandan çıkar(ır); sarı macOS'taki gibi devre dışı.
    y: şeridin üst kenarı; trigger_h: imleç bu yüksekliğin içinde beklerse açılır."""
    H = 30

    def __init__(self, mx, mw, on_close, on_exit):
        super().__init__(type=Gtk.WindowType.POPUP)       # override-redirect: tam ekranın üstünde
        self.set_app_paintable(True)
        vis = self.get_screen().get_rgba_visual()
        if vis:
            self.set_visual(vis)
        self.mx, self.mw, self.y, self.trigger_h = mx, mw, 0, 2
        self.on_close, self.on_exit = on_close, on_exit
        self.set_size_request(mw, self.H)
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON_RELEASE_MASK |
                        Gdk.EventMask.POINTER_MOTION_MASK | Gdk.EventMask.LEAVE_NOTIFY_MASK)
        self.connect("draw", self._draw)
        self.connect("button-release-event", self._release)
        self.connect("motion-notify-event", lambda w, e: self._set_hover(e.x < 80))
        self.connect("leave-notify-event", lambda *_: self._set_hover(False))
        self.xid, self.title, self.hover = None, "", False
        self._edge_since = None
        self._poll_id = None

    # ---------- izleme ----------
    def start(self, y, trigger_h, delay=0.25):
        self.y, self.trigger_h, self.delay = y, trigger_h, delay
        self.hide()
        self.move(self.mx, y)
        if self._poll_id is None:
            self._poll_id = GLib.timeout_add(POLL_MS, self._poll)

    def stop(self):
        if self._poll_id is not None:
            GLib.source_remove(self._poll_id)
            self._poll_id = None
        self._edge_since = None
        self.hide()

    def _poll(self):
        x, y = pointer()
        inside = self.mx <= x < self.mx + self.mw
        if self.get_visible():
            if not inside or y > self.y + self.H + 12:
                self.hide()
        elif inside and y < self.trigger_h:
            now = time.monotonic()
            self._edge_since = self._edge_since or now
            if now - self._edge_since >= self.delay:        # kısa bekleme: yanlışlıkla açılmasın
                self._reveal()
        else:
            self._edge_since = None
        return True

    def _reveal(self):
        w = Wnck.Screen.get_default().get_active_window()
        if w is None:
            return
        self.xid, self.title = w.get_xid(), w.get_name() or ""
        self._edge_since = None
        self.hover = False
        self.show_all()
        if self.get_window() is not None:
            self.get_window().raise_()

    # ---------- çizim ----------
    def _set_hover(self, on):
        if on != self.hover:
            self.hover = on
            self.queue_draw()
        return False

    def _draw(self, w, cr):
        W, H = self.mw, self.H
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.set_source_rgba(*design.surface(0.96))
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)
        cr.rectangle(0, H - 1, W, 1)
        cr.set_source_rgba(0, 0, 0, 0.12)
        cr.fill()
        cy = H / 2
        for i, rgb in enumerate(((1.0, 0.37, 0.34), (0.78, 0.78, 0.79), (0.16, 0.78, 0.25))):
            cx = 20 + i * 20
            design.circle(cr, cx, cy, 6)
            cr.set_source_rgb(*rgb)
            cr.fill()
            if not self.hover or i == 1:
                continue
            cr.set_source_rgba(0, 0, 0, 0.55)
            cr.set_line_width(1.2)
            if i == 0:                                     # ×
                for dx in (-1, 1):
                    cr.move_to(cx - 2.6, cy - 2.6 * dx)
                    cr.line_to(cx + 2.6, cy + 2.6 * dx)
                cr.stroke()
            else:                                          # tam ekrandan çık: içe bakan iki üçgen
                for s in (-1, 1):
                    cr.move_to(cx + 0.6 * s, cy + 0.6 * s)
                    cr.line_to(cx + 3.6 * s, cy + 0.6 * s)
                    cr.line_to(cx + 0.6 * s, cy + 3.6 * s)
                    cr.close_path()
                    cr.fill()
        lay = PangoCairo.create_layout(cr)
        lay.set_font_description(Pango.FontDescription(f"{design.FONT} Semi-Bold 10"))
        lay.set_width(int((W - 240) * Pango.SCALE))
        lay.set_ellipsize(Pango.EllipsizeMode.END)
        lay.set_text(self.title, -1)
        tw, th = lay.get_pixel_size()
        cr.move_to((W - tw) / 2, (H - th) / 2)
        cr.set_source_rgba(*design.ink(0.70))
        PangoCairo.show_layout(cr, lay)
        return True

    def _release(self, w, e):
        if self.xid is None or e.button != 1 or abs(e.y - self.H / 2) > 9:
            return True
        if abs(e.x - 20) <= 9:
            self.hide()
            self.on_close(self.xid, e.time)
        elif abs(e.x - 60) <= 9:
            self.hide()
            self.on_exit(self.xid)
        return True
