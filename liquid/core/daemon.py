"""Liquid — süreç yönetimi: tek kopya (PID), aç/kapat sinyali, başka bileşeni başlatma.

PLAN.md §5 tuzakları burada çözülür:
  - bayat PID dosyası başka bir süreci gösterebilir → /proc/PID/cmdline doğrulaması
  - SIGUSR1 üst süreçten ENGELLİ miras kalabilir → her daemon başında engeli kaldır
"""
import os
import signal
import subprocess
import sys

RUN = os.path.join(os.environ.get("XDG_RUNTIME_DIR") or os.path.expanduser("~/.cache"), "liquid")
LOGS = os.path.expanduser("~/.cache/liquid")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _pidfile(name):
    return os.path.join(RUN, f"{name}.pid")


def _cmdline(pid):
    try:
        with open(f"/proc/{pid}/cmdline", "rb") as f:
            return f.read().replace(b"\0", b" ").decode(errors="ignore")
    except Exception:
        return ""


def running(name):
    """Bileşen çalışıyorsa PID'i (cmdline'da 'liquid' ve bileşen adı olmalı)."""
    try:
        with open(_pidfile(name)) as f:
            pid = int(f.read().strip())
    except Exception:
        return None
    # bileşenler hep `python3 -m liquid.<ad>` ile başlar → cmdline'da tam bu ifade olmalı
    if pid != os.getpid() and f"liquid.{name} " in _cmdline(pid) + " ":
        return pid
    return None


def claim(name):
    """Daemon başında: engelli sinyalleri aç; aynı bileşen zaten varsa False."""
    try:
        signal.pthread_sigmask(signal.SIG_UNBLOCK, {signal.SIGUSR1, signal.SIGUSR2, signal.SIGTERM})
    except Exception:
        pass
    if running(name):
        return False
    os.makedirs(RUN, exist_ok=True)
    with open(_pidfile(name), "w") as f:
        f.write(str(os.getpid()))
    return True


def start(name, *args):
    """`python3 -m liquid.<name>` olarak ayrık başlat; çıktı ~/.cache/liquid/<name>.log."""
    if running(name):
        return
    os.makedirs(LOGS, exist_ok=True)
    env = dict(os.environ)
    env["PYTHONPATH"] = ROOT + (":" + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    log = open(os.path.join(LOGS, f"{name}.log"), "a")
    try:
        subprocess.Popen(["setsid", "-f", sys.executable, "-m", f"liquid.{name}", *args],
                         stdout=log, stderr=log, stdin=subprocess.DEVNULL, env=env, cwd=ROOT)
    finally:
        log.close()


def signal_component(name, sig=signal.SIGUSR1):
    """Çalışan bileşene sinyal (aç/kapat); çalışmıyorsa başlat + kısa süre sonra göster."""
    pid = running(name)
    if pid:
        os.kill(pid, sig)
        return True
    start(name, "--show")
    return False


def on_signal(sig, callback):
    """GLib ana döngüsünde sinyal işleyici (Gtk süreçleri için)."""
    from gi.repository import GLib
    GLib.unix_signal_add(GLib.PRIORITY_HIGH, sig, lambda: (callback(), True)[1])
