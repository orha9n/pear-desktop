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
import signal
import sys
import time

import cairo
import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("PangoCairo", "1.0")
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib, Pango, PangoCairo  # noqa: E402

from .core import design, wallpaper, daemon, config_path, screen_geometry, restart_on_monitor_change  # noqa: E402
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


def text(cr, s, x, y, size, weight="Bold", color=(0, 0, 0, 1), align="left", font=None, middle=False):
    """middle=True: y büyük harflerin (rakamların) görsel ortası — satır kutusunun değil."""
    lay = PangoCairo.create_layout(cr)
    lay.set_font_description(Pango.FontDescription(f"{font or design.FONT} {weight} {size}"))
    lay.set_text(s, -1)
    w, h = lay.get_pixel_size()
    if align == "center":
        x -= w / 2
    elif align == "right":
        x -= w
    if middle:
        ink, _log = lay.get_pixel_extents()
        y -= ink.y + ink.height / 2 if s.strip() else h / 2
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
        if e.button == 1 and Gallery.editing() and math.hypot(e.x - self.pad - 6, e.y - self.pad - 6) <= BADGE_R + 2:
            Gallery.instance._set(self.kind, False)
            return True
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
        m.append(Gtk.SeparatorMenuItem())
        ed = Gtk.MenuItem(label=t("edit_widgets"))
        ed.connect("activate", lambda *_: Gallery.instance and Gallery.instance.show_gallery())
        m.append(ed)
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
        if Gallery.editing():                   # macOS düzenleme modu: sol üstte "−" rozeti
            design.circle(cr, 6, 6, BADGE_R)
            cr.set_source_rgba(0.55, 0.55, 0.58, 0.96)
            cr.fill()
            cr.set_source_rgba(1, 1, 1, 1)
            cr.set_line_width(2)
            cr.move_to(1.5, 6)
            cr.line_to(10.5, 6)
            cr.stroke()
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
        W = self.W                                  # oranlar hedef görselden (PLAN.md, 24.10)
        design.soft_shadow(cr, 0, 0, W, self.H, R, strength=0.06, spread=8, dy=2)
        design.rrect(cr, 0, 0, W, self.H, R)
        cr.set_source_rgba(*design.paper(1))
        cr.fill()
        now = GLib.DateTime.new_now_local()
        y, mo, today = now.get_year(), now.get_month(), now.get_day_of_month()
        month = MONTHS_TR[mo - 1] if LANG == "tr" else now.format("%B").upper()
        x0, cw = W * 0.0765, W * 0.121
        text(cr, month, W * 0.110, W * 0.145, 7.6, "Bold", (*design.RED, 1), middle=True)
        days = DAYS_TR if LANG == "tr" else DAYS_EN
        for i, d in enumerate(days):
            col = design.ink(0.86 if i < 5 else 0.40)
            text(cr, d, x0 + cw * i + cw / 2, W * 0.259, 7.6, "Bold", col, "center", middle=True)
        cal = calendar.Calendar(firstweekday=0).monthdayscalendar(y, mo)
        first = W * 0.381
        step = min(W * 0.118, (W * 0.88 - first) / max(1, len(cal) - 1))   # 6 haftalık ayda sıkışır
        for r, week in enumerate(cal):
            for c, d in enumerate(week):
                if not d:
                    continue
                cx, cy = x0 + cw * c + cw / 2, first + r * step
                if d == today:
                    design.circle(cr, cx, cy, W * 0.056)
                    cr.set_source_rgba(*design.RED, 1)
                    cr.fill()
                    col = (1, 1, 1, 1)
                else:
                    col = design.ink(0.86 if c < 5 else 0.40)
                text(cr, str(d), cx, cy, 8.8, "Bold", col, "center", middle=True)


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
                            tint=design.glass_tint(0.30), dark=design.dark(), shadow=0.35, rim=0.35)
        cx, cy, rr = self.W / 2, self.H / 2, self.W * 0.44
        design.circle(cr, cx, cy, rr)
        cr.set_source_rgba(*design.paper(1))
        cr.fill()
        cr.set_line_cap(cairo.LINE_CAP_BUTT)
        for i in range(60):                               # saat çizgileri kalın siyah, dakikalar ince
            a = i * math.pi / 30
            hour = i % 5 == 0
            r0, r1 = rr * (0.975 - (0.09 if hour else 0.05)), rr * 0.975
            cr.move_to(cx + math.sin(a) * r0, cy - math.cos(a) * r0)
            cr.line_to(cx + math.sin(a) * r1, cy - math.cos(a) * r1)
            cr.set_source_rgba(*design.ink(0.90 if hour else 0.45))
            cr.set_line_width(1.7 if hour else 0.7)
            cr.stroke()
        for h in range(1, 13):                            # rakamlar
            a = h * math.pi / 6
            nx, ny = cx + math.sin(a) * rr * 0.68, cy - math.cos(a) * rr * 0.68
            text(cr, str(h), nx, ny, 13, "Bold", design.ink(0.92), "center", middle=True)
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
            hand(a, 9, 2.2, design.ink(0.95))
            cr.save()
            cr.translate(cx, cy)
            cr.rotate(a)
            design.rrect(cr, -2.6, -ln, 5.2, ln - 7, 2.6)
            cr.set_source_rgba(*design.ink(0.95))
            cr.fill()
            cr.restore()
        hand(sa, rr * 0.96, 1.1, (*design.ORANGE, 1), back=rr * 0.16)
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
        design.soft_shadow(cr, 0, 0, self.W, self.H, R, strength=0.06, spread=8, dy=2)
        cr.save()
        design.rrect(cr, 0, 0, self.W, self.H, R)
        cr.clip()
        if self.surface is not None:
            cr.set_source_surface(self.surface, 0, 0)
        else:
            cr.set_source_rgba(0.85, 0.85, 0.88, 1)
        cr.paint()
        cr.restore()

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


