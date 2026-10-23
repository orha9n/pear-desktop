"""Liquid — komut satırı: kısayollar ve betikler bileşenleri buradan açar/kapatır.

  python3 -m liquid.ctl toggle spotlight|launcher|controlcenter
  python3 -m liquid.ctl start|stop            (oturum bekçisi + tüm bileşenler)
  python3 -m liquid.ctl status
"""
import os
import signal
import sys

from .core import daemon
from .session import COMPONENTS


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
    elif cmd == "status":
        for name in ("session",) + COMPONENTS:
            pid = daemon.running(name)
            print(f"{name:14s} {'çalışıyor (' + str(pid) + ')' if pid else '—'}")
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
