"""Liquid — duvar kâğıdı: xfdesktop'un kullandığı resim, ekrana yerleştirme ve bulanık bölgeler.

Cam yüzeyler (dock, widget'lar, Uygulamalar ekranı) arkadaki duvar kâğıdının bulanık halini
çizer; compositor blur'u (picom) gerekmez. Sonuçlar önbellekte tutulur.
"""
import os
import subprocess

import cairo

_cache = {}


def _sh(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=3).stdout.strip()
    except Exception:
        return ""


def primary_output():
    out = _sh(["xrandr"])
    for want in (" connected primary", " connected"):
        for line in out.splitlines():
            if want in line:
                return line.split()[0]
    return "0"


def current(workspace=0):
    """(resim yolu, stil, değişim zamanı) — stil: 5 yakınlaştır, 3 uzat, diğerleri ≈ kapla."""
    mon = primary_output()
    for m in (f"monitor{mon}", "monitor0"):
        base = f"/backdrop/screen0/{m}/workspace{workspace}"
        p = _sh(["xfconf-query", "-c", "xfce4-desktop", "-p", f"{base}/last-image"])
        if p and os.path.exists(p):
            st = _sh(["xfconf-query", "-c", "xfce4-desktop", "-p", f"{base}/image-style"])
            try:
                mt = os.path.getmtime(p)
            except OSError:
                mt = 0
            return p, int(st) if st.isdigit() else 5, mt
    return None, 5, 0


def _screen_image(path, style, mw, mh):
    from PIL import Image
    key = ("img", path, style, mw, mh, os.path.getmtime(path))
    if key in _cache:
        return _cache[key]
    im = Image.open(path).convert("RGB")
    iw, ih = im.size
    if style == 3:
        im = im.resize((mw, mh), Image.LANCZOS)
    else:
        s = max(mw / iw, mh / ih)
        im = im.resize((max(mw, round(iw * s)), max(mh, round(ih * s))), Image.LANCZOS)
        x0, y0 = (im.width - mw) // 2, (im.height - mh) // 2
        im = im.crop((x0, y0, x0 + mw, y0 + mh))
    _cache.clear()                     # tek duvar kâğıdı tutulur (bellek)
    _cache[key] = im
    return im


def _to_surface(im):
    im = im.convert("RGBA")
    w, h = im.size
    data = bytearray(im.tobytes("raw", "BGRA"))
    stride = cairo.ImageSurface.format_stride_for_width(cairo.FORMAT_ARGB32, w)
    if stride != w * 4:                # her zaman eşit (ARGB32), ama emniyet
        im = im.crop((0, 0, stride // 4, h))
        data = bytearray(im.tobytes("raw", "BGRA"))
    return cairo.ImageSurface.create_for_data(data, cairo.FORMAT_ARGB32, stride // 4, h, stride)


def region(mw, mh, x, y, w, h, blur=28, saturate=1.25, workspace=0):
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
    except Exception:
        return None
    _cache[key] = surf
    return surf


def sharp_region(mw, mh, x, y, w, h, workspace=0):
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
