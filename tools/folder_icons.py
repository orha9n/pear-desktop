# SPDX-License-Identifier: GPL-3.0-only
"""macOS (Big Sur / Tahoe) tarzı klasör simgeleri: assets/icons/MacTahoe-Folders{,-dark}.

Klasör simgelerini çizer, geri kalan her şeyi MacTahoe / MacTahoe-dark temasından devralır.
Yeniden üretmek için: python3 tools/folder_icons.py   (çıktı depoya commit edilir)"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ICONS = ROOT / "assets" / "icons"
# tema adı -> devraldığı MacTahoe varyantı (Karanlık Mod MacTahoe-dark'a geçer)
THEMES = {"MacTahoe-Folders": "MacTahoe", "MacTahoe-Folders-dark": "MacTahoe-dark"}

DEFS = """<defs>
  <linearGradient id="back" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#4CA8EE"/><stop offset="1" stop-color="#2F8FE0"/>
  </linearGradient>
  <linearGradient id="front" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#86CDFB"/><stop offset="1" stop-color="#5BB4F5"/>
  </linearGradient>
  <linearGradient id="paper" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#FFFFFF"/><stop offset="1" stop-color="#E9F1F8"/>
  </linearGradient>
  <filter id="sh" x="-10%" y="-10%" width="120%" height="130%">
    <feGaussianBlur in="SourceAlpha" stdDeviation="3"/>
    <feOffset dy="3"/>
    <feComponentTransfer><feFuncA type="linear" slope="0.28"/></feComponentTransfer>
    <feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
