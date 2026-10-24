"""Liquid — komut satırı: kısayollar ve betikler bileşenleri buradan açar/kapatır.

  python3 -m liquid.ctl toggle spotlight|launcher|controlcenter
  python3 -m liquid.ctl start|stop            (oturum bekçisi + tüm bileşenler)
  python3 -m liquid.ctl status
  python3 -m liquid.ctl fullscreen            (etkin pencere tam ekran aç/kapat — ⌃⌘F)
  python3 -m liquid.ctl app quit|hide|hide-others|minimize   (⌘Q ⌘H ⌥⌘H ⌘M)
  python3 -m liquid.ctl compositor [picom|xfwm]   (gerçek cam: picom; geri: xfwm)
  python3 -m liquid.ctl widgets edit           (Widget'ları Düzenle — masaüstü sağ tık menüsü)
"""
import os
import signal
import subprocess
import sys

from .core import daemon
from .session import COMPONENTS


def app_action(what):
    """macOS uygulama kısayolları: etkin UYGULAMANIN (yalnız pencerenin değil) tüm pencereleri."""
    import gi
    gi.require_version("Gtk", "3.0")
    gi.require_version("Wnck", "3.0")
    from gi.repository import Gtk, Wnck
    from .core import apps
    Gtk.init([])
    scr = Wnck.Screen.get_default()
    scr.force_update()
    act = scr.get_active_window()
    if act is None or act.get_window_type() != Wnck.WindowType.NORMAL:
        return                                    # masaüstü / Liquid'in kendi pencereleri
    normal = [w for w in scr.get_windows() if w.get_window_type() == Wnck.WindowType.NORMAL]
    idx = apps.AppIndex()
    did = idx.desktop_for(act)
    own = [w for w in normal if did and idx.desktop_for(w) == did] or [act]
    if what == "quit":
        for w in own:
            w.close(0)
    elif what == "hide":
        for w in own:
            w.minimize()
    elif what == "hide-others":
        for w in normal:
            if w not in own:
                w.minimize()
    elif what == "minimize":
        act.minimize()


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "toggle" and len(sys.argv) > 2:
        daemon.signal_component(sys.argv[2])
    elif cmd == "start":
        daemon.start("session")
    elif cmd == "stop":
        for name in ("session",) + COMPONENTS:
            pid = daemon.running(name)
            if pid:
                os.kill(pid, signal.SIGTERM)
    elif cmd == "fullscreen":
        pid = daemon.running("bar")                     # bar: macOS tam ekranı (çubuğun altında)
        if pid:
            os.kill(pid, signal.SIGUSR2)
        else:
            subprocess.run(["wmctrl", "-r", ":ACTIVE:", "-b", "toggle,fullscreen"])
    elif cmd == "app" and len(sys.argv) > 2:
        app_action(sys.argv[2])
    elif cmd == "widgets" and sys.argv[2:] == ["edit"]:
        daemon.signal_component("widgets", signal.SIGUSR2)
    elif cmd == "compositor":
        from . import compositor
        compositor.main(sys.argv[2:])
    elif cmd == "status":
        for name in ("session",) + COMPONENTS:
            pid = daemon.running(name)
            print(f"{name:14s} {'çalışıyor (' + str(pid) + ')' if pid else '—'}")
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
