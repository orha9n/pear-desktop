#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-only
# ============================================================
#  Liquid — macOS 27 görünümünü bu kullanıcıya uygula (Linux Mint XFCE)
#  Kullanım:  ./install.sh            (gerekirse sudo ile paket + tema kurar)
#             ./install.sh --no-apt   (paket adımını atla)
#  Değiştirilen HER ayarın önceki değeri ~/.local/share/liquid/backups/values.tsv'ye yazılır;
#  ./uninstall.sh yalnızca bunları geri yükler (sonradan yaptığın ayarlara dokunmaz).
#  Dokunulmayanlar: ses/medya tuşları, Super tuşu, Print, ~/.config/gtk-3.0/gtk.css.
# ============================================================
set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NO_APT=0
for arg in "$@"; do
  case "$arg" in
    --no-apt) NO_APT=1 ;;
    -h|--help) echo "Kullanım: ./install.sh [--no-apt]"; exit 0 ;;
    *) echo "Bilinmeyen seçenek: $arg" >&2; exit 2 ;;
  esac
done
BK="$HOME/.local/share/liquid/backups"; VALS="$BK/values.tsv"
# Eski sürümlerin geri alma kaydıyla uyumluluk.
MIRROR="$HOME/.local/share/liquid/values.tsv"
say()  { echo -e "\n\033[1;36m>> $*\033[0m"; }
ok()   { echo -e "   \033[1;32m✓\033[0m $*"; }
warn() { echo -e "   \033[1;33m!\033[0m $*"; }

case "${XDG_CURRENT_DESKTOP:-}" in *XFCE*) ;; *) echo "!! XFCE oturumu gerekli (şu an: ${XDG_CURRENT_DESKTOP:-?})"; exit 1;; esac
if [ "${XDG_SESSION_TYPE:-x11}" != x11 ] || [ -z "${DISPLAY:-}" ]; then
  echo "!! X11 grafik oturumu gerekli" >&2; exit 1
fi
[ "$(id -u)" = 0 ] && { echo "!! root olarak değil, kendi kullanıcınla çalıştır (sudo gerekirse kendisi sorar)"; exit 1; }
# Yollar kısayol ve .desktop dosyalarında kullanılır; satır sonuna izin verme.
case "$ROOT" in *$'\n'*|*$'\r'*) echo "!! Proje yolu satır sonu içeremez" >&2; exit 1;; esac
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"

# xfconf özelliğini ayarla; İLK değiştirişte eski değeri (ya da yokluğunu) kaydet.
# 5. sütun: Liquid'in yazdığı değerin kabuk deseni → uninstall, kullanıcı sonradan değiştirdiyse dokunmaz.
# (Adı xset değil: X11'in xset komutunu gölgelemesin.)
xfset() {   # kanal özellik tür değer [desen]
  local ch="$1" p="$2" typ="$3" v="$4" pat="${5:-$4}" old
  if ! grep -qP "^\Q$ch\E\t\Q$p\E\t" "$VALS" 2>/dev/null; then
    old="$(xfconf-query -c "$ch" -p "$p" 2>/dev/null)" || old="__UNSET__"
    printf '%s\t%s\t%s\t%s\t%s\n' "$ch" "$p" "$typ" "$old" "$pat" >> "$VALS"
  fi
  xfconf-query -c "$ch" -p "$p" -t "$typ" -s "$v" --create
  cp "$VALS" "$MIRROR"
}

# ---------- 1) paketler ----------
say "1/7  Paketler"
PKGS="python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-wnck-3.0 gir1.2-dbusmenu-glib-0.4 python3-pil
  x11-utils wmctrl xdotool playerctl brightnessctl pulseaudio-utils network-manager fonts-inter
  appmenu-gtk2-module appmenu-gtk3-module appmenu-registrar sassc libxml2-utils git picom
  gir1.2-xapp-1.0 xapps-common python3-cairo x11-xserver-utils libnotify-bin
  xfce4-notifyd xfce4-screenshooter network-manager-gnome bluez rfkill xdg-utils xdg-user-dirs"
