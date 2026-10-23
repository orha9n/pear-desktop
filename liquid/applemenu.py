"""Liquid — Elma menüsü, macOS onay uyarıları ve "Bu Mac Hakkında" penceresi.

Menüler (bu süreçteki tüm Gtk.Menu'ler) MENU_CSS ile macOS 26 görünümünü alır:
açık, yarı saydam, köşe 12, seçimde mavi kapsül.
"""
import os
import platform
import pwd
import re
import shutil
import subprocess

from gi.repository import Gtk, Gdk, GLib

from .core import design
from .core.i18n import t

def menu_css():
    """Bu süreçteki tüm Gtk.Menu'lerin macOS 26 görünümü (açık / koyu)."""
    d = design.dark()
    bg, line, fg = ("rgba(40,40,43,0.95)", "rgba(255,255,255,0.12)", "255,255,255") if d else \
        ("rgba(246,246,248,0.94)", "rgba(0,0,0,0.10)", "0,0,0")
    return f"""
menu, .menu, .context-menu {{ background-color: {bg}; border-radius: 12px;
    border: 1px solid {line}; padding: 5px; box-shadow: none; }}
menu menuitem {{ padding: 4px 10px; min-height: 18px; border-radius: 7px; color: rgba({fg},0.88);
    font-family: "SF Pro Text", "{design.FONT}", sans-serif; font-size: 13px; }}
menu menuitem label {{ color: rgba({fg},0.88); }}
menu menuitem .accel {{ color: rgba({fg},0.38); }}
menu menuitem:hover, menu menuitem:selected {{ background-color: rgba(10,130,255,0.95); }}
menu menuitem:hover label, menu menuitem:selected label,
menu menuitem:hover .accel, menu menuitem:selected .accel {{ color: #ffffff; }}
menu menuitem:disabled label {{ color: rgba({fg},0.30); }}
menu separator {{ background-color: {line}; min-height: 1px; margin: 5px 10px; }}
menu menuitem check, menu menuitem radio {{ background: none; border: none; box-shadow: none;
    min-width: 14px; min-height: 14px; margin-right: 6px; color: inherit; }}
menu menuitem check:not(:checked), menu menuitem radio:not(:checked) {{ -gtk-icon-source: none; }}
menu menuitem check:checked {{ -gtk-icon-source: -gtk-icontheme("object-select-symbolic"); }}
menu menuitem.header label {{ font-weight: 700; }}
menu arrow {{ color: rgba({fg},0.5); }}
"""


def card_css():
    d = design.dark()
    fg, dim, btn, btn_h = ("#f5f5f7", "rgba(255,255,255,0.6)", "rgba(255,255,255,0.12)", "rgba(255,255,255,0.18)") \
        if d else ("#1d1d1f", "rgba(0,0,0,0.6)", "rgba(0,0,0,0.07)", "rgba(0,0,0,0.12)")
    return f"""
#lcard label {{ color: {fg}; font-family: "SF Pro Text", "{design.FONT}", sans-serif; }}
#lcard .title {{ font-size: 13px; font-weight: 700; }}
#lcard .detail {{ font-size: 11px; color: {dim}; }}
#lcard .big {{ font-size: 26px; font-weight: 800; }}
#lcard .sub {{ font-size: 12px; color: {dim}; }}
#lcard .key {{ font-size: 12px; color: {dim}; }}
#lcard .val {{ font-size: 12px; font-weight: 600; }}
#lcard entry {{ border-radius: 7px; }}
#lcard button {{ border-radius: 980px; border: none; box-shadow: none; background-image: none;
    padding: 6px 0; font-size: 13px; }}
#lcard button.primary {{ background-color: #0a84ff; color: white; }}
#lcard button.primary label {{ color: white; font-weight: 600; }}
#lcard button.secondary {{ background-color: {btn}; }}
#lcard button.secondary:hover {{ background-color: {btn_h}; }}
"""


_providers = {}


