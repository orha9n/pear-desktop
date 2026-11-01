# Contributing to Pear

Develop on Linux Mint Xfce with X11. Keep changes focused and explain the behavior
being changed. System libraries are installed through apt by `install.sh`; avoid
adding pip substitutes for distribution-provided GTK bindings.

## Checks

```bash
./tools/check.sh
```

The check script validates Python and shell syntax and runs regression tests with
an isolated HOME and runtime directory. It does not run installation or interact
with your desktop. GitHub Actions runs the same command.

With `dpkg-deb` available, the checks also build and extract a temporary `.deb`,
verify dependencies, ownership, file checksums, executable permissions and the
packaged CLI. Build the distributable with `python3 tools/build_deb.py`.
Package metadata and the menu entry are in `packaging/debian/`. Do not apply
per-user desktop settings from package maintainer scripts running as root.

For a visible component preview in a development desktop session:

```bash
python3 tools/preview.py launcher 8
```

Previews create real windows and can write Pear settings. Use a disposable user
or VM for installation, compositor, panel, shortcut and uninstall changes.

## Desktop smoke checks

Before a release, use a fresh Linux Mint Xfce VM and verify:

1. Installation, logout/login, autostart and `bin/liquid status`.
2. Menu exports and fallback menus; application launch, close and dock pinning.
3. Search, calculations, widgets, notification history and Control Center.
4. Fullscreen entry/exit, dark mode and picom/xfwm switching.
5. A second installation preserves the original recovery values.
6. Uninstall restores the original desktop and preserves later user changes.
7. Clone paths with spaces and monitor hotplug; record any hardware limitations.

Automated checks do not replace these graphical checks. Never invoke install or
uninstall in CI against a developer's real session.

## Issues and pull requests

For bugs, include your Mint/Xfce versions, Python and picom versions, X11 session,
reproduction steps and relevant logs from `~/.cache/liquid/`. Review logs and
screenshots for personal information before attaching them. Do not attach browser
profiles, recovery files, credentials or complete home-directory dumps.

Keep `Wnck.Window` references transient: retain XIDs and resolve them when needed.
Use argument lists for subprocesses and keep blocking system queries off GTK's
main loop. Preserve existing user settings and backups in installation changes.

Keep UI strings in `liquid/core/i18n.py`, update both languages, and document new
dependencies and user-visible changes. Include attribution for every third-party
asset. Contributions are submitted under the project's GPL-3.0-only license;
third-party material must retain its applicable license notices.
