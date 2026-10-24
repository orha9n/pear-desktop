"""Liquid — gerçek cam için compositor seçimi: xfwm4'ün kendi compositor'ü ya da picom.

xfwm4 compositor'ü arkadaki pencereleri bulanıklaştıramaz; bu yüzden cam yüzeyler duvar kâğıdının
bulanık bir kopyasını çiziyordu (arkada pencere olsa da duvar kâğıdı görünürdü). picom açıkken
Control Center / Spotlight / Uygulamalar gerçek bulanıklık kullanır (glass()), değilse eski yol sürer.

  liquid compositor picom   xfwm4 compositor'ünü kapat (önceki değer yedeklenir), picom'u başlat
  liquid compositor xfwm    picom'u durdur, xfwm4 compositor'ünü yedekteki değere döndür
  liquid compositor         şu anki durum

Seçim ~/.config/liquid/compositor.json'da durur; oturum bekçisi picom'u ayakta tutar, picom
sürekli çöküyorsa kendiliğinden xfwm4'e döner (ekran compositor'süz kalmasın).
"""
import json
import math
import os
import shutil
import subprocess
import time

CONF = os.path.join(os.path.dirname(os.path.abspath(__file__)), "picom.conf")
STATE = os.path.expanduser("~/.config/liquid/compositor.json")
ROLE = "liquid-glass"


def _xfwm(value=None):
    p = ["xfconf-query", "-c", "xfwm4", "-p", "/general/use_compositing"]
    if value is None:
        r = subprocess.run(p, capture_output=True, text=True)
        return r.stdout.strip() or "true"
    subprocess.run(p + ["-t", "bool", "-s", value, "--create"])


def load():
    try:
        with open(STATE) as f:
            return json.load(f)
    except Exception:
        return {"mode": "xfwm"}


def _save(st):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    with open(STATE, "w") as f:
        json.dump(st, f)


def picom_pid():
    for pid in os.listdir("/proc"):
        if pid.isdigit():
            try:
                with open(f"/proc/{pid}/stat") as f:
                    st = f.read()
            except OSError:
                continue
            # "PID (comm) durum …" — kapanmış ama toplanmamış (zombi) picom sayılmaz
            if st[st.find("(") + 1:st.rfind(")")] == "picom" and st[st.rfind(")") + 2] != "Z":
                return int(pid)
    return None


def _ours(pid):
    """Bu picom bizim ayarımızla mı başladı? (picom paketi /etc/xdg/autostart ile kendi varsayılanını açıyor)"""
    try:
        with open(f"/proc/{pid}/cmdline", "rb") as f:
            return CONF.encode() in f.read()
    except OSError:
        return False


# picom paketinin /etc/xdg/autostart/picom.desktop'u her girişte ayarsız bir picom açıyordu; bekçi onu
# "çalışıyor" sayıp bizimkini hiç başlatmıyordu (cam bulanıklığı ve gölge kuralları devre dışı). Kullanıcı
# düzeyinde gizle; xfwm'e dönüşte (ve uninstall'da) yalnız bizim yazdığımız dosya silinir.
AUTOSTART = os.path.expanduser("~/.config/autostart/picom.desktop")


def hide_system_autostart():
    if os.path.exists("/etc/xdg/autostart/picom.desktop") and not os.path.exists(AUTOSTART):
        os.makedirs(os.path.dirname(AUTOSTART), exist_ok=True)
        with open(AUTOSTART, "w") as f:
            f.write("[Desktop Entry]\nType=Application\nName=picom\nHidden=true\nX-Liquid=true\n")


def restore_system_autostart():
    try:
        with open(AUTOSTART) as f:
            if "X-Liquid=true" in f.read():
                os.remove(AUTOSTART)
    except OSError:
        pass


def start_picom():
    log = open(os.path.expanduser("~/.cache/liquid/picom.log"), "a")
    try:
        # setsid -f: başlatan süreçten (oturum bekçisi) kopar → kapanınca zombi kalmaz
        subprocess.Popen(["setsid", "-f", "picom", "--config", CONF], stdout=log, stderr=log,
                         stdin=subprocess.DEVNULL).wait()
    finally:
        log.close()


def stop_picom():
    pid = picom_pid()
    if pid:
        try:
            os.kill(pid, 15)
        except OSError:
            pass
        for _ in range(20):
            if not picom_pid():
                break
            time.sleep(0.1)


