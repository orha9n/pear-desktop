# SPDX-License-Identifier: GPL-3.0-only
"""Pear — eski sürümlerin picom kurulumunu geri alır (Pear artık picom kullanmıyor).

Eski sürümler xfwm4 compositor'ünü kapatıp kendi ayarıyla picom açıyordu; seçim
~/.config/liquid/compositor.json'da, önceki xfwm4 değeri de orada duruyordu. Bu modül o durumu
bir kez temizler: Pear'in açtığı picom'u durdurur ve xfwm4 compositor'ünü önceki değerine döndürür.
picom paketine dokunmaz (kullanıcı başka amaçla kurmuş olabilir). Pear'in yazdığı, sistem picom
autostart'ını gizleyen dosya paket kurulu oldukça yerinde kalır: kaldırılırsa sonraki girişte ayarsız
bir picom xfwm4 ile yarışırdı. Paket kaldırılmışsa dosya da silinir.
Oturum başlarken ve uninstall.sh'ta çalışır; iz yoksa hiçbir şey yapmaz.

  python3 -m liquid.legacy_picom
"""
import json
import os
import signal
import subprocess
import time

STATE = os.path.expanduser("~/.config/liquid/compositor.json")
AUTOSTART = os.path.expanduser("~/.config/autostart/picom.desktop")
SYSTEM_AUTOSTART = "/etc/xdg/autostart/picom.desktop"
CONF_MARK = b"liquid/picom.conf"          # eski Pear'in picom'u bu ayar dosyasıyla başlıyordu


def _our_picom_pids():
    pids = []
    for pid in os.listdir("/proc"):
        if not pid.isdigit():
            continue
        try:
            with open(f"/proc/{pid}/comm") as f:
                if f.read().strip() != "picom":
                    continue
            with open(f"/proc/{pid}/cmdline", "rb") as f:
                if CONF_MARK in f.read():
                    pids.append(int(pid))
        except OSError:
            continue
    return pids


def _stop_picom():
    pids = _our_picom_pids()
    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            pass
    for _ in range(20):
        if not _our_picom_pids():
            break
        time.sleep(0.1)
    return bool(pids)


def _restore_autostart():
    if os.path.exists(SYSTEM_AUTOSTART):          # picom kurulu: gizleme kalsın
        return False
    try:
        with open(AUTOSTART) as f:
            if "X-Liquid=true" in f.read():
                os.remove(AUTOSTART)
                return True
    except OSError:
        pass
    return False


def _set_xfwm_compositing(value):
    try:
        subprocess.run(["xfconf-query", "-c", "xfwm4", "-p", "/general/use_compositing",
                        "-t", "bool", "-s", value, "--create"], timeout=5, check=False)
    except (OSError, subprocess.TimeoutExpired):
        pass


def cleanup(note=print):
    """Eski picom kurulumunun izi varsa geri al. Bir şey yaptıysa True döner."""
    state = None
    try:
        with open(STATE) as f:
            state = json.load(f)
    except (OSError, ValueError):
        pass
    stopped = _stop_picom()
    restored = _restore_autostart()
    if state is not None or stopped:          # picom gidince ekran compositor'süz kalmasın
        value = str((state or {}).get("xfwm_compositing", "true")).lower()
        _set_xfwm_compositing("false" if value == "false" else "true")
    if state is not None:
        try:
            os.remove(STATE)
        except OSError:
            pass
    did = stopped or restored or state is not None
    if did:
        note("eski picom kurulumu kaldırıldı — xfwm4 compositor'ü kullanılıyor")
    return did


if __name__ == "__main__":
    cleanup()
