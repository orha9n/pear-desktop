"""Liquid — macOS 26/27 menü çubuğu (tamamen saydam).

Sol:  Elma menüsü · KALIN uygulama adı · uygulamanın kendi menüleri (global menü).
      Electron/Qt/Chromium → com.canonical.AppMenu.Registrar + dbusmenu
      GTK                  → _GTK_MENUBAR_OBJECT_PATH (GMenuModel)
      Masaüstü/pencere yok → Finder menüleri
Sağ:  pil · Wi-Fi · Spotlight · Control Center · "1 Nis Çar 09:41"
Arka plan YOK: yazılar duvar kâğıdının üstünde; renk (beyaz/siyah) duvar kâğıdının üst
şeridinin parlaklığına göre seçilir, hafif gölgeyle okunur.

Çalıştırma: python3 -m liquid.bar
"""
import os
import re
import sys
import threading

# appmenu-gtk-module bu süreçteki Gtk.MenuBar'ı global menüye taşıyıp GİZLER → kapat (Gtk'den önce)
os.environ["GTK_MODULES"] = ":".join(
    m for m in os.environ.get("GTK_MODULES", "").split(":") if m and "appmenu" not in m)
os.environ["UBUNTU_MENUPROXY"] = "0"

import cairo  # noqa: E402
import gi  # noqa: E402
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("Wnck", "3.0")
gi.require_version("Dbusmenu", "0.4")
from gi.repository import Gtk, Gdk, GLib, Gio, Wnck, Dbusmenu, GdkPixbuf  # noqa: E402

from .core import design, wallpaper, daemon, apps, screen_geometry, set_strut  # noqa: E402
from .core.i18n import t  # noqa: E402
from . import applemenu  # noqa: E402
from .glyphs import Glyph, battery_state, wifi_state  # noqa: E402

H = design.BAR_H
MODS = {"Control": "⌃", "Shift": "⇧", "Alt": "⌥", "Super": "⌘"}
KEYS = {"Delete": "⌫", "BackSpace": "⌫", "Return": "↩", "Escape": "⎋", "Tab": "⇥", "Left": "←",
        "Right": "→", "Up": "↑", "Down": "↓", "plus": "+", "minus": "−", "space": "Space"}


def sh_bg(cmd):
    try:
        import subprocess
        subprocess.Popen(cmd, start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


def strip_mnemonic(s):
    """'_Dosya' → 'Dosya' (macOS'ta alt çizgili harf yok); '__' → '_'."""
    return re.sub(r"_(.)", r"\1", (s or "").replace("__", "\0")).replace("\0", "_")


def item(label, cb=None, accel=None, sensitive=True, bold=False):
    """Sağda kısayol yazan menü öğesi (⌘Q gibi)."""
    mi = Gtk.MenuItem()
    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=28)
    lbl = Gtk.Label(xalign=0)
    lbl.set_markup(f"<b>{GLib.markup_escape_text(label)}</b>" if bold else GLib.markup_escape_text(label))
    box.pack_start(lbl, True, True, 0)
    if accel:
        ac = Gtk.Label(label=accel)
        ac.get_style_context().add_class("accel")
        box.pack_end(ac, False, False, 0)
    mi.add(box)
    mi.set_sensitive(sensitive)
    if cb:
        mi.connect("activate", lambda *_: cb())
    return mi


def sep():
    return Gtk.SeparatorMenuItem()


# ----------------------------- dbusmenu → Gtk -----------------------------
def shortcut_text(dm):
    try:
        v = dm.property_get_variant("shortcut")
        if v is None:
            return None
        keys = v.unpack()[0]
        key = keys[-1]
        key = KEYS.get(key, key.upper() if len(key) == 1 else key)
        return "".join(MODS.get(k, "") for k in keys[:-1]) + key
    except Exception:
        return None


def dbus_fill(menu, dm):
    for ch in menu.get_children():
        menu.remove(ch)
    prev_sep = True
    for c in dm.get_children():
        mi = dbus_item(c)
        if mi is None:
            continue
        is_sep = isinstance(mi, Gtk.SeparatorMenuItem)
        if is_sep and prev_sep:
            continue
        menu.append(mi)
        prev_sep = is_sep
    kids = menu.get_children()
    if kids and isinstance(kids[-1], Gtk.SeparatorMenuItem):
        menu.remove(kids[-1])
    menu.show_all()


