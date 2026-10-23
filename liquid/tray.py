"""Liquid — sistem tepsisi (macOS'ta menü çubuğunun sağındaki "menu bar extras").

XFCE paneli kapatıldığı için tepsi ikonu kullanan uygulamaların (Güncelleme Yöneticisi, Blueman, Claude,
Telegram…) ikonları hiçbir yerde görünmüyordu. Burada libxapp'ın XApp.StatusIconMonitor'ü
kullanılır (Mint'in MATE/Cinnamon apletleri de bunu kullanır):
  - libxapp XAppStatusIcon kullanan uygulamalar (mintUpdate, mintreport…) doğrudan görünür;
  - StatusNotifierItem/AppIndicator kullananlar (Electron, Blueman, ayatana) Mint'in
    xapp-sn-watcher köprüsüyle XApp ikonuna çevrilir — köprü burada başlatılır.
Tıklama/kaydırma uygulamaya iletilir; menüyü uygulama kendisi, verilen konumda açar.
Eski XEmbed (_NET_SYSTEM_TRAY) ikonları desteklenmez.
"""
import os
import subprocess

import gi
gi.require_version("XApp", "1.0")
from gi.repository import Gtk, Gdk, Gio, GLib, GObject, XApp  # noqa: E402

ICON = 16                                   # macOS menü çubuğu simgesi
SN_WATCHER_DESKTOP = "/etc/xdg/autostart/xapp-sn-watcher.desktop"
# çubuğun kendi simgeleri zaten gösterdiği için tepside tekrar edilmeyenler (macOS'ta tek Wi-Fi simgesi var)
SKIP = {"nm-applet", "xfce4-power-manager"}


def start_sn_watcher():
    """SNI → XApp köprüsü (xapp-sn-watcher) çalışmıyorsa başlat."""
    for pid in os.listdir("/proc"):
        if pid.isdigit():
            try:
                with open(f"/proc/{pid}/comm") as f:
                    if f.read().strip() == "xapp-sn-watcher":
                        return
            except OSError:
                pass
    try:
        exe = next(ln.split("=", 1)[1].strip() for ln in open(SN_WATCHER_DESKTOP) if ln.startswith("Exec="))
        # köprü yalnızca org.x.apps.statusicon status-notifier-enabled-desktops'taki masaüstlerinde
        # (MATE, Cinnamon) çalışıp XFCE'de hemen çıkıyor → ayarı kalıcı değiştirmeden yalnız onun ortamında
        env = dict(os.environ, XDG_CURRENT_DESKTOP="MATE")
        subprocess.Popen([exe], env=env, start_new_session=True, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
    except Exception:
        pass


class TrayIcon(Gtk.EventBox):
    def __init__(self, proxy):
        super().__init__()
        self.proxy = proxy
        self.get_style_context().add_class("tray")
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON_RELEASE_MASK |
                        Gdk.EventMask.SCROLL_MASK)
        self.image = Gtk.Image()
        self.image.set_margin_start(6)
        self.image.set_margin_end(6)
        self.add(self.image)
        proxy.props.icon_size = ICON
        flags = GObject.BindingFlags.DEFAULT | GObject.BindingFlags.SYNC_CREATE
        proxy.bind_property("tooltip-text", self, "tooltip-markup", flags)
        proxy.bind_property("visible", self, "visible", flags)
        proxy.connect("notify::icon-name", lambda *_: self._icon())
        self.connect("button-press-event", self._press)
        self.connect("button-release-event", self._release)
        self.connect("scroll-event", self._scroll)
        self._icon()

    def name(self):
        return (self.proxy.props.name or "").replace("org.x.StatusIcon.", "").lower()

    def _icon(self):
        s = self.proxy.props.icon_name or ""
        self.image.set_pixel_size(ICON)
        try:
            gic = Gio.FileIcon.new(Gio.File.new_for_path(s)) if os.path.exists(s) else Gio.ThemedIcon.new(s)
            self.image.set_from_gicon(gic, Gtk.IconSize.MENU)
        except Exception:
            self.image.set_from_icon_name("image-missing", Gtk.IconSize.MENU)

    def _origin(self):
        """Menü bu ikonun altında açılsın (çubuk ekranın üstünde → TOP)."""
        a = self.get_allocation()
        _, x, y = self.get_window().get_origin()
        return x + a.x, y + a.y + a.height

    def _press(self, w, e):
        x, y = self._origin()
        self.proxy.call_button_press(x, y, e.button, e.time, Gtk.PositionType.TOP, None, None)
        return True

    def _release(self, w, e):
        x, y = self._origin()
        self.proxy.call_button_release(x, y, e.button, e.time, Gtk.PositionType.TOP, None, None)
        return True

    def _scroll(self, w, e):
        ok, d = e.get_scroll_direction()
        if ok and d != Gdk.ScrollDirection.SMOOTH:
            delta = -1 if d in (Gdk.ScrollDirection.UP, Gdk.ScrollDirection.LEFT) else 1
            self.proxy.call_scroll_sync(delta, XApp.ScrollDirection(int(d)), e.time, None)
        return True


class Tray(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.icons = {}
        self.monitor = XApp.StatusIconMonitor()
        self.monitor.connect("icon-added", self._added)
        self.monitor.connect("icon-removed", self._removed)
        GLib.idle_add(lambda: (start_sn_watcher(), False)[1])

    @staticmethod
    def _key(proxy):
        return proxy.get_name() + proxy.get_object_path()

    def _added(self, mon, proxy):
        key = self._key(proxy)
        if key in self.icons or (proxy.props.name or "").replace("org.x.StatusIcon.", "") in SKIP:
            return
        ic = self.icons[key] = TrayIcon(proxy)
        self.pack_start(ic, False, False, 0)
        ic.show_all()
        ic.set_visible(proxy.props.visible)
        self._sort()

    def _removed(self, mon, proxy):
        ic = self.icons.pop(self._key(proxy), None)
        if ic is not None:
            self.remove(ic)
            ic.destroy()

    def _sort(self):
        for i, ic in enumerate(sorted(self.icons.values(), key=lambda c: c.name())):
            self.reorder_child(ic, i)
