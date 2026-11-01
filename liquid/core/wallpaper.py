# SPDX-License-Identifier: GPL-3.0-only
"""Pear — duvar kâğıdı: xfdesktop'un kullandığı resim, ekrana yerleştirme ve bulanık bölgeler.

Cam yüzeyler (dock, widget'lar, Uygulamalar ekranı) arkadaki duvar kâğıdının bulanık halini
çizer; compositor blur'u (picom) gerekmez. Sonuçlar önbellekte tutulur.
"""
import os
import subprocess
import time

import cairo

_cache = {}
TTL = 4.0                 # xfconf/xrandr sonucu bu kadar saniye önbellekte (saat widget'ı saniyede bir
_props = (0.0, {})        # çiziliyor, Spotlight her tuşta yeniden boyutlanıyordu → her seferinde 3 süreç)
_output = (0.0, "0")


def _sh(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=3).stdout.strip()
    except Exception:
        return ""


def primary_output():
    global _output
    if time.monotonic() - _output[0] < 30:
        return _output[1]
    out = _sh(["xrandr", "--current"])            # --current: yeniden algılama (probe) yapma
    name = "0"
    for want in (" connected primary", " connected"):
        name = next((ln.split()[0] for ln in out.splitlines() if want in ln), None)
        if name:
            break
    _output = (time.monotonic(), name or "0")
    return _output[1]


def _desktop_props():
    """xfce4-desktop kanalının tamamı tek `xfconf-query -lv` çağrısıyla (önbellekli)."""
    global _props
    if time.monotonic() - _props[0] < TTL:
        return _props[1]
    d = {}
    for line in _sh(["xfconf-query", "-c", "xfce4-desktop", "-lv"]).splitlines():
        k, _, v = line.partition(" ")
        d[k] = v.strip()
    _props = (time.monotonic(), d)
    return d


def _active_workspace(props):
    """xfdesktop "tüm çalışma alanlarına uygula" (single-workspace-mode, varsayılan açık) ise o alanın
    numarası; değilse etkin çalışma alanı."""
    if props.get("/backdrop/single-workspace-mode", "true") != "false":
        n = props.get("/backdrop/single-workspace-number", "0")
        return int(n) if n.isdigit() else 0
    try:
        from gi.repository import Gdk
        return max(0, Gdk.Screen.get_default().get_current_desktop())
    except Exception:
        return 0


def current(workspace=None):
    """(resim yolu, stil, değişim zamanı) — stil: 0 yok, 1 ortala, 2 döşe, 3 uzat, 4 sığdır, 5 yakınlaştır."""
    props = _desktop_props()
    ws = _active_workspace(props) if workspace is None else workspace
    mon = primary_output()
    for m in (f"monitor{mon}", "monitor0"):
        base = f"/backdrop/screen0/{m}/workspace{ws}"
        p = props.get(f"{base}/last-image", "")
        if p and os.path.exists(p):
            st = props.get(f"{base}/image-style", "5")
            try:
                mt = os.path.getmtime(p)
            except OSError:
                mt = 0
            return p, int(st) if st.isdigit() else 5, mt
    return None, 5, 0


