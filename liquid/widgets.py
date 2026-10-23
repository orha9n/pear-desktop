"""Liquid — masaüstü widget'ları (macOS 26/27): Takvim, Analog Saat, Fotoğraf.

Hedef görseldeki düzen (sol üst): [Takvim][Saat] üstte, [Fotoğraf (orta boy)] altta.
Her widget ayrı, masaüstü katmanında (diğer pencerelerin altında) duran bir penceredir;
sürükleyerek taşınır, konumu ~/.config/liquid/widgets.ini'de saklanır. Sağ tık: fotoğraf seç,
kaldır. Saydam köşeler xfwm4 compositoru ile.

Çalıştırma: python3 -m liquid.widgets
"""
import calendar
import configparser
import math
import os

import cairo
import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("PangoCairo", "1.0")
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib, Pango, PangoCairo  # noqa: E402

from .core import design, wallpaper, daemon, config_path, screen_geometry  # noqa: E402
from .core.i18n import t, LANG  # noqa: E402

CONF = config_path("widgets.ini")
S, G = design.WIDGET_S, design.WIDGET_GAP
ML, MT = design.WIDGET_MARGIN
R = design.WIDGET_RADIUS
PHOTO_DEFAULT = os.path.join(daemon.ROOT, "assets", "widgets", "photo.jpg")

MONTHS_TR = ["OCAK", "ŞUBAT", "MART", "NİSAN", "MAYIS", "HAZİRAN", "TEMMUZ", "AĞUSTOS", "EYLÜL",
             "EKİM", "KASIM", "ARALIK"]
DAYS_TR = ["P", "S", "Ç", "P", "C", "C", "P"]
DAYS_EN = ["M", "T", "W", "T", "F", "S", "S"]


def conf():
    cp = configparser.ConfigParser()
    cp.optionxform = str
    cp.read(CONF)
    return cp


def save(section, **kv):
    cp = conf()
    if not cp.has_section(section):
        cp.add_section(section)
    for k, v in kv.items():
        cp.set(section, k, str(v))
    with open(CONF, "w") as f:
        cp.write(f)


def text(cr, s, x, y, size, weight="Bold", color=(0, 0, 0, 1), align="left", font=None):
    lay = PangoCairo.create_layout(cr)
    lay.set_font_description(Pango.FontDescription(f"{font or design.FONT} {weight} {size}"))
    lay.set_text(s, -1)
    w, h = lay.get_pixel_size()
    if align == "center":
        x -= w / 2
    elif align == "right":
        x -= w
    cr.move_to(x, y)
    cr.set_source_rgba(*color)
    PangoCairo.show_layout(cr, lay)
    return w, h


class Widget(Gtk.Window):
    """Masaüstü katmanında, sürüklenebilir, yuvarlak köşeli widget penceresi."""
    kind = "widget"

    def __init__(self, w, h, default_xy):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.set_title(f"Liquid Widget {self.kind}")
        self.set_decorated(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_keep_below(True)
        self.set_accept_focus(False)
        self.set_type_hint(Gdk.WindowTypeHint.UTILITY)
        self.stick()
        self.set_app_paintable(True)
        vis = self.get_screen().get_rgba_visual()
        if vis:
            self.set_visual(vis)
        self.W, self.H = w, h
        self.pad = 14                           # gölge payı
        self.set_size_request(w + 2 * self.pad, h + 2 * self.pad)
        self.mx, self.my, self.mw, self.mh = screen_geometry()
        cp = conf()
        x = cp.getint(self.kind, "x", fallback=default_xy[0])
        y = cp.getint(self.kind, "y", fallback=default_xy[1])
        self.move(x - self.pad, y - self.pad)
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON_RELEASE_MASK)
        self.connect("draw", self._draw)
        self.connect("button-press-event", self._press)
        self.connect("configure-event", self._moved)
        self.backdrop = None
        self._wp_key = None
        self._save_id = None

    def _moved(self, w, e):
        if self._save_id:
            GLib.source_remove(self._save_id)
        self._save_id = GLib.timeout_add(500, self._save_pos)
        self._wp_key = None                     # cam arka planı yeni konuma göre
        return False

    def _save_pos(self):
        x, y = self.get_position()
        save(self.kind, x=x + self.pad, y=y + self.pad)
        self._save_id = None
        self.queue_draw()
        return False

    def _press(self, w, e):
        if e.button == 1:
            self.begin_move_drag(e.button, int(e.x_root), int(e.y_root), e.time)
        elif e.button == 3:
            m = self.context_menu()
            m.show_all()
            m.attach_to_widget(self, None)
            m.popup_at_pointer(e)
        return True

    def context_menu(self):
        m = Gtk.Menu()
        rm = Gtk.MenuItem(label=t("remove_widget"))
        rm.connect("activate", lambda *_: (save(self.kind, hidden=1), self.hide()))
        m.append(rm)
        return m

    def glass_backdrop(self):
        p, st, mt = wallpaper.current()
        x, y = self.get_position()
        key = (p, st, mt, x, y)
        if key != self._wp_key:
            self._wp_key = key
            self.backdrop = wallpaper.region(self.mw, self.mh, max(0, x), max(0, y),
                                             self.W + 2 * self.pad, self.H + 2 * self.pad, blur=24)
        return self.backdrop

    def _draw(self, w, cr):
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.set_source_rgba(0, 0, 0, 0)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)
        cr.translate(self.pad, self.pad)
        self.paint(cr)
        return True

    def paint(self, cr):
        pass


