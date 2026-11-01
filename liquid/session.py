# SPDX-License-Identifier: GPL-3.0-only
"""Pear — oturum bekçisi: tüm bileşenleri başlatır, kapanırsa yeniden açar, XFCE panelini kapatır.

Tek autostart girdisi bunu çalıştırır (~/.config/autostart/liquid.desktop).
XFCE panelini kapatırken `xfce4-panel --quit` DÖNGÜDE çalıştırılmaz (her biri
"xfce4-panel" adlı ayrı süreç olup hata penceresi açıyordu) → gerçek panel PID'ine SIGTERM.

Çalıştırma: python3 -m liquid.session
"""
import os
import signal
import time

from . import compositor
from .core import daemon

COMPONENTS = ("bar", "dock", "widgets", "launcher", "controlcenter", "spotlight")


def real_panel_pids():
    out = []
    for pid in os.listdir("/proc"):
        if not pid.isdigit():
            continue
        try:
            with open(f"/proc/{pid}/cmdline", "rb") as f:
                args = f.read().split(b"\0")
        except Exception:
            continue
        if not args or os.path.basename(args[0]) != b"xfce4-panel":
            continue
        if any(a in (b"--quit", b"-q", b"--restart", b"-r", b"--preferences") for a in args[1:]):
            continue
        out.append(int(pid))
    return out


def stop_xfce_panel():
    if os.environ.get("LIQUID_KEEP_PANEL") == "1":
        return
    for pid in real_panel_pids():
        try:
            os.kill(pid, signal.SIGTERM)
        except Exception:
            pass


def stop_all():
    for name in COMPONENTS:
        pid = daemon.running(name)
        if pid:
            try:
                os.kill(pid, signal.SIGTERM)
            except Exception:
                pass


def main():
    if not daemon.claim("session"):
        return
    signal.signal(signal.SIGTERM, lambda *a: (stop_all(), os._exit(0)))
    daemon.note("oturum başladı")
    seen = {}
    keeper = compositor.Keeper()
    while True:
        stop_xfce_panel()
        keeper.tick(daemon.note)
        for name in COMPONENTS:
            pid = daemon.running(name)
            if pid is None:
                if seen.get(name):        # çalışıyordu, artık yok → çöktü ya da öldürüldü
                    daemon.note(f"{name} (PID {seen[name]}) kapanmış — yeniden başlatılıyor "
                                f"(çökme ise: coredumpctl info {seen[name]})")
                daemon.start(name)
            seen[name] = pid
        time.sleep(5)


if __name__ == "__main__":
    main()
