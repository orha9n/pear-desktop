#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-only
# ============================================================
#  Liquid — geri alma: bileşenleri kapatır, install.sh'nin değiştirdiği ayarları
#  Kullanıcı veri dizinindeki ÖNCEKİ değerlerine döndürür, XFCE panelini geri açar.
#  Temalar/ikonlar silinmez (zararsız; istersen: ./uninstall.sh --themes).
# ============================================================
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REMOVE_THEMES=0
for arg in "$@"; do
  case "$arg" in
    --themes) REMOVE_THEMES=1 ;;
    -h|--help) echo "Kullanım: ./uninstall.sh [--themes]"; exit 0 ;;
    *) echo "Bilinmeyen seçenek: $arg" >&2; exit 2 ;;
  esac
done
[ "$(id -u)" != 0 ] || { echo "!! Kendi kullanıcınla çalıştır" >&2; exit 1; }
BK="$HOME/.local/share/liquid/backups"
VALS="$BK/values.tsv"
MIRROR="$HOME/.local/share/liquid/values.tsv"
[ -f "$VALS" ] || VALS="$ROOT/backup/values.tsv"
[ -f "$VALS" ] || { [ -f "$MIRROR" ] && VALS="$MIRROR"; }      # proje yedeği yoksa dıştaki kopya
say() { echo -e "\n\033[1;36m>> $*\033[0m"; }
FAILED=0

say "Pear kapatılıyor"
rm -f "$HOME/.config/autostart/liquid.desktop"
"$ROOT/bin/liquid" compositor xfwm >/dev/null 2>&1 || true     # picom → xfwm4 compositor (önceki değer)
"$ROOT/bin/liquid" stop >/dev/null 2>&1 || true
sleep 1

say "Ayarlar geri yükleniyor"
if [ -f "$VALS" ]; then
  # en son yazılan önce geri alınır (aynı özellik bir kez kaydedilir zaten)
  while IFS=$'\x1f' read -r ch p typ old pat; do
    [ -n "$ch" ] || continue
    # kullanıcı Liquid'den sonra kendisi değiştirdiyse (ör. başka duvar kâğıdı seçtiyse) dokunma
    if [ -n "$pat" ]; then
      cur="$(xfconf-query -c "$ch" -p "$p" 2>/dev/null)" || cur=""
      # shellcheck disable=SC2254
      case "$cur" in $pat) ;; *) echo "   · $ch $p: sonradan değiştirilmiş ($cur) — korunuyor"; continue ;; esac
    fi
    [ "$typ" = double ] && old="${old/,/.}"     # Türkçe yerel ayar "0,900000" yazar, xfconf yalnız "0.9" okur
    if [ "$old" = "__UNSET__" ]; then
      # Zaten silinmiş bir özellik başarıyla geri alınmış sayılır.
      if xfconf-query -c "$ch" -p "$p" >/dev/null 2>&1; then
        xfconf-query -c "$ch" -p "$p" -r 2>/dev/null || FAILED=1
      fi
    else
      xfconf-query -c "$ch" -p "$p" -t "$typ" -s "$old" --create 2>/dev/null || FAILED=1
    fi
  done < <(tac "$VALS" | tr '\t' '\037')
  if [ "$FAILED" = 0 ]; then
    if mv "$VALS" "$VALS.restored-$(date +%Y%m%d-%H%M%S)"; then
      rm -f "$MIRROR"
      echo "   ✓ ayarlar önceki değerlerine döndü"
    else FAILED=1; fi
  else
    echo "   ! Bazı ayarlar geri yüklenemedi; yedekler korundu. Oturum içinde yeniden dene." >&2
  fi
else
  echo "   ! Geri yüklenecek ayar kaydı bulunamadı"
fi

G4="$HOME/.config/gtk-4.0"                      # install.sh'nin GTK4 stilleri (işaret dosyasıyla)
if [ -f "$G4/.liquid" ]; then
  rm -rf "$G4/"{gtk.css,gtk-dark.css,gtk-Light.css,gtk-Dark.css,assets,windows-assets,.liquid}
  ORIG="$BK/gtk-4.0.orig"
  [ -d "$ORIG" ] || ORIG="$ROOT/backup/gtk-4.0.orig"
  if [ -d "$ORIG" ]; then
    if cp -a "$ORIG/." "$G4/"; then
      mv "$ORIG" "$ORIG.restored-$(date +%Y%m%d-%H%M%S)" || FAILED=1
    else
      touch "$G4/.liquid"
      FAILED=1
    fi
  fi
  rmdir "$G4" 2>/dev/null
  echo "   ✓ GTK4 teması kaldırıldı"
fi

LT="$HOME/.local/share/themes/Liquid"           # install.sh'nin bildirim teması (işaret dosyasıyla)
[ -f "$LT/.liquid" ] && rm -rf "$LT" && echo "   ✓ bildirim teması kaldırıldı"
PYTHONPATH="$ROOT" python3 -m liquid.desktopmenu remove && echo "   ✓ masaüstü menüsünden Widget'ları Düzenle… kaldırıldı" || FAILED=1
PYTHONPATH="$ROOT" python3 -m liquid.firefox remove || FAILED=1

XP="$HOME/.xprofile"
[ -f "$XP" ] && sed -i '/# LIQUID-START/,/# LIQUID-END/d' "$XP" && echo "   ✓ ~/.xprofile temizlendi"

say "XFCE paneli açılıyor"
pgrep -x xfce4-panel >/dev/null || setsid -f xfce4-panel >/dev/null 2>&1 < /dev/null
echo "   ✓ panel"

if [ "$REMOVE_THEMES" = 1 ]; then
  rm -rf "$HOME/.local/share/icons/MacTahoe" "$HOME/.local/share/icons/MacTahoe-light" \
         "$HOME/.local/share/icons/MacTahoe-dark" "$HOME/.local/share/icons/WhiteSur-cursors" \
         "$HOME/.local/share/backgrounds/liquid"
  sudo rm -f /usr/share/xfce4/backdrops/liquid-golden-gate.jpg
  echo "   ✓ kullanıcı temaları silindi (sistem teması için: sudo rm -rf /usr/share/themes/MacTahoe-*)"
fi
if [ "$FAILED" != 0 ]; then echo "!! Geri alma tamamlanamadı; yedekleri silmeden hataları kontrol et." >&2; exit 1; fi
echo -e "\n\033[1;32m✓ Geri alındı.\033[0m"