def dbus_item(dm):
    if dm.property_exist("visible") and not dm.property_get_bool("visible"):
        return None
    if dm.property_get("type") == "separator":
        return Gtk.SeparatorMenuItem()
    label = strip_mnemonic(dm.property_get("label"))
    toggle = dm.property_get("toggle-type")
    if toggle in ("checkmark", "radio"):
        mi = Gtk.CheckMenuItem(label=label)
        mi.set_draw_as_radio(toggle == "radio")
        mi.set_active(dm.property_get_int("toggle-state") == 1)
    else:
        mi = item(label, accel=shortcut_text(dm))
    if dm.property_exist("enabled") and not dm.property_get_bool("enabled"):
        mi.set_sensitive(False)
    if dm.get_children() or dm.property_get("children-display") == "submenu":
        sub = Gtk.Menu()
        dbus_fill(sub, dm)

        def about(*_):
            try:
                dm.send_about_to_show(None, None)
            except Exception:
                pass
            dbus_fill(sub, dm)
        sub.connect("show", about)
        mi.set_submenu(sub)
    else:
        mi.connect("activate", lambda *_: dm.handle_event(
            "clicked", GLib.Variant("i", 0), Gtk.get_current_event_time()))
    return mi


def gtk_menu_props(xid):
    import subprocess
    out = subprocess.run(["xprop", "-id", str(xid), "-notype", "_GTK_UNIQUE_BUS_NAME",
                          "_GTK_MENUBAR_OBJECT_PATH", "_GTK_APPLICATION_OBJECT_PATH",
                          "_GTK_WINDOW_OBJECT_PATH", "_UNITY_OBJECT_PATH"],
                         capture_output=True, text=True).stdout
    props = {}
    for line in out.splitlines():
        m = re.match(r'(\w+) = "(.*)"', line.strip())
        if m:
            props[m.group(1)] = m.group(2)
    return props


