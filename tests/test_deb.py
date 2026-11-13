# SPDX-License-Identifier: GPL-3.0-only
"""Validate the actual .deb payload without installing into the developer's OS."""
import hashlib
import io
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile
import unittest

from tools.build_deb import build, ROOT


@unittest.skipUnless(shutil.which("dpkg-deb"), "dpkg-deb is unavailable")
class DebianPackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.directory = Path(cls.temp.name)
        cls.deb = build(cls.directory / "output")
        subprocess.run(["dpkg-deb", "--raw-extract", str(cls.deb), str(cls.directory / "extracted")], check=True)
        cls.extracted = cls.directory / "extracted"

    def test_filename_matches_github_release_asset(self):
        self.assertEqual(self.deb.name, "pear-desktop_0.1.0.alpha1_all.deb")
        version = subprocess.check_output(["dpkg-deb", "--field", str(self.deb), "Version"], text=True).strip()
        self.assertEqual(version, "0.1.0~alpha1")

    def test_dependency_metadata_covers_every_installer_package(self):
        dependencies = subprocess.check_output(["dpkg-deb", "--field", str(self.deb), "Depends"], text=True)
        names = {item.strip().split()[0] for item in dependencies.split(',')}
        installer = (ROOT / "install.sh").read_text()
        required = set(re.search(r'PKGS="([^"]+)"', installer).group(1).split())
        self.assertFalse(required - names, required - names)
        self.assertFalse({"git", "libxml2-utils"} & names)
        self.assertEqual(subprocess.check_output(["dpkg-deb", "--field", str(self.deb), "Architecture"], text=True).strip(), 'all')

    def test_payload_excludes_developer_state_and_has_root_ownership(self):
        data = subprocess.check_output(["dpkg-deb", "--fsys-tarfile", str(self.deb)])
        with tarfile.open(fileobj=io.BytesIO(data)) as archive:
            for member in archive.getmembers():
                self.assertEqual((member.uid, member.gid), (0, 0))
                self.assertFalse({'.git', 'backup', '__pycache__', '.env', 'dist'} & set(Path(member.name).parts))
        for path in ('usr/share/pear/assets/branding/pear.png', 'usr/share/pear/LICENSE',
                     'usr/share/pear/assets/tray/CREDITS.md', 'usr/share/doc/pear-desktop/copyright'):
            self.assertTrue((self.extracted / path).is_file(), path)

    def test_payload_checksums_and_executable_modes(self):
        for line in (self.extracted / 'DEBIAN/md5sums').read_text().splitlines():
            expected, path = line.split('  ', 1)
            self.assertEqual(hashlib.md5((self.extracted / path).read_bytes()).hexdigest(), expected)
        for path in ('usr/bin/pear', 'usr/bin/pear-setup', 'usr/bin/pear-reset',
                     'usr/share/pear/bin/pear', 'usr/share/pear/install.sh', 'DEBIAN/prerm'):
            self.assertEqual((self.extracted / path).stat().st_mode & 0o777, 0o755)
            subprocess.run(['sh' if path != 'usr/share/pear/install.sh' else 'bash', '-n', str(self.extracted / path)], check=True)
        self.assertFalse((self.extracted / 'DEBIAN/postinst').exists())

    def test_extracted_cli_help_works_without_source_checkout_or_display(self):
        env = dict(os.environ, HOME=str(self.directory / 'home'), PYTHONDONTWRITEBYTECODE='1')
        env.pop('DISPLAY', None)
        env.pop('WAYLAND_DISPLAY', None)
        result = subprocess.run([str(self.extracted / 'usr/share/pear/bin/pear'), '--help'],
                                cwd=self.directory, env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('compositor', result.stdout)
        self.assertFalse(Path(env['HOME']).exists())

    def test_menu_entry_is_valid(self):
        if not shutil.which('desktop-file-validate'):
            self.skipTest('desktop-file-validate is unavailable')
        subprocess.run(['desktop-file-validate', str(self.extracted / 'usr/share/applications/pear-desktop.desktop')], check=True)

    def test_invalid_metadata_is_rejected(self):
        with self.assertRaises(ValueError):
            build(self.directory / 'bad', version='1\nDepends: bad')
        with self.assertRaises(ValueError):
            build(self.directory / 'bad', maintainer='Name\nInvalid: field')
        self.assertFalse((self.directory / 'bad').exists())
