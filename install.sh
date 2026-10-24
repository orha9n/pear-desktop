#!/usr/bin/env bash
# ============================================================
#  Liquid — macOS 27 görünümünü bu kullanıcıya uygula (Linux Mint XFCE)
#  Kullanım:  ./install.sh            (gerekirse sudo ile paket + tema kurar)
#             ./install.sh --no-apt   (paket adımını atla)
#  Değiştirilen HER ayarın önceki değeri backup/values.tsv'ye yazılır;
#  ./uninstall.sh yalnızca bunları geri yükler (sonradan yaptığın ayarlara dokunmaz).
#  Dokunulmayanlar: ses/medya tuşları, Super tuşu, Print, ~/.config/gtk-3.0/gtk.css.
# ============================================================
set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NO_APT=0; [ "${1:-}" = "--no-apt" ] && NO_APT=1
BK="$ROOT/backup"; VALS="$BK/values.tsv"
# yedeğin ikinci kopyası proje klasörünün DIŞINDA (backup/ git'te değil; klasör silinirse geri alma kalsın)
MIRROR="$HOME/.local/share/liquid/values.tsv"
say()  { echo -e "\n\033[1;36m>> $*\033[0m"; }
ok()   { echo -e "   \033[1;32m✓\033[0m $*"; }
warn() { echo -e "   \033[1;33m!\033[0m $*"; }

case "${XDG_CURRENT_DESKTOP:-}" in *XFCE*) ;; *) echo "!! XFCE oturumu gerekli (şu an: ${XDG_CURRENT_DESKTOP:-?})"; exit 1;; esac
[ "$(id -u)" = 0 ] && { echo "!! root olarak değil, kendi kullanıcınla çalıştır (sudo gerekirse kendisi sorar)"; exit 1; }
mkdir -p "$BK" "$(dirname "$MIRROR")"; touch "$VALS"

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
  appmenu-gtk2-module appmenu-gtk3-module appmenu-registrar sassc libxml2-utils git picom"
MISSING=""
for p in $PKGS; do dpkg-query -W -f='${Status}' "$p" 2>/dev/null | grep -q "ok installed" || MISSING="$MISSING $p"; done
if [ -z "$MISSING" ]; then ok "hepsi kurulu"
elif [ "$NO_APT" = 1 ]; then warn "eksik (atlandı):$MISSING"
else sudo apt-get install -y $MISSING && ok "kuruldu:$MISSING"; fi

# ---------- 2) temalar (MacTahoe GTK + pencere, ikonlar, imleç) ----------
say "2/7  MacTahoe tema, ikonlar, imleç"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
clone() { git clone -q --depth=1 "https://github.com/vinceliuice/$1.git" "$TMP/$1"; }
if [ ! -d /usr/share/themes/MacTahoe-Light/xfwm4 ] && [ ! -d "$HOME/.themes/MacTahoe-Light/xfwm4" ]; then
  clone MacTahoe-gtk-theme && (cd "$TMP/MacTahoe-gtk-theme" && sudo ./install.sh -c light -c dark -o normal)
fi
if [ ! -d "$HOME/.local/share/icons/MacTahoe" ] && [ ! -d /usr/share/icons/MacTahoe ]; then
  clone MacTahoe-icon-theme && (cd "$TMP/MacTahoe-icon-theme" && ./install.sh -d "$HOME/.local/share/icons")
fi
if [ ! -d "$HOME/.local/share/icons/WhiteSur-cursors" ]; then
  clone WhiteSur-cursors && cp -r "$TMP/WhiteSur-cursors/dist" "$HOME/.local/share/icons/WhiteSur-cursors"
fi
# GTK4/libadwaita uygulamaları (Takvim, Hesap Makinesi…) ~/.config/gtk-4.0/gtk.css'i okur. MacTahoe'nun
# kendi betiğini çalıştırmadan (o ~/.themes'e de kurup uygulama ekliyor) yalnız gtk-4.0 stilleri derlenir.
G4="$HOME/.config/gtk-4.0"
if [ ! -f "$G4/.liquid" ]; then
  if [ -e "$G4/gtk.css" ] && [ ! -e "$BK/gtk-4.0.orig" ]; then cp -a "$G4" "$BK/gtk-4.0.orig"; fi
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
xfset xfwm4 /general/title_alignment string center
xfset xfwm4 /general/title_font string "Inter Semi-Bold 10"
xfset xfwm4 /general/use_compositing bool true
xfset xfwm4 /general/show_frame_shadow bool true
xfset xfwm4 /general/show_popup_shadow bool true
xfset xfwm4 /general/placement_mode string center
ok "trafik ışıkları solda, başlık ortada, Inter"

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
ok "~/.xprofile (oturumu kapatıp açınca etkin)"

# ---------- 6) kısayol + oturum başlangıcı ----------
say "6/7  Kısayollar (⌘Space ⌃⌘F ⌘Q ⌘H ⌥⌘H ⌘M), otomatik başlatma"
xfset xfce4-keyboard-shortcuts "/commands/custom/<Super>space" string "$ROOT/bin/liquid toggle spotlight"
xfset xfce4-keyboard-shortcuts "/commands/custom/<Primary><Super>f" string "$ROOT/bin/liquid fullscreen"
xfset xfce4-keyboard-shortcuts "/commands/custom/<Super>q" string "$ROOT/bin/liquid app quit"          # ⌘Q
xfset xfce4-keyboard-shortcuts "/commands/custom/<Super>h" string "$ROOT/bin/liquid app hide"          # ⌘H
xfset xfce4-keyboard-shortcuts "/commands/custom/<Alt><Super>h" string "$ROOT/bin/liquid app hide-others"
xfset xfce4-keyboard-shortcuts "/commands/custom/<Super>m" string "$ROOT/bin/liquid app minimize"      # ⌘M
mkdir -p "$HOME/.config/autostart"
cat > "$HOME/.config/autostart/liquid.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Liquid
Comment=macOS 27 görünümü (menü çubuğu, dock, widget'lar)
Exec=$ROOT/bin/liquid start
Terminal=false
X-GNOME-Autostart-enabled=true
EOF
ok "~/.config/autostart/liquid.desktop"
# masaüstü sağ tık → "Widget'ları Düzenle…" (Thunar özel eylemi; yalnız bizim eylemimiz eklenir/silinir)
[ -e "$HOME/.config/Thunar/uca.xml" ] && [ ! -e "$BK/uca.xml.orig" ] && cp -a "$HOME/.config/Thunar/uca.xml" "$BK/uca.xml.orig"
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
echo -e "\n\033[1;32m✓ Liquid kuruldu.\033[0m  Global menüler için bir kez oturumu kapatıp aç."
echo "  Geri almak için: ./uninstall.sh"