</defs>"""

# Arka kapak (sol ustte sekmeli)
BACK = ('<path fill="url(#back)" d="M38 40h50c6 0 9 2 12 6l6 8c3 4 6 6 12 6h100'
        'c10 0 18 8 18 18v116c0 10-8 18-18 18H38c-10 0-18-8-18-18V58c0-10 8-18 18-18z"/>')
PAPER = '<rect x="32" y="70" width="192" height="100" rx="8" fill="url(#paper)"/>'
FRONT = ('<rect x="20" y="82" width="216" height="134" rx="16" fill="url(#front)"/>'
         '<path d="M36 82.8h184c8 0 14.6 6 15.6 13.6" fill="none" stroke="#B9E3FE" stroke-width="1.6" stroke-linecap="round"/>'
         '<path d="M20.4 96.4C21.4 88.8 28 82.8 36 82.8" fill="none" stroke="#B9E3FE" stroke-width="1.6" stroke-linecap="round"/>')
# Acik klasor: on kapak egik
FRONT_OPEN = ('<path fill="url(#front)" d="M30 98h204c9 0 15 8 13 16l-18 90c-2 8-8 12-16 12H40'
              'c-8 0-14-4-16-12L17 114c-2-8 4-16 13-16z"/>'
              '<path d="M30 98.8h204" stroke="#B9E3FE" stroke-width="1.6" stroke-linecap="round"/>')

# On yuzde kabartma (Apple gibi koyu mavi, hafif gomulu) semboller; merkez ~ (128,150)
G = "#2C86D3"
GLYPHS = {
    "documents": f'<path fill="{G}" d="M108 118h28l16 16v38c0 3-2 5-5 5h-39c-3 0-5-2-5-5v-49c0-3 2-5 5-5z"/>'
                 '<path fill="#86CDFB" opacity=".55" d="M136 118v13c0 2 1 3 3 3h13z"/>'
                 '<rect x="113" y="145" width="30" height="4" rx="2" fill="#7FC4F7"/>'
                 '<rect x="113" y="155" width="30" height="4" rx="2" fill="#7FC4F7"/>'
                 '<rect x="113" y="165" width="20" height="4" rx="2" fill="#7FC4F7"/>',
    "download": f'<circle cx="128" cy="149" r="30" fill="none" stroke="{G}" stroke-width="7"/>'
                f'<path d="M128 133v28M116 151l12 12 12-12" fill="none" stroke="{G}" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/>',
    "pictures": f'<rect x="98" y="124" width="60" height="48" rx="7" fill="none" stroke="{G}" stroke-width="6"/>'
                f'<circle cx="114" cy="139" r="5.5" fill="{G}"/>'
                f'<path fill="{G}" d="M102 168l18-20 10 11 10-14 15 23z"/>',
    "music": f'<path fill="{G}" d="M120 125l32-8v40a10 8 0 1 1-6-7.3V131l-20 5v29a10 8 0 1 1-6-7.3z"/>',
    "videos": f'<rect x="98" y="126" width="60" height="44" rx="7" fill="none" stroke="{G}" stroke-width="6"/>'
              f'<path fill="{G}" d="M120 136v24l20-12z"/>',
    "desktop": f'<rect x="96" y="122" width="64" height="42" rx="6" fill="none" stroke="{G}" stroke-width="6"/>'
               f'<path d="M118 177h20M128 166v10" stroke="{G}" stroke-width="6" stroke-linecap="round"/>',
    "home": f'<path fill="none" stroke="{G}" stroke-width="7" stroke-linejoin="round" stroke-linecap="round" d="M100 148l28-24 28 24M108 141v32h40v-32"/>'
            f'<rect x="121" y="155" width="14" height="18" rx="2" fill="{G}"/>',
    "templates": f'<g fill="{G}"><rect x="102" y="124" width="22" height="22" rx="4"/><rect x="132" y="124" width="22" height="22" rx="4"/>'
                 '<rect x="102" y="152" width="22" height="22" rx="4"/><rect x="132" y="152" width="22" height="22" rx="4"/></g>',
    "public": f'<circle cx="128" cy="134" r="11" fill="{G}"/><path fill="{G}" d="M104 174c0-15 11-24 24-24s24 9 24 24z"/>',
    "code": f'<path d="M114 133l-16 16 16 16M142 133l16 16-16 16M134 127l-12 44" fill="none" stroke="{G}" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/>',
    "games": f'<path fill="{G}" d="M106 134h44c10 0 16 8 17 18l2 12c1 8-8 12-14 6l-8-8h-38l-8 8c-6 6-15 2-14-6l2-12c1-10 7-18 17-18z"/>'
             '<path d="M112 143v12M106 149h12" stroke="#7FC4F7" stroke-width="4" stroke-linecap="round"/>'
             '<circle cx="146" cy="145" r="3.5" fill="#7FC4F7"/><circle cx="153" cy="152" r="3.5" fill="#7FC4F7"/>',
}


def svg(body):
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256" viewBox="0 0 256 256">'
            + DEFS + '<g filter="url(#sh)">' + body + '</g></svg>\n')


BASE = BACK + PAPER + FRONT
ICONS_SVG = {"folder": BASE, "folder-open": BACK + PAPER + FRONT_OPEN,
             "folder-drag-accept": BACK + PAPER + FRONT_OPEN}
ICONS_SVG.update({"folder-" + k: BASE + g for k, g in GLYPHS.items()})

# Eşdeğer adlar (aynı klasördeki dosyaya göreli sembolik bağ)
ALIASES = {
    "folder": ["inode-directory", "default-folder", "folder-blue", "blue-folder", "folder-new"],
    "folder-open": ["inode-directory-open", "folder-visiting"],
    "folder-documents": ["folder-document", "default-folder-documents"],
    "folder-download": ["folder-downloads", "default-folder-download"],
    "folder-pictures": ["folder-images", "folder-image", "default-folder-pictures"],
    "folder-music": ["folder-sound", "default-folder-music"],
    "folder-videos": ["folder-video", "default-folder-videos"],
    "folder-desktop": ["user-desktop", "desktop"],
    "folder-home": ["user-home", "default-folder-home"],
    "folder-templates": ["folder-template", "default-folder-templates"],
    "folder-public": ["folder-publicshare", "default-folder-public"],
    "folder-code": ["folder-development", "folder-projects"],
}

INDEX = """[Icon Theme]
Name={name}
Comment=Pear: macOS-style folders on top of {parent}
Inherits={parent},hicolor
Directories=places/scalable

[places/scalable]
Context=Places
Size=256
MinSize=16
MaxSize=512
Type=Scalable
"""


def build(icons=ICONS):
    for name, parent in THEMES.items():
        theme = Path(icons) / name
        out = theme / "places" / "scalable"
        out.mkdir(parents=True, exist_ok=True)
        (theme / "index.theme").write_text(INDEX.format(name=name, parent=parent), encoding="utf-8")
        for icon, body in ICONS_SVG.items():
            (out / f"{icon}.svg").write_text(svg(body), encoding="utf-8")
        for target, names in ALIASES.items():
            for alias in names:
                link = out / f"{alias}.svg"
                if link.is_symlink() or link.exists():
                    link.unlink()
                os.symlink(f"{target}.svg", link)
    return [Path(icons) / name for name in THEMES]


if __name__ == "__main__":
    for path in build():
        print("✓", path.relative_to(ROOT))