# ----------------------------- çubuk -----------------------------
class Bar(Gtk.Window):
    def __init__(self):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.set_name("lbar")
        self.set_title("Liquid Bar")
        self.set_decorated(False)
        self.set_type_hint(Gdk.WindowTypeHint.DOCK)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_keep_above(True)
        self.stick()
        self.set_app_paintable(True)
        vis = self.get_screen().get_rgba_visual()
        if vis:
            self.set_visual(vis)
        self.mx, self.my, self.mw, self.mh = screen_geometry()
        self.set_size_request(self.mw, H)
        self.set_default_size(self.mw, H)
        self.set_resizable(False)
        self.move(self.mx, self.my)
        self.connect("draw", self._draw_bg)
        self.connect("realize", lambda *_: GLib.timeout_add(200, self._strut))

        self.css = Gtk.CssProvider()
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), self.css, Gtk.STYLE_PROVIDER_PRIORITY_USER + 10)
        self.light_text = True
        self._wp_key = None
        self._update_text_color(force=True)

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        box.set_margin_start(10)
        box.set_margin_end(12)
        self.add(box)
        self.menubar = Gtk.MenuBar()
        self.menubar.set_valign(Gtk.Align.CENTER)
        self.menubar.connect("deactivate", self._menus_closed)
        box.pack_start(self.menubar, False, False, 0)
        box.pack_start(Gtk.Box(), True, True, 0)
        self.right = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.right.set_valign(Gtk.Align.CENTER)
        box.pack_end(self.right, False, False, 0)

        # Elma menüsü (aynı süreçte → anında; diğer menülere kayarak geçilir)
        self.apple = Gtk.MenuItem()
        self.apple.get_style_context().add_class("apple")
        self.apple_glyph = Glyph("apple", 16)
        self.apple.add(self.apple_glyph)
        self.menubar.append(self.apple)
        self.apple.set_submenu(applemenu.build())
        self.appitem = Gtk.MenuItem(label="Finder")
        self.appitem.get_style_context().add_class("appname")
        self.menubar.append(self.appitem)

        self._build_right()
        self.wnck = Wnck.Screen.get_default()
        self.wnck.force_update()
        self.index = apps.AppIndex()
        self.cur = None                 # (XID, .desktop) — Wnck.Window nesnesi SAKLANMAZ (bkz. _window)
        self.dbus_client = None
        self.gmodel = None
        self._open = False
        self._dirty = False
        self.wnck.connect("active-window-changed", lambda *_: GLib.idle_add(self.on_active))
        self.wnck.connect("active-workspace-changed", lambda *_: self._update_text_color())
        self.on_active()
        GLib.timeout_add_seconds(3, self._poll)
        self._poll()
        self._tick_clock()

    # ---------- görünüm ----------
    def _update_text_color(self, force=False):
        """Duvar kâğıdının üst şeridi parlaksa siyah, değilse beyaz yazı (macOS gibi)."""
        p, st, mt = wallpaper.current()
        key = (p, st, mt)
        if key == self._wp_key and not force:
            return
        self._wp_key = key
        lum = wallpaper.luminance(self.mw, self.mh, 0, 0, self.mw, H)
        self.light_text = lum < 0.72
        fg = "rgba(255,255,255,0.96)" if self.light_text else "rgba(0,0,0,0.86)"
        shadow = "0 1px 2px rgba(0,0,0,0.30)" if self.light_text else "none"
        hov = "rgba(255,255,255,0.22)" if self.light_text else "rgba(0,0,0,0.10)"
        self.css.load_from_data(f"""
#lbar, #lbar * {{ font-family: "SF Pro Text", "{design.FONT}", sans-serif; }}
#lbar menubar {{ background: none; border: none; box-shadow: none; padding: 0; min-height: 0; }}
#lbar menubar > menuitem {{ padding: 0 9px; margin: 3px 0; min-height: {H - 6}px; border-radius: 6px;
    background: none; box-shadow: none; border: none; color: {fg}; }}
#lbar menubar > menuitem label {{ font-size: {design.BAR_FONT_PX}px; font-weight: 500; color: {fg};
    text-shadow: {shadow}; }}
#lbar menubar > menuitem.appname label {{ font-weight: 700; }}
#lbar menubar > menuitem.apple {{ padding: 0 12px 0 10px; }}
#lbar menubar > menuitem:hover {{ background-color: {hov}; }}
#lbar button {{ background: none; border: none; box-shadow: none; padding: 0 7px; margin: 3px 0;
    min-height: {H - 6}px; min-width: 0; border-radius: 6px; }}
#lbar button:hover, #lbar button:checked {{ background-color: {hov}; }}
#lbar button label {{ font-size: {design.BAR_FONT_PX}px; font-weight: 500; color: {fg}; text-shadow: {shadow}; }}
""" + applemenu.MENU_CSS)
        for g in getattr(self, "glyphs", []):
            g.light = self.light_text
            g.queue_draw()
        if hasattr(self, "apple_glyph"):
            self.apple_glyph.light = self.light_text
            self.apple_glyph.queue_draw()

    def _draw_bg(self, w, cr):
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.set_source_rgba(0, 0, 0, 0)          # tamamen saydam (macOS 26/27)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)
        return False

    def _strut(self):
        win = self.get_window()
        if win:
            sf = self.get_scale_factor()
            set_strut(win, top=(self.my + H) * sf, x0=self.mx * sf, x1=(self.mx + self.mw) * sf - 1)
        return False

    # ---------- sağ taraf ----------
    def _build_right(self):
        self.glyphs = []
        if battery_state()[0] is not None:
            self.g_batt = self._glyph_button("battery", 30, self._battery_menu)
        else:
            self.g_batt = None
        self.g_wifi = self._glyph_button("wifi", 20, self._wifi_menu)
        self._glyph_button("spotlight", 18, lambda b: daemon.signal_component("spotlight"))
        self._glyph_button("cc", 20, lambda b: daemon.signal_component("controlcenter"))
        self.clock = Gtk.Label()
        b = Gtk.Button()
        b.set_relief(Gtk.ReliefStyle.NONE)
        b.set_can_focus(False)
        b.add(self.clock)
        b.connect("clicked", lambda *_: daemon.signal_component("widgets", ))
        self.right.pack_start(b, False, False, 0)

    def _glyph_button(self, kind, width, on_click):
        g = Glyph(kind, width)
        g.light = self.light_text
        self.glyphs.append(g)
        b = Gtk.Button()
        b.set_relief(Gtk.ReliefStyle.NONE)
        b.set_can_focus(False)
        b.add(g)
        b.connect("clicked", on_click)
        self.right.pack_start(b, False, False, 0)
        return g

    def _popup(self, menu, btn):
        menu.show_all()
        menu.attach_to_widget(btn, None)
        # olay ver: olaysız popup grab alamaz ve görünmez
        menu.popup_at_widget(btn, Gdk.Gravity.SOUTH_WEST, Gdk.Gravity.NORTH_WEST, Gtk.get_current_event())

    def _battery_menu(self, btn):
        cap, status, ac = battery_state()
        m = Gtk.Menu()
        m.append(item(f"{t('battery')}      %{cap}", sensitive=False, bold=True))
        m.append(item(f"{t('power_source')}: {t('power_adapter') if ac else t('battery')}", sensitive=False))
        m.append(sep())
        m.append(item(t("battery_settings"), lambda: sh_bg(["xfce4-power-manager-settings"])))
        self._popup(m, btn)

    def _wifi_menu(self, btn):
        import subprocess
        on, ssid, _ = wifi_state()
        m = Gtk.Menu()
        head = Gtk.CheckMenuItem(label="Wi-Fi")
        head.set_active(on)
        head.get_style_context().add_class("header")
        head.connect("toggled", lambda w: sh_bg(["nmcli", "radio", "wifi", "on" if w.get_active() else "off"]))
        m.append(head)
        if on:
            m.append(sep())
            rows = subprocess.run(["env", "LC_ALL=C.UTF-8", "nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY",
                                   "dev", "wifi", "list", "--rescan", "no"],
                                  capture_output=True, text=True).stdout.splitlines()
            sh_bg(["nmcli", "dev", "wifi", "rescan"])      # bir sonraki açılışa taze liste
            seen, nets = set(), []
            for r in rows:
                parts = re.split(r"(?<!\\):", r)
                if len(parts) < 3 or not parts[0] or parts[0] in seen:
                    continue
                seen.add(parts[0])
                nets.append((parts[0].replace("\\:", ":"), int(parts[1] or 0), parts[2]))
            nets.sort(key=lambda n: (n[0] != ssid, -n[1]))
            for nm, sig, sec in nets[:10]:
                mi = Gtk.CheckMenuItem(label=nm + ("  🔒" if sec and sec != "--" else ""))
                mi.set_active(nm == ssid)
                mi.connect("activate", lambda w, n=nm: sh_bg(["nmcli", "dev", "wifi", "connect", n]))
                m.append(mi)
        m.append(sep())
        m.append(item(t("wifi_settings"), lambda: sh_bg(["nm-connection-editor"])))
        self._popup(m, btn)

    def _tick_clock(self):
        now = GLib.DateTime.new_now_local()
        self.clock.set_text(now.format("%-d %b %a %H:%M"))       # "1 Nis Çar 09:41"
        GLib.timeout_add_seconds(max(1, 60 - now.get_second()), self._tick_clock)
        return False

    def _poll(self):
        self._update_text_color()
        if self.g_batt:
            self.g_batt.state = battery_state()
            self.g_batt.queue_draw()

        def wifi_bg():
            st = wifi_state()
            GLib.idle_add(lambda: (setattr(self.g_wifi, "state", st), self.g_wifi.queue_draw(), False)[2])
        threading.Thread(target=wifi_bg, daemon=True).start()
        return True

    # ---------- aktif uygulama + global menü ----------
    def _is_ours(self, w):
        if w is None:
            return False
        if w.get_pid() == os.getpid():
            return True
        cl = (w.get_class_group_name() or "").lower() + " " + (w.get_name() or "").lower()
        return "liquid" in cl or "xfce4-notifyd" in cl

    def on_active(self):
        w = self.wnck.get_active_window()
        if self._is_ours(w) or (w is not None and w.get_window_type() in (
                Wnck.WindowType.DOCK, Wnck.WindowType.MENU, Wnck.WindowType.SPLASHSCREEN,
                Wnck.WindowType.UTILITY)):
            return False
        if w is None or w.get_window_type() == Wnck.WindowType.DESKTOP:
            key = (None, "finder")
        else:
            key = (w.get_xid(), self.index.desktop_for(w))
        if key == self.cur:
            return False
        self.cur = key
        if self._open:
            self._dirty = True
            return False
        self._rebuild()
        return False

    def _window(self):
        """Aktif uygulamanın penceresi (kapandıysa None). Wnck.Window'u özniteliğe koymak çökertir:
        pencere kapanınca libwnck nesneyi yok eder, Python'un bıraktığı geç unref → segfault."""
        xid = self.cur[0] if self.cur else None
        return Wnck.Window.get(xid) if xid else None

    def _menus_closed(self, *_):
        self._open = False
        self.apple.set_submenu(applemenu.build())     # Son Kullanılanlar güncel kalsın
        if self._dirty:
            self._dirty = False
            self._rebuild()

    def _clear(self):
        for ch in self.menubar.get_children()[2:]:
            self.menubar.remove(ch)
        for prefix in ("app", "win", "unity"):
            self.menubar.insert_action_group(prefix, None)
        self.dbus_client = None
        self.gmodel = None

    def _track(self, mi):
        sub = mi.get_submenu()
        if sub is not None:
            sub.connect("show", lambda *_: setattr(self, "_open", True))
        return mi

    def _rebuild(self):
        self._clear()
        xid, did = self.cur
        if xid is None:
            self._finder()
            return
        nm = apps.name(did, self._window())
        self.appitem.get_child().set_text(nm)
        self.appitem.set_submenu(self._app_menu(nm, did))
        props = gtk_menu_props(xid)
        if props.get("_GTK_MENUBAR_OBJECT_PATH") and props.get("_GTK_UNIQUE_BUS_NAME"):
            self._gtk_menus(props)
            return
        try:
            reg = Gio.DBusProxy.new_for_bus_sync(
                Gio.BusType.SESSION, Gio.DBusProxyFlags.NONE, None, "com.canonical.AppMenu.Registrar",
                "/com/canonical/AppMenu/Registrar", "com.canonical.AppMenu.Registrar", None)
            svc, path = reg.call_sync("GetMenuForWindow", GLib.Variant("(u)", (xid,)),
                                      Gio.DBusCallFlags.NONE, 500, None).unpack()
        except Exception:
            svc, path = "", "/"
        if svc and path != "/":
            client = Dbusmenu.Client.new(svc, path)
            self.dbus_client = client
            client.connect("layout-updated", lambda c: self._dbus_layout(c))
            GLib.timeout_add(150, lambda: (self._dbus_layout(client), False)[1])
        self.menubar.show_all()

    def _dbus_layout(self, client):
        if client is not self.dbus_client:
            return
        if self._open:
            self._dirty = True
            return
        root = client.get_root()
        for ch in self.menubar.get_children()[2:]:
            self.menubar.remove(ch)
        if root is not None:
            for c in root.get_children():
                mi = dbus_item(c)
                if mi is not None and not isinstance(mi, Gtk.SeparatorMenuItem):
                    self.menubar.append(self._track(mi))
        self.menubar.show_all()

    def _gtk_menus(self, props):
        bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        name = props["_GTK_UNIQUE_BUS_NAME"]
        for prefix, key in (("app", "_GTK_APPLICATION_OBJECT_PATH"), ("win", "_GTK_WINDOW_OBJECT_PATH"),
                            ("unity", "_UNITY_OBJECT_PATH")):
            p = props.get(key) or (props["_GTK_MENUBAR_OBJECT_PATH"] if prefix == "unity" else None)
            if p:
                self.menubar.insert_action_group(prefix, Gio.DBusActionGroup.get(bus, name, p))
        model = Gio.DBusMenuModel.get(bus, name, props["_GTK_MENUBAR_OBJECT_PATH"])
        self.gmodel = model

        def items(mm):
            for i in range(mm.get_n_items()):
                s = mm.get_item_link(i, "section")
                if s is not None:
                    yield from items(s)
                else:
                    yield mm, i

        def fill(*_):
            if model is not self.gmodel:
                return
            for ch in self.menubar.get_children()[2:]:
                self.menubar.remove(ch)
            for mm, i in items(model):
                lab = mm.get_item_attribute_value(i, "label", GLib.VariantType("s"))
                sub = mm.get_item_link(i, "submenu")
                if lab is None or sub is None:
                    continue
                mi = Gtk.MenuItem(label=strip_mnemonic(lab.get_string()))
                mi.set_submenu(Gtk.Menu.new_from_model(sub))
                self.menubar.append(self._track(mi))
            self.menubar.show_all()
        model.connect("items-changed", fill)
        fill()

    # ---------- uygulama adı menüsü ----------
    def _windows_of(self, did):
        return [w for w in self.wnck.get_windows()
                if w.get_window_type() == Wnck.WindowType.NORMAL and self.index.desktop_for(w) == did]

    def _app_menu(self, nm, did):
        m = Gtk.Menu()
        ts = Gtk.get_current_event_time
        own = lambda: self._windows_of(did) or [w for w in (self._window(),) if w]  # noqa: E731
        m.append(item(t("about_app").format(nm), lambda: applemenu.about_app(nm, apps.info(did)),
                      sensitive=bool(did)))
        m.append(sep())
        m.append(item(t("hide_app").format(nm), lambda: [w.minimize() for w in own()], "⌘H"))
        m.append(item(t("hide_others"), lambda: [w.minimize() for w in self.wnck.get_windows()
                                                 if w.get_window_type() == Wnck.WindowType.NORMAL
                                                 and w not in own()], "⌥⌘H"))
        m.append(sep())
        m.append(item(t("quit_app").format(nm), lambda: [w.close(ts()) for w in own()], "⌘Q"))
        m.show_all()
        m.connect("show", lambda *_: setattr(self, "_open", True))
        return m

    # ---------- Finder (masaüstü) ----------
    def _finder(self):
        self.appitem.get_child().set_text("Finder")
        home = os.path.expanduser("~")

        def xdg(d):
            return GLib.get_user_special_dir(d) or home

        def opn(p):
            return lambda: sh_bg(["thunar", p])

        fm = Gtk.Menu()
        fm.append(item(t("about_app").format("Finder"), sensitive=False))
        fm.append(sep())
        fm.append(item(t("settings_dots"), lambda: sh_bg(["thunar-settings"]), "⌘,"))
        fm.append(sep())
        fm.append(item(t("empty_trash") + "…", applemenu.confirm_empty_trash, "⇧⌘⌫"))
        fm.show_all()
        fm.connect("show", lambda *_: setattr(self, "_open", True))
        self.appitem.set_submenu(fm)
        D = GLib.UserDirectory
        menus = [
            (t("m_file"), [(t("new_finder"), opn(home), "⌘N"), (t("new_folder"), self._new_folder, "⇧⌘N"),
                           None, (t("find"), lambda: daemon.signal_component("spotlight"), "⌘F")]),
            (t("m_edit"), [(t("undo"), None, "⌘Z"), (t("redo"), None, "⇧⌘Z"), None, (t("cut"), None, "⌘X"),
                           (t("copy"), None, "⌘C"), (t("paste"), None, "⌘V"), (t("select_all"), None, "⌘A")]),
            (t("m_view"), [(t("as_icons"), None, "⌘1"), (t("as_list"), None, "⌘2")]),
            (t("m_go"), [(t("go_home"), opn(home), "⇧⌘H"), (t("go_desktop"), opn(xdg(D.DIRECTORY_DESKTOP)), "⇧⌘D"),
                         (t("go_documents"), opn(xdg(D.DIRECTORY_DOCUMENTS)), "⇧⌘O"),
                         (t("go_downloads"), opn(xdg(D.DIRECTORY_DOWNLOAD)), "⌥⌘L"), None,
                         (t("go_computer"), opn("/"), "⇧⌘C"),
                         (t("go_network"), lambda: sh_bg(["thunar", "network:///"]), "⇧⌘K"),
                         (t("go_apps"), lambda: daemon.signal_component("launcher"), "⇧⌘A"), None,
                         (t("trash"), lambda: sh_bg(["thunar", "trash:///"]), None)]),
            (t("m_window"), [(t("minimize_all"), self._minimize_all, "⌥⌘M")]),
            (t("m_help"), [("Liquid", lambda: sh_bg(["xdg-open", os.path.join(daemon.ROOT, "README.md")]), None)]),
        ]
        for title, entries in menus:
            mi = Gtk.MenuItem(label=title)
            sub = Gtk.Menu()
            for e in entries:
                sub.append(sep() if e is None else item(e[0], e[1], e[2], sensitive=e[1] is not None))
            mi.set_submenu(sub)
            self.menubar.append(self._track(mi))
        self.menubar.show_all()

    def _new_folder(self):
        base = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DESKTOP) or os.path.expanduser("~")
        path, n = os.path.join(base, t("untitled_folder")), 2
        while os.path.exists(path):
            path = os.path.join(base, f"{t('untitled_folder')} {n}")
            n += 1
        os.makedirs(path, exist_ok=True)

    def _minimize_all(self):
        for w in self.wnck.get_windows():
            if w.get_window_type() == Wnck.WindowType.NORMAL:
                w.minimize()


def main():
    if not daemon.claim("bar"):
        return
    b = Bar()
    b.connect("destroy", Gtk.main_quit)
    b.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