# ----------------------------- Takvim -----------------------------
class CalendarWidget(Widget):
    kind = "calendar"

    def __init__(self):
        super().__init__(S, S, (ML, MT))
        GLib.timeout_add_seconds(60, lambda: (self.queue_draw(), True)[1])

    def paint(self, cr):
        design.soft_shadow(cr, 0, 0, self.W, self.H, R, strength=0.16, spread=10, dy=3)
        design.rrect(cr, 0, 0, self.W, self.H, R)
        cr.set_source_rgba(1, 1, 1, 0.98)
        cr.fill()
        now = GLib.DateTime.new_now_local()
        y, mo, today = now.get_year(), now.get_month(), now.get_day_of_month()
        month = MONTHS_TR[mo - 1] if LANG == "tr" else now.format("%B").upper()
        text(cr, month, 17, 15, 8.5, "Heavy", (*design.RED, 1))
        days = DAYS_TR if LANG == "tr" else DAYS_EN
        x0, cw, top, rh = 15, (self.W - 30) / 7, 36, 19.5
        for i, d in enumerate(days):
            col = (0, 0, 0, 0.88) if i < 5 else (0, 0, 0, 0.42)
            text(cr, d, x0 + cw * i + cw / 2, top, 7.5, "Bold", col, "center")
        cal = calendar.Calendar(firstweekday=0).monthdayscalendar(y, mo)
        for r, week in enumerate(cal):
            for c, d in enumerate(week):
                if not d:
                    continue
                cx = x0 + cw * c + cw / 2
                cy = top + 18 + r * rh
                if d == today:
                    design.circle(cr, cx, cy + 6.5, 9)
                    cr.set_source_rgba(*design.RED, 1)
                    cr.fill()
                    col = (1, 1, 1, 1)
                else:
                    col = (0, 0, 0, 0.88) if c < 5 else (0, 0, 0, 0.42)
                text(cr, str(d), cx, cy, 7.5, "Bold", col, "center")


# ----------------------------- Analog saat -----------------------------
class ClockWidget(Widget):
    kind = "clock"

    def __init__(self):
        super().__init__(S, S, (ML + S + G, MT))
        GLib.timeout_add(1000, lambda: (self.queue_draw(), True)[1])

    def paint(self, cr):
        bd = self.glass_backdrop()
        # cam kart: bulanık duvar kâğıdı + sıcak beyaz ton (hedefteki pembemsi cam)
        design.liquid_glass(cr, 0, 0, self.W, self.H, R, backdrop=bd, backdrop_xy=(-self.pad, -self.pad),
                            tint=(1, 1, 1, 0.30))
        cx, cy, rr = self.W / 2, self.H / 2, self.W / 2 - 13
        design.circle(cr, cx, cy, rr)
        cr.set_source_rgba(1, 1, 1, 1)
        cr.fill()
        for i in range(60):                               # dakika çizgileri
            a = i * math.pi / 30
            r1 = rr - (5 if i % 5 == 0 else 3.2)
            cr.move_to(cx + math.sin(a) * r1, cy - math.cos(a) * r1)
            cr.line_to(cx + math.sin(a) * (rr - 1.8), cy - math.cos(a) * (rr - 1.8))
            cr.set_source_rgba(0, 0, 0, 0.55 if i % 5 == 0 else 0.22)
            cr.set_line_width(1.2 if i % 5 == 0 else 0.8)
            cr.stroke()
        for h in range(1, 13):                            # rakamlar
            a = h * math.pi / 6
            nx, ny = cx + math.sin(a) * (rr - 17), cy - math.cos(a) * (rr - 17)
            lay = PangoCairo.create_layout(cr)
            lay.set_font_description(Pango.FontDescription(f"{design.FONT} Semi-Bold 13"))
            lay.set_text(str(h), -1)
            tw, th = lay.get_pixel_size()
            cr.move_to(nx - tw / 2, ny - th / 2)
            cr.set_source_rgba(0, 0, 0, 0.92)
            PangoCairo.show_layout(cr, lay)
        now = GLib.DateTime.new_now_local()
        hh, mm, ss = now.get_hour() % 12, now.get_minute(), now.get_second()
        cr.set_line_cap(cairo.LINE_CAP_ROUND)

        def hand(angle, length, width, color, back=0.0):
            cr.move_to(cx - math.sin(angle) * back, cy + math.cos(angle) * back)
            cr.line_to(cx + math.sin(angle) * length, cy - math.cos(angle) * length)
            cr.set_source_rgba(*color)
            cr.set_line_width(width)
            cr.stroke()
        ha = (hh + mm / 60) * math.pi / 6
        ma = (mm + ss / 60) * math.pi / 30
        sa = ss * math.pi / 30
        for a, ln in ((ha, rr * 0.52), (ma, rr * 0.80)):     # macOS: ince sap + kalın gövde
            hand(a, 9, 2.2, (0, 0, 0, 0.95))
            cr.save()
            cr.translate(cx, cy)
            cr.rotate(a)
            design.rrect(cr, -2.6, -ln, 5.2, ln - 7, 2.6)
            cr.set_source_rgba(0, 0, 0, 0.95)
            cr.fill()
            cr.restore()
        hand(sa, rr * 0.86, 1.1, (*design.ORANGE, 1), back=rr * 0.18)
        design.circle(cr, cx, cy, 3.2)
        cr.set_source_rgba(*design.ORANGE, 1)
        cr.fill()
        design.circle(cr, cx, cy, 1.3)
        cr.set_source_rgba(1, 1, 1, 1)
        cr.fill()


