# SPDX-License-Identifier: GPL-3.0-only
"""Behavioral checks without a graphical session or changes to desktop settings."""
import contextlib
import io
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import cairo

from liquid import ctl, desktopmenu, firefox
from liquid.core import daemon, i18n
from liquid.core.power import estimate_text
from liquid.spotlight import calc, scan_files
from liquid.glyphs import Glyph, PEAR_ICON

ROOT = Path(__file__).resolve().parents[1]


class BrandingTests(unittest.TestCase):
    def test_pear_mask_draws_in_both_menu_colors(self):
        from types import SimpleNamespace
        icon = cairo.ImageSurface.create_from_png(PEAR_ICON)
        self.assertEqual((icon.get_width(), icon.get_height()), (100, 100))
        for light in (True, False):
            target = cairo.ImageSurface(cairo.FORMAT_ARGB32, 18, 24)
            widget = SimpleNamespace(kind='pear', _brand=icon,
                                     _fg=lambda a=1: (1, 1, 1, a) if light else (0, 0, 0, a))
            Glyph._paint(widget, cairo.Context(target), 18, 24, 12, None)
            target.flush()
            self.assertTrue(any(bytes(target.get_data())[3::4]))


class FirefoxRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.profile = Path(self.temp.name) / "profile"
        self.profile.mkdir()
        self.state = Path(self.temp.name) / "state.json"
        self.patches = [patch.object(firefox, "STATE", self.state),
                        patch.object(firefox, "default_profile", return_value=self.profile)]
        for item in self.patches:
            item.start()
            self.addCleanup(item.stop)

    def install(self):
        with contextlib.redirect_stdout(io.StringIO()):
            firefox.install()

    def test_repeated_install_keeps_original_styles_and_preferences(self):
        chrome = self.profile / "chrome"
        chrome.mkdir()
        css = chrome / "userChrome.css"
        css.write_text('/* my CSS */\n')
        asset = chrome / "liquid-titlebar.css"
        asset.write_text('/* previous asset */\n')
        userjs = self.profile / "user.js"
        userjs.write_text('user_pref("custom.setting", true);\n')
        (self.profile / "prefs.js").write_text(f'user_pref("{firefox.PREF}", 0);\n')
        self.install()
        self.install()
        self.assertEqual(css.read_text().count(firefox.IMPORT), 1)
        self.assertEqual(userjs.read_text().count(firefox.BLOCK), 1)
        firefox.remove()
        self.assertEqual(css.read_text(), '/* my CSS */\n')
        self.assertEqual(asset.read_text(), '/* previous asset */\n')
        self.assertIn('user_pref("custom.setting", true);', userjs.read_text())
        self.assertIn(f'user_pref("{firefox.PREF}", 0);', userjs.read_text())
        self.assertFalse(self.state.exists())

    def test_later_user_changes_survive_removal(self):
        self.install()
        userjs = self.profile / "user.js"
        later = f'user_pref("{firefox.PREF}", 0);\nuser_pref("{firefox.STYLE_PREF}", false);\n'
        userjs.write_text(userjs.read_text() + later)
        asset = self.profile / "chrome/liquid-titlebar.css"
        asset.write_text('/* edited by user */')
        firefox.remove()
        self.assertEqual(asset.read_text(), '/* edited by user */')
        self.assertEqual(userjs.read_text(), later)
        self.assertFalse((self.profile / "chrome/userChrome.css").exists())

    def test_missing_profile_is_a_noop(self):
        with patch.object(firefox, "default_profile", return_value=None):
            self.install()
        self.assertFalse(self.state.exists())


