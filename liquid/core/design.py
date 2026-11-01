# SPDX-License-Identifier: GPL-3.0-only
"""Pear — tasarım sabitleri ve ortak çizim yardımcıları (macOS 26/27 "Liquid Glass").

Ölçüler 1920x1080 referans ekranına göre tanımlanır.
"""
import math

import cairo

FONT = "Inter"                 # SF Pro'ya en yakın özgür yazı tipi (fonts-inter)
FONT_DISPLAY = "Inter Display"

# ---- menü çubuğu ----
BAR_H = 30
BAR_FONT_PX = 13

# ---- dock ----
DOCK_ICON = 54
DOCK_PAD = 8                   # cam gövde iç boşluğu
DOCK_GAP = 6                   # ikonlar arası
DOCK_BOTTOM = 12               # ekran altı ile arası
DOCK_WINDOW_GAP = 14           # büyütülmüş pencere ile cam gövde arasındaki boşluk
DOCK_RADIUS = 26
DOCK_SEP_W = 15

# ---- widget'lar ----
WIDGET_S = 172                 # küçük widget (kare)
WIDGET_GAP = 18
WIDGET_MARGIN = (18, 48)       # sol, üst (menü çubuğunun altından)
WIDGET_RADIUS = 24

RED = (1.0, 0.23, 0.19)        # macOS sistem kırmızısı
ORANGE = (1.0, 0.58, 0.0)
BLUE = (0.04, 0.52, 1.0)


# ---- Karanlık Mod: renkler temaya (xsettings Net/ThemeName, ör. MacTahoe-Dark) göre ----
def dark():
    try:
        from gi.repository import Gtk
        s = Gtk.Settings.get_default()
        return s is not None and "dark" in (s.props.gtk_theme_name or "").lower()
    except Exception:
        return False


def ink(a=1.0):
    """Yazı / çizgi rengi: açıkta siyah, koyuda beyaz."""
    return (1, 1, 1, a) if dark() else (0, 0, 0, a)


def icon_ink(a=0.9):
    return (0.92, 0.92, 0.94, a) if dark() else (0.1, 0.1, 0.12, a)


def paper(a=1.0):
    """Kart / saat kadranı yüzeyi."""
    return (0.17, 0.17, 0.18, a) if dark() else (1, 1, 1, a)


def surface(a=1.0):
    """Menü, balon, uyarı kartı arka planı."""
    return (0.19, 0.19, 0.2, a) if dark() else (0.965, 0.965, 0.973, a)


def tile(a):
    """Control Center modülü."""
    return (1, 1, 1, 0.10) if dark() else (1, 1, 1, a)


def glass_tint(a):
    return (0.10, 0.10, 0.12, min(0.6, a + 0.12)) if dark() else (1, 1, 1, a)


def on_theme_change(cb):
    """Tema değişince (Control Center → Karanlık Mod) cb() — her süreçte xsettings ile gelir."""
    from gi.repository import Gtk
    Gtk.Settings.get_default().connect("notify::gtk-theme-name", lambda *_: cb())


def rrect(cr, x, y, w, h, r):
    """Yuvarlak köşeli dikdörtgen yolu (macOS'un 'squircle'ına yakın, sürekli eğri)."""
    r = max(0.0, min(r, w / 2, h / 2))
    # sürekli köşe: kübik eğriler (yay yerine) → macOS kartlarındaki yumuşak köşe
    k = 0.62 * r
    cr.new_sub_path()
    cr.move_to(x + r, y)
    cr.line_to(x + w - r, y)
    cr.curve_to(x + w - r + k, y, x + w, y + r - k, x + w, y + r)
    cr.line_to(x + w, y + h - r)
    cr.curve_to(x + w, y + h - r + k, x + w - r + k, y + h, x + w - r, y + h)
    cr.line_to(x + r, y + h)
    cr.curve_to(x + r - k, y + h, x, y + h - r + k, x, y + h - r)
    cr.line_to(x, y + r)
    cr.curve_to(x, y + r - k, x + r - k, y, x + r, y)
    cr.close_path()


