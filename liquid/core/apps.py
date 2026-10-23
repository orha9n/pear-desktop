"""Liquid — uygulamalar: .desktop listesi, pencere → uygulama eşleme, macOS adları.

Eşleme sırası: GIO_LAUNCHED_DESKTOP_FILE (yalnızca _PID tutarsa; değişken alt süreçlere miras
kalır) → WM_CLASS örnek/grup → StartupWMClass → çalıştırılabilir dosya adı.
"""
import os

from gi.repository import Gio, GLib

from .i18n import t, fold

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
# yorumlayıcılar: süreç adı uygulamayı söylemez (mintinstall = python3.12) → betik adına bak
_INTERP = ("python", "perl", "ruby", "node", "java", "gjs", "mono", "sh", "bash", "dash", "env", "electron")
_SCRIPT_EXT = (".py", ".pl", ".rb", ".js", ".sh", ".jar", ".exe")


def _interp(name):
    return any(name == i or name.startswith(i) and name[len(i):].replace(".", "").isdigit() for i in _INTERP)


def _strip_ext(name):
    for e in _SCRIPT_EXT:
        if name.endswith(e):
            return name[:-len(e)]
    return name


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
        kw = fold(" ".join([ai.get_display_name() or "", ai.get_generic_name() or "",
                            " ".join(ai.get_keywords() or []), ai.get_description() or ""]))
        nm = name(did)
        out.append({"did": did, "name": nm, "key": fold(nm), "info": ai, "kw": kw})
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
            if ex and ex not in _SKIP_EXE and not _interp(ex):
                keys.add(_strip_ext(ex))
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
        cands = [_strip_ext((w.get_class_instance_name() or "").lower()),
                 _strip_ext((w.get_class_group_name() or "").lower())]
        if pid:
            try:
                exe = os.path.basename(os.readlink(f"/proc/{pid}/exe")).lower()
                if _interp(exe):
                    # python3 /usr/lib/linuxmint/mintinstall/mintinstall.py → "mintinstall"
                    with open(f"/proc/{pid}/cmdline", "rb") as f:
                        args = [a.decode(errors="ignore") for a in f.read().split(b"\0") if a]
                    script = next((a for a in args[1:] if not a.startswith("-")), "")
                    if script:
                        cands.append(_strip_ext(os.path.basename(script).lower()))
                else:
                    cands.append(exe)
            except Exception:
                pass
        for c in cands:
            for k in (c, c.split(".")[-1], c.replace(" ", "-")):
                if k and k in self.idx:
                    return self.idx[k]
        return None


# Açılan uygulamalar Liquid bileşeninin stdout/stderr'ini (~/.cache/liquid/*.log) miras alıp
# loglara yazıyordu (Chrome SSL hataları vb.) → çıktıları /dev/null'a
_SPAWN = GLib.SpawnFlags.SEARCH_PATH | GLib.SpawnFlags.STDOUT_TO_DEV_NULL | GLib.SpawnFlags.STDERR_TO_DEV_NULL


def launch(ai, uris=None):
    from gi.repository import Gdk
    ctx = Gdk.Display.get_default().get_app_launch_context()
    try:
        ai.launch_uris_as_manager(uris or [], ctx, _SPAWN, None, None, None, None)
        return True
    except Exception:
        return False


def launch_action(ai, action):
    """Masaüstü eylemi ("Yeni Pencere" vb.). Gio.DesktopAppInfo.launch_action çıktıyı yönlendiremiyor →
    eylemin Exec satırını kendimiz çalıştırıyoruz (%f/%u gibi alan kodları atılır)."""
    try:
        kf = GLib.KeyFile()
        kf.load_from_file(ai.get_filename(), GLib.KeyFileFlags.NONE)
        _, argv = GLib.shell_parse_argv(kf.get_string(f"Desktop Action {action}", "Exec"))
        argv = [a for a in argv if not (len(a) == 2 and a.startswith("%"))]
        GLib.spawn_async(argv, flags=_SPAWN)
        return True
    except Exception:
        return False