# ----------------------------- Widget galerisi -----------------------------
KINDS = (("calendar", "app_calendar", "x-office-calendar"), ("clock", "w_clock", "preferences-system-time"),
         ("photo", "w_photo", "image-x-generic"))
PREVIEW = 0.72                                    # galerideki canlı önizleme ölçeği
BADGE_R = 10                                      # düzenleme modundaki "−" rozeti


def _card(win, keep_above=True):
    """Liquid cam kart penceresi (DIALOG, kenarsız, saydam köşeli)."""
    from .applemenu import install_css, _card_bg
    from . import compositor
    win.set_name("lcard")
    compositor.mark(win)
    win.set_decorated(False)
    win.set_resizable(False)
    win.set_skip_taskbar_hint(True)
    win.set_skip_pager_hint(True)
    win.set_keep_above(keep_above)
    win.set_type_hint(Gdk.WindowTypeHint.DIALOG)
    win.set_app_paintable(True)
    vis = win.get_screen().get_rgba_visual()
    if vis:
        win.set_visual(vis)
    install_css("card", Gtk.STYLE_PROVIDER_PRIORITY_USER + 20)
    win.connect("draw", _card_bg)


def _present(win):
    win.show_all()
    win.set_keep_above(True)
    win.present()
    GLib.timeout_add(60, lambda: (win.get_window() and win.get_window().focus(Gdk.CURRENT_TIME), False)[1])


