"""Liquid — "Uygulamalar" ekranı (macOS 26'da Launchpad'in yerini alan tam ekran ızgara).

  - Arka plan: duvar kâğıdının tamamı bulanık + hafif karartılmış
  - Üstte cam kapsül arama; yazdıkça süzer, Enter ilk sonucu açar
  - 7 x 5 ızgara, sayfalar: tekerlek / ←→ / sürükleme / alttaki noktalar
  - Esc önce aramayı temizler sonra kapatır; boş yere tıklamak kapatır
  - RAM'de bekler: SIGUSR1 = aç/kapat (dock'taki Uygulamalar, menü çubuğu Git → Uygulamalar)

Çalıştırma: python3 -m liquid.launcher [--show]
"""
import math
import signal
import sys
import time

import cairo
import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("PangoCairo", "1.0")
from gi.repository import Gtk, Gdk, GdkPixbuf, Gio, GLib, Pango, PangoCairo  # noqa: E402

from .core import design, wallpaper, daemon, apps, screen_geometry, restart_on_monitor_change  # noqa: E402
from .core.i18n import t, fold  # noqa: E402

COLS, ROWS = 7, 5
PER = COLS * ROWS
ANIM_MS = 170


def rank(a, q):
    n = a["key"]
    if n.startswith(q):
        return 0
    if any(w.startswith(q) for w in n.split()):
        return 1
    if q in n:
        return 2
    return 3 if q in a["kw"] else None


