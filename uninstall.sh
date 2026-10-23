#!/usr/bin/env bash
# ============================================================
#  Liquid — geri alma: bileşenleri kapatır, install.sh'nin değiştirdiği ayarları
#  backup/values.tsv'deki ÖNCEKİ değerlerine döndürür, XFCE panelini geri açar.
#  Temalar/ikonlar silinmez (zararsız; istersen: ./uninstall.sh --themes).
# ============================================================
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VALS="$ROOT/backup/values.tsv"
MIRROR="$HOME/.local/share/liquid/values.tsv"
[ -f "$VALS" ] || { [ -f "$MIRROR" ] && VALS="$MIRROR"; }      # proje yedeği yoksa dıştaki kopya
say() { echo -e "\n\033[1;36m>> $*\033[0m"; }

say "Liquid kapatılıyor"
rm -f "$HOME/.config/autostart/liquid.desktop"
"$ROOT/bin/liquid" compositor xfwm >/dev/null 2>&1 || true     # picom → xfwm4 compositor (önceki değer)
"$ROOT/bin/liquid" stop >/dev/null 2>&1 || true
sleep 1

say "Ayarlar geri yükleniyor"
if [ -f "$VALS" ]; then
  # en son yazılan önce geri alınır (aynı özellik bir kez kaydedilir zaten)
  tac "$VALS" | while IFS=$'\t' read -r ch p typ old pat; do
    [ -n "$ch" ] || continue
    # kullanıcı Liquid'den sonra kendisi değiştirdiyse (ör. başka duvar kâğıdı seçtiyse) dokunma
    if [ -n "$pat" ]; then
      cur="$(xfconf-query -c "$ch" -p "$p" 2>/dev/null)" || cur=""
      # shellcheck disable=SC2254
      case "$cur" in $pat) ;; *) echo "   · $ch $p: sonradan değiştirilmiş ($cur) — korunuyor"; continue ;; esac
    fi
    if [ "$old" = "__UNSET__" ]; then
      xfconf-query -c "$ch" -p "$p" -r 2>/dev/null
    else
      xfconf-query -c "$ch" -p "$p" -t "$typ" -s "$old" --create 2>/dev/null
    fi
  done
  mv "$VALS" "$VALS.restored-$(date +%Y%m%d-%H%M%S)"
  rm -f "$MIRROR"
  echo "   ✓ ayarlar önceki değerlerine döndü"
else
  echo "   ! backup/values.tsv yok — geri yüklenecek ayar kaydı bulunamadı"
fi

G4="$HOME/.config/gtk-4.0"                      # install.sh'nin GTK4 stilleri (işaret dosyasıyla)
if [ -f "$G4/.liquid" ]; then
  rm -rf "$G4/"{gtk.css,gtk-dark.css,gtk-Light.css,gtk-Dark.css,assets,windows-assets,.liquid}
  [ -d "$ROOT/backup/gtk-4.0.orig" ] && cp -a "$ROOT/backup/gtk-4.0.orig/." "$G4/"
  rmdir "$G4" 2>/dev/null
  echo "   ✓ GTK4 teması kaldırıldı"
fi

XP="$HOME/.xprofile"
[ -f "$XP" ] && sed -i '/# LIQUID-START/,/# LIQUID-END/d' "$XP" && echo "   ✓ ~/.xprofile temizlendi"

say "XFCE paneli açılıyor"
pgrep -x xfce4-panel >/dev/null || setsid -f xfce4-panel >/dev/null 2>&1 < /dev/null
echo "   ✓ panel"

if [ "${1:-}" = "--themes" ]; then
  rm -rf "$HOME/.local/share/icons/MacTahoe" "$HOME/.local/share/icons/MacTahoe-light" \
         "$HOME/.local/share/icons/MacTahoe-dark" "$HOME/.local/share/icons/WhiteSur-cursors" \
         "$HOME/.local/share/backgrounds/liquid"
  sudo rm -f /usr/share/xfce4/backdrops/liquid-golden-gate.jpg
  echo "   ✓ kullanıcı temaları silindi (sistem teması için: sudo rm -rf /usr/share/themes/MacTahoe-*)"
fi
echo -e "\n\033[1;32m✓ Geri alındı.\033[0m"