MISSING=()
for p in $PKGS; do dpkg-query -W -f='${Status}' "$p" 2>/dev/null | grep -q "ok installed" || MISSING+=("$p"); done
if [ "${#MISSING[@]}" = 0 ]; then ok "hepsi kurulu"
elif [ "$NO_APT" = 1 ]; then warn "eksik paketler: ${MISSING[*]}"; exit 1
else
  sudo apt-get install -y "${MISSING[@]}"
  ok "kuruldu: ${MISSING[*]}"
fi
python3 -c 'import gi, cairo, PIL; gi.require_version("Gtk", "3.0"); gi.require_version("Wnck", "3.0"); gi.require_version("Dbusmenu", "0.4"); gi.require_version("XApp", "1.0"); from gi.repository import Gtk, Wnck, Dbusmenu, XApp'
mkdir -p "$BK" "$(dirname "$MIRROR")"
for name in values.tsv gtk-4.0.orig uca.xml.orig; do
  if [ -e "$ROOT/backup/$name" ] && [ ! -e "$BK/$name" ]; then cp -a "$ROOT/backup/$name" "$BK/$name"; fi
done
if [ ! -f "$VALS" ] && [ -f "$MIRROR" ]; then cp -a "$MIRROR" "$VALS"; fi
touch "$VALS"

# ---------- 2) temalar (MacTahoe GTK + pencere, ikonlar, imleç) ----------
say "2/7  MacTahoe tema, ikonlar, imleç"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
clone() {
  local repo="$1" revision
  case "$repo" in
    MacTahoe-gtk-theme) revision=1e45e19f510edb8cde18fa84d6cd5319f60b086b ;;
    MacTahoe-icon-theme) revision=839848b9a8a38a92a6936e30c4abe35cc6f2546d ;;
    WhiteSur-cursors) revision=e190baf618ed95ee217d2fd45589bd309b37672b ;;
    *) return 1 ;;
  esac
  git init -q "$TMP/$repo"
  git -C "$TMP/$repo" fetch -q --depth=1 "https://github.com/vinceliuice/$repo.git" "$revision"
  git -C "$TMP/$repo" checkout -q --detach FETCH_HEAD
}
if [ ! -d /usr/share/themes/MacTahoe-Light/xfwm4 ] && [ ! -d "$HOME/.themes/MacTahoe-Light/xfwm4" ]; then
  clone MacTahoe-gtk-theme && (cd "$TMP/MacTahoe-gtk-theme" && sudo ./install.sh -c light -c dark -o normal)
fi
if [ ! -d "$HOME/.local/share/icons/MacTahoe" ] && [ ! -d /usr/share/icons/MacTahoe ]; then
  clone MacTahoe-icon-theme && (cd "$TMP/MacTahoe-icon-theme" && ./install.sh -d "$HOME/.local/share/icons")
fi
if [ ! -d "$HOME/.local/share/icons/WhiteSur-cursors" ]; then
  mkdir -p "$HOME/.local/share/icons"
  clone WhiteSur-cursors && cp -r "$TMP/WhiteSur-cursors/dist" "$HOME/.local/share/icons/WhiteSur-cursors"
fi
# GTK4/libadwaita uygulamaları (Takvim, Hesap Makinesi…) ~/.config/gtk-4.0/gtk.css'i okur. MacTahoe'nun
# kendi betiğini çalıştırmadan (o ~/.themes'e de kurup uygulama ekliyor) yalnız gtk-4.0 stilleri derlenir.
G4="$HOME/.config/gtk-4.0"
if [ ! -f "$G4/.liquid" ]; then
  if [ -d "$G4" ] && [ ! -e "$BK/gtk-4.0.orig" ]; then cp -a "$G4" "$BK/gtk-4.0.orig"; fi
  [ -d "$TMP/MacTahoe-gtk-theme" ] || clone MacTahoe-gtk-theme
  SRC="$TMP/MacTahoe-gtk-theme/src"
  cp "$SRC/sass/_theme-options.scss" "$SRC/sass/_theme-options-temp.scss"
  cp "$SRC/sass/_gtk-base.scss" "$SRC/sass/_gtk-base-temp.scss"
  mkdir -p "$G4"
  rm -rf "$G4/"{gtk.css,gtk-dark.css,gtk-Light.css,gtk-Dark.css,assets,windows-assets}
  sassc -t expanded "$SRC/main/gtk-4.0/gtk-Light.scss" "$G4/gtk-Light.css"
  sassc -t expanded "$SRC/main/gtk-4.0/gtk-Dark.scss" "$G4/gtk-Dark.css"
  ln -sf gtk-Light.css "$G4/gtk.css"; ln -sf gtk-Dark.css "$G4/gtk-dark.css"
  cp -r "$SRC/assets/gtk/common-assets/assets" "$G4/"
  cp -r "$SRC/assets/gtk/scalable" "$G4/assets/"
  cp -r "$SRC/assets/gtk/windows-assets/titlebutton" "$G4/windows-assets"
  touch "$G4/.liquid"