def install_css(kind, priority=Gtk.STYLE_PROVIDER_PRIORITY_USER + 10):
    """Bu süreçte menü ("menu") ya da kart ("card") stilini bir kez yükle; tema değişince yenile."""
    if kind in _providers:
        return
    prov = Gtk.CssProvider()
    make = menu_css if kind == "menu" else card_css
    prov.load_from_data(make().encode())
    Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), prov, priority)
    design.on_theme_change(lambda: prov.load_from_data(make().encode()))
    _providers[kind] = prov


def sh_bg(cmd):
    try:
        subprocess.Popen(cmd, start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


def _item(label, cb=None, accel=None):
    from .bar import item
    return item(label, cb, accel)


def full_name():
    try:
        p = pwd.getpwuid(os.getuid())
        return p.pw_gecos.split(",")[0].strip() or p.pw_name
    except Exception:
        return ""


def _app_store():
    for c in ("mintinstall", "gnome-software", "plasma-discover"):
        if shutil.which(c):
            return [c]
    return ["xdg-open", "https://flathub.org"]


def _recent():
    sub = Gtk.Menu()
    try:
        items = sorted(Gtk.RecentManager.get_default().get_items(), key=lambda r: r.get_modified(), reverse=True)
        items = [r for r in items if r.exists()][:10]
    except Exception:
        items = []
    if not items:
        mi = Gtk.MenuItem(label=t("a_no_recent"))
        mi.set_sensitive(False)
        sub.append(mi)
    else:
        for r in items:
            mi = Gtk.MenuItem(label=r.get_display_name())
            mi.connect("activate", lambda w, u=r.get_uri(): sh_bg(["xdg-open", u]))
            sub.append(mi)
        sub.append(Gtk.SeparatorMenuItem())
        clr = Gtk.MenuItem(label=t("a_clear"))
        clr.connect("activate", lambda *_: Gtk.RecentManager.get_default().purge_items())
        sub.append(clr)
    sub.show_all()
    return sub


def build():
    m = Gtk.Menu()

    def add(w):
        m.append(w)

    add(_item(t("a_about"), about_mac))
    add(Gtk.SeparatorMenuItem())
    add(_item(t("a_settings"), lambda: sh_bg(["xfce4-settings-manager"])))
    add(_item(t("a_appstore"), lambda: sh_bg(_app_store())))
    add(Gtk.SeparatorMenuItem())
    rec = Gtk.MenuItem(label=t("a_recent"))
    rec.set_submenu(_recent())
    add(rec)
    add(Gtk.SeparatorMenuItem())
    add(_item(t("a_forcequit"), lambda: sh_bg(["xfce4-taskmanager"]) if shutil.which("xfce4-taskmanager")
              else sh_bg(["xkill"]), "⌥⌘⎋"))
    add(Gtk.SeparatorMenuItem())
    add(_item(t("a_sleep"), lambda: sh_bg(["systemctl", "suspend"])))
    add(_item(t("a_restart"), lambda: confirm("restart")))
    add(_item(t("a_shutdown"), lambda: confirm("shutdown")))
    add(Gtk.SeparatorMenuItem())
    add(_item(t("a_lock"), lambda: sh_bg(["xflock4"]), "⌃⌘Q"))
    add(_item(t("a_logout").format(full_name()), lambda: confirm("logout"), "⇧⌘Q"))
    m.show_all()
    return m


# ----------------------------- onay uyarısı (macOS 26) -----------------------------
_ACTIONS = {
    "restart": ("q_restart", "do_restart", ["systemctl", "reboot"]),
    "shutdown": ("q_shutdown", "do_shutdown", ["systemctl", "poweroff"]),
    "logout": ("q_logout", "do_logout", ["xfce4-session-logout", "--logout"]),
}


def _card_window(width):
    w = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
    w.set_name("lcard")
    w.set_title("Liquid")
    w.set_decorated(False)
    w.set_resizable(False)
    w.set_keep_above(True)
    w.set_position(Gtk.WindowPosition.CENTER)
    w.set_default_size(width, -1)
    w.set_app_paintable(True)
    vis = w.get_screen().get_rgba_visual()
    if vis:
        w.set_visual(vis)
    install_css("card", Gtk.STYLE_PROVIDER_PRIORITY_USER + 20)
    w.connect("draw", _card_bg)
    w.connect("key-press-event", lambda wd, e: wd.destroy() if e.keyval == Gdk.KEY_Escape else None)
    return w


def _card_bg(wd, cr):
    """app_paintable pencerede GTK arka planı çizmez (CSS'teki #lcard rengi görünmüyordu, kart
    saydamdı) → köşeleri saydam bırakıp kartı kendimiz çiziyoruz; çocuklar üstüne çizilir."""
    cr.set_operator(0)                                  # CLEAR
    cr.paint()
    cr.set_operator(2)                                  # OVER
    w, h = wd.get_allocated_width(), wd.get_allocated_height()
    design.rrect(cr, 0.5, 0.5, w - 1, h - 1, 22)
    cr.set_source_rgba(*design.surface(0.97))
    cr.fill_preserve()
    cr.set_source_rgba(*design.ink(0.08 if not design.dark() else 0.14))
    cr.set_line_width(1)
    cr.stroke()
    return False


def _icon(name, size):
    try:
        return Gtk.Image.new_from_pixbuf(Gtk.IconTheme.get_default().load_icon(name, size, 0))
    except Exception:
        return Gtk.Image()


def _alert(icon, question, detail, action_label, cmd, width=260):
    """macOS uyarı kartı: simge, soru, açıklama, [Vazgeç] [eylem]. (pencere, açıklama etiketi, go)"""
    w = _card_window(width)
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    for m in ("top", "bottom", "start", "end"):
        getattr(box, f"set_margin_{m}")(18)
    w.add(box)
    box.pack_start(_icon(icon, 56), False, False, 2)
    q = Gtk.Label(label=question, wrap=True, justify=Gtk.Justification.CENTER, max_width_chars=30)
    q.get_style_context().add_class("title")
    box.pack_start(q, False, False, 0)
    d = Gtk.Label(label=detail, wrap=True, justify=Gtk.Justification.CENTER, max_width_chars=34)
    d.get_style_context().add_class("detail")
    box.pack_start(d, False, False, 0)
    row = Gtk.Box(spacing=8, homogeneous=True)
    row.set_margin_top(10)
    cancel = Gtk.Button(label=t("cancel"))
    cancel.get_style_context().add_class("secondary")
    act = Gtk.Button(label=action_label)
    act.get_style_context().add_class("primary")
    row.pack_start(cancel, True, True, 0)
    row.pack_start(act, True, True, 0)
    box.pack_start(row, False, False, 0)

    def go(*_):
        sh_bg(cmd)
        w.destroy()
    cancel.connect("clicked", lambda *_: w.destroy())
    act.connect("clicked", go)
    act.set_can_default(True)
    w.set_default(act)
    w.show_all()
    act.grab_focus()
    return w, d, go


def confirm_empty_trash():
    """Çöpü boşaltmak geri alınamaz → her zaman sor (geri sayım YOK, macOS gibi)."""
    _alert("user-trash-full", t("q_empty_trash"), t("q_no_undo"), t("empty_trash"),
           ["gio", "trash", "--empty"], width=320)


def confirm(kind, seconds=60):
    qk, bk, cmd = _ACTIONS[kind]
    w, d, go = _alert("system-shutdown" if kind != "logout" else "system-log-out", t(qk),
                      t("q_detail").format(seconds), t(bk), cmd)
    left = {"n": seconds}

    def tick():
        if not w.get_visible():
            return False
        left["n"] -= 1
        if left["n"] <= 0:
            go()
            return False
        d.set_text(t("q_detail").format(left["n"]))
        return True
    GLib.timeout_add_seconds(1, tick)


# ----------------------------- Bu Mac Hakkında -----------------------------
def _read(p):
    try:
        with open(p) as f:
            return f.read().strip()
    except Exception:
        return ""


def system_info():
    cpu = next((l.split(":", 1)[1].strip() for l in _read("/proc/cpuinfo").splitlines()
                if l.lower().startswith("model name")), platform.processor())
    cpu = re.sub(r"\((R|TM)\)", "", cpu)
    cpu = re.sub(r"\s+(CPU\s+)?@.*$|\s+\d+-Core Processor$", "", cpu).strip()
    gb = next((int(l.split()[1]) / 1048576 for l in _read("/proc/meminfo").splitlines()
               if l.startswith("MemTotal:")), 0)
    mem = next((x for x in (2, 4, 6, 8, 12, 16, 18, 24, 32, 36, 48, 64, 96, 128) if x >= gb * 0.97), round(gb))
    junk = ("to be filled", "system product", "default string", "o.e.m", "not applicable")
    ver = _read("/sys/devices/virtual/dmi/id/product_version")
    nm = _read("/sys/devices/virtual/dmi/id/product_name")
    vnd = _read("/sys/devices/virtual/dmi/id/sys_vendor")
    ok = lambda v: v and len(v) > 2 and not any(j in v.lower() for j in junk)  # noqa: E731
    model = ver if ok(ver) and not ver.replace(".", "").isdigit() else \
        " ".join(x for x in (vnd if ok(vnd) else "", nm if ok(nm) else "") if x) or "Linux PC"
    osname = next((l.split("=", 1)[1].strip('"') for l in _read("/etc/os-release").splitlines()
                   if l.startswith("PRETTY_NAME=")), "Linux")
    st = os.statvfs("/")
    return {"model": model, "cpu": cpu, "mem": f"{mem} GB", "os": osname,
            "disk": f"{st.f_blocks * st.f_frsize / 1e9:.0f} GB", "kernel": platform.release()}


def about_mac():
    info = system_info()
    w = _card_window(300)
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
    for m, v in (("top", 26), ("bottom", 22), ("start", 34), ("end", 34)):
        getattr(box, f"set_margin_{m}")(v)
    w.add(box)
    box.pack_start(_icon("computer-laptop", 128) if Gtk.IconTheme.get_default().has_icon("computer-laptop")
                   else _icon("computer", 128), False, False, 4)
    big = Gtk.Label(label=info["model"])
    big.get_style_context().add_class("big")
    box.pack_start(big, False, False, 2)
    sub = Gtk.Label(label=info["os"])
    sub.get_style_context().add_class("sub")
    box.pack_start(sub, False, False, 0)
    grid = Gtk.Grid(column_spacing=12, row_spacing=6, halign=Gtk.Align.CENTER)
    grid.set_margin_top(16)
    for i, (k, v) in enumerate(((t("a_chip"), info["cpu"]), (t("a_memory"), info["mem"]),
                                (t("a_disk"), info["disk"]), (t("a_kernel"), info["kernel"]))):
        kl = Gtk.Label(label=k, xalign=1)
        kl.get_style_context().add_class("key")
        vl = Gtk.Label(label=v, xalign=0, wrap=True, max_width_chars=30)
        vl.get_style_context().add_class("val")
        grid.attach(kl, 0, i, 1, 1)
        grid.attach(vl, 1, i, 1, 1)
    box.pack_start(grid, False, False, 0)
    btn = Gtk.Button(label="OK")
    btn.get_style_context().add_class("secondary")
    btn.set_margin_top(18)
    btn.connect("clicked", lambda *_: w.destroy())
    box.pack_start(btn, False, False, 0)
    w.show_all()


def about_app(name, info):
    d = Gtk.AboutDialog(program_name=name)
    if info is not None:
        d.set_comments(info.get_description() or "")
        ic = info.get_icon()
        if ic is not None:
            try:
                d.set_logo(Gtk.IconTheme.get_default().lookup_by_gicon(ic, 96, 0).load_icon())
            except Exception:
                pass
    d.connect("response", lambda w, r: w.destroy())
    d.show()

