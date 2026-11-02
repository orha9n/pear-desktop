# Pear

<img src="assets/branding/pear.png" alt="Pear logo" width="72" height="72">

A macOS-inspired desktop interface for **Linux Mint Xfce on X11**, written in
Python 3, GTK 3 and cairo. Pear adds a menu bar, glass dock, desktop widgets,
application launcher, search and Control Center to your existing Xfce desktop.

![Pear desktop on Linux Mint Xfce, showing the pear menu icon, transparent menu bar and glass dock](.github/images/pear-desktop.png)

*Pear running on Linux Mint Xfce with its menu bar and glass dock. Click the image to view it at full size.*

**Alpha software.** Pear is a desktop customization application, not a Linux
operating system or a replacement window manager. Clean-machine graphical testing
is still required. [Türkçe kurulum ve kullanım kılavuzu](docs/README.tr.md).

[Installation](#installation) · [Usage](#usage) · [Uninstall](#uninstall) ·
[Troubleshooting](#troubleshooting) · [Development](#development)

## Features

- Transparent menu bar, application menus, XApp system tray, battery estimates and Wi-Fi/VPN controls.
- Glass dock with pinned/running applications, window actions and drag ordering.
- Calendar, analog clock and photo widgets, widget gallery and notification history.
- Application launcher; search for applications and local file names; calculator and web search.
- Control Center for audio, brightness, dark mode, Bluetooth, media and notifications.
- Open System Reports from Control Center when Mint's `mintreport` is installed; Bluetooth and System Reports icons stay hidden in the menu bar.
- Fullscreen window controls, optional picom blur and Turkish/English interface text.

## Before installing

The development environment is **Linux Mint 22.3 Xfce, using X11**. Start with a
fresh test user or VM if you want to evaluate Pear without changing your main desktop.

| System | Status |
| --- | --- |
| Linux Mint Xfce + X11 | Development target; fresh installation still needs graphical validation. |
| Other Debian/Ubuntu-based Xfce + X11 systems | Experimental candidates; package availability and behavior are unverified. |
| Cinnamon, GNOME, KDE or Wayland sessions | Unsupported. Installing a `.deb` does not make these sessions compatible. |
| Fedora or Arch | No package or installation procedure is provided. |

Open a terminal **inside your logged-in Xfce desktop** and check:

```bash
printf 'Desktop: %s\nSession: %s\nDisplay: %s\n' \
  "$XDG_CURRENT_DESKTOP" "$XDG_SESSION_TYPE" "$DISPLAY"
```

The desktop value must contain `XFCE`, the session should be `x11`, and the display
must be nonempty (for example `:0`). If you are in another desktop or Wayland,
log out and choose an Xfce/X11 session first. Do not run desktop setup over SSH,
from a text-only console or as root.

You need internet access for system packages and GitHub theme downloads, and a
user account allowed to use `sudo`. Pear uses distribution packages for Python,
GTK 3, cairo, Pillow, libwnck, dbusmenu, XApp and system tools; no pip installation
or Python virtual environment is needed.

Setup changes themes, icons, cursors, fonts, titlebar buttons, wallpaper,
notifications, keyboard shortcuts, GTK 4 styles and supported Firefox profiles.
While Pear runs, it closes the Xfce panel and shows its own bar and dock. See
[Changes and recovery files](#changes-and-recovery-files) before proceeding.

## Installation

Choose **one** method:

| Method | Choose it when | Commands after installation |
| --- | --- | --- |
| **A. `.deb` package** | You want to test a published binary release. | `pear`, `pear-setup`, `pear-reset` |
| **B. Source checkout** | You want to develop Pear, or no `.deb` has been published yet. | `./bin/pear`, `bash install.sh`, `bash uninstall.sh` from the checkout |

Both methods install the same application. Avoid activating a source checkout and
a packaged installation for the same user at the same time. If switching methods,
restore the desktop using the old method's uninstall/reset command first.

### A. Install the `.deb` package

#### 1. Download the installable file

Open [GitHub Releases](https://github.com/orha9n/pear-desktop/releases). Open the
`v0.1.0-alpha1` pre-release, expand **Assets**, and download:

```text
pear-desktop_0.1.0.alpha1_all.deb
```

The file must end in **`.deb`**. GitHub's automatic **Source code (zip)** and
**Source code (tar.gz)** attachments, and **Code → Download ZIP**, are source
archives and cannot be installed using `apt install`.

If the release or its `.deb` attachment is not available, use
[Method B](#b-install-from-source) instead. A package built locally in `dist/`
becomes downloadable only after a maintainer uploads it to a GitHub release.

#### 2. Open a terminal in the download folder

In your file manager, open the folder where you saved the `.deb`, then choose
**Open Terminal Here**. In that terminal, verify the file is present:

```bash
ls -lh ./pear-desktop_0.1.0.alpha1_all.deb
```

If the command says the file does not exist, open the correct folder before
continuing. The commands below are for this exact alpha filename; substitute the
actual filename when installing a later release.

#### 3. Install the package and its dependencies

```bash
sudo apt update
sudo apt install ./pear-desktop_0.1.0.alpha1_all.deb
```

Enter your **Linux user password** if sudo asks. The `./` tells apt that this is a
local file. Apt installs the app and resolves its system dependencies. Wait for
this step to finish successfully before continuing.

This step installs files under `/usr/share/pear` and commands under `/usr/bin`.
**It does not activate the Pear desktop.** The `.deb` contains application code
and bundled assets; external themes are downloaded during the next step.

#### 4. Apply Pear to your user session

In the same Xfce/X11 desktop terminal, run **without sudo**:

```bash
pear-setup
```

You can also open **Pear Setup** from the applications menu. Setup downloads the
pinned MacTahoe theme/icon and WhiteSur cursor sources, applies desktop settings,
adds autostart and starts Pear. It may request sudo for the system GTK theme and
wallpaper. Keep internet access available until it finishes.

Do not run `sudo pear-setup`: settings and recovery files belong to your desktop
user. If setup prints an error, use [Troubleshooting](#troubleshooting) rather than
assuming the installation completed.

#### 5. Log out, log in and check

Save your work, log out of Xfce and log back in. This enables application menu
exports. Open a new terminal and run:

```bash
pear status
```

You should see running process IDs for `session`, `bar`, `dock`, `widgets`,
`launcher`, `controlcenter` and `spotlight`. The hidden launcher/search components
still run in the background. You should also see the Pear menu bar, dock and
widgets. Press **Super+Space** to try search.

### B. Install from source

Open a terminal in your **Xfce/X11 desktop**, as your regular user. These commands
clone the project into a persistent directory under your home folder:

```bash
sudo apt update
sudo apt install git
mkdir -p "$HOME/.local/share"
git clone https://github.com/orha9n/pear-desktop.git "$HOME/.local/share/pear-desktop"
cd "$HOME/.local/share/pear-desktop"
bash install.sh
```

If that checkout already exists, do not clone over it; use the existing checkout
or follow [Updating](#updating). `install.sh` installs missing apt dependencies,
downloads external themes, records recovery state, configures Xfce and starts Pear.
Run it **without sudo**; it requests sudo for individual system operations.

After setup, log out and back in. To check this source installation:

```bash
cd "$HOME/.local/share/pear-desktop"
./bin/pear status
```

Keep the checkout at this location: its path is recorded in autostart and keyboard
shortcuts. If you move it, run `bash install.sh` from the new location again. A
source checkout does not install the global `pear-setup` or `pear-reset` commands.

Source installer options, run from the checkout:

```bash
bash install.sh --help
bash install.sh --no-apt
LIQUID_NO_PICOM=1 bash install.sh
```

`--no-apt` requires every listed apt dependency to be installed already and stops
if any is missing. It still downloads themes and can request sudo for them.
`LIQUID_NO_PICOM=1` skips enabling picom during setup. See
[THIRD_PARTY.md](THIRD_PARTY.md) for pinned theme revisions and licenses.

## Usage

For a `.deb` installation, run:

```bash
pear --help
pear status
pear start
pear stop
pear toggle spotlight
pear toggle launcher
pear toggle controlcenter
pear widgets edit
pear fullscreen
pear compositor
pear compositor xfwm
pear compositor picom
```

For a source installation, run the same subcommands using `./bin/pear` from the
checkout, for example `./bin/pear toggle spotlight`.

| Shortcut or action | Result |
| --- | --- |
| Super+Space | Toggle search |
| Ctrl+Super+F | Toggle Pear fullscreen for the active window |
| Super+Q / Super+H / Alt+Super+H / Super+M | Quit / hide / hide others / minimize |
| Menu bar clock | Notification Center and widget controls |
| Desktop context menu | Edit widgets |
| Dock right click | Window actions and pinning |

The default dock shows only applications installed on the system. Some application
labels follow the macOS-inspired appearance; the file manager remains Thunar.
Dock settings (`items`, `icon_size`, `magnify`) are in `~/.config/liquid/dock.ini`;
widget settings are in `~/.config/liquid/widgets.ini`.

`pear stop` stops the application processes; it does **not** restore your original
Xfce settings. To return to your previous desktop, follow [Uninstall](#uninstall).

## Updating

For a `.deb` installation, download the new `.deb`, then run:

```bash
pear-reset
sudo apt install ./NEW_PACKAGE_FILENAME.deb
pear-setup
```

Replace `NEW_PACKAGE_FILENAME.deb` with the downloaded file's actual name and run
apt from its folder. Log out and back in afterward. `pear-reset` and `pear-setup`
run as your regular user; only the apt command uses sudo.

For a source installation, from its checkout:

```bash
bash uninstall.sh
git pull --ff-only
bash install.sh
```

Log out and back in afterward. Keep your recovery files and check for local code
changes before updating a development checkout.

## Uninstall

### Installed from `.deb`

First restore your desktop **inside your graphical session, without sudo**:

```bash
pear-reset
```

Wait for it to finish successfully. Then remove the system package:

```bash
sudo apt remove pear-desktop
```

The order matters: `pear-reset` uses files supplied by the package. Removing or
purging the package alone does not restore per-user settings. Run reset before
removal for each desktop user who activated Pear. `apt purge` is not a substitute
for this reset step.

### Installed from source

From the same checkout used during installation:

```bash
bash uninstall.sh
```

Keep that checkout until restoration succeeds. The optional `--themes` flag
(`pear-reset --themes` or `bash uninstall.sh --themes`) also deletes named user
icon/cursor directories and wallpaper; it removes those directories even if they
existed before Pear. It leaves system GTK themes and apt dependencies installed.

### What is restored

Reset stops Pear, removes its autostart/profile/menu entries, restores recorded
Xfce settings when their current values still match Pear's values, restores the
saved GTK 4 styles and reopens the Xfce panel. Firefox preferences are restored on
its next start. Apt dependencies and external system GTK themes remain installed.
If a setting cannot be restored, reset reports a failure and keeps its recovery
record for a retry. Do not delete the recovery files before reset finishes.

## Changes and recovery files

| Location | Purpose |
| --- | --- |
| `~/.local/share/liquid/backups/` | Original Xfce values and GTK 4 recovery files. |
| `~/.local/share/liquid/values.tsv` | Legacy mirror of recorded Xfce values. |
| `~/.config/liquid/` | Dock/widgets settings; Firefox and compositor recovery state. |
| `~/.cache/liquid/` | Component logs and wallpaper cache. |
| `~/.config/autostart/liquid.desktop` | Starts Pear at login after setup. |
| `~/.xprofile` | Marked block enabling application menu exports. |
| `~/.config/gtk-4.0/` | Backed-up, then installed GTK 4 styles. |

Pear also adds a Thunar widget action and a local notification theme. In supported
Firefox default profiles, it manages marked `user.js` preferences and imports a
separate stylesheet into `userChrome.css`, preserving existing CSS. Firefox reads
these changes on its next start. The Python module, marker names and existing
state directories retain the old `liquid` identifier for compatibility.

## Troubleshooting

Use `pear` below for `.deb` installs; use `./bin/pear` from the checkout for source
installs. Do not run either command as root.

| Problem | What to check or do |
| --- | --- |
| `.deb` is not visible in the repository file list | Open **Releases → release → Assets**. `dist/` is excluded from Git; a maintainer must upload the package as a release attachment. |
| Release or package download returns 404 | The release may not be published, the attachment may be missing, or the repository may require access. Use an available asset or install from source; a source ZIP is not a `.deb`. |
| `Unable to locate package pear-desktop` | For a downloaded package, use `sudo apt install ./pear-desktop_0.1.0.alpha1_all.deb` from its folder. There is no Pear apt repository configured by these instructions. |
| Local `.deb` file cannot be found | Use **Open Terminal Here** in the download folder and check the exact filename with `ls`. |
| Apt reports missing/uninstallable dependencies | Run `sudo apt update`; confirm your distribution provides the dependencies. Other Debian/Ubuntu-based systems are unverified. Do not force installation with ignored dependencies. |
| `pear-setup: command not found` | The `.deb` install may not have completed. Check `dpkg-query -W pear-desktop`. For a source checkout, use `bash install.sh` instead. |
| Setup says Xfce or X11 is required | Check the environment command under **Before installing**; use your logged-in Xfce/X11 graphical session. |
| GitHub theme fetch fails | Check network/GitHub access and retry setup. Package installation does not include the external themes. |
| Pear is installed, but the desktop is unchanged | Complete `pear-setup`; apt installation alone does not apply settings. |
| Global menus are missing | Log out and back in. Applications must export compatible menus; some use generic fallback menus. |
| Blank/flickering blur or compositor problems | Run `pear compositor xfwm` to return to Xfce compositing, then check the logs. |
| You want the original panel and settings back | Run `pear-reset` (or `bash uninstall.sh` for source) in your desktop session. |

To inspect the current status and recent component logs:

```bash
pear status
tail -n 80 "$HOME/.cache/liquid/session.log"
tail -n 80 "$HOME/.cache/liquid/bar.log"
tail -n 80 "$HOME/.cache/liquid/picom.log"
```

A log may not exist if its component has not started. Include the failed command,
its complete error output, your distribution/version and Xfce/X11 session details
when opening an issue. Remove personal information from logs and screenshots.

## Known limitations

- Components use the primary monitor; a separate bar/dock on each secondary
  monitor is not implemented. Monitor changes restart the components.
- Global menus depend on GTK GMenuModel or dbusmenu exports. Some GTK 4, Firefox
  and Electron applications use generic fallback menus.
- Legacy XEmbed tray icons are unsupported; XApp and SNI/AppIndicator use XApp's watcher bridge.
- Brightness, Bluetooth, battery estimates and media controls depend on hardware,
  services and permissions. A music player/calendar application is not bundled.
- Firefox integration detects default profiles in `~/.mozilla/firefox` or
  `~/.config/mozilla/firefox`; Flatpak/Snap profiles are not automatically found.
- GPU blur and fullscreen placement need hardware testing. Repeated picom failures
  trigger a fallback to xfwm4 compositing.

## Development

```text
bin/pear          source CLI entry point
liquid/           GTK components and session supervisor
liquid/core/      shared drawing, apps, locale, power and process helpers
assets/           branding, styles and attributed images
packaging/debian/ package metadata, menu entry and package instructions
tools/            validation, package builder and component preview helpers
tests/            regression and package-payload checks
```

From the checkout, validate the project and build a test package:

```bash
bash tools/check.sh
python3 tools/build_deb.py
```

The checks do not apply desktop settings. When `dpkg-deb` is available, they build
and extract a temporary package to inspect its contents, dependencies and CLI.
The build writes a `.deb` and its `.sha256` file into `dist/`; building it does not
install it. Set `--maintainer 'Your Name <your-public-email>'` for a public release;
test builds use a reserved `example.invalid` address. See
[CONTRIBUTING.md](CONTRIBUTING.md) for graphical smoke checks.

`dist/` is ignored by Git. Push the source and upload the built `.deb` as a
**Release asset** separately. GitHub Actions also builds a package as a workflow
artifact; that artifact does not automatically create a GitHub Release.

## License

Original project code is licensed under [GNU GPL v3.0 only](LICENSE). Photographs
and the Papirus tray icon retain their own licenses and attribution; see
[THIRD_PARTY.md](THIRD_PARTY.md). Pear is independent and is not affiliated with
Apple or other vendors whose applications or themes it supports.
