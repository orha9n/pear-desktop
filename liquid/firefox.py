# SPDX-License-Identifier: GPL-3.0-only
"""Firefox birleşik başlığı ve kompakt trafik ışıkları (sonraki açılışta).

prefs.js çalışan tarayıcı tarafından yazılır; onu değiştirmeyiz. user.js içindeki
yalnızca kendi bloklarımızı yönetir, önceki tercihleri kaldırmada geri getiririz.
Var olan userChrome.css korunur; ayrı stil dosyamız başta içe aktarılır.
"""
import configparser
import hashlib
import json
from pathlib import Path
import re
import sys

from .core import config_path

STATE = Path(config_path("firefox-titlebar.json"))
PREF = "browser.tabs.inTitlebar"
BLOCK = '\n// LIQUID-TITLEBAR-START\nuser_pref("browser.tabs.inTitlebar", 1);\n// LIQUID-TITLEBAR-END\n'
PATTERN = re.compile(r'^\s*user_pref\("browser\.tabs\.inTitlebar",\s*([012])\s*\);', re.M)
STYLE_PREF = "toolkit.legacyUserProfileCustomizations.stylesheets"
STYLE_BLOCK = '\n// LIQUID-CHROME-START\nuser_pref("toolkit.legacyUserProfileCustomizations.stylesheets", true);\n// LIQUID-CHROME-END\n'
STYLE_PATTERN = re.compile(r'^\s*user_pref\("toolkit\.legacyUserProfileCustomizations\.stylesheets",\s*(true|false)\s*\);', re.M)
STYLE = Path(__file__).resolve().parent.parent / "assets/firefox/liquid-titlebar.css"
IMPORT = '@import url("liquid-titlebar.css"); /* Liquid Firefox titlebar */\n'


def default_profile():
    for root in (Path.home() / ".config/mozilla/firefox", Path.home() / ".mozilla/firefox"):
        cp = configparser.ConfigParser()
        cp.read(root / "profiles.ini")
        for section in cp.sections():
            if section.startswith("Install") and cp.has_option(section, "Default"):
                path = root / cp[section]["Default"]
                if path.is_dir():
                    return path
    return None


def install():
    state = json.loads(STATE.read_text()) if STATE.exists() else None
    profile = Path(state["profile"]) if state else default_profile()
    if profile is None:
        return
    userjs = profile / "user.js"
    original = userjs.read_text() if userjs.exists() else ""
    prefs = (profile / "prefs.js").read_text() if (profile / "prefs.js").exists() else ""
    if state is None:
        previous = PATTERN.findall(prefs + "\n" + original)
        state = {"profile": str(profile), "original": original,
                 "previous": int(previous[-1]) if previous else 2}
        original += BLOCK
    chrome = profile / "chrome"
    chrome.mkdir(exist_ok=True)
    css = chrome / "userChrome.css"
    asset = chrome / "liquid-titlebar.css"
    current_css = css.read_text() if css.exists() else ""
    if "chrome" not in state:
        previous_style = STYLE_PATTERN.findall(prefs + "\n" + original)
        state["chrome"] = {"previous_enabled": previous_style[-1] if previous_style else "false",
                           "asset_original": asset.read_text() if asset.exists() else None,
                           "css_existed": css.exists()}
    installed = STYLE.read_text()
    state["chrome"]["installed_hash"] = hashlib.sha256(installed.encode()).hexdigest()
    STATE.write_text(json.dumps(state, indent=2))  # İlk yedeği güncelleme sırasında koru.
    if STYLE_BLOCK not in original:
        userjs.write_text(original + STYLE_BLOCK)
    asset.write_text(installed)
    if IMPORT not in current_css:
        css.write_text(IMPORT + current_css)  # @import, @namespace ve kurallardan önce gelmeli.
    print("Firefox: kompakt trafik ışıkları ve birleşik başlık sonraki açılışta etkinleşecek.")


def remove():
    if not STATE.exists():
        return
    state = json.loads(STATE.read_text())
    userjs = Path(state["profile"]) / "user.js"
    current = userjs.read_text() if userjs.exists() else ""
    if BLOCK in current:
        remaining = current.replace(BLOCK, "", 1)
        # Firefox yeni değeri prefs.js'e kaydetmiş olabilir. Eski tercihi sonraki
        # açılışta uygula; kullanıcı bloktan sonra kendi tercihini yazmışsa koru.
        later = current.split(BLOCK, 1)[1]
        if not PATTERN.search(later):
            remaining += f'\n// Liquid: önceki başlık tercihi\nuser_pref("{PREF}", {state["previous"]});\n'
        userjs.write_text(remaining)
    if "chrome" in state:
        previous = state["chrome"]
        current = userjs.read_text() if userjs.exists() else ""
        if STYLE_BLOCK in current:
            later = current.split(STYLE_BLOCK, 1)[1]
            current = current.replace(STYLE_BLOCK, "", 1)
            if not STYLE_PATTERN.search(later):
                current += f'\n// Liquid: önceki stil tercihi\nuser_pref("{STYLE_PREF}", {previous["previous_enabled"]});\n'
            userjs.write_text(current)
        css = Path(state["profile"]) / "chrome/userChrome.css"
        if css.exists():
            remaining = css.read_text().replace(IMPORT, "", 1)
            if remaining or previous["css_existed"]:
                css.write_text(remaining)
            else:
                css.unlink()
        asset = css.parent / "liquid-titlebar.css"
        if asset.exists() and hashlib.sha256(asset.read_bytes()).hexdigest() == previous["installed_hash"]:
            if previous["asset_original"] is None:
                asset.unlink()
            else:
                asset.write_text(previous["asset_original"])
    STATE.unlink()


if __name__ == "__main__":
    {"install": install, "remove": remove}[sys.argv[1]]()
