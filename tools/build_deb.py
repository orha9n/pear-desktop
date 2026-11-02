#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Build an architecture-independent test .deb without root or desktop changes."""
import argparse
import gzip
import hashlib
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VERSION = "0.1.0~alpha1"


def build(output, version=DEFAULT_VERSION, maintainer="Pear contributors <pear@example.invalid>"):
    if not re.fullmatch(r"[0-9][A-Za-z0-9.+~:-]*", version):
        raise ValueError("Invalid Debian version")
    if not re.fullmatch(r"[^<>\r\n]+ <[^<>\s]+@[^<>\s]+>", maintainer):
        raise ValueError("Maintainer must be 'Name <email>'")
    if not shutil.which("dpkg-deb"):
        raise RuntimeError("dpkg-deb is required (install the dpkg package)")
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="pear-deb-") as directory:
        stage = Path(directory)
        app = stage / "usr/share/pear"
        app.mkdir(parents=True)
        # Explicit payload: never include .git, local state, dist or Python caches.
        shutil.copytree(ROOT / "liquid", app / "liquid",
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"))
        shutil.copytree(ROOT / "assets", app / "assets")
        shutil.copytree(ROOT / "bin", app / "bin")
        shutil.copytree(ROOT / "docs", app / "docs")
        for name in ("install.sh", "uninstall.sh", "README.md", "LICENSE", "THIRD_PARTY.md", "CONTRIBUTING.md"):
            shutil.copy2(ROOT / name, app / name)
        package_doc = app / "packaging/debian"
        package_doc.mkdir(parents=True)
        shutil.copy2(ROOT / "packaging/debian/README.Debian", package_doc / "README.Debian")
        commands = stage / "usr/bin"
        commands.mkdir(parents=True)
        wrappers = {
            "pear": 'exec /usr/share/pear/bin/pear "$@"',
            "pear-setup": 'exec /usr/share/pear/install.sh --no-apt "$@"',
            "pear-reset": 'exec /usr/share/pear/uninstall.sh "$@"',
        }
        for name, command in wrappers.items():
            (commands / name).write_text("#!/bin/sh\n# SPDX-License-Identifier: GPL-3.0-only\n" + command + "\n")
        applications = stage / "usr/share/applications"
        applications.mkdir(parents=True)
        shutil.copy2(ROOT / "packaging/debian/pear.desktop", applications / "pear-desktop.desktop")
        pixmaps = stage / "usr/share/pixmaps"
        pixmaps.mkdir(parents=True)
        shutil.copy2(ROOT / "assets/branding/pear.png", pixmaps / "pear-desktop.png")
        doc = stage / "usr/share/doc/pear-desktop"
        doc.mkdir(parents=True)
        shutil.copy2(ROOT / "packaging/debian/README.Debian", doc / "README.Debian")
        shutil.copy2(ROOT / "THIRD_PARTY.md", doc / "THIRD_PARTY.md")
        with (doc / "COPYING.gz").open("wb") as stream:
            with gzip.GzipFile(filename="", mode="wb", fileobj=stream, mtime=0) as archive:
                archive.write((ROOT / "LICENSE").read_bytes())
        (doc / "copyright").write_text(
            "Pear original code: GPL-3.0-only; see COPYING.gz.\n"
            "Project mark: maintainer-provided pear image.\n\n"
            + (ROOT / "THIRD_PARTY.md").read_text() + "\n"
            + "\n\n".join((ROOT / path).read_text() for path in (
                "assets/wallpaper/CREDITS.md", "assets/widgets/CREDITS.md", "assets/tray/CREDITS.md")))
        metadata = stage / "DEBIAN"
        metadata.mkdir()
        size = (sum(p.stat().st_size for p in stage.rglob("*") if p.is_file()) + 1023) // 1024
        control = (ROOT / "packaging/debian/control").read_text()
        for key, value in (("VERSION", version), ("MAINTAINER", maintainer), ("SIZE", str(size))):
            control = control.replace("@" + key + "@", value)
        (metadata / "control").write_text(control)
        shutil.copy2(ROOT / "packaging/debian/prerm", metadata / "prerm")
        files = sorted(p for p in stage.rglob("*") if p.is_file() and metadata not in p.parents)
        (metadata / "md5sums").write_text("".join(
            hashlib.md5(p.read_bytes()).hexdigest() + "  " + str(p.relative_to(stage)) + "\n" for p in files))
        # dpkg expects public read-only data and executable entry points, owned by root.
        executables = set(commands.iterdir()) | {app / "bin/liquid", app / "bin/pear", app / "install.sh",
                                                 app / "uninstall.sh", metadata / "prerm"}
        for path in stage.rglob("*"):
            path.chmod(0o755 if path.is_dir() or path in executables else 0o644)
        stage.chmod(0o755)
        # GitHub release assets turn "~" into "."; name the file the way it will be downloaded.
        dest = output / f"pear-desktop_{version.replace('~', '.')}_all.deb"
        subprocess.run(["dpkg-deb", "--root-owner-group", "-Zxz", "--build", str(stage), str(dest)], check=True)
        (output / (dest.name + ".sha256")).write_text(hashlib.sha256(dest.read_bytes()).hexdigest() + "  " + dest.name + "\n")
        return dest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    parser.add_argument("--version", default=DEFAULT_VERSION)
    parser.add_argument("--maintainer", default="Pear contributors <pear@example.invalid>")
    args = parser.parse_args()
    print(build(args.output, args.version, args.maintainer))


if __name__ == "__main__":
    main()