fi
ok "MacTahoe-Light · MacTahoe ikonları · WhiteSur imleçleri · GTK4 (~/.config/gtk-4.0)"

# ---------- 3) görünüm ayarları ----------
say "3/7  Pencere teması, ikonlar, yazı tipi"
xfset xsettings /Net/ThemeName string MacTahoe-Light "MacTahoe-*"      # Karanlık Mod: MacTahoe-Dark
xfset xsettings /Net/IconThemeName string MacTahoe "MacTahoe*"
xfset xsettings /Gtk/CursorThemeName string WhiteSur-cursors
xfset xsettings /Gtk/CursorThemeSize int 24
xfset xsettings /Gtk/FontName string "Inter 10"
xfset xsettings /Xft/HintStyle string hintslight
xfset xsettings /Xft/RGBA string rgb
xfset xfwm4 /general/theme string MacTahoe-Light "MacTahoe-*"
xfset xfwm4 /general/button_layout string "CHM|"
xfset xfwm4 /general/button_offset int 10
xfset xfwm4 /general/button_spacing int 2
xfset xfwm4 /general/title_alignment string center
xfset xfwm4 /general/title_font string "Inter Semi-Bold 10"
xfset xfwm4 /general/use_compositing bool true
xfset xfwm4 /general/show_frame_shadow bool true
xfset xfwm4 /general/show_popup_shadow bool true
xfset xfwm4 /general/placement_mode string center
ok "trafik ışıkları solda, başlık ortada, Inter"
PYTHONPATH="$ROOT" python3 -m liquid.firefox install

# ---------- 4) duvar kâğıdı ----------
say "4/7  Duvar kâğıdı (Golden Gate)"
# Mint duvar kâğıtlarının YANINA koy: XFCE Masaüstü ayarları yalnızca geçerli resmin klasörünü
# listeler; ayrı klasörde dururken Mint'in kendi duvar kâğıtları listede görünmüyordu.
WP=/usr/share/xfce4/backdrops/liquid-golden-gate.jpg
if [ ! -f "$WP" ] && ! sudo cp "$ROOT/assets/wallpaper/golden-gate.jpg" "$WP"; then
  WP="$HOME/.local/share/backgrounds/liquid/golden-gate.jpg"; mkdir -p "$(dirname "$WP")"
  cp "$ROOT/assets/wallpaper/golden-gate.jpg" "$WP"
fi
PROPS="$(xfconf-query -c xfce4-desktop -l 2>/dev/null | grep -E '/last-image$' || true)"
for mon in $(xrandr | awk '/ connected/{print $1}'); do
  for ws in 0 1 2 3; do PROPS="$PROPS
/backdrop/screen0/monitor$mon/workspace$ws/last-image"; done
done
echo "$PROPS" | sort -u | while read -r p; do
  [ -n "$p" ] || continue
  xfset xfce4-desktop "$p" string "$WP"
  xfset xfce4-desktop "${p%/last-image}/image-style" int 5
done
ok "assets/wallpaper/golden-gate.jpg (Levi Clancy, CC BY-SA 4.0)"

# ---------- 5) global menü (GTK uygulamaları menülerini çubuğa versin) ----------
say "5/7  Global menü"
XP="$HOME/.xprofile"; touch "$XP"
sed -i '/# LIQUID-START/,/# LIQUID-END/d' "$XP"          # eski sürümün bloğunu yenisiyle değiştir
cat >> "$XP" <<'EOF'
# LIQUID-START — GTK uygulamaları menülerini Liquid menü çubuğuna versin
# (Mint zaten ekliyorsa ikinci kez ekleme: GTK_MODULES=appmenu-gtk-module:appmenu-gtk-module:… oluyordu)
case ":${GTK_MODULES:-}:" in
  *:appmenu-gtk-module:*) ;;
  *) export GTK_MODULES="${GTK_MODULES:+$GTK_MODULES:}appmenu-gtk-module" ;;