def _screen_image(path, style, mw, mh):
    """Ekran boyutuna yerleştirilmiş duvar kâğıdı. Sonuç ~/.cache/liquid/wp/ altında PNG olarak tüm
    bileşenlerle paylaşılır: progressive JPEG küçük ölçekte çözülürken bile libjpeg tüm katsayıları
    tutuyor (9600×5400 → ~180 MB tepe); her bileşen ayrı çözmesin, ilk gelen bir kez çözsün."""
    import fcntl
    import hashlib
    from PIL import Image
    key = ("img", path, style, mw, mh, os.path.getmtime(path))
    if key in _cache:
        return _cache[key]
    d = os.path.join(os.path.expanduser("~/.cache/liquid"), "wp")
    os.makedirs(d, exist_ok=True)
    disk = os.path.join(d, hashlib.sha1(repr(key).encode()).hexdigest()[:16] + ".png")
    with open(os.path.join(d, ".lock"), "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)              # aynı anda başlayan bileşenler sırayla
        if os.path.exists(disk):
            try:
                im = Image.open(disk).convert("RGB")
                _cache.clear()
                _cache[key] = im
                return im
            except Exception:
                pass
        im = _render(path, style, mw, mh)
        for old in os.listdir(d):                     # eski duvar kâğıtlarının önbelleği
            if old.endswith(".png") and len(os.listdir(d)) > 8:
                os.remove(os.path.join(d, old))
        im.save(disk + ".tmp", "PNG", compress_level=1)
        os.replace(disk + ".tmp", disk)
    _cache.clear()                     # tek duvar kâğıdı tutulur (bellek)
    _cache[key] = im
    return im


def _render(path, style, mw, mh):
    from PIL import Image
    src = Image.open(path)
    iw, ih = src.size
    # JPEG'i doğrudan gereken ölçeğe yakın çöz (1/2, 1/4, 1/8): Mint'in 9600×5400 duvar kâğıdı tam
    # çözülünce 156 MB, yeniden boyutlandırırken ~270 MB oluyordu — her bileşende ayrı ayrı.
    if style in (3, 4, 5) or style not in (1, 2):
        s = min(mw / iw, mh / ih) if style == 4 else max(mw / iw, mh / ih)
        src.draft("RGB", (max(1, int(iw * s)), max(1, int(ih * s))) if style != 3 else (mw, mh))
    src = src.convert("RGB")
    iw, ih = src.size
    if style == 3:                                  # uzat
        im = src.resize((mw, mh), Image.LANCZOS)
    elif style in (1, 2, 4):                        # ortala / döşe / sığdır: boşluklar siyah
        im = Image.new("RGB", (mw, mh), (0, 0, 0))
        if style == 2:
            for y in range(0, mh, ih):
                for x in range(0, mw, iw):
                    im.paste(src, (x, y))
        else:
            if style == 4:
                s = min(mw / iw, mh / ih)
                src = src.resize((max(1, round(iw * s)), max(1, round(ih * s))), Image.LANCZOS)
            im.paste(src, ((mw - src.width) // 2, (mh - src.height) // 2))
    else:                                           # 5 yakınlaştır (ve bilinmeyenler): kapla
        s = max(mw / iw, mh / ih)
        im = src.resize((max(mw, round(iw * s)), max(mh, round(ih * s))), Image.LANCZOS)
        x0, y0 = (im.width - mw) // 2, (im.height - mh) // 2
        im = im.crop((x0, y0, x0 + mw, y0 + mh))
    del src
    _trim()
    return im


def _trim():
    """Büyük geçici PIL tamponları serbest kalınca glibc belleği sisteme geri vermiyor → iade et."""
    try:
        import ctypes
        ctypes.CDLL("libc.so.6").malloc_trim(0)
    except Exception:
        pass


def _to_surface(im):
    im = im.convert("RGBA")
    w, h = im.size
    data = bytearray(im.tobytes("raw", "BGRA"))
    stride = cairo.ImageSurface.format_stride_for_width(cairo.FORMAT_ARGB32, w)
    if stride != w * 4:                # her zaman eşit (ARGB32), ama emniyet
        im = im.crop((0, 0, stride // 4, h))
        data = bytearray(im.tobytes("raw", "BGRA"))
    return cairo.ImageSurface.create_for_data(data, cairo.FORMAT_ARGB32, stride // 4, h, stride)


def region(mw, mh, x, y, w, h, blur=28, saturate=1.25, workspace=None):
    """Ekrandaki (x, y, w, h) bölgesinin bulanık duvar kâğıdı yüzeyi (yoksa None).
    macOS camı arkayı bulanıklaştırır ve renkleri hafif doygunlaştırır."""
    path, style, mt = current(workspace)
    if not path:
        return None
    key = ("reg", path, style, mt, mw, mh, x, y, w, h, blur, saturate)
    if key in _cache:
        return _cache[key]
    try:
        from PIL import ImageFilter, ImageEnhance
        im = _screen_image(path, style, mw, mh)
        m = blur * 2
        box = (max(0, x - m), max(0, y - m), min(mw, x + w + m), min(mh, y + h + m))
        part = im.crop(box).filter(ImageFilter.GaussianBlur(blur))
        part = ImageEnhance.Color(part).enhance(saturate)
        part = part.crop((x - box[0], y - box[1], x - box[0] + w, y - box[1] + h))
        surf = _to_surface(part)
        _trim()
    except Exception:
        return None
    _cache[key] = surf
    return surf


def sharp_region(mw, mh, x, y, w, h, workspace=None):
    """Bulanıklaştırılmamış bölge (menü çubuğunun okunabilirlik ölçümü için)."""
    path, style, _ = current(workspace)
    if not path:
        return None
    try:
        return _screen_image(path, style, mw, mh).crop((x, y, x + w, y + h))
    except Exception:
        return None


def luminance(mw, mh, x, y, w, h):
    """Bölgenin ortalama parlaklığı 0..1 (menü çubuğu yazı rengi seçimi)."""
    im = sharp_region(mw, mh, x, y, w, h)
    if im is None:
        return 0.3
    im = im.resize((max(1, w // 8), max(1, h // 4))).convert("L")
    px = list(im.getdata())
    return sum(px) / (255 * len(px))
