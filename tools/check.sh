#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-only
# Read-only source validation; tests run outside the developer's HOME/session.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
bash -n install.sh uninstall.sh tools/check.sh
sh -n bin/liquid bin/pear
sh -n packaging/debian/prerm
if command -v shellcheck >/dev/null; then
  shellcheck install.sh uninstall.sh tools/check.sh bin/liquid bin/pear packaging/debian/prerm
fi
python3 - <<'PY'
from pathlib import Path
paths = sorted(Path('liquid').rglob('*.py')) + sorted(Path('tools').glob('*.py')) + sorted(Path('tests').glob('*.py'))
for path in paths:
    compile(path.read_text(encoding='utf-8'), str(path), 'exec')
print(f'Python syntax: {len(paths)} files OK')
PY
CHECK_HOME="$(mktemp -d)"
trap 'rm -rf "$CHECK_HOME"' EXIT
mkdir -p "$CHECK_HOME/run"
env -u DISPLAY -u WAYLAND_DISPLAY HOME="$CHECK_HOME" XDG_RUNTIME_DIR="$CHECK_HOME/run" \
  PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git diff --check
fi
