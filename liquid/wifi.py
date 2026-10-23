"""Liquid — Wi-Fi: ağ listesi, kayıtlı ağa bağlanma, şifre kartı (macOS'taki "… için şifre girin").

Eski menü: liste menü açılırken ana iş parçacığında nmcli ile alınıyordu (çubuk donabiliyordu) ve
şifreli, kayıtlı olmayan ağa tıklamak `nmcli dev wifi connect` ile şifre sormadan sessizce başarısız
oluyordu. Şifre NetworkManager'a D-Bus (AddAndActivateConnection) ile verilir: komut satırına
(/proc/*/cmdline herkesçe okunur) hiç yazılmaz.
"""
import re
import subprocess
import threading

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, Gdk, GLib, Gio  # noqa: E402

from .core.i18n import t

NM = "org.freedesktop.NetworkManager"


def _run(cmd, timeout=4):
    try:
        return subprocess.run(["env", "LC_ALL=C.UTF-8", *cmd], capture_output=True, text=True,
                              timeout=timeout).stdout
    except Exception:
        return ""


def scan():
    """(radyo açık, bağlı SSID, sinyal, [(ssid, sinyal, güvenlik)]) — tarama tetiklemez (--rescan no)."""
    on = _run(["nmcli", "radio", "wifi"]).strip().lower().startswith("en")
    ssid, sig, seen, nets = "", 0, set(), []
    for line in _run(["nmcli", "-t", "-f", "ACTIVE,SSID,SIGNAL,SECURITY", "dev", "wifi", "list",
                      "--rescan", "no"]).splitlines():
        parts = re.split(r"(?<!\\):", line)
        if len(parts) < 4 or not parts[1]:
            continue
        name = parts[1].replace("\\:", ":")
        s = int(parts[2]) if parts[2].isdigit() else 0
        if parts[0] == "yes":
            ssid, sig = name, s
        if name not in seen:
            seen.add(name)
            nets.append((name, s, parts[3] if parts[3] != "--" else ""))
    nets.sort(key=lambda n: (n[0] != ssid, -n[1]))
    return on, ssid, sig, nets


def _notify(msg):
    subprocess.Popen(["notify-send", "-i", "network-wireless", "Wi-Fi", msg],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)


def _saved(ssid):
    for line in _run(["nmcli", "-t", "-f", "NAME,TYPE", "connection", "show"]).splitlines():
        name, _, typ = line.rpartition(":")
        if typ == "802-11-wireless" and name.replace("\\:", ":") == ssid:
            return True
    return False


def _wifi_device():
    for line in _run(["nmcli", "-t", "-f", "DEVICE,TYPE", "device"]).splitlines():
        dev, _, typ = line.partition(":")
        if typ == "wifi":
            return dev
    return None


def connect(ssid, security):
    """Ağa tıklanınca: kayıtlıysa bağlan; açık ağsa bağlan; kişisel şifreliyse şifre kartı;
    kurumsal (802.1X) / WEP ise ağ ayarlarını aç. Ağ işleri arka planda yapılır."""
    def work():
        if _saved(ssid):
            ok = "successfully" in _run(["nmcli", "connection", "up", "id", ssid], timeout=40)
        elif not security:
            ok = "successfully" in _run(["nmcli", "dev", "wifi", "connect", ssid], timeout=40)
        elif "802.1X" in security or "WEP" in security:
            GLib.idle_add(lambda: (subprocess.Popen(["nm-connection-editor"], start_new_session=True), False)[1])
            return
        else:
            GLib.idle_add(password_card, ssid, security)
            return
        if not ok:
            GLib.idle_add(_notify, t("wifi_failed").format(ssid))
    threading.Thread(target=work, daemon=True).start()


def _add_and_activate(ssid, security, psk):
    dev = _wifi_device()
    if dev is None:
        _notify(t("wifi_failed").format(ssid))
        return
    bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
    try:
        dev_path = bus.call_sync(NM, "/org/freedesktop/NetworkManager", NM, "GetDeviceByIpIface",
                                 GLib.Variant("(s)", (dev,)), None, Gio.DBusCallFlags.NONE, 3000, None)[0]
    except Exception:
        _notify(t("wifi_failed").format(ssid))
        return
    mgmt = "sae" if "WPA3" in security and "WPA2" not in security and "WPA1" not in security else "wpa-psk"
    settings = GLib.Variant("a{sa{sv}}", {
        "connection": {"id": GLib.Variant("s", ssid), "type": GLib.Variant("s", "802-11-wireless")},
        "802-11-wireless": {"ssid": GLib.Variant("ay", ssid.encode()),
                            "mode": GLib.Variant("s", "infrastructure")},
        "802-11-wireless-security": {"key-mgmt": GLib.Variant("s", mgmt), "psk": GLib.Variant("s", psk)},
    })

    def done(src, res):
        try:
            src.call_finish(res)
        except Exception:
            _notify(t("wifi_failed").format(ssid))
    bus.call(NM, "/org/freedesktop/NetworkManager", NM, "AddAndActivateConnection",
             GLib.Variant.new_tuple(settings, GLib.Variant("o", dev_path), GLib.Variant("o", "/")),
             None, Gio.DBusCallFlags.NONE,
             30000, None, done)


def password_card(ssid, security):
    """macOS: "“ağ” Wi-Fi ağı için şifre gerekiyor" kartı."""
    from .applemenu import _card_window, _icon
    w = _card_window(300)
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    for m in ("top", "bottom", "start", "end"):
        getattr(box, f"set_margin_{m}")(18)
    w.add(box)
    box.pack_start(_icon("network-wireless", 48), False, False, 2)
    q = Gtk.Label(label=t("wifi_password").format(ssid), wrap=True, justify=Gtk.Justification.CENTER,
                  max_width_chars=32)
    q.get_style_context().add_class("title")
    box.pack_start(q, False, False, 0)
    entry = Gtk.Entry(visibility=False, placeholder_text=t("password"))
    entry.set_activates_default(True)
    box.pack_start(entry, False, False, 6)
    row = Gtk.Box(spacing=8, homogeneous=True)
    cancel = Gtk.Button(label=t("cancel"))
    cancel.get_style_context().add_class("secondary")
    join = Gtk.Button(label=t("join"))
    join.get_style_context().add_class("primary")
    join.set_sensitive(False)
    row.pack_start(cancel, True, True, 0)
    row.pack_start(join, True, True, 0)
    box.pack_start(row, False, False, 0)
    entry.connect("changed", lambda e: join.set_sensitive(len(e.get_text()) >= 8))   # WPA: en az 8

    def go(*_):
        psk = entry.get_text()
        if len(psk) < 8:
            return
        w.destroy()
        _add_and_activate(ssid, security, psk)
    cancel.connect("clicked", lambda *_: w.destroy())
    join.connect("clicked", go)
    join.set_can_default(True)
    w.set_default(join)
    w.show_all()
    w.present()
    GLib.timeout_add(60, lambda: (w.get_window() and w.get_window().focus(Gdk.CURRENT_TIME),
                                  entry.grab_focus(), False)[2])
    return False
