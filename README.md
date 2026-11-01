# Pear

<img src="assets/branding/pear.png" alt="Pear pear logo" width="72" height="72">

A macOS-inspired desktop interface for **Linux Mint Xfce on X11**, written in
Python 3, GTK 3 and cairo. Pear provides a transparent menu bar, a glass dock,
desktop widgets, an application launcher, Spotlight-style search and Control Center.

**Status: experimental.** This is a desktop customization application, not a Linux
distribution or a replacement window manager. Other desktops and Wayland are not
supported. [Türkçe belge](docs/README.tr.md).

## Features

- Menu bar with application menus, an XApp system tray, battery estimates and Wi-Fi/VPN controls.
- Dock with pinned and running applications, drag ordering and window actions.
- Calendar, analog clock and photo widgets, a widget gallery and notification history.
- Application launcher and search for applications, local file names, calculations and the web.
- Control Center for audio, brightness, dark mode, Bluetooth, media playback and notifications.
- Fullscreen window controls, optional picom blur and Turkish/English UI text.

## Requirements

- Linux Mint Xfce, an active **X11** graphical session and a regular user account.
- Network access for apt packages and the external themes on GitHub.
- `sudo` access to install system packages, the GTK theme and wallpaper.

The installer checks the required apt packages, including PyGObject, cairo, Pillow,
GTK 3, libwnck, dbusmenu, XApp, NetworkManager and picom. These are system packages;
there is no pip dependency installation. Optional applications such as a music
player or calendar must be installed separately.

## Install the Debian test package

On a Debian/Ubuntu-based Xfce system, open a terminal in the directory containing
the downloaded `.deb` and run:

```bash
sudo apt install ./pear-desktop_0.1.0~alpha1_all.deb
pear-setup
```

Run `pear-setup` as your normal user inside an **Xfce X11** session, or select
**Pear Setup** in the applications menu. Initial setup needs internet to download
the pinned themes and may request sudo. Log out and back in afterward. The package
installs the app in `/usr/share/pear` and provides `pear`, `pear-setup` and
`pear-reset` commands. Installing the package itself does not change your desktop.

Restore the desktop before removing the package:

```bash
pear-reset
sudo apt remove pear-desktop
```

This is an alpha test package. Linux Mint Xfce is the development target; other
Debian/Ubuntu-based systems still need graphical testing. It is not a package for
Fedora, Arch, other desktops or Wayland. Package removal does not restore user
settings automatically. Package details: [README.Debian](packaging/debian/README.Debian).

Build a `.deb` from this checkout without root:

```bash
python3 tools/build_deb.py
```

The output goes to `dist/`, with a SHA-256 checksum. Public release builds should
provide `--maintainer 'Your Name <your-public-email>'`; local test builds use a
reserved `example.invalid` address. CI also builds the package as a downloadable artifact.

## Install from source

Clone this repository using its GitHub **Code** button, or download and extract a
source archive. In the extracted project directory, run:

```bash
./install.sh
```

Run it as your normal user; it requests sudo when needed. Read the script before
running it: it installs external themes and changes your desktop settings.
Log out and back in once after installation to enable application menu exports.
Keep the project directory in place: autostart and keyboard shortcuts use its path.
If you move it, run the installer again from the new location.

```bash
./install.sh --no-apt              # require all packages to be installed already
LIQUID_NO_PICOM=1 ./install.sh      # use xfwm4 compositing instead of enabling picom
./install.sh --help
```

Theme downloads use pinned Git revisions listed in [THIRD_PARTY.md](THIRD_PARTY.md).
`--no-apt` still downloads themes when needed and may request sudo for them.

## What installation changes

The installer configures XFCE themes, icons, cursors, fonts, titlebar buttons,
wallpaper, notifications and six keyboard shortcuts. It adds a marked block to
`~/.xprofile`, an autostart entry and a Thunar widget action. While Pear runs,
the session supervisor closes the XFCE panel and maintains its own components.

GTK 4 styles are installed into `~/.config/gtk-4.0` with a backup. If a supported
Firefox default profile exists, Pear adds marked `user.js` preferences and a
separate stylesheet imported by `userChrome.css`. Existing CSS is preserved;
Firefox picks up these changes at its next start.