class Launcher(Gtk.Window):
    def __init__(self):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.set_name("lapps")
        self.set_title("Liquid Apps")
        self.set_decorated(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_keep_above(True)
        # tam ekran (fullscreen) modunda xfwm4 "üstte" bayrağını düşürüyor; kullanıcının "her zaman
        # üstte" pencereleri öne geçiyordu → diyalog tipi + ekran boyutunda pencere (fullscreen YOK)
        self.set_type_hint(Gdk.WindowTypeHint.DIALOG)
        self.set_app_paintable(True)
        vis = self.get_screen().get_rgba_visual()
        if vis:
            self.set_visual(vis)
        self.mx, self.my, self.mw, self.mh = screen_geometry()
        self.set_default_size(self.mw, self.mh)
        self.set_size_request(self.mw, self.mh)
        self.set_resizable(False)
        self.move(self.mx, self.my)
        css = Gtk.CssProvider()
        css.load_from_data(f"""
#lapps entry {{ background-color: rgba(255,255,255,0.20); color: #fff; border-radius: 980px;
    border: 1px solid rgba(255,255,255,0.35); box-shadow: inset 0 1px rgba(255,255,255,0.35);
    padding: 4px 12px; min-height: 24px; font-family: "SF Pro Text","{design.FONT}",sans-serif;
    font-size: 13px; caret-color: #fff; }}
#lapps entry image {{ color: rgba(255,255,255,0.85); }}
""".encode())
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), css,
                                                 Gtk.STYLE_PROVIDER_PRIORITY_USER + 20)
        ov = Gtk.Overlay()
        self.add(ov)
        self.area = Gtk.DrawingArea()
        self.area.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON_RELEASE_MASK |
                             Gdk.EventMask.SCROLL_MASK | Gdk.EventMask.SMOOTH_SCROLL_MASK)
        self.area.connect("draw", self.on_draw)
        self.area.connect("button-press-event", self.on_press)
        self.area.connect("button-release-event", self.on_release)
        self.area.connect("scroll-event", self.on_scroll)
        ov.add(self.area)
        self.entry = Gtk.SearchEntry(placeholder_text=t("search"))
        self.entry.set_halign(Gtk.Align.CENTER)
        self.entry.set_valign(Gtk.Align.START)
        self.entry.set_margin_top(54)
        self.entry.set_size_request(250, -1)
        self.entry.connect("search-changed", lambda *_: self._filter())
        self.entry.connect("activate", lambda *_: self.view and self._launch(self.view[0]))
        ov.add_overlay(self.entry)
        self.connect("key-press-event", self.on_key)
        self.connect("focus-out-event", self._focus_out)

        self.apps = []
        self.view = []
        self.surf = {}
        self.page, self.offset = 0, 0.0
        self.alpha, self.zoom = 0.0, 1.0
        self.anim = None
        self.anim_id = None
        self.press = None
        self.bg = None
        self._wp_key = None
        self._shown_at = 0.0
        self._acc, self._last_scroll = 0.0, 0.0
        self._reload()
        Gio.AppInfoMonitor.get().connect("changed", lambda *_: GLib.timeout_add(500, self._reload))
        GLib.idle_add(self._preload)
        GLib.idle_add(lambda: (self._bg(), False)[1])

    # ---------- veri ----------
    def _reload(self):
        self.apps = apps.all_apps()
        self.surf.clear()
        self._filter()
        return False

    def _ip(self):
        cw = self.mw * (1 - 2 * 0.13) / COLS
        ch = (self.mh - 150 - 120) / ROWS
        return int(min(cw * 0.56, ch * 0.60, 104))

    def _icon(self, a):
        if a["did"] in self.surf:
            return self.surf[a["did"]]
        sf = self.get_scale_factor()
        size = self._ip() * sf
        th = Gtk.IconTheme.get_default()
        s = None
        try:
            gic = a["info"].get_icon()
            info = (th.lookup_by_gicon(gic, size, Gtk.IconLookupFlags.FORCE_SIZE) if gic else None) or \
                th.lookup_icon("application-x-executable", size, Gtk.IconLookupFlags.FORCE_SIZE)
            pb = info.load_icon()
            if pb.get_width() != size:
                pb = pb.scale_simple(size, size, GdkPixbuf.InterpType.HYPER)
            s = Gdk.cairo_surface_create_from_pixbuf(pb, sf, None)
        except Exception:
            s = None
        self.surf[a["did"]] = s
        return s

    def _preload(self):
        for a in self.apps:
            if a["did"] not in self.surf:
                self._icon(a)
                return True
        return False

    def _filter(self):
        q = fold(self.entry.get_text().strip())
        if not q:
            self.view = self.apps
        else:
            hits = [(r, a["key"], a) for a in self.apps if (r := rank(a, q)) is not None]
            self.view = [h[2] for h in sorted(hits, key=lambda h: (h[0], h[1]))]
        self.page, self.offset = 0, 0.0
        self.area.queue_draw()

    def _pages(self):
        return max(1, math.ceil(len(self.view) / PER))

    def _bg(self):
        p, st, mt = wallpaper.current()
        if (p, st, mt) != self._wp_key:
            self._wp_key = (p, st, mt)
            self.bg = wallpaper.region(self.mw, self.mh, 0, 0, self.mw, self.mh, blur=40, saturate=1.15)

    # ---------- geometri ----------
    def _cell(self, i):
        page, pos = divmod(i, PER)
        r, c = divmod(pos, COLS)
        mx = self.mw * 0.13
        top, bottom = 150, self.mh - 120
        cw, ch = (self.mw - 2 * mx) / COLS, (bottom - top) / ROWS
        return mx + c * cw + (page - self.offset) * self.mw, top + r * ch, cw, ch

    def _hit(self, x, y):
        ip = self._ip()
        first = self.page * PER
        for i in range(first, min(first + PER, len(self.view))):
            cx, cy, cw, ch = self._cell(i)
            ix, iy = cx + (cw - ip) / 2, cy + 4
            if ix - 8 <= x <= ix + ip + 8 and iy - 4 <= y <= iy + ip + 26:
                return self.view[i]
        return None

    def _dot(self, x, y):
        n = self._pages()
        x0 = self.mw / 2 - (n - 1) * 9
        for p in range(n):
            if n > 1 and abs(x - (x0 + p * 18)) <= 8 and abs(y - (self.mh - 70)) <= 10:
                return p
        return None

    # ---------- çizim ----------
    def on_draw(self, w, cr):
        W, H = self.mw, self.mh
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.set_source_rgba(0, 0, 0, 0)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)
        if self.bg is not None:
            cr.set_source_surface(self.bg, 0, 0)
            cr.paint_with_alpha(self.alpha)
            cr.set_source_rgba(0, 0, 0, 0.18 * self.alpha)
        else:
            cr.set_source_rgba(0.12, 0.12, 0.14, 0.86 * self.alpha)
        cr.paint()
        ip = self._ip()
        lay = PangoCairo.create_layout(cr)
        lay.set_font_description(Pango.FontDescription(f"{design.FONT} Medium 10"))
        lay.set_ellipsize(Pango.EllipsizeMode.END)
        lay.set_alignment(Pango.Alignment.CENTER)
        cr.save()
        cr.translate(W / 2, H / 2)
        cr.scale(self.zoom, self.zoom)
        cr.translate(-W / 2, -H / 2)
        lo, hi = math.floor(self.offset), math.ceil(self.offset)
        for i, a in enumerate(self.view):
            if i // PER not in (lo, hi):
                continue
            x, y, cw, ch = self._cell(i)
            if x + cw < 0 or x > W:
                continue
            ix, iy = x + (cw - ip) / 2, y + 4
            s = self._icon(a)
            if s:
                cr.set_source_surface(s, ix, iy)
                cr.paint_with_alpha(self.alpha)
                if self.press is not None and self.press[2] is a:
                    design.rrect(cr, ix + ip * .07, iy + ip * .07, ip * .86, ip * .86, ip * .22)
                    cr.set_source_rgba(0, 0, 0, 0.30)
                    cr.fill()
            lay.set_width(int((cw - 8) * Pango.SCALE))
            lay.set_text(a["name"], -1)
            cr.move_to(x + 4, iy + ip + 8)
            cr.set_source_rgba(0, 0, 0, 0.40 * self.alpha)
            PangoCairo.show_layout(cr, lay)
            cr.move_to(x + 4, iy + ip + 7)
            cr.set_source_rgba(1, 1, 1, 0.97 * self.alpha)
            PangoCairo.show_layout(cr, lay)
        cr.restore()
        n = self._pages()
        if n > 1:
            x0 = W / 2 - (n - 1) * 9
            for p in range(n):
                design.circle(cr, x0 + p * 18, H - 70, 3.6)
                cr.set_source_rgba(1, 1, 1, (0.95 if p == self.page else 0.40) * self.alpha)
                cr.fill()
        if not self.view:
            lay.set_width(-1)
            lay.set_text(t("no_results"), -1)
            tw, th = lay.get_pixel_size()
            cr.move_to((W - tw) / 2, H / 2 - th)
            cr.set_source_rgba(1, 1, 1, 0.75 * self.alpha)
            PangoCairo.show_layout(cr, lay)
        return True

    # ---------- animasyon ----------
    def _animate(self, target, done=None):
        self.anim = (target, done, time.monotonic(), self.alpha)
        if self.anim_id is None:
            self.anim_id = GLib.timeout_add(16, self._tick)

    def _tick(self):
        busy = False
        if self.anim is not None:
            ta, done, t0, a0 = self.anim
            p = min(1.0, (time.monotonic() - t0) * 1000 / ANIM_MS)
            e = 1 - (1 - p) ** 3
            self.alpha = a0 + (ta - a0) * e
            self.zoom = 1.0 + 0.06 * (1 - self.alpha)
            if p >= 1.0:
                self.anim = None
                if done:
                    done()
            else:
                busy = True
        if abs(self.offset - self.page) > 0.002:
            self.offset += (self.page - self.offset) * 0.22
            busy = True
        else:
            self.offset = float(self.page)
        self.area.queue_draw()
        if not busy:
            self.anim_id = None
        return busy

    def _go(self, p):
        p = max(0, min(self._pages() - 1, p))
        if p != self.page:
            self.page = p
            if self.anim_id is None:
                self.anim_id = GLib.timeout_add(16, self._tick)

    # ---------- göster / gizle ----------
    def toggle(self):
        if self.get_visible() and (self.anim is None or self.anim[0] > 0):
            self.hide_apps()
        else:
            self.show_apps()

    def show_apps(self):
        self._bg()
        self.entry.set_text("")
        self._filter()
        self.alpha, self.zoom = 0.0, 1.06
        self._shown_at = time.monotonic()
        self.move(self.mx, self.my)
        self.show_all()
        # xfwm4 odak-çalma koruması yeni pencereyi öndeki pencerenin ALTINA koyabiliyor ve
        # "üstte" bayrağı haritalamada düşebiliyor → gösterdikten sonra yeniden uygula + öne al
        self.set_keep_above(True)
        if self.get_window() is not None:
            self.get_window().raise_()
        self.present()
        GLib.timeout_add(60, self._focus)
        self._animate(1.0)

    def _focus(self):
        win = self.get_window()
        if win is not None:
            win.focus(Gdk.CURRENT_TIME)
        self.entry.grab_focus_without_selecting()
        return False

    def _focus_out(self, *_):
        if self.get_visible() and time.monotonic() - self._shown_at > 0.6:
            self.hide_apps()
        return False

    def hide_apps(self):
        self._animate(0.0, done=self.hide)

    # ---------- olaylar ----------
    def on_key(self, w, e):
        k = e.keyval
        if k == Gdk.KEY_Escape:
            if self.entry.get_text():
                self.entry.set_text("")
            else:
                self.hide_apps()
            return True
        if not self.entry.get_text() and k in (Gdk.KEY_Right, Gdk.KEY_Page_Down, Gdk.KEY_Left, Gdk.KEY_Page_Up):
            self._go(self.page + (1 if k in (Gdk.KEY_Right, Gdk.KEY_Page_Down) else -1))
            return True
        return False

    def on_scroll(self, w, e):
        dx = dy = 0.0
        if e.direction == Gdk.ScrollDirection.SMOOTH:
            _, dx, dy = e.get_scroll_deltas()
        else:
            dy = 1 if e.direction in (Gdk.ScrollDirection.DOWN, Gdk.ScrollDirection.RIGHT) else -1
        self._acc += dx + dy
        now = time.monotonic()
        if abs(self._acc) >= 1.0 and now - self._last_scroll > 0.35:
            self._go(self.page + (1 if self._acc > 0 else -1))
            self._last_scroll, self._acc = now, 0.0
        return True

    def on_press(self, w, e):
        if e.button == 1:
            self.press = (e.x, e.y, self._hit(e.x, e.y))
            self.area.queue_draw()
        return True

    def on_release(self, w, e):
        if e.button != 1 or self.press is None:
            return True
        x0, y0, it = self.press
        self.press = None
        if abs(e.x - x0) > 60 and abs(e.x - x0) > abs(e.y - y0):
            self._go(self.page + (1 if e.x < x0 else -1))
        elif (d := self._dot(e.x, e.y)) is not None:
            self._go(d)
        elif it is not None and self._hit(e.x, e.y) is it:
            self._launch(it)
        elif it is None:
            self.hide_apps()
        self.area.queue_draw()
        return True

    def _launch(self, a):
        apps.launch(a["info"])
        self.hide_apps()


def main():
    if not daemon.claim("launcher"):
        return
    restart_on_monitor_change()
    lp = Launcher()
    daemon.on_signal(signal.SIGUSR1, lp.toggle)
    if "--show" in sys.argv:
        GLib.timeout_add(150, lambda: (lp.show_apps(), False)[1])
    Gtk.main()


if __name__ == "__main__":
    main()
