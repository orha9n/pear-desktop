"""Liquid — Control Center (macOS 26/27, Liquid Glass modüller). GTK + cairo, ek bağımlılık yok.

Düzen (genişlik 330):
  [Bağlantı: Wi-Fi / Bluetooth / Karanlık Mod]  [Odak]
                                               [Ekranlar][Ekran Görüntüsü]
  [Ekran parlaklığı ───────────────]
  [Ses ─────────────────────────────]
  [Şimdi Çalıyor        ▶  ⏭]
Menü çubuğundaki CC glifine tıklayınca (SIGUSR1) sağ üstte açılır; dışarı tıklayınca kapanır.

Çalıştırma: python3 -m liquid.controlcenter [--show]
"""
import math
import os
import re
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

import cairo
import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("PangoCairo", "1.0")
from gi.repository import Gtk, Gdk, GLib, Pango, PangoCairo  # noqa: E402

from .core import design, wallpaper, daemon, screen_geometry  # noqa: E402
from .core.i18n import t  # noqa: E402

W = 330
PAD = 12
GAP = 10
TILE_R = 20


def run(cmd, timeout=3):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout).stdout.strip()
    except Exception:
        return ""


def run_bg(cmd):
    try:
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    except Exception:
        pass


# ----------------------------- sistem durumu -----------------------------
def wifi():
    on = run(["nmcli", "radio", "wifi"]).lower().startswith("en")
    ssid = ""
    for line in run(["env", "LC_ALL=C.UTF-8", "nmcli", "-t", "-f", "ACTIVE,SSID", "dev", "wifi", "list",
                     "--rescan", "no"]).splitlines():
        a, _, s = line.partition(":")
        if a == "yes" and s:
            ssid = s.replace("\\:", ":")
            break
    return on, ssid


def bluetooth():
    if "Soft blocked: yes" in run(["rfkill", "list", "bluetooth"]):
        return False
    return "Powered: yes" in run(["bluetoothctl", "show"], timeout=2)


def set_bluetooth(on):
    def work():
        run(["rfkill", "unblock" if on else "block", "bluetooth"])
        if on:
            time.sleep(0.6)
            run(["bluetoothctl", "power", "on"], timeout=4)
    threading.Thread(target=work, daemon=True).start()


def dnd():
    return run(["xfconf-query", "-c", "xfce4-notifyd", "-p", "/do-not-disturb"]) == "true"


def dark():
    return "Dark" in run(["xfconf-query", "-c", "xsettings", "-p", "/Net/ThemeName"])


def set_dark(on):
    run_bg(["xfconf-query", "-c", "xsettings", "-p", "/Net/ThemeName", "-s", "MacTahoe-Dark" if on else "MacTahoe-Light"])
    run_bg(["xfconf-query", "-c", "xfwm4", "-p", "/general/theme", "-s", "MacTahoe-Dark" if on else "MacTahoe-Light"])
    run_bg(["xfconf-query", "-c", "xsettings", "-p", "/Net/IconThemeName", "-s", "MacTahoe-dark" if on else "MacTahoe"])


def backlight():
    base = Path("/sys/class/backlight")
    try:
        return next(iter(sorted(base.iterdir())), None)
    except Exception:
        return None


def brightness():
    bl = backlight()
    if bl:
        try:
            return round(int((bl / "brightness").read_text()) * 100 / int((bl / "max_brightness").read_text()))
        except Exception:
            pass
    return 100


def set_brightness(p):
    if backlight():
        run_bg(["brightnessctl", "-q", "set", f"{max(1, p)}%"])


def volume():
    m = re.search(r"(\d+)%", run(["pactl", "get-sink-volume", "@DEFAULT_SINK@"]))
    return int(m.group(1)) if m else 50


