"""Liquid — macOS 26/27 Dock (Liquid Glass).

  - Sıvı cam gövde: arkadaki duvar kâğıdı bulanık + doygun, üstte parlak iç kenar, yumuşak gölge
  - Finder · Uygulamalar · sabitli uygulamalar · çalışan (sabitlenmemiş) uygulamalar ·
    ayraç · İndirilenler · Çöp Kutusu
  - Çalışanların altında nokta, açılışta zıplama, üzerinde isim balonu
  - Sağ tık: pencereler · Aç / Yeni Pencere · Dock'ta Tut / Kaldır · Çık; Çöp: Boşalt
  - Sürükleyerek sıralama; büyütme (magnification) macOS gibi varsayılan KAPALI (ayar)
  - Ekranın altında alan ayırır (büyütülmüş pencereler dock'un üstünde biter)

Ayarlar: ~/.config/liquid/dock.ini  [dock] items, icon_size, magnify
Çalıştırma: python3 -m liquid.dock
"""
import configparser
import math
import os
import signal
import subprocess
import sys
import time

import cairo
import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("Wnck", "3.0")
gi.require_version("PangoCairo", "1.0")
from gi.repository import Gtk, Gdk, GdkPixbuf, Gio, GLib, Wnck, Pango, PangoCairo  # noqa: E402

from .core import design, wallpaper, daemon, apps, config_path, screen_geometry, set_strut, restart_on_monitor_change  # noqa: E402
from .core.i18n import t  # noqa: E402
from . import fullscreen  # noqa: E402

CONF = config_path("dock.ini")
ASSETS = os.path.join(daemon.ROOT, "assets")
TRASH = Gio.File.new_for_uri("trash:///")   # tüm disklerin çöpü (~/.local/share/Trash + /…/.Trash-UID)
FPS = 16
CALENDAR_APPS = ("org.gnome.Calendar.desktop", "gnome-calendar.desktop", "thunderbird-calendar.desktop")
ALWAYS_RUNNING = ("thunar.desktop",)          # macOS'ta Finder hep çalışır → hep nokta


