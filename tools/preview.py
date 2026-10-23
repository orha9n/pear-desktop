"""Geliştirme önizlemesi: bir bileşeni MacTahoe ikonlarıyla (sadece bu süreçte) çalıştırır.
Kullanım: python3 tools/preview.py dock|bar|widgets|launcher [saniye]"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gi  # noqa: E402
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib  # noqa: E402

name = sys.argv[1]
secs = float(sys.argv[2]) if len(sys.argv) > 2 else 8
Gtk.Settings.get_default().set_property("gtk-icon-theme-name", "MacTahoe")
mod = __import__(f"liquid.{name}", fromlist=["main"])
GLib.timeout_add(int(secs * 1000), Gtk.main_quit)
os.environ["LIQUID_PREVIEW"] = "1"
mod.main()