def set_volume(p):
    run_bg(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "0"])
    run_bg(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{p}%"])


def player():
    st = run(["playerctl", "status"])
    meta = run(["playerctl", "metadata", "--format", "{{title}}\t{{artist}}\t{{mpris:artUrl}}"])
    title, artist, art = (meta.split("\t") + ["", "", ""])[:3] if meta else ("", "", "")
    if art.startswith("file://"):
        from urllib.parse import unquote
        art = unquote(art[7:])
    else:
        art = ""
    return st, title, artist, art


# ----------------------------- pencere -----------------------------
class ControlCenter(Gtk.Window):
    def __init__(self):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.set_title("Liquid Control Center")
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
        self.shadow = 16
        # yükseklik: bağlantı bloğu 154 + 2 kaydırıcı 64 + oynatıcı 70 + boşluklar
        self.H = PAD * 2 + 154 + GAP + 64 + GAP + 64 + GAP + 72
        self.set_size_request(W + 2 * self.shadow, self.H + 2 * self.shadow)
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON_RELEASE_MASK |
                        Gdk.EventMask.POINTER_MOTION_MASK | Gdk.EventMask.SCROLL_MASK)
        self.connect("draw", self.on_draw)
        self.connect("button-press-event", self.on_press)
        self.connect("button-release-event", self.on_release)
        self.connect("motion-notify-event", self.on_motion)
        self.connect("scroll-event", self.on_scroll)
        self.connect("focus-out-event", self._focus_out)
        self.connect("key-press-event", lambda w, e: self.hide() if e.keyval == Gdk.KEY_Escape else None)
        self.st = {"wifi": (True, ""), "bt": False, "dnd": False, "dark": False, "bri": 100, "vol": 50,
                   "player": ("", "", "", "")}
        self.drag = None           # "bri" | "vol"
        self.regions = []          # (x, y, w, h, eylem)
        self.backdrop = None
        self._shown_at = 0.0
        self._art = (None, None)

    # ---------- konum / görünürlük ----------
    def _place(self):
        x = self.mx + self.mw - W - 10 - self.shadow
        y = self.my + design.BAR_H + 6 - self.shadow
        self.move(x, y)
        self.backdrop = wallpaper.region(self.mw, self.mh, x + self.shadow, y + self.shadow, W, self.H, blur=30)

    def toggle(self):
        if self.get_visible():
            self.hide()
        else:
            self.show_cc()

    def show_cc(self):
        self._place()
        self._shown_at = time.monotonic()
        self.show_all()
        # xfwm4 odak-çalma koruması yeni pencereyi öndeki pencerenin ALTINA koyabiliyor ve
        # "üstte" bayrağı haritalamada düşebiliyor → gösterdikten sonra yeniden uygula + öne al
        self.set_keep_above(True)
        if self.get_window() is not None:
            self.get_window().raise_()
        self.present()
        GLib.timeout_add(60, lambda: (self.get_window() and self.get_window().focus(Gdk.CURRENT_TIME), False)[1])
        threading.Thread(target=self._refresh, daemon=True).start()

    def _focus_out(self, *_):
        if time.monotonic() - self._shown_at > 0.5:
            self.hide()
        return False

    def _refresh(self):
        st = {"wifi": wifi(), "bt": bluetooth(), "dnd": dnd(), "dark": dark(), "bri": brightness(),
              "vol": volume(), "player": player()}
        GLib.idle_add(lambda: (self.st.update(st), self.queue_draw(), False)[2])

    # ---------- çizim yardımcıları ----------
    def _sym(self, name, size, rgba):
        th = Gtk.IconTheme.get_default()
        info = th.lookup_icon(name, size, Gtk.IconLookupFlags.FORCE_SYMBOLIC | Gtk.IconLookupFlags.FORCE_SIZE)
        if info is None:
            return None
        c = Gdk.RGBA(*rgba)
        try:
            pb, _ = info.load_symbolic(c, None, None, None)
            return pb
        except Exception:
            return None

    def _icon(self, cr, name, x, y, size, rgba):
        pb = self._sym(name, size, rgba)
        if pb is not None:
            Gdk.cairo_set_source_pixbuf(cr, pb, x, y)
            cr.paint()

    def _text(self, cr, s, x, y, size, weight="Semi-Bold", rgba=(0, 0, 0, 0.88), width=None):
        lay = PangoCairo.create_layout(cr)
        lay.set_font_description(Pango.FontDescription(f"{design.FONT} {weight} {size}"))
        if width:
            lay.set_width(int(width * Pango.SCALE))
            lay.set_ellipsize(Pango.EllipsizeMode.END)
        lay.set_text(s, -1)
        cr.move_to(x, y)
        cr.set_source_rgba(*rgba)
        PangoCairo.show_layout(cr, lay)

    def _tile(self, cr, x, y, w, h, r=TILE_R):
        design.rrect(cr, x, y, w, h, r)
        cr.set_source_rgba(1, 1, 1, 0.42)
        cr.fill()
        design.rrect(cr, x + 0.5, y + 0.5, w - 1, h - 1, r)
        g = cairo.LinearGradient(0, y, 0, y + h)
        g.add_color_stop_rgba(0, 1, 1, 1, 0.8)
        g.add_color_stop_rgba(1, 1, 1, 1, 0.15)
        cr.set_source(g)
        cr.set_line_width(1)
        cr.stroke()

    def _circle_btn(self, cr, cx, cy, r, on, icon):
        design.circle(cr, cx, cy, r)
        cr.set_source_rgba(*design.BLUE, 1) if on else cr.set_source_rgba(0, 0, 0, 0.10)
        cr.fill()
        s = int(r * 1.05)
        self._icon(cr, icon, cx - s / 2, cy - s / 2, s, (1, 1, 1, 1) if on else (0.1, 0.1, 0.12, 0.9))

    # ---------- çizim ----------
    def on_draw(self, w, cr):
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.set_source_rgba(0, 0, 0, 0)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)
        cr.translate(self.shadow, self.shadow)
        design.liquid_glass(cr, 0, 0, W, self.H, 26, backdrop=self.backdrop, tint=(1, 1, 1, 0.34))
        self.regions = []
        st = self.st
        x0, y = PAD, PAD
        bw = (W - 2 * PAD - GAP) * 0.53
        sw = W - 2 * PAD - GAP - bw
        # --- bağlantı kartı ---
        self._tile(cr, x0, y, bw, 154)
        rows = (("wifi", "network-wireless-symbolic", "Wi-Fi",
                 st["wifi"][1] or (t("on") if st["wifi"][0] else t("off")), st["wifi"][0]),
                ("bt", "bluetooth-active-symbolic", "Bluetooth", t("on") if st["bt"] else t("off"), st["bt"]),
                ("dark", "weather-clear-night-symbolic", t("dark_mode"), t("on") if st["dark"] else t("off"),
                 st["dark"]))
        for i, (key, icon, title, sub, on) in enumerate(rows):
            ry = y + 14 + i * 46
            self._circle_btn(cr, x0 + 28, ry + 15, 15, on, icon)
            self._text(cr, title, x0 + 52, ry + 2, 9.5, "Semi-Bold", width=bw - 60)
            self._text(cr, sub, x0 + 52, ry + 17, 8, "Regular", (0, 0, 0, 0.55), width=bw - 60)
            self.regions.append((x0, ry, bw, 40, key))
        # --- Odak (Rahatsız Etme) ---
        fx = x0 + bw + GAP
        self._tile(cr, fx, y, sw, 72)
        self._circle_btn(cr, fx + 26, y + 36, 15, st["dnd"], "notifications-disabled-symbolic"
                         if Gtk.IconTheme.get_default().has_icon("notifications-disabled-symbolic")
                         else "weather-clear-night-symbolic")
        self._text(cr, t("focus"), fx + 48, y + 20, 9.5, "Semi-Bold", width=sw - 52)
        self._text(cr, t("on") if st["dnd"] else t("off"), fx + 48, y + 36, 8, "Regular", (0, 0, 0, 0.55))
        self.regions.append((fx, y, sw, 72, "dnd"))
        # --- iki kare kutucuk ---
        qw = (sw - GAP) / 2
        for j, (key, icon, label) in enumerate((("mirror", "video-display-symbolic", t("display")),
                                                ("shot", "camera-photo-symbolic", t("screenshot")))):
            qx = fx + j * (qw + GAP)
            self._tile(cr, qx, y + 82, qw, 72)
            self._icon(cr, icon, qx + qw / 2 - 10, y + 96, 20, (0.1, 0.1, 0.12, 0.85))
            lay = PangoCairo.create_layout(cr)
            lay.set_font_description(Pango.FontDescription(f"{design.FONT} Medium 7"))
            lay.set_width(int((qw - 6) * Pango.SCALE))
            lay.set_alignment(Pango.Alignment.CENTER)
            lay.set_wrap(Pango.WrapMode.WORD)
            lay.set_text(label, -1)
            cr.move_to(qx + 3, y + 122)
            cr.set_source_rgba(0, 0, 0, 0.75)
            PangoCairo.show_layout(cr, lay)
            self.regions.append((qx, y + 82, qw, 72, key))
        y += 154 + GAP
        # --- kaydırıcılar ---
        for key, title, icon, val in (("bri", t("display"), "display-brightness-symbolic", st["bri"]),
                                      ("vol", t("sound"), "audio-volume-high-symbolic", st["vol"])):
            self._tile(cr, x0, y, W - 2 * PAD, 64)
            self._text(cr, title, x0 + 14, y + 9, 9.5, "Semi-Bold")
            sx, sy, sl, sh = x0 + 14, y + 32, W - 2 * PAD - 28, 22
            design.rrect(cr, sx, sy, sl, sh, sh / 2)
            cr.set_source_rgba(0, 0, 0, 0.10)
            cr.fill()
            fw = sh + (sl - sh) * max(0, min(100, val)) / 100
            design.rrect(cr, sx, sy, fw, sh, sh / 2)
            cr.set_source_rgba(1, 1, 1, 1)
            cr.fill()
            self._icon(cr, icon, sx + 5, sy + 3, 16, (0.35, 0.35, 0.38, 1))
            design.circle(cr, sx + fw - sh / 2, sy + sh / 2, sh / 2 - 0.5)
            cr.set_source_rgba(1, 1, 1, 1)
            cr.fill_preserve()
            cr.set_source_rgba(0, 0, 0, 0.12)
            cr.set_line_width(1)
            cr.stroke()
            self.regions.append((sx, sy - 6, sl, sh + 12, key))
            y += 64 + GAP
        # --- Şimdi Çalıyor ---
        self._tile(cr, x0, y, W - 2 * PAD, 72)
        status, title, artist, art = st["player"]
        ax, ay = x0 + 12, y + 12
        design.rrect(cr, ax, ay, 48, 48, 9)
        cr.save()
        cr.clip()
        surf = self._art_surface(art)
        if surf is not None:
            cr.set_source_surface(surf, ax, ay)
        else:
            cr.set_source_rgba(0, 0, 0, 0.08)
        cr.paint()
        cr.restore()
        if surf is None:
            self._icon(cr, "audio-x-generic-symbolic", ax + 14, ay + 14, 20, (0.3, 0.3, 0.33, 0.8))
        self._text(cr, title or t("not_playing"), ax + 60, ay + 7, 9.5, "Semi-Bold", width=150)
        self._text(cr, artist, ax + 60, ay + 24, 8, "Regular", (0, 0, 0, 0.55), width=150)
        px = W - PAD - 76
        self._icon(cr, "media-playback-pause-symbolic" if status == "Playing" else "media-playback-start-symbolic",
                   px, y + 26, 20, (0.1, 0.1, 0.12, 0.9))
        self._icon(cr, "media-skip-forward-symbolic", px + 36, y + 26, 20, (0.1, 0.1, 0.12, 0.9))
        self.regions.append((px - 6, y + 18, 32, 36, "play"))
        self.regions.append((px + 30, y + 18, 32, 36, "next"))
        return True

    def _art_surface(self, path):
        if path == self._art[0]:
            return self._art[1]
        s = None
        if path and os.path.exists(path):
            try:
                from gi.repository import GdkPixbuf
                pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(path, 48, 48, False)
                s = Gdk.cairo_surface_create_from_pixbuf(pb, 1, None)
            except Exception:
                s = None
        self._art = (path, s)
        return s

    # ---------- etkileşim ----------
    def _hit(self, x, y):
        x, y = x - self.shadow, y - self.shadow
        for rx, ry, rw, rh, key in self.regions:
            if rx <= x <= rx + rw and ry <= y <= ry + rh:
                return key, rx, rw
        return None, 0, 0

    def _slide(self, key, x, rx, rw):
        v = int(max(0, min(100, (x - self.shadow - rx - 11) / max(1, rw - 22) * 100)))
        self.st[key] = v
        (set_brightness if key == "bri" else set_volume)(v)
        self.queue_draw()

    def on_press(self, w, e):
        if e.button != 1:
            return True
        key, rx, rw = self._hit(e.x, e.y)
        if key in ("bri", "vol"):
            self.drag = (key, rx, rw)
            self._slide(key, e.x, rx, rw)
        return True

    def on_motion(self, w, e):
        if self.drag:
            self._slide(self.drag[0], e.x, self.drag[1], self.drag[2])
        return True

    def on_release(self, w, e):
        if self.drag:
            self.drag = None
            return True
        key, _, _ = self._hit(e.x, e.y)
        st = self.st
        if key == "wifi":
            on = not st["wifi"][0]
            st["wifi"] = (on, st["wifi"][1] if on else "")
            run_bg(["nmcli", "radio", "wifi", "on" if on else "off"])
        elif key == "bt":
            st["bt"] = not st["bt"]
            set_bluetooth(st["bt"])
        elif key == "dark":
            st["dark"] = not st["dark"]
            set_dark(st["dark"])
        elif key == "dnd":
            st["dnd"] = not st["dnd"]
            run_bg(["xfconf-query", "-c", "xfce4-notifyd", "-p", "/do-not-disturb", "-t", "bool", "-s",
                    "true" if st["dnd"] else "false", "--create"])
        elif key == "mirror":
            self.hide()
            run_bg(["xfce4-display-settings", "--minimal"])
        elif key == "shot":
            self.hide()
            GLib.timeout_add(300, lambda: (run_bg(["xfce4-screenshooter", "-r"]), False)[1])
        elif key in ("play", "next"):
            run_bg(["playerctl", "play-pause" if key == "play" else "next"])
            GLib.timeout_add(400, lambda: (threading.Thread(target=self._refresh, daemon=True).start(), False)[1])
        self.queue_draw()
        return True

    def on_scroll(self, w, e):
        key, rx, rw = self._hit(e.x, e.y)
        if key in ("bri", "vol"):
            up = e.direction in (Gdk.ScrollDirection.UP, Gdk.ScrollDirection.RIGHT) or \
                (e.direction == Gdk.ScrollDirection.SMOOTH and e.get_scroll_deltas()[2] < 0)
            v = max(0, min(100, self.st[key] + (6 if up else -6)))
            self.st[key] = v
            (set_brightness if key == "bri" else set_volume)(v)
            self.queue_draw()
        return True


def main():
    if not daemon.claim("controlcenter"):
        return
    cc = ControlCenter()
    daemon.on_signal(signal.SIGUSR1, cc.toggle)
    if "--show" in sys.argv:
        GLib.timeout_add(150, lambda: (cc.show_cc(), False)[1])
    Gtk.main()


if __name__ == "__main__":
    main()