esac
export UBUNTU_MENUPROXY=1
# LIQUID-END
EOF
ok "$HOME/.xprofile (oturumu kapatıp açınca etkin)"

# ---------- 6) kısayol + oturum başlangıcı ----------
say "6/7  Kısayollar (⌘Space ⌃⌘F ⌘Q ⌘H ⌥⌘H ⌘M), otomatik başlatma"
LIQUID_CMD="$(python3 -c 'import shlex, sys; print(shlex.quote(sys.argv[1]))' "$ROOT/bin/liquid")"
xfset xfce4-keyboard-shortcuts "/commands/custom/<Super>space" string "$LIQUID_CMD toggle spotlight"
xfset xfce4-keyboard-shortcuts "/commands/custom/<Primary><Super>f" string "$LIQUID_CMD fullscreen"
xfset xfce4-keyboard-shortcuts "/commands/custom/<Super>q" string "$LIQUID_CMD app quit"
xfset xfce4-keyboard-shortcuts "/commands/custom/<Super>h" string "$LIQUID_CMD app hide"
xfset xfce4-keyboard-shortcuts "/commands/custom/<Alt><Super>h" string "$LIQUID_CMD app hide-others"
xfset xfce4-keyboard-shortcuts "/commands/custom/<Super>m" string "$LIQUID_CMD app minimize"
# shellcheck disable=SC2016 # Python must receive literal dollar signs.
DESKTOP_EXEC="$(python3 -c 'import sys; s=sys.argv[1]; s=s.replace("\\", "\\\\").replace("\"", "\\\"").replace("`", "\\`").replace("$", "\\$").replace("%", "%%"); print(chr(34)+s+chr(34))' "$ROOT/bin/liquid")"
# Desktop Entry string escaping is applied before Exec argument parsing.
DESKTOP_EXEC="${DESKTOP_EXEC//\\/\\\\}"
mkdir -p "$HOME/.config/autostart"
cat > "$HOME/.config/autostart/liquid.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Pear
Comment=Pear desktop (menu bar, dock, widgets)
Exec=$DESKTOP_EXEC start
Terminal=false
X-GNOME-Autostart-enabled=true
EOF
ok "$HOME/.config/autostart/liquid.desktop"
# bildirimler: macOS kartı (kendi temamız) + geçmiş kaydı (Bildirim Merkezi'nde görünsün)
NT="$HOME/.local/share/themes/Liquid/xfce-notify-4.0"
mkdir -p "$NT" && cp "$ROOT/assets/notify/gtk.css" "$NT/gtk.css" && touch "$NT/../.liquid"
xfset xfce4-notifyd /theme string Liquid
xfset xfce4-notifyd /initial-opacity double 1.0 "1*"
xfset xfce4-notifyd /notification-log bool true
pkill -HUP -x xfce4-notifyd 2>/dev/null || true
ok "bildirimler: Liquid teması, geçmiş açık"
# masaüstü sağ tık → "Widget'ları Düzenle…" (Thunar özel eylemi; yalnız bizim eylemimiz eklenir/silinir)
PYTHONPATH="$ROOT" python3 -m liquid.desktopmenu install && ok "masaüstü menüsü: Widget'ları Düzenle…"

# ---------- 7) başlat ----------
say "7/7  Başlatılıyor"
"$ROOT/bin/liquid" stop >/dev/null 2>&1 || true
sleep 1
"$ROOT/bin/liquid" start
sleep 4
# gerçek cam: xfwm4 compositor'ü yerine picom (önceki değer ~/.config/liquid/compositor.json'da;
# geri dönmek için: liquid compositor xfwm). İstemezsen: LIQUID_NO_PICOM=1 ./install.sh
if [ "${LIQUID_NO_PICOM:-0}" != 1 ] && command -v picom >/dev/null; then
  "$ROOT/bin/liquid" compositor picom || warn "picom başlamadı — xfwm4 compositor'ü kullanılıyor"
fi
"$ROOT/bin/liquid" status
echo -e "\n\033[1;32m✓ Pear kuruldu.\033[0m  Global menüler için bir kez oturumu kapatıp aç."
echo "  Geri almak için: ./uninstall.sh"