Recovery files live outside the repository in `~/.local/share/liquid/backups/`.
The legacy `~/.local/share/liquid/values.tsv` copy remains supported. Firefox and
compositor state are stored in `~/.config/liquid/`.
The internal Python module and existing state directory names remain `liquid`
for compatibility with earlier installations; the application is named Pear.

## Uninstall

From the project directory, run:

```bash
./uninstall.sh
./uninstall.sh --themes           # also remove user icon/cursor themes and wallpaper
```

Uninstall stops Pear, restores recorded XFCE settings when their current values
still match Pear's values, removes its autostart/profile/menu entries, restores
the saved GTK 4 styles and reopens the XFCE panel. Firefox preferences are restored
through `user.js` on the next browser start. Theme packages and apt dependencies
remain installed. `--themes` removes the named user icon/cursor directories, even
if they existed before Pear; system GTK themes remain installed.

Keep your recovery files until you have finished uninstalling. A partial or failed
installation can be reversed using the same uninstall script.

## Usage

| Shortcut or action | Result |
| --- | --- |
| Super+Space | Toggle search |
| Ctrl+Super+F | Toggle Pear fullscreen for the active window |
| Super+Q / Super+H / Alt+Super+H / Super+M | Quit / hide / hide others / minimize |
| Menu bar clock | Notification Center and widget controls |
| Desktop context menu | Edit widgets |
| Dock right click | Window actions and pinning |

```bash
bin/pear --help
bin/pear status
bin/pear start
bin/pear stop
bin/pear toggle spotlight
bin/pear toggle launcher
bin/pear toggle controlcenter
bin/pear widgets edit
bin/pear fullscreen
bin/pear compositor             # show compositor status
bin/pear compositor xfwm        # restore xfwm4 compositing
bin/pear compositor picom       # enable picom blur
```

Dock settings are in `~/.config/liquid/dock.ini` (`items`, `icon_size`, `magnify`);
widget settings are in `~/.config/liquid/widgets.ini`. The default dock includes
only applications installed on the system. Some application labels intentionally
follow the macOS-inspired appearance; the file manager remains Thunar.

## Troubleshooting and limitations

- Logs: `~/.cache/liquid/<component>.log`; supervisor events: `session.log`;
  compositor output: `picom.log`. Component logs rotate when restarted above 512 KB.
- Menus require applications to export GTK GMenuModel or dbusmenu data. Some
  GTK 4, Firefox and Electron applications use generic fallback menus.
- Components are displayed on the primary monitor. A separate bar/dock on each
  secondary monitor is not implemented; monitor changes restart the components.
- Legacy XEmbed tray icons are unsupported. XApp and SNI/AppIndicator icons use
  XApp's watcher bridge.
- Brightness depends on hardware and permissions; Bluetooth, media controls and
  battery estimates depend on the corresponding system services.
- Firefox integration supports default profiles found in `~/.mozilla/firefox` or
  `~/.config/mozilla/firefox`; sandboxed Flatpak/Snap profiles are not detected.
- Fullscreen placement and GPU blur need verification on your hardware. If picom
  repeatedly fails, Pear falls back to xfwm4 compositing.
- Stopping Pear does not run uninstall or restore all desktop settings. Use
  `./uninstall.sh` to restore the original desktop.

## Development

```text
bin/pear       CLI entry point
liquid/          GTK components and session supervisor
liquid/core/     shared drawing, application mapping, power, locale and process helpers
assets/          branding, styles and attributed images
tools/           validation and component preview helpers
tests/           automated regression tests
```

Run `./tools/check.sh` for syntax checks and isolated regression tests. It does not
install themes, start Pear or change your desktop. See [CONTRIBUTING.md](CONTRIBUTING.md)
for the development workflow and desktop smoke checks.

## License

Original project code is licensed under [GNU GPL v3.0 only](LICENSE). Bundled
photographs and the Papirus tray icon retain their own licenses and attribution;
see [THIRD_PARTY.md](THIRD_PARTY.md). Pear is an independent project and is not
affiliated with Apple or other vendors whose applications or themes it supports.