def use_picom():
    if not shutil.which("picom"):
        print("picom kurulu değil: sudo apt install picom")
        return False
    st = load()
    if st.get("mode") != "picom":
        st["xfwm_compositing"] = _xfwm()               # geri dönüşte yazılacak önceki değer
    _xfwm("false")
    hide_system_autostart()
    time.sleep(0.6)                                   # xfwm4 _NET_WM_CM_S0'ı bıraksın
    pid = picom_pid()
    if pid and not _ours(pid):
        stop_picom()
        pid = None
    if not pid:
        start_picom()
    time.sleep(1.5)
    if not picom_pid():
        print("picom başlayamadı (~/.cache/liquid/picom.log) — xfwm4 compositor'üne dönülüyor")
        _xfwm(st.get("xfwm_compositing", "true"))
        return False
    st["mode"] = "picom"
    _save(st)
    return True


def use_xfwm():
    st = load()
    _save({"mode": "xfwm"})                           # önce seçim: bekçi arada picom'u geri açmasın
    restore_system_autostart()
    stop_picom()
    _xfwm(st.get("xfwm_compositing", "true"))


class Keeper:
    """Oturum bekçisinde: picom seçiliyse ayakta tut; 2 dakikada 4 kez düşerse xfwm4'e dön."""

    def __init__(self):
        self.deaths = []
        self.had = False

    def tick(self, note):
        if load().get("mode") != "picom":
            return
        pid = picom_pid()
        if pid and not _ours(pid):
            note(f"ayarsız picom (PID {pid}, sistem autostart'ı) — Liquid ayarıyla değiştiriliyor")
            hide_system_autostart()
            stop_picom()
            start_picom()
            return
        if pid:
            self.had = True
            return
        now = time.monotonic()
        if self.had:
            self.deaths = [t for t in self.deaths if now - t < 120] + [now]
            note(f"picom kapanmış ({len(self.deaths)}. kez) — yeniden başlatılıyor")
        if len(self.deaths) >= 4 or not shutil.which("picom"):
            note("picom tutunamıyor — xfwm4 compositor'üne dönüldü (liquid compositor picom ile yeniden dene)")
            use_xfwm()
            return
        self.had = False
        _xfwm("false")
        start_picom()


# ---------- bileşenler için: gerçek cam ----------
_active = [0.0, False]


def active():
    """picom çalışıyor mu (2 sn önbellek) — cam çizimi buna göre gerçek bulanıklık ya da kopya."""
    now = time.monotonic()
    if now - _active[0] > 2:
        _active[:] = [now, picom_pid() is not None]
    return _active[1]


def mark(win):
    """Pencere picom'un blur kuralına girsin (haritalanmadan önce çağrılmalı)."""
    win.set_role(ROLE)


def _rounded_region(x, y, w, h, r):
    import cairo
    reg = cairo.Region()
    r = max(0, min(int(r), w // 2, h // 2))
    for i in range(r):                               # köşe satırları: yay boyunca içeri çekilir
        d = r - math.sqrt(max(0.0, r * r - (r - i - 0.5) ** 2))
        inset = int(round(d))
        for yy in (y + i, y + h - 1 - i):
            reg.union(cairo.RectangleInt(x + inset, yy, w - 2 * inset, 1))
    reg.union(cairo.RectangleInt(x, y + r, w, h - 2 * r))
    return reg


def shape(win, x, y, w, h, r):
    """picom açıkken pencerenin X şekli cam yüzeyin kendisi olsun: bulanıklık ve gölge köşeleri
    izler, kenardaki saydam pay (eski elle çizilmiş gölge) bulanıklaşmaz. Kapalıyken şekil kalkar."""
    gw = win.get_window()
    if gw is None:
        return
    key = (x, y, w, h, int(r)) if active() else None
    if getattr(win, "_glass_shape", "-") == key:
        return
    win._glass_shape = key
    gw.shape_combine_region(_rounded_region(*key) if key else None, 0, 0)


def main(argv):
    if argv and argv[0] == "picom":
        ok = use_picom()
        print("picom etkin — gerçek cam açık" if ok else "değişiklik yapılmadı")
    elif argv and argv[0] == "xfwm":
        use_xfwm()
        print("xfwm4 compositor'üne dönüldü")
    else:
        st = load()
        print(f"seçim: {st.get('mode')}  picom: {'çalışıyor' if picom_pid() else '—'}  "
              f"xfwm4 use_compositing: {_xfwm()}")