def soft_shadow(cr, x, y, w, h, r, strength=0.22, spread=10, dy=4):
    """Yumuşak dış gölge: katmanlı yarı saydam yollar (cairo'da gerçek blur yok)."""
    steps = max(1, spread // 2)
    for i in range(steps, 0, -1):
        a = strength * (1 - i / (steps + 1)) / steps * 2.2
        g = i * 2
        rrect(cr, x - g / 2, y - g / 2 + dy, w + g, h + g, r + g / 2)
        cr.set_source_rgba(0, 0, 0, a)
        cr.fill()


def liquid_glass(cr, x, y, w, h, r, backdrop=None, backdrop_xy=(0, 0), dark=False,
                 tint=None, shadow=True, rim=1.0):
    """macOS 26 Liquid Glass yüzeyi.

    backdrop: arkadaki duvar kâğıdının BULANIK cairo yüzeyi (ekran koordinatı backdrop_xy'de
    başlar). Katmanlar: gölge → bulanık arka → beyaz/koyu ton → üstten parlama gradyanı →
    iç kenar ışığı (üstte parlak, altta sönük) → ince dış çizgi.
    """
    if shadow:
        k = shadow if isinstance(shadow, float) else 1.0
        soft_shadow(cr, x, y, w, h, r, strength=(0.18 if not dark else 0.35) * k, spread=12, dy=3)
    cr.save()
    rrect(cr, x, y, w, h, r)
    cr.clip()
    if backdrop is not None:
        cr.set_source_surface(backdrop, backdrop_xy[0], backdrop_xy[1])
        cr.paint()
    t = tint or ((0.10, 0.10, 0.12, 0.38) if dark else (1, 1, 1, 0.24))
    cr.set_source_rgba(*t)
    cr.paint()
    # üstten aşağı yumuşak parlama (camın kalınlığı)
    g = cairo.LinearGradient(0, y, 0, y + h)
    g.add_color_stop_rgba(0.0, 1, 1, 1, 0.20 if not dark else 0.10)
    g.add_color_stop_rgba(0.45, 1, 1, 1, 0.04)
    g.add_color_stop_rgba(1.0, 1, 1, 1, 0.0)
    cr.set_source(g)
    cr.paint()
    cr.restore()
    # iç kenar ışığı: üst kenar parlak, alt kenar hafif
    cr.save()
    rrect(cr, x + 0.75, y + 0.75, w - 1.5, h - 1.5, r - 0.75)
    edge = cairo.LinearGradient(0, y, 0, y + h)
    edge.add_color_stop_rgba(0.0, 1, 1, 1, (0.75 if not dark else 0.35) * rim)
    edge.add_color_stop_rgba(0.5, 1, 1, 1, 0.18 * rim)
    edge.add_color_stop_rgba(1.0, 1, 1, 1, (0.38 if not dark else 0.15) * rim)
    cr.set_source(edge)
    cr.set_line_width(1.5)
    cr.stroke()
    rrect(cr, x - 0.5, y - 0.5, w + 1, h + 1, r + 0.5)
    cr.set_source_rgba(0, 0, 0, 0.10 if not dark else 0.45)
    cr.set_line_width(1)
    cr.stroke()
    cr.restore()


def text_shadow(cr, draw_fn, alpha=0.35, dy=0.6):
    """Saydam menü çubuğundaki beyaz yazılar için hafif gölge: draw_fn(cr) iki kez çizer."""
    cr.save()
    cr.translate(0, dy)
    draw_fn(cr, (0, 0, 0, alpha))
    cr.restore()
    draw_fn(cr, None)


def circle(cr, cx, cy, r):
    cr.new_sub_path()
    cr.arc(cx, cy, r, 0, 2 * math.pi)