# ----------------------------- Fotoğraf -----------------------------
class PhotoWidget(Widget):
    kind = "photo"

    def __init__(self):
        super().__init__(2 * S + G, S, (ML, MT + S + G))
        self.surface = None
        self.path = conf().get("photo", "path", fallback=PHOTO_DEFAULT)
        self._load()

    def _load(self):
        try:
            sf = self.get_scale_factor()
            pb = GdkPixbuf.Pixbuf.new_from_file(self.path)
            sw, sh = self.W * sf, self.H * sf
            k = max(sw / pb.get_width(), sh / pb.get_height())       # kapla (cover)
            pb = pb.scale_simple(int(pb.get_width() * k) + 1, int(pb.get_height() * k) + 1,
                                 GdkPixbuf.InterpType.HYPER)
            x, y = (pb.get_width() - sw) // 2, (pb.get_height() - sh) // 2
            pb = pb.new_subpixbuf(int(x), int(y), int(sw), int(sh))
            self.surface = Gdk.cairo_surface_create_from_pixbuf(pb, sf, None)
        except Exception:
            self.surface = None
        self.queue_draw()

    def paint(self, cr):
        design.soft_shadow(cr, 0, 0, self.W, self.H, R, strength=0.18, spread=10, dy=3)
        cr.save()
        design.rrect(cr, 0, 0, self.W, self.H, R)
        cr.clip()
        if self.surface is not None:
            cr.set_source_surface(self.surface, 0, 0)
        else:
            cr.set_source_rgba(0.85, 0.85, 0.88, 1)
        cr.paint()
        cr.restore()
        design.rrect(cr, 0.5, 0.5, self.W - 1, self.H - 1, R)        # ince iç kenar ışığı
        cr.set_source_rgba(1, 1, 1, 0.25)
        cr.set_line_width(1)
        cr.stroke()

    def context_menu(self):
        m = super().context_menu()
        ch = Gtk.MenuItem(label=t("choose_photo"))
        ch.connect("activate", lambda *_: self._choose())
        m.prepend(Gtk.SeparatorMenuItem())
        m.prepend(ch)
        return m

    def _choose(self):
        dlg = Gtk.FileChooserNative.new(t("choose_photo"), None, Gtk.FileChooserAction.OPEN, None, None)
        flt = Gtk.FileFilter()
        flt.add_pixbuf_formats()
        dlg.add_filter(flt)
        pics = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_PICTURES)
        if pics:
            dlg.set_current_folder(pics)
        if dlg.run() == Gtk.ResponseType.ACCEPT:
            self.path = dlg.get_filename()
            save("photo", path=self.path)
            self._load()


def main():
    if not daemon.claim("widgets"):
        return
    css = Gtk.CssProvider()
    from .applemenu import MENU_CSS
    css.load_from_data(MENU_CSS.encode())
    Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_USER + 10)
    cp = conf()
    wins = []
    for cls in (CalendarWidget, ClockWidget, PhotoWidget):
        if cp.get(cls.kind, "hidden", fallback="0") != "1":
            w = cls()
            w.show_all()
            wins.append(w)
    if not wins:
        return
    Gtk.main()


if __name__ == "__main__":
    main()
