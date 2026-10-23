"""Liquid — Spotlight (macOS 26/27: ortada büyük cam kapsül + sonuç listesi). GTK + cairo.

Arar: hesap makinesi (3,5*2 gibi ondalık virgül dahil; güvenli ayrıştırıcı) · uygulamalar ·
ev dizinindeki dosya/klasörler · web. ↑↓ gezinme, Enter açar, Esc kapatır; ikinci ⌘Space
(ya da menü çubuğundaki büyüteç) kapatır.

Çalıştırma: python3 -m liquid.spotlight [--show]
"""
import ast
import operator
import os
import re
import signal
import subprocess
import sys
import threading
import time
import urllib.parse

import cairo
import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("PangoCairo", "1.0")
from gi.repository import Gtk, Gdk, GLib, Gio, GdkPixbuf, Pango, PangoCairo  # noqa: E402

from .core import design, wallpaper, daemon, apps, screen_geometry  # noqa: E402
from .core.i18n import t, fold  # noqa: E402

W = 680
BAR = 58
ROW = 46
MAXROWS = 9
_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
        ast.Pow: operator.pow, ast.Mod: operator.mod, ast.FloorDiv: operator.floordiv,
        ast.USub: operator.neg, ast.UAdd: operator.pos}


def _ev(n):
    if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
        return n.value
    if isinstance(n, ast.BinOp) and type(n.op) in _OPS:
        a, b = _ev(n.left), _ev(n.right)
        if isinstance(n.op, ast.Pow) and (abs(b) > 1000 or (abs(a) > 1e6 and b > 10)):
            raise ValueError                      # 9**9**9 gibi ifadeler süreci kilitler
        return _OPS[type(n.op)](a, b)
    if isinstance(n, ast.UnaryOp) and type(n.op) in _OPS:
        return _OPS[type(n.op)](_ev(n.operand))
    raise ValueError


def calc(expr):
    e = expr.strip().rstrip("=").replace("×", "*").replace("÷", "/")
    if re.fullmatch(r"[\d\s+\-*/().,%^]+", e) and "," in e and "." not in e:
        e = e.replace(",", ".")
    if not re.fullmatch(r"[\d\s+\-*/().%^]+", e) or not re.search(r"\d\s*[+\-*/%^]", e):
        return None
    try:
        r = _ev(ast.parse(e.replace("^", "**"), mode="eval").body)
    except Exception:
        return None
    try:
        if isinstance(r, float):
            if r != r or abs(r) == float("inf"):
                return None
            s = str(int(r)) if r.is_integer() and abs(r) < 1e15 else f"{r:.10g}"
        elif abs(r) < 10 ** 15:
            s = str(r)
        else:
            # float'a sığmayan tamsayı (9^999): f"{r:.6e}" OverflowError veriyordu → Decimal ile bilimsel gösterim
            from decimal import Decimal
            s = f"{Decimal(r):.6e}"
    except (OverflowError, ValueError):
        return None
    return s.replace(".", ",") if os.environ.get("LANG", "").startswith("tr") else s


def scan_files(root, depth=4, limit=40000):
    out, stack = [], [(root, 0)]
    skip = {"node_modules", "__pycache__", "venv", ".venv", "site-packages", "snap"}
    while stack and len(out) < limit:
        d, lv = stack.pop()
        try:
            with os.scandir(d) as it:
                for en in it:
                    if en.name.startswith(".") or en.name in skip:
                        continue
                    try:
                        isdir = en.is_dir(follow_symlinks=False)
                    except OSError:
                        continue
                    out.append((fold(en.name), en.path, isdir))
                    if isdir and lv < depth:
                        stack.append((en.path, lv + 1))
        except OSError:
            pass
    return out


