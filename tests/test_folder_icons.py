# SPDX-License-Identifier: GPL-3.0-only
"""The committed folder icon themes must match tools/folder_icons.py and be valid."""
import filecmp
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

from tools.folder_icons import ICONS, THEMES, build


class FolderIconTests(unittest.TestCase):
    def test_committed_icons_match_generator(self):
        with tempfile.TemporaryDirectory() as tmp:
            build(tmp)
            for name in THEMES:
                fresh, committed = Path(tmp) / name, ICONS / name
                for path in sorted(fresh.rglob("*")):
                    rel = path.relative_to(fresh)
                    other = committed / rel
                    self.assertTrue(other.is_symlink() or other.exists(), f"missing {name}/{rel}; run tools/folder_icons.py")
                    if path.is_symlink():
                        self.assertEqual(path.readlink(), other.readlink(), f"{name}/{rel}")
                    elif path.is_file():
                        self.assertTrue(filecmp.cmp(path, other, shallow=False), f"stale {name}/{rel}; run tools/folder_icons.py")

    def test_themes_are_valid(self):
        for name, parent in THEMES.items():
            theme = ICONS / name
            self.assertIn(f"Inherits={parent},hicolor", (theme / "index.theme").read_text(encoding="utf-8"))
            icons = list((theme / "places" / "scalable").glob("*.svg"))
            self.assertGreater(len(icons), 20)
            for icon in icons:
                self.assertTrue(icon.resolve().is_file(), f"broken link {icon}")
                self.assertTrue(ET.parse(icon).getroot().tag.endswith("svg"))
            self.assertTrue((theme / "places" / "scalable" / "inode-directory.svg").resolve().is_file())


if __name__ == "__main__":
    unittest.main()