class CommandTests(unittest.TestCase):
    def test_unknown_component_cannot_start_arbitrary_module(self):
        with patch('sys.argv', ['liquid', 'toggle', '../../untrusted']), \
                patch.object(daemon, 'signal_component') as signal_component, \
                contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as error:
                ctl.main()
        self.assertEqual(error.exception.code, 2)
        signal_component.assert_not_called()

    def test_toggle_routes_known_component(self):
        with patch('sys.argv', ['liquid', 'toggle', 'launcher']), \
                patch.object(daemon, 'signal_component') as signal_component:
            ctl.main()
        signal_component.assert_called_once_with('launcher')

    def test_invalid_app_action_is_rejected(self):
        with patch('sys.argv', ['liquid', 'app', 'oops']), \
                patch.object(ctl, 'app_action') as action, \
                contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as error:
                ctl.main()
        self.assertEqual(error.exception.code, 2)
        action.assert_not_called()

    def test_script_help_and_unknown_options_have_no_side_effects(self):
        with tempfile.TemporaryDirectory() as directory:
            env = dict(os.environ, HOME=directory)
            for script in ('install.sh', 'uninstall.sh'):
                for flag, expected in (('--help', 0), ('--unknown-option', 2)):
                    result = subprocess.run(['bash', str(ROOT / script), flag], env=env,
                                            capture_output=True, text=True)
                    self.assertEqual(result.returncode, expected, result.stderr)
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_stale_pid_does_not_match_an_unrelated_process(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(daemon, 'RUN', directory):
            (Path(directory) / 'bar.pid').write_text('12345')
            with patch.object(daemon, '_cmdline', return_value='python3 -m unrelated.bar'):
                self.assertIsNone(daemon.running('bar'))
            with patch.object(daemon, '_cmdline', return_value='python3 -m liquid.bar'):
                self.assertEqual(daemon.running('bar'), 12345)


class SearchAndLocaleTests(unittest.TestCase):
    def test_calculator_arithmetic_and_decimal_comma(self):
        with patch.dict(os.environ, LANG='en_US.UTF-8'):
            self.assertEqual(calc('3,5*2'), '7')
            self.assertEqual(calc('(12+3)/2'), '7.5')
            self.assertEqual(calc('2^10'), '1024')
            self.assertIsNotNone(calc('9^999'))

    def test_calculator_rejects_code_and_invalid_arithmetic(self):
        for expression in ('__import__("os")', '1/0', '9^9^9', '2+', 'hello'):
            self.assertIsNone(calc(expression), expression)

    def test_turkish_case_folding(self):
        for word in ('İSTANBUL', 'Istanbul', 'ıstanbul', 'istanbul'):
            self.assertEqual(i18n.fold(word), 'istanbul')

    def test_gettext_locale_precedence(self):
        with patch.dict(os.environ, {'LC_ALL': 'C', 'LANGUAGE': 'tr', 'LANG': 'tr_TR.UTF-8'}, clear=True):
            self.assertEqual(i18n._lang(), 'en')
        with patch.dict(os.environ, {'LANGUAGE': 'tr:en', 'LANG': 'en_US.UTF-8'}, clear=True):
            self.assertEqual(i18n._lang(), 'tr')

    def test_file_scan_ignores_hidden_dependencies_and_symlink_recursion(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'visible.txt').touch()
            for name in ('.private', 'node_modules'):
                (root / name).mkdir()
                (root / name / 'secret.txt').touch()
            (root / 'loop').symlink_to(root, target_is_directory=True)
            results = scan_files(directory)
            self.assertIn(str(root / 'visible.txt'), [row[1] for row in results])
            self.assertNotIn('secret.txt', [row[0] for row in results])
            self.assertFalse(next(row[2] for row in results if row[0] == 'loop'))

    def test_power_estimates_cover_full_and_unavailable_states(self):
        self.assertEqual(estimate_text(4), i18n.t('battery_full'))
        self.assertEqual(estimate_text(2), i18n.t('battery_time_unavailable'))
        self.assertEqual(estimate_text(2, empty=3600),
                         i18n.t('battery_time_left').format(i18n.t('battery_hours').format(1)))


class DesktopMenuTests(unittest.TestCase):
    def test_install_remove_preserves_other_thunar_actions(self):
        with tempfile.TemporaryDirectory() as directory:
            uca = Path(directory) / 'uca.xml'
            original = '<actions>\n<action><unique-id>mine</unique-id></action>\n</actions>\n'
            uca.write_text(original)
            with patch.object(desktopmenu, 'UCA', str(uca)), \
                    patch.object(desktopmenu, '_desktop_name', return_value='Desktop'), \
                    patch.object(daemon, 'ROOT', '/tmp/a project'):
                desktopmenu.install()
                desktopmenu.install()
                self.assertEqual(uca.read_text().count(desktopmenu.UID), 1)
                self.assertIn("'/tmp/a project/bin/liquid'", uca.read_text())
                desktopmenu.remove()
                self.assertEqual(uca.read_text(), original)


class UninstallRecoveryTests(unittest.TestCase):
    def run_uninstall(self, fail=False, current='Liquid'):
        """Run a copied uninstaller against stub commands, never the real session."""
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        project = root / 'project with spaces'
        commands = root / 'commands'
        home = root / 'home'
        for directory in (project / 'bin', commands, home):
            directory.mkdir(parents=True)
        shutil.copy2(ROOT / 'uninstall.sh', project / 'uninstall.sh')
        for name in ('python3', 'sleep', 'pgrep'):
            path = commands / name
            path.write_text('#!/bin/sh\nexit 0\n')
            path.chmod(0o755)
        (commands / 'id').write_text('#!/bin/sh\necho 1000\n')
        (commands / 'id').chmod(0o755)
        cli = project / 'bin/liquid'
        cli.write_text('#!/bin/sh\nexit 0\n')
        cli.chmod(0o755)
        xfconf = commands / 'xfconf-query'
        xfconf.write_text('''#!/bin/sh
for argument in "$@"; do
  if [ "$argument" = --create ]; then
    printf '%s\\n' "$@" >> "$HOME/restore-arguments"
    exit "$RESTORE_FAIL"
  fi
done
printf '%s\\n' "$CURRENT_VALUE"
''')
        xfconf.chmod(0o755)
        backup = home / '.local/share/liquid/backups/values.tsv'
        backup.parent.mkdir(parents=True)
        # Empty original value must not collapse TSV columns during read.
        backup.write_text('xsettings\t/Net/ThemeName\tstring\t\tLiquid\n')
        env = dict(os.environ, HOME=str(home), PATH=str(commands) + ':/usr/bin:/bin',
                   RESTORE_FAIL='1' if fail else '0', CURRENT_VALUE=current)
        result = subprocess.run(['bash', str(project / 'uninstall.sh')], env=env,
                                capture_output=True, text=True)
        return result, home, backup

    def test_restore_preserves_empty_original_value(self):
        result, home, backup = self.run_uninstall()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(backup.exists())
        self.assertIn('-s\n\n--create\n', (home / 'restore-arguments').read_text())
        self.assertEqual(len(list(backup.parent.glob('values.tsv.restored-*'))), 1)

    def test_restore_failure_keeps_recovery_file(self):
        result, home, backup = self.run_uninstall(fail=True)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertTrue(backup.exists())

    def test_user_changed_setting_is_not_overwritten(self):
        result, home, backup = self.run_uninstall(current='My new theme')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((home / 'restore-arguments').exists())


if __name__ == '__main__':
    unittest.main()
