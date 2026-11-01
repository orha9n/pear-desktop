# SPDX-License-Identifier: GPL-3.0-only
"""Pear — masaüstü sağ tık menüsüne "Widget'ları Düzenle…" (macOS Sonoma+).

xfdesktop'un masaüstü menüsü Thunar'ın özel eylemlerini (~/.config/Thunar/uca.xml) de gösterir; boş alana
sağ tıklayınca dosya bilgisi masaüstü klasörünün kendisidir. Eylem yalnız o klasörün adıyla eşleşir.
Kullanıcının kendi eylemlerine dokunulmaz: bizimki unique-id ile eklenir/silinir, dosyanın geri kalanı aynen kalır.

  python3 -m liquid.desktopmenu install|remove
"""
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
from xml.sax.saxutils import escape

from .core import daemon
from .core.i18n import t

UCA = os.path.expanduser("~/.config/Thunar/uca.xml")
UID = "liquid-edit-widgets"
EMPTY = '<?xml version="1.0" encoding="UTF-8"?>\n<actions>\n</actions>\n'


def _desktop_name():
    try:
        d = subprocess.run(["xdg-user-dir", "DESKTOP"], capture_output=True, text=True).stdout.strip()
    except Exception:
        d = ""
    return os.path.basename(d.rstrip("/")) or "Desktop"


def _block():
    cmd = shlex.quote(os.path.join(daemon.ROOT, "bin", "liquid")).replace("%", "%%") + " widgets edit"
    return (f"<action>\n\t<icon>preferences-desktop</icon>\n\t<name>{escape(t('edit_widgets'))}</name>\n"
            f"\t<submenu></submenu>\n\t<unique-id>{UID}</unique-id>\n\t<command>{escape(cmd)}</command>\n"
            f"\t<description>Liquid</description>\n\t<range></range>\n"
            f"\t<patterns>{escape(_desktop_name())}</patterns>\n\t<directories/>\n</action>\n")


def _strip(xml):
    return re.sub(r"<action>(?:(?!</action>).)*?<unique-id>" + UID + r"</unique-id>.*?</action>\n?", "",
                  xml, flags=re.S)


def install():
    xml = Path(UCA).read_text() if os.path.exists(UCA) else EMPTY
    xml = _strip(xml).replace("</actions>", _block() + "</actions>", 1)
    os.makedirs(os.path.dirname(UCA), exist_ok=True)
    with open(UCA + ".tmp", "w") as f:
        f.write(xml)
    os.replace(UCA + ".tmp", UCA)


def remove():
    if os.path.exists(UCA):
        xml = Path(UCA).read_text()
        new = _strip(xml)
        if new != xml:
            with open(UCA + ".tmp", "w") as f:
                f.write(new)
            os.replace(UCA + ".tmp", UCA)


if __name__ == "__main__":
    {"install": install, "remove": remove}[sys.argv[1] if len(sys.argv) > 1 else "install"]()