class Gallery(Gtk.Window):
    """macOS "Widget'ları Düzenle": ekranın altında ortada geniş cam sayfa. Canlı önizlemeye tıkla =
    masaüstüne ekle; açıkken masaüstündeki widget'ların köşesinde "−" rozeti (tıkla = kaldır)."""
    instance = None

    def __init__(self, classes, live):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        Gallery.instance = self
        self.classes, self.live = classes, live           # kind -> sınıf, kind -> açık pencere
        self.previews = {}                                 # açık olmayan türler için gizli örnek (önizleme)
        self.set_title("Liquid Widgets")
        _card(self)
        self.connect("key-press-event", lambda w, e: (e.keyval == Gdk.KEY_Escape and self.done(), False)[1])
        self.connect("hide", lambda *_: self._editing(False))
        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        for m in ("top", "bottom", "start", "end"):
            getattr(self.box, f"set_margin_{m}")(22)
        self.add(self.box)
        GLib.timeout_add(1000, lambda: (self.get_visible() and self.queue_draw(), True)[1])   # saat önizlemesi

    @staticmethod
    def editing():
        g = Gallery.instance
        return g is not None and g.get_visible()

    def _editing(self, on):
        for w in self.live.values():
            w.queue_draw()

    def _sample(self, kind):
        w = self.live.get(kind)
        if w is None:
            w = self.previews.get(kind) or self.previews.setdefault(kind, self.classes[kind]())
        return w

    def _preview(self, kind, k=PREVIEW):
        """Widget'ın canlı küçük kopyası (galeri, Bildirim Merkezi)."""
        w = self._sample(kind)
        da = Gtk.DrawingArea()
        da.set_size_request(round(w.W * k), round(w.H * k))

        def draw(_da, cr):
            cr.scale(k, k)
            self._sample(kind).paint(cr)
        da.connect("draw", draw)
        return da

    def _rebuild(self):
        for ch in self.box.get_children():
            self.box.remove(ch)
        title = Gtk.Label(label=t("widgets"), xalign=0)
        title.get_style_context().add_class("big")
        self.box.pack_start(title, False, False, 0)
        hint = Gtk.Label(label=t("add_hint"), xalign=0)
        hint.get_style_context().add_class("sub")
        self.box.pack_start(hint, False, False, 0)
        row = Gtk.Box(spacing=28)
        row.set_margin_top(14)
        cp = conf()
        for kind, label, _icon in KINDS:
            on = cp.get(kind, "hidden", fallback="0") != "1"
            col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            ev = Gtk.EventBox()
            ev.set_valign(Gtk.Align.END)
            ev.add(self._preview(kind))
            ev.set_opacity(0.45 if on else 1.0)
            if not on:
                ev.connect("button-release-event", lambda *_a, k=kind: (self._set(k, True), True)[1])
                ev.connect("realize", lambda e: e.get_window().set_cursor(
                    Gdk.Cursor.new_from_name(e.get_display(), "pointer")))
            col.pack_start(ev, True, True, 0)
            lb = Gtk.Label(label=t(label))
            lb.get_style_context().add_class("val")
            col.pack_start(lb, False, False, 0)
            sub = Gtk.Label(label=t("on_desktop") if on else "")
            sub.get_style_context().add_class("detail")
            col.pack_start(sub, False, False, 0)
            row.pack_start(col, False, False, 0)
        self.box.pack_start(row, False, False, 0)
        foot = Gtk.Box()
        done = Gtk.Button(label=t("done"))
        done.get_style_context().add_class("primary")
        done.set_size_request(96, -1)
        done.connect("clicked", lambda *_: self.done())
        foot.pack_end(done, False, False, 0)
        foot.set_margin_top(8)
        self.box.pack_start(foot, False, False, 0)
        self.box.show_all()

    def _set(self, kind, on):
        save(kind, hidden=0 if on else 1)
        w = self.live.get(kind)
        if on:
            if w is None:
                w = self.live[kind] = self.previews.pop(kind, None) or self.classes[kind]()
            w.show_all()
        elif w is not None:
            w.hide()
        if self.get_visible():
            self._rebuild()
            self._place()
        self._editing(True)

    def _place(self):
        mx, my, mw, mh = screen_geometry()
        w, h = self.get_preferred_size()[1].width, self.get_preferred_size()[1].height
        dock = design.DOCK_ICON + 2 * design.DOCK_PAD + design.DOCK_BOTTOM
        self.move(mx + (mw - w) // 2, my + mh - h - dock - 16)

    def show_gallery(self):
        self._rebuild()
        self._place()
        _present(self)
        self._editing(True)

    def done(self):
        self.hide()


# ----------------------------- Bildirim Merkezi -----------------------------
NOTIFY_DB = os.path.expanduser("~/.cache/xfce4/notifyd/log.sqlite")


def notifications(limit=12):
    """xfce4-notifyd geçmişi (salt okunur): (zaman, uygulama, simge, başlık, metin), yeniden eskiye."""
    import sqlite3
    try:
        db = sqlite3.connect(f"file:{NOTIFY_DB}?mode=ro", uri=True, timeout=0.5)
        rows = db.execute("SELECT timestamp, app_name, icon_id, summary, body FROM notifications "
                          "ORDER BY timestamp DESC LIMIT ?", (limit,)).fetchall()
        db.close()
        return rows
    except Exception:
        return []


def ago(ts):
    sec = ts / 1e6 if ts > 1e14 else ts / 1e3 if ts > 1e11 else ts     # notifyd: µs
    d = max(0, time.time() - sec)
    if d < 60:
        return t("now")
    if d < 3600:
        return f"{int(d // 60)} dk" if LANG == "tr" else f"{int(d // 60)}m"
    if d < 86400:
        return f"{int(d // 3600)} sa" if LANG == "tr" else f"{int(d // 3600)}h"
    return time.strftime("%d.%m", time.localtime(sec))


class NotificationCenter(Gtk.Window):
    """macOS: menü çubuğunda saate tıklayınca sağda açılan Bildirim Merkezi; en altta "Widget'ları Düzenle…"."""
    W = 356

    def __init__(self, gallery):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.gallery = gallery
        self.set_title("Liquid Notification Center")
        _card(self)
        self.connect("focus-out-event", lambda *_: (time.monotonic() - self._shown > 0.5 and self.hide(), False)[1])
        self.connect("key-press-event", lambda w, e: (e.keyval == Gdk.KEY_Escape and self.hide(), False)[1])
        self._shown = 0.0
        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        for m in ("top", "bottom", "start", "end"):
            getattr(self.box, f"set_margin_{m}")(12)
        self.add(self.box)
        GLib.timeout_add(1000, lambda: (self.get_visible() and self.queue_draw(), True)[1])   # saat widget'ı

    def _rebuild(self):
        from .applemenu import _icon
        for ch in self.box.get_children():
            self.box.remove(ch)
        rows = notifications()
        if not rows:
            e = Gtk.Label(label=t("no_notifications"))
            e.get_style_context().add_class("empty")
            e.set_margin_top(18)
            e.set_margin_bottom(18)
            self.box.pack_start(e, False, False, 0)
        for ts, app, icon, summary, body in rows:
            card = Gtk.Box(spacing=10)
            card.get_style_context().add_class("notif")
            img = _icon(icon or "dialog-information", 32) if icon and not os.path.isabs(icon) else \
                _icon("dialog-information", 32)
            img.set_valign(Gtk.Align.START)
            img.set_margin_start(12)
            img.set_margin_top(10)
            card.pack_start(img, False, False, 0)
            col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            col.set_margin_top(9)
            col.set_margin_bottom(10)
            col.set_margin_end(12)
            head = Gtk.Box()
            a = Gtk.Label(label=(app or "").upper(), xalign=0)
            a.get_style_context().add_class("app")
            head.pack_start(a, True, True, 0)
            tm = Gtk.Label(label=ago(ts))
            tm.get_style_context().add_class("app")
            head.pack_end(tm, False, False, 0)
            col.pack_start(head, False, False, 0)
            for txt, cls in ((summary, "val"), (body, "sub")):
                if txt:
                    lb = Gtk.Label(label=txt, xalign=0)
                    lb.set_line_wrap(True)
                    lb.set_max_width_chars(34)
                    lb.set_lines(3)
                    lb.set_ellipsize(Pango.EllipsizeMode.END)
                    lb.get_style_context().add_class(cls)
                    col.pack_start(lb, False, False, 0)
            card.pack_start(col, True, True, 0)
            self.box.pack_start(card, False, False, 0)
        # macOS: bildirimlerin altında widget'lar (küçükler yan yana, orta boy altta), panel genişliğine sığar
        k = (self.W - 24) / (2 * S + G)
        small = Gtk.Box(spacing=round(G * k))
        small.set_margin_top(6)
        for kind in ("calendar", "clock"):
            small.pack_start(self.gallery._preview(kind, k), False, False, 0)
        self.box.pack_start(small, False, False, 0)
        self.box.pack_start(self.gallery._preview("photo", k), False, False, round(G * k / 2 - 4))
        ed = Gtk.Button(label=t("edit_widgets"))
        ed.get_style_context().add_class("secondary")
        ed.set_halign(Gtk.Align.CENTER)
        ed.set_size_request(180, -1)
        ed.set_margin_top(4)
        ed.connect("clicked", lambda *_: (self.hide(), self.gallery.show_gallery()))
        self.box.pack_start(ed, False, False, 0)
        self.box.show_all()

    def toggle(self):
        if self.get_visible():
            self.hide()
            return
        self._rebuild()
        mx, my, mw, _ = screen_geometry()
        self.set_size_request(self.W, -1)
        self.move(mx + mw - self.W - 10, my + design.BAR_H + 6)
        self._shown = time.monotonic()
        _present(self)


def main():
    if not daemon.claim("widgets"):
        return
    restart_on_monitor_change()
    from .applemenu import install_css
    install_css("menu")
    cp = conf()
    classes = {c.kind: c for c in (CalendarWidget, ClockWidget, PhotoWidget)}
    live = {}
    for kind, cls in classes.items():
        if cp.get(kind, "hidden", fallback="0") != "1":
            live[kind] = cls()
            live[kind].show_all()
    # Görünür widget olmasa da süreç AYAKTA kalır (çıkarsa bekçi 5 sn'de bir yeniden başlatıyordu).
    # SIGUSR1 = menü çubuğunda saate tıklama → Bildirim Merkezi (altında "Widget'ları Düzenle…").
    gallery = Gallery(classes, live)
    center = NotificationCenter(gallery)
    design.on_theme_change(lambda: [w.queue_draw() for w in live.values()])
    daemon.on_signal(signal.SIGUSR1, center.toggle)
    daemon.on_signal(signal.SIGUSR2, gallery.show_gallery)     # masaüstü sağ tık → Widget'ları Düzenle…
    if "--show" in sys.argv:
        GLib.timeout_add(150, lambda: (gallery.show_gallery(), False)[1])
    Gtk.main()


if __name__ == "__main__":
    main()