def sh_bg(cmd):
    try:
        subprocess.Popen(cmd, start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


def load_conf():
    cp = configparser.ConfigParser()
    cp.optionxform = str
    cp.read(CONF)
    if not cp.has_section("dock"):
        cp.add_section("dock")
    return cp


def save_items(items):
    cp = load_conf()
    cp.set("dock", "items", ";".join(items))
    with open(CONF, "w") as f:
        cp.write(f)


class Item:
    def __init__(self, kind, key=None, info=None, name="", icon=None):
        self.kind = kind            # app | apps | win | folder | trash | sep
        self.key = key              # .desktop kimliği / klasör yolu / pencere sınıfı
        self.info, self.name, self.icon = info, name, icon
        self.windows = []           # XID'ler — Wnck.Window nesnesi SAKLANMAZ (bkz. wins)
        self.pinned = False
        self.bounce_t0 = self.bounce_until = 0.0
        self.surface = None
        self.x = self.w = 0.0

    @property
    def running(self):
        return bool(self.windows)

    @property
    def wins(self):
        """Hâlâ açık pencereler. Wnck.Window'u öznitelikte tutmak çökertir: pencere kapanınca libwnck
        nesneyi yok eder, Python'un sonradan bıraktığı unref → segfault (g_hash_table_remove)."""
        return [w for w in map(Wnck.Window.get, self.windows) if w is not None]


class Dock(Gtk.Window):
    def __init__(self):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        cp = load_conf()
        self.S = cp.getint("dock", "icon_size", fallback=design.DOCK_ICON)
        self.MAG = cp.getfloat("dock", "magnify", fallback=1.0)          # 1.0 = kapalı (macOS varsayılanı)
        keys = [k for k in cp.get("dock", "items", fallback="").split(";") if k]
        if not keys:
            keys = [k for k in apps.DEFAULT_DOCK if k == "@apps" or apps.info(k)]
            # aynı uygulamanın iki kimliği (code / com.microsoft.VSCode) → ilki
            if "com.microsoft.VSCode.desktop" in keys and "code.desktop" in keys:
                keys.remove("code.desktop")
            save_items(keys)
        self.keys = keys

        self.set_title("Liquid Dock")
        self.set_decorated(False)
        self.set_type_hint(Gdk.WindowTypeHint.DOCK)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_keep_above(True)
        self.set_accept_focus(False)
        self.stick()
        self.set_app_paintable(True)
        vis = self.get_screen().get_rgba_visual()
        if vis:
            self.set_visual(vis)
        self.add_events(Gdk.EventMask.POINTER_MOTION_MASK | Gdk.EventMask.LEAVE_NOTIFY_MASK |
                        Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON_RELEASE_MASK)
        self.connect("draw", self.on_draw)
        self.connect("motion-notify-event", self.on_motion)
        self.connect("leave-notify-event", self.on_leave)
        self.connect("button-press-event", self.on_press)
        self.connect("button-release-event", self.on_release)
        self.connect("realize", lambda *_: GLib.timeout_add(200, self._strut))

        self.mx, self.my, self.mw, self.mh = screen_geometry()
        self.M = round(self.S * max(1.0, self.MAG))
        self.BG_H = self.S + 2 * design.DOCK_PAD
        self.WIN_H = 40 + (self.M - self.S) + self.BG_H + design.DOCK_BOTTOM + 10
        self.set_size_request(self.mw, self.WIN_H)
        self.move(self.mx, self.my + self.mh - self.WIN_H)

        self.mouse_x = None
        self._last_mx = 0.0
        self.hover = 0.0
        self.hover_item = None
        self.press = None
        self.dragging = False
        self.anim_id = None
        self._bubble_at = 0.0
        self.backdrop = None
        self._wp_key = None
        self.items = []
        self.theme = Gtk.IconTheme.get_default()
        self.theme.connect("changed", lambda *_: [setattr(i, "surface", None) for i in self.items])

        # .desktop'u olmayan pencerelerin ikonu Wnck'den gelir; varsayılan 32 px büyütülünce bulanıktı
        Wnck.set_default_icon_size(self.M * self.get_scale_factor())
        self.wnck = Wnck.Screen.get_default()
        self.wnck.force_update()
        self.index = apps.AppIndex()
        self.wnck.connect("window-opened", lambda *_: GLib.idle_add(self.refresh))
        self.wnck.connect("window-closed", lambda *_: GLib.idle_add(self.refresh))
        self.wnck.connect("active-window-changed", lambda *_: self.queue_draw())
        self.wnck.connect("active-workspace-changed", lambda *_: self._check_wallpaper())
        self.refresh()
        GLib.timeout_add_seconds(2, self._poll)
        # tam ekranda dock gizli; fare en alta gelince belirir (macOS)
        self.fs_hidden = False
        self._fs_poll_id = None
        self._edge_since = None
        self.fs = fullscreen.Watcher(self.wnck, self._fs_changed)

    # ---------- düzen ----------
    def _strut(self):
        win = self.get_window()
        if win:
            sf = self.get_scale_factor()
            set_strut(win, bottom=(self.BG_H + design.DOCK_BOTTOM) * sf,
                      x0=self.mx * sf, x1=(self.mx + self.mw) * sf - 1)
            self._input()
        return False

    def refresh(self):
        old = {(i.kind, i.key): i for i in self.items}
        running, extra = {}, {}
        for w in self.wnck.get_windows():
            if w.get_window_type() != Wnck.WindowType.NORMAL or w.is_skip_tasklist():
                continue
            did = self.index.desktop_for(w)
            if did:
                running.setdefault(did, []).append(w)
            else:
                extra.setdefault(w.get_class_group_name() or w.get_name() or "?", []).append(w)

        items = []
        for key in self.keys:
            if key == "@apps":
                it = old.get(("apps", None)) or Item("apps", None, None, t("app_apps"),
                                                     os.path.join(ASSETS, "apps.svg"))
                items.append(it)
                continue
            it = old.get(("app", key))
            if it is None:
                ai = apps.info(key)
                if ai is None:
                    continue
                it = Item("app", key, ai, apps.name(key), ai.get_icon())
            it.pinned = True
            it.windows = [w.get_xid() for w in running.pop(key, [])]
            items.append(it)
        for key, wins in running.items():
            it = old.get(("app", key))
            if it is None:
                ai = apps.info(key)
                if ai is None:
                    continue
                it = Item("app", key, ai, apps.name(key), ai.get_icon())
            it.pinned = False
            it.windows = [w.get_xid() for w in wins]
            items.append(it)
        for key, wins in extra.items():
            it = old.get(("win", key)) or Item("win", key, None, key, wins[0].get_icon())
            it.windows = [w.get_xid() for w in wins]
            items.append(it)
        items.append(old.get(("sep", None)) or Item("sep"))
        dl = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DOWNLOAD) or os.path.expanduser("~/Downloads")
        items.append(old.get(("folder", dl)) or Item("folder", dl, None, t("downloads"), "folder-download"))
        items.append(old.get(("trash", None)) or Item("trash", None, None, t("trash"), "user-trash"))
        self.items = items
        self._trash_full = None
        self._poll_trash()
        self._input()
        self.queue_draw()
        return False

    def _calendar_icon(self, size):
        """macOS takvim ikonu: beyaz kare, üstte kırmızı kısa gün adı, ortada büyük gün numarası."""
        surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
        cr = cairo.Context(surf)
        m = size * 0.08
        design.rrect(cr, m, m, size - 2 * m, size - 2 * m, size * 0.22)
        cr.set_source_rgba(1, 1, 1, 1)
        cr.fill_preserve()
        cr.set_source_rgba(0, 0, 0, 0.10)
        cr.set_line_width(max(1, size / 96))
        cr.stroke()
        now = GLib.DateTime.new_now_local()
        for txt, y, fsz, col, weight in ((now.format("%a"), 0.17, 0.15, (*design.RED, 1), "Semi-Bold"),
                                         (str(now.get_day_of_month()), 0.30, 0.42, (0.12, 0.12, 0.13, 1), "Light")):
            lay = PangoCairo.create_layout(cr)
            lay.set_font_description(Pango.FontDescription(f"{design.FONT} {weight} {int(size * fsz * 0.75)}"))
            lay.set_text(txt, -1)
            tw, th = lay.get_pixel_size()
            cr.move_to((size - tw) / 2, size * y)
            cr.set_source_rgba(*col)
            PangoCairo.show_layout(cr, lay)
        return surf

    def _icon(self, it):
        if it.kind == "app" and it.key in CALENDAR_APPS:
            day = GLib.DateTime.new_now_local().get_day_of_month()
            if getattr(it, "_cal_day", None) != day or it.surface is None:
                it._cal_day = day
                it.surface = self._calendar_icon(self.M * self.get_scale_factor())
            return it.surface
        if it.surface is not None:
            return it.surface or None
        size = self.M * self.get_scale_factor()
        pb = None
        try:
            ic = it.icon
            if isinstance(ic, GdkPixbuf.Pixbuf):
                pb = ic
            elif isinstance(ic, str) and ic.startswith("/"):
                pb = GdkPixbuf.Pixbuf.new_from_file_at_size(ic, size, size)
            else:
                gic = Gio.ThemedIcon.new(ic) if isinstance(ic, str) else ic
                info = self.theme.lookup_by_gicon(gic, size, Gtk.IconLookupFlags.FORCE_SIZE) if gic else None
                info = info or self.theme.lookup_icon("application-x-executable", size,
                                                      Gtk.IconLookupFlags.FORCE_SIZE)
                pb = info.load_icon() if info else None
        except Exception:
            pb = None
        if pb is None:
            it.surface = False
            return None
        if pb.get_width() != size:
            pb = pb.scale_simple(size, size, GdkPixbuf.InterpType.HYPER)
        it.surface = Gdk.cairo_surface_create_from_pixbuf(pb, 1, None)
        return it.surface

    def _scale(self, cx):
        if self.MAG <= 1.0 or (self.mouse_x is None and self.hover <= 0.001):
            return 1.0
        mx = self.mouse_x if self.mouse_x is not None else self._last_mx
        R = self.S * 3.0
        d = abs(cx - mx)
        return 1.0 if d >= R else 1.0 + (self.MAG - 1.0) * self.hover * math.cos(d / R * math.pi / 2) ** 1.6

    def _layout(self):
        S, G, P = self.S, design.DOCK_GAP, design.DOCK_PAD
        base, x = [], 0.0
        for it in self.items:
            w = design.DOCK_SEP_W if it.kind == "sep" else S
            base.append((x, w))
            x += w + G
        total = x - G + 2 * P
        x0 = (self.mw - total) / 2 + P
        widths = [design.DOCK_SEP_W if it.kind == "sep" else S * self._scale(x0 + bx + bw / 2)
                  for it, (bx, bw) in zip(self.items, base)]
        total2 = sum(widths) + G * (len(widths) - 1) + 2 * P
        x = (self.mw - total2) / 2 + P
        for it, w in zip(self.items, widths):
            it.x, it.w = x, w
            x += w + G
        self.bg_x, self.bg_w = (self.mw - total2) / 2, total2
        self.bg_y = self.WIN_H - design.DOCK_BOTTOM - self.BG_H

    def _fs_changed(self, fs):
        if fs and self._fs_poll_id is None:
            self._fs_poll_id = GLib.timeout_add(fullscreen.POLL_MS, self._fs_poll)
        elif not fs and self._fs_poll_id is not None:
            GLib.source_remove(self._fs_poll_id)
            self._fs_poll_id = None
        self._edge_since = None
        self._fs_hide(fs)

    def _fs_hide(self, hidden):
        self.fs_hidden = hidden
        fullscreen.set_hidden(self, hidden)
        if not hidden:
            self._input()

    def _fs_poll(self):
        x, y = fullscreen.pointer()
        bottom = self.my + self.mh
        inside = self.mx <= x < self.mx + self.mw
        if self.fs_hidden:
            if inside and y >= bottom - 2:
                now = time.monotonic()
                self._edge_since = self._edge_since or now
                if now - self._edge_since >= 0.25:
                    self._edge_since = None
                    self._fs_hide(False)
                    if self.get_window() is not None:
                        self.get_window().raise_()
            else:
                self._edge_since = None
        elif self.press is None and (not inside or y < bottom - self.WIN_H):
            self._fs_hide(True)
        return True

    def _input(self):
        if not self.get_window():
            return
        if self.fs_hidden:
            self.input_shape_combine_region(cairo.Region())
            return
        self._layout()
        grow = self.mouse_x is not None or self.hover > 0
        top = self.bg_y - (self.M - self.S) - (2 if grow else 0)
        pad = 60 if grow else 0
        r = cairo.RectangleInt(int(self.bg_x) - pad, int(top), int(self.bg_w) + 2 * pad, int(self.WIN_H - top))
        self.input_shape_combine_region(cairo.Region(r))

    # ---------- arka plan ----------
    def _check_wallpaper(self):
        p, st, mt = wallpaper.current()
        key = (p, st, mt)
        if key != self._wp_key:
            self._wp_key = key
            y = self.mh - self.WIN_H
            self.backdrop = wallpaper.region(self.mw, self.mh, 0, y, self.mw, self.WIN_H, blur=26)
            self.queue_draw()

    def _poll(self):
        self._check_wallpaper()
        self._poll_trash()
        # takvim ikonu gece yarısı yeni güne geçsin (eskiden ancak dock yeniden çizilince değişiyordu)
        day = GLib.DateTime.new_now_local().get_day_of_month()
        if day != getattr(self, "_day", day):
            self.queue_draw()
        self._day = day
        return True

    def _poll_trash(self):
        try:
            full = TRASH.query_info("trash::item-count", Gio.FileQueryInfoFlags.NONE, None) \
                .get_attribute_uint32("trash::item-count") > 0
        except Exception:
            full = False
        if full != getattr(self, "_trash_full", None):
            self._trash_full = full
            for it in self.items:
                if it.kind == "trash":
                    it.icon = "user-trash-full" if full else "user-trash"
                    it.surface = None
            self.queue_draw()

    # ---------- çizim ----------
    def on_draw(self, w, cr):
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.set_source_rgba(0, 0, 0, 0)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)
        if self._wp_key is None:
            self._check_wallpaper()
        self._layout()
        design.liquid_glass(cr, self.bg_x, self.bg_y, self.bg_w, self.BG_H, design.DOCK_RADIUS,
                            backdrop=self.backdrop, backdrop_xy=(0, 0),
                            tint=design.glass_tint(0.20), dark=design.dark())
        now = time.monotonic()
        anim = False
        sf = self.get_scale_factor()
        by, bh = self.bg_y, self.BG_H
        for it in self.items:
            if it.kind == "sep":
                cx = it.x + it.w / 2
                cr.rectangle(cx - 0.5, by + 12, 1, bh - 24)
                cr.set_source_rgba(1, 1, 1, 0.55)
                cr.fill()
                cr.rectangle(cx + 0.5, by + 12, 1, bh - 24)
                cr.set_source_rgba(0, 0, 0, 0.10)
                cr.fill()
                continue
            surf = self._icon(it)
            size = it.w
            iy = by + bh - design.DOCK_PAD - size
            if it.bounce_until > now:
                anim = True
                iy -= abs(math.sin((now - it.bounce_t0) / 0.62 * math.pi)) * self.S * 0.42
            elif it.bounce_until and it.running:
                it.bounce_until = 0
            if surf is not None:
                cr.save()
                cr.translate(it.x, iy)
                k = size / (self.M * sf)
                cr.scale(k, k)
                cr.set_source_surface(surf, 0, 0)
                cr.get_source().set_filter(cairo.FILTER_GOOD)
                dim = (self.press is not None and self.press[0] is it and not self.dragging)
                cr.paint_with_alpha(0.55 if (self.dragging and self.press and self.press[0] is it) else 1.0)
                cr.restore()
                if dim:                                           # basılıyken karart (macOS)
                    design.rrect(cr, it.x + size * 0.06, iy + size * 0.06, size * 0.88, size * 0.88, size * 0.22)
                    cr.set_source_rgba(0, 0, 0, 0.30)
                    cr.fill()
            if it.running or it.key in ALWAYS_RUNNING:
                design.circle(cr, it.x + size / 2, by + bh - 3.2, 2.1)
                cr.set_source_rgba(*design.ink(0.55))
                cr.fill()
        hi = self.hover_item
        if hi is not None and hi.kind != "sep" and not self.dragging and now - self._bubble_at > 0.18:
            self._bubble(cr, hi, by)
        if anim:
            self._anim()
        return True

    def _bubble(self, cr, it, by):
        """macOS 26 isim balonu: koyu cam kapsül, beyaz yazı."""
        layout = PangoCairo.create_layout(cr)
        layout.set_font_description(Pango.FontDescription(f"{design.FONT} Medium 10"))
        layout.set_text(it.name, -1)
        tw, th = layout.get_pixel_size()
        bw, bh = tw + 24, th + 12
        cx = it.x + it.w / 2
        x = max(4, min(self.mw - bw - 4, cx - bw / 2))
        y = max(2, by - bh - 12 - (it.w - self.S))
        design.soft_shadow(cr, x, y, bw, bh, bh / 2, strength=0.18, spread=8, dy=2)
        design.rrect(cr, x, y, bw, bh, bh / 2)
        cr.set_source_rgba(*design.surface(0.92))
        cr.fill_preserve()
        cr.set_source_rgba(0, 0, 0, 0.10)
        cr.set_line_width(1)
        cr.stroke()
        cr.move_to(x + 12, y + 6)
        cr.set_source_rgba(*design.ink(0.92))
        PangoCairo.show_layout(cr, layout)

    def _anim(self):
        if self.anim_id is None:
            self.anim_id = GLib.timeout_add(FPS, self._tick)

    def _tick(self):
        target = 1.0 if self.mouse_x is not None else 0.0
        step = FPS / 110.0
        if abs(self.hover - target) > 0.001:
            self.hover = min(target, self.hover + step) if target > self.hover else max(target, self.hover - step)
        bouncing = any(i.bounce_until > time.monotonic() for i in self.items)
        self.queue_draw()
        if abs(self.hover - target) <= 0.001 and not bouncing:
            self.hover = target
            self.anim_id = None
            if target == 0.0:
                self._input()
            return False
        return True

    # ---------- fare ----------
    def _item_at(self, x, y):
        if y < self.bg_y - (self.M - self.S) - 4:
            return None
        for it in self.items:
            if it.x - design.DOCK_GAP / 2 <= x <= it.x + it.w + design.DOCK_GAP / 2:
                return it
        return None

    def on_motion(self, w, e):
        inside = self.bg_x - 10 <= e.x <= self.bg_x + self.bg_w + 10 and e.y >= self.bg_y - (self.M - self.S) - 6
        if not inside and self.press is None:
            return self.on_leave(w, e)
        if self.mouse_x is None:
            self.mouse_x = e.x
            self._input()
        self.mouse_x = self._last_mx = e.x
        hi = self._item_at(e.x, e.y)
        if hi is not self.hover_item:
            self.hover_item = hi
            self._bubble_at = time.monotonic()
            GLib.timeout_add(200, lambda: (self.queue_draw(), False)[1])
        if self.press and not self.dragging and abs(e.x - self.press[1]) > 8 and self.press[0].pinned:
            self.dragging = True
        if self.dragging:
            self._drag_to(e.x)
        self._anim()
        return True

    def on_leave(self, w, e):
        if e.type == Gdk.EventType.LEAVE_NOTIFY and e.detail == Gdk.NotifyType.INFERIOR:
            return False
        if self.mouse_x is not None:
            self._last_mx = self.mouse_x
        self.mouse_x = None
        self.hover_item = None
        self._anim()
        return False

    def _drag_to(self, x):
        it = self.press[0]
        for other in self.items:
            if other is not it and (other.pinned or other.kind == "apps") and other.x <= x <= other.x + other.w:
                a, b = self.items.index(it), self.items.index(other)
                self.items[a], self.items[b] = self.items[b], self.items[a]
                self.keys = ["@apps" if i.kind == "apps" else i.key for i in self.items
                             if i.pinned or i.kind == "apps"]
                break

    def on_press(self, w, e):
        it = self._item_at(e.x, e.y)
        if it is None or it.kind == "sep":
            return False
        if e.button == 3:
            self._menu(it, e)
        elif e.button == 1:
            self.press = (it, e.x)
            self.queue_draw()
        return True

    def on_release(self, w, e):
        if e.button != 1 or self.press is None:
            return False
        it, was_drag = self.press[0], self.dragging
        self.press, self.dragging = None, False
        if was_drag:
            save_items(self.keys)
        elif self._item_at(e.x, e.y) is it:
            self.activate(it, e.time)
        self.queue_draw()
        return True

    # ---------- eylemler ----------
    def activate(self, it, ts):
        if it.kind == "apps":
            daemon.signal_component("launcher")
        elif it.kind == "trash":
            sh_bg(["thunar", "trash:///"])
        elif it.kind == "folder":
            sh_bg(["thunar", it.key])
        elif it.running:
            wins = it.wins
            if not wins:
                return
            # macOS: tıklamak uygulamayı öne getirir, KÜÇÜLTMEZ. Görünen penceresi yoksa küçültülmüş
            # son pencereyi geri açar; varsa en son kullanılanı (etkinse onu) öne alır.
            active = self.wnck.get_active_window()
            mine = active is not None and active.get_xid() in it.windows
            shown = [wd for wd in wins if not wd.is_minimized()]
            if not shown:
                wins[-1].unminimize(ts)
                wins[-1].activate(ts)
            else:
                (active if mine else shown[-1]).activate(ts)
        elif it.info is not None:
            self.launch(it)

    def launch(self, it):
        if apps.launch(it.info):
            it.bounce_t0 = time.monotonic()
            it.bounce_until = it.bounce_t0 + 0.62 * 4
            self._anim()

    def _menu(self, it, e):
        from .applemenu import confirm_empty_trash
        m = Gtk.Menu()

        def add(label, cb, sensitive=True):
            mi = Gtk.MenuItem(label=label)
            mi.set_sensitive(sensitive)
            mi.connect("activate", lambda *_: cb())
            m.append(mi)
        ts = Gtk.get_current_event_time
        if it.kind == "trash":
            add(t("open"), lambda: sh_bg(["thunar", "trash:///"]))
            m.append(Gtk.SeparatorMenuItem())
            add(t("empty_trash") + "…", confirm_empty_trash, bool(self._trash_full))
        elif it.kind in ("folder", "apps"):
            add(t("open"), lambda: self.activate(it, ts()))
        else:
            for xid in it.windows:
                wd = Wnck.Window.get(xid)
                if wd is not None:
                    add((wd.get_name() or it.name)[:60], lambda x=xid: self._win_do(x, "activate"))
            if it.windows:
                m.append(Gtk.SeparatorMenuItem())
            if it.info is not None:
                add(t("new_window") if it.running else t("open"), lambda: self.launch(it))
                for a in it.info.list_actions()[:6]:
                    add(it.info.get_action_name(a), lambda a=a: apps.launch_action(it.info, a))
                m.append(Gtk.SeparatorMenuItem())
                add(t("remove_from_dock") if it.pinned else t("keep_in_dock"), lambda: self._pin(it, not it.pinned))
            elif it.kind == "win":
                add(t("keep_in_dock"), lambda: self._pin_win(it))
            if it.windows:
                m.append(Gtk.SeparatorMenuItem())
                add(t("quit"), lambda: [wd.close(ts()) for wd in it.wins])
        m.show_all()
        m.attach_to_widget(self, None)
        m.popup_at_pointer(e)

    def _win_do(self, xid, what):
        wd = Wnck.Window.get(xid)
        if wd is not None:
            getattr(wd, what)(Gtk.get_current_event_time())

    def _pin_win(self, it):
        """.desktop'u olmayan uygulamayı Dock'ta tut: komut satırından bir .desktop üretilir
        (~/.local/share/applications/liquid-*.desktop), sonra normal sabitli uygulama olur."""
        wins = it.wins
        did = apps.make_desktop(wins[0]) if wins else None
        if did is None:
            return
        self.keys.append(did)
        save_items(self.keys)

        def again(tries=[6]):                    # GIO yeni .desktop dosyasını biraz sonra görür
            if apps.info(did) is None and tries[0] > 0:
                tries[0] -= 1
                return True
            self.index = apps.AppIndex()
            self.refresh()
            return False
        GLib.timeout_add(300, again)

    def _pin(self, it, on):
        if on and it.key not in self.keys:
            last = max([i for i, k in enumerate(self.keys)] + [-1])
            self.keys.insert(last + 1, it.key)
        elif not on and it.key in self.keys:
            self.keys.remove(it.key)
        save_items(self.keys)
        self.refresh()


def main():
    if not daemon.claim("dock"):
        return
    restart_on_monitor_change()
    from .applemenu import install_css
    install_css("menu")
    d = Dock()
    design.on_theme_change(d.queue_draw)
    daemon.on_signal(signal.SIGUSR2, d.fs.check)          # bar: macOS tam ekranı değişti
    d.connect("destroy", Gtk.main_quit)
    d.show_all()
    GLib.timeout_add(300, lambda: (d._input(), False)[1])
    Gtk.main()


if __name__ == "__main__":
    main()