class Spotlight(Gtk.Window):
    def __init__(self):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.set_name("lspot")
        self.set_title("Liquid Spotlight")
        self.set_decorated(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_keep_above(True)
        self.set_type_hint(Gdk.WindowTypeHint.DIALOG)
        self.set_app_paintable(True)
        vis = self.get_screen().get_rgba_visual()
        if vis:
            self.set_visual(vis)
        self.mx, self.my, self.mw, self.mh = screen_geometry()
        self.sh = 18
        css = Gtk.CssProvider()
        css.load_from_data(f"""
#lspot entry {{ background: none; border: none; box-shadow: none; color: rgba(0,0,0,0.88);
    font-family: "SF Pro Display","{design.FONT}",sans-serif; font-size: 22px; font-weight: 400;
    padding: 0; caret-color: rgba(10,132,255,1); }}
""".encode())
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), css,
                                                 Gtk.STYLE_PROVIDER_PRIORITY_USER + 20)
        ov = Gtk.Overlay()
        self.add(ov)
        self.area = Gtk.DrawingArea()
        self.area.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.POINTER_MOTION_MASK)
        self.area.connect("draw", self.on_draw)
        self.area.connect("button-press-event", self.on_click)
        self.area.connect("motion-notify-event", self.on_motion)
        ov.add(self.area)
        self.entry = Gtk.Entry(placeholder_text=t("spotlight"))
        self.entry.set_halign(Gtk.Align.START)
        self.entry.set_valign(Gtk.Align.START)
        self.entry.set_margin_start(self.sh + 58)
        self.entry.set_margin_top(self.sh + 14)
        self.entry.set_size_request(W - 80, 30)
        self.entry.connect("changed", lambda *_: self._search())
        self.entry.connect("activate", lambda *_: self._open(self.sel))
        self.entry.connect("key-press-event", self.on_key)
        ov.add_overlay(self.entry)
        self.connect("focus-out-event", self._focus_out)
        self.apps = apps.all_apps()
        Gio.AppInfoMonitor.get().connect("changed", lambda *_: setattr(self, "apps", apps.all_apps()))
        self.files, self._files_at = [], 0.0
        self.results, self.sel = [], 0
        self.icons = {}
        self.backdrop = None
        self._shown_at = 0.0
        self._resize()

    # ---------- boyut / konum ----------
    def _resize(self):
        n = min(len(self.results), MAXROWS)
        self.H = BAR + (n * ROW + 16 if n else 0)
        self.set_size_request(W + 2 * self.sh, self.H + 2 * self.sh)
        self.resize(W + 2 * self.sh, self.H + 2 * self.sh)
        x = self.mx + (self.mw - W) // 2 - self.sh
        y = self.my + int(self.mh * 0.20) - self.sh
        self.move(x, y)
        self.backdrop = wallpaper.region(self.mw, self.mh, x + self.sh, y + self.sh, W,
                                         BAR + MAXROWS * ROW + 16, blur=30)
        self.area.queue_draw()

    def toggle(self):
        if self.get_visible():
            self.hide()
        else:
            self.show_spot()

    def show_spot(self):
        if time.monotonic() - self._files_at > 120:
            self._files_at = time.monotonic()
            threading.Thread(target=lambda: setattr(self, "files", scan_files(os.path.expanduser("~"))),
                             daemon=True).start()
        self.entry.set_text("")
        self.results = []
        self._resize()
        self._shown_at = time.monotonic()
        self.show_all()
        # xfwm4 odak-çalma koruması yeni pencereyi öndeki pencerenin ALTINA koyabiliyor ve
        # "üstte" bayrağı haritalamada düşebiliyor → gösterdikten sonra yeniden uygula + öne al
        self.set_keep_above(True)
        if self.get_window() is not None:
            self.get_window().raise_()
        self.present()
        GLib.timeout_add(60, self._focus)

    def _focus(self):
        win = self.get_window()
        if win is not None:
            win.focus(Gdk.CURRENT_TIME)
        self.entry.grab_focus()
        return False

    def _focus_out(self, *_):
        if time.monotonic() - self._shown_at > 0.5:
            self.hide()
        return False

    # ---------- arama ----------
    def _search(self):
        q = self.entry.get_text().strip()
        ql = fold(q)
        res = []
        if q:
            c = calc(q)
            if c is not None:
                res.append(("calc", "= " + c, t("app_calculator"), "accessories-calculator", c))
            hits = []
            for a in self.apps:
                n = a["key"]
                r = 0 if n.startswith(ql) else 1 if any(w.startswith(ql) for w in n.split()) else \
                    2 if ql in n else 3 if ql in a["kw"] else None
                if r is not None:
                    hits.append((r, n, a))
            for _, _, a in sorted(hits, key=lambda h: (h[0], h[1]))[:6]:
                res.append(("app", a["name"], a["info"].get_description() or t("go_apps"), a["info"].get_icon(), a))
            if len(ql) >= 2 and c is None:
                home = os.path.expanduser("~")
                fh = sorted(((0 if nm.startswith(ql) else 1, not d, len(nm), p, d)
                             for nm, p, d in self.files if ql in nm))[:4]
                for *_, p, d in fh:
                    res.append(("file", os.path.basename(p), os.path.dirname(p).replace(home, "~", 1),
                                "folder" if d else "text-x-generic", p))
            # en fazla MAXROWS satır çiziliyor: fazlası görünmez seçilip açılabiliyordu; web araması hep son satır
            res = res[:MAXROWS - 1]
            res.append(("web", t("web_search").format(q), "DuckDuckGo", "web-browser", q))
        self.results, self.sel = res, 0
        self._resize()

    def _open(self, i):
        if not (0 <= i < len(self.results)):
            return
        kind, *_, data = self.results[i]
        if kind == "app":
            apps.launch(data["info"])
        elif kind == "file":
            subprocess.Popen(["xdg-open", data], start_new_session=True,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif kind == "web":
            subprocess.Popen(["xdg-open", "https://duckduckgo.com/?q=" + urllib.parse.quote_plus(data)],
                             start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif kind == "calc":
            Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD).set_text(data, -1)
        self.hide()

    def on_key(self, w, e):
        if e.keyval == Gdk.KEY_Escape:
            self.hide()
            return True
        if e.keyval in (Gdk.KEY_Down, Gdk.KEY_Up) and self.results:
            self.sel = (self.sel + (1 if e.keyval == Gdk.KEY_Down else -1)) % len(self.results)
            self.area.queue_draw()
            return True
        return False

    def _row_at(self, y):
        i = int((y - self.sh - BAR - 8) // ROW)
        return i if 0 <= i < min(len(self.results), MAXROWS) and y > self.sh + BAR else None

    def on_motion(self, w, e):
        i = self._row_at(e.y)
        if i is not None and i != self.sel:
            self.sel = i
            self.area.queue_draw()
        return False

    def on_click(self, w, e):
        i = self._row_at(e.y)
        if i is not None:
            self._open(i)
        return True

    # ---------- çizim ----------
    def _pix(self, icon, size):
        key = (str(icon), size)
        if key in self.icons:
            return self.icons[key]
        th = Gtk.IconTheme.get_default()
        s = None
        try:
            gic = Gio.ThemedIcon.new(icon) if isinstance(icon, str) else icon
            info = th.lookup_by_gicon(gic, size, Gtk.IconLookupFlags.FORCE_SIZE)
            if info:
                pb = info.load_icon()
                if pb.get_width() != size:
                    pb = pb.scale_simple(size, size, GdkPixbuf.InterpType.HYPER)
                s = Gdk.cairo_surface_create_from_pixbuf(pb, 1, None)
        except Exception:
            s = None
        self.icons[key] = s
        return s

    def on_draw(self, w, cr):
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.set_source_rgba(0, 0, 0, 0)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)
        cr.translate(self.sh, self.sh)
        r = BAR / 2 if not self.results else 24
        design.liquid_glass(cr, 0, 0, W, self.H, r, backdrop=self.backdrop, tint=(1, 1, 1, 0.55))
        # büyüteç
        cr.set_line_width(2.2)
        cr.arc(30, BAR / 2 - 2, 8, 0, 6.2832)
        cr.set_source_rgba(0, 0, 0, 0.55)
        cr.stroke()
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.move_to(36, BAR / 2 + 4)
        cr.line_to(41, BAR / 2 + 9)
        cr.stroke()
        if not self.results:
            return True
        cr.rectangle(16, BAR, W - 32, 1)
        cr.set_source_rgba(0, 0, 0, 0.08)
        cr.fill()
        for i, (kind, title, sub, icon, _) in enumerate(self.results[:MAXROWS]):
            y = BAR + 8 + i * ROW
            if i == self.sel:
                design.rrect(cr, 8, y, W - 16, ROW - 2, 10)
                cr.set_source_rgba(*design.BLUE, 0.95)
                cr.fill()
            s = self._pix(icon, 30)
            if s:
                cr.set_source_surface(s, 20, y + (ROW - 2 - 30) / 2)
                cr.paint()
            fg = (1, 1, 1, 1) if i == self.sel else (0, 0, 0, 0.88)
            sb = (1, 1, 1, 0.8) if i == self.sel else (0, 0, 0, 0.5)
            for txt, yy, sz, wt, col in ((title, y + 5, 10.5, "Semi-Bold", fg), (sub, y + 24, 8.5, "Regular", sb)):
                lay = PangoCairo.create_layout(cr)
                lay.set_font_description(Pango.FontDescription(f"{design.FONT} {wt} {sz}"))
                lay.set_width(int((W - 90) * Pango.SCALE))
                lay.set_ellipsize(Pango.EllipsizeMode.END)
                lay.set_text(txt or "", -1)
                cr.move_to(62, yy)
                cr.set_source_rgba(*col)
                PangoCairo.show_layout(cr, lay)
        return True


def main():
    if not daemon.claim("spotlight"):
        return
    sp = Spotlight()
    GLib.idle_add(lambda: (sp._resize(), False)[1])      # cam arka planını önceden hesapla
    daemon.on_signal(signal.SIGUSR1, sp.toggle)
    if "--show" in sys.argv:
        GLib.timeout_add(150, lambda: (sp.show_spot(), False)[1])
    Gtk.main()


if __name__ == "__main__":
    main()
