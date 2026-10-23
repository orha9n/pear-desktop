"""Liquid — uygulamalar: .desktop listesi, pencere → uygulama eşleme, macOS adları.

Eşleme sırası: GIO_LAUNCHED_DESKTOP_FILE (yalnızca _PID tutarsa; değişken alt süreçlere miras
kalır) → WM_CLASS örnek/grup → StartupWMClass → çalıştırılabilir dosya adı.
"""
import os

from gi.repository import Gio

from .i18n import t

# macOS adı (dock balonu, menü çubuğundaki kalın ad). MacTahoe ikonları bu uygulamalara
# macOS ikonlarını (Finder yüzü, App Store, Ayarlar dişlisi…) zaten veriyor.
MAC_NAMES = {
    "thunar.desktop": "Finder",
    "firefox.desktop": "Firefox",
    "thunderbird.desktop": "Mail",
    "org.gnome.Rhythmbox3.desktop": t("app_music"),
    "mintinstall.desktop": "App Store",
    "xfce-settings-manager.desktop": t("app_settings"),
    "xfce4-terminal.desktop": "Terminal",
    "org.gnome.Calendar.desktop": t("app_calendar"),
    "org.gnome.Contacts.desktop": t("app_contacts"),
    "org.gnome.Photos.desktop": t("app_photos"),
    "shotwell.desktop": t("app_photos"),
    "pix.desktop": t("app_photos"),
    "xed.desktop": "TextEdit",
    "org.gnome.TextEditor.desktop": "TextEdit",
    "gnome-calculator.desktop": t("app_calculator"),
    "org.gnome.Calculator.desktop": t("app_calculator"),
    "com.microsoft.VSCode.desktop": "Code",
    "code.desktop": "Code",
    "com.anthropic.Claude.desktop": "Claude",
    "google-chrome.desktop": "Chrome",
    "xfce4-taskmanager.desktop": t("app_activity"),
}

# Dock varsayılanı: macOS sırası, sadece kurulu olanlar
DEFAULT_DOCK = ["thunar.desktop", "@apps", "firefox.desktop", "google-chrome.desktop",
                "thunderbird.desktop", "org.gnome.Calendar.desktop", "org.gnome.Rhythmbox3.desktop",
                "xed.desktop", "gnome-calculator.desktop", "org.gnome.Calculator.desktop",
                "xfce4-terminal.desktop", "com.microsoft.VSCode.desktop", "code.desktop",
                "com.anthropic.Claude.desktop", "mintinstall.desktop", "xfce-settings-manager.desktop"]

_SKIP_EXE = ("env", "sh", "bash", "flatpak", "python3", "python", "gio", "snap")


def info(did):
    """Gio.DesktopAppInfo.new kurulu olmayan uygulamada TypeError atar → None."""
    try:
        return Gio.DesktopAppInfo.new(did)
    except Exception:
        return None


def name(did, window=None):
    if did in MAC_NAMES:
        return MAC_NAMES[did]
    ai = info(did) if did else None
    if ai is not None:
        n = ai.get_name() or ""
        if n and len(n) <= 18:
            return n
    if window is not None:
        g = (window.get_class_group_name() or "").split(".")[-1]
        if g:
            return g[:1].upper() + g[1:]
    return ai.get_name() if ai is not None else "?"


def all_apps():
    """Menüde görünmesi gereken tüm uygulamalar, ada göre sıralı."""
    out = []
    for ai in Gio.AppInfo.get_all():
        if not isinstance(ai, Gio.DesktopAppInfo) or not ai.should_show():
            continue
        did = ai.get_id() or ""
        kw = " ".join([ai.get_display_name() or "", ai.get_generic_name() or "",
                       " ".join(ai.get_keywords() or []), ai.get_description() or ""]).lower()
        out.append({"did": did, "name": name(did), "info": ai, "kw": kw})
    out.sort(key=lambda a: a["name"].casefold())
    return out


class AppIndex:
    def __init__(self):
        self.idx = {}
        for ai in Gio.AppInfo.get_all():
            if not isinstance(ai, Gio.DesktopAppInfo):
                continue
            did = ai.get_id() or ""
            keys = {did[:-8].lower() if did.endswith(".desktop") else did.lower()}
            wm = ai.get_startup_wm_class()
            if wm:
                keys.add(wm.lower())
            ex = os.path.basename((ai.get_executable() or "").strip()).lower()
            if ex and ex not in _SKIP_EXE:
                keys.add(ex)
            for k in list(keys):
                keys.add(k.split(".")[-1])
            for k in keys:
                self.idx.setdefault(k, did)

    def desktop_for(self, w):
        pid = w.get_pid()
        if pid:
            try:
                with open(f"/proc/{pid}/environ", "rb") as f:
                    env = dict(e.split(b"=", 1) for e in f.read().split(b"\0") if b"=" in e)
                df = env.get(b"GIO_LAUNCHED_DESKTOP_FILE")
                if df and env.get(b"GIO_LAUNCHED_DESKTOP_FILE_PID") == str(pid).encode():
                    return os.path.basename(df.decode())
            except Exception:
                pass
        cands = [(w.get_class_instance_name() or "").lower(), (w.get_class_group_name() or "").lower()]
        if pid:
            try:
                cands.append(os.path.basename(os.readlink(f"/proc/{pid}/exe")).lower())
            except Exception:
                pass
        for c in cands:
            for k in (c, c.split(".")[-1], c.replace(" ", "-")):
                if k and k in self.idx:
                    return self.idx[k]
        return None


def launch(ai, uris=None):
    from gi.repository import Gdk
    ctx = Gdk.Display.get_default().get_app_launch_context()
    try:
        if uris:
            ai.launch_uris(uris, ctx)
        else:
            ai.launch([], ctx)
        return True
    except Exception:
        return False
