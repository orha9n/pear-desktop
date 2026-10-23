# Liquid — macOS 27 görünümü, Linux Mint XFCE için (sıfırdan)

> Bu dosya projenin hafızasıdır. Her adımdan önce oku, her adımdan sonra **Durum** ve
> **Günlük** bölümlerini güncelle. Kullanıcının kararları ve öğrenilen tuzaklar burada.

## 1. Kullanıcının istekleri (aynen)
- Hedef: `~/Desktop/upgrade-to-macos-27-golden-gate-hero.png` içindeki görünüm — **native, kendin üret**.
- macOS 27 tasarımını Linux Mint'e getir. **Cupertino üzerinden gitme.** Beğendiğin bileşen
  (tema, ikon seti vb.) varsa kullan, ama sistemi **kendin, sıfırdan** yap.
- `~/Desktop/macbook` içeriğini tamamen sil, tüm geliştirme **bu klasörün içinde** olsun. ✅ silindi
- Geliştirme ve uygulama yükleme yetkisi verildi; çekinmeden geliştir. Gerekirse soru sor.
- Yapılacak her şeyi önce bu MD dosyasına yaz (unutmamak için).
- Daha önceki geri bildirimler: duvar kâğıdını değiştirmek "macOS görünümü" değildir — asıl iş
  menü çubuğu, dock, pencereler, widget'lar; "benziyor" deme, ölç ve karşılaştır.
  Silme/yıkıcı işlemlerden önce kapsamı netleştir.

## 2. Hedef tasarım (PNG'den ölçülenler)
Görüntüdeki ekran ≈ 1335×865 px (MacBook Air 13", ~0.91 ölçek). 1920×1080 ekranda karşılıkları:

| Öğe | Görünüm | 1920×1080 hedef |
|---|---|---|
| **Menü çubuğu** | **Tamamen saydam**, arka plan yok; beyaz yazı/ikon doğrudan duvar kâğıdında (hafif gölge) | yükseklik 30 px, yazı 13 px |
| Sol | Elma logosu · **Finder** (kalın) · Dosya · Düzen · Görüntü · Git · Pencere · Yardım | öğe arası ~10 px |
| Sağ | Pil (beyaz dolu kapsül) · Wi-Fi · Spotlight (büyüteç) · Control Center · `1 Nis Çar 09:41` | tarih biçimi `%-d %b %a %H:%M` |
| **Widget: Takvim** (küçük) | Beyaz kart, köşe ~22; `NİSAN` kırmızı kalın küçük harf başlık; P S Ç P C C P; bugün kırmızı daire; hafta sonu gri | 180×180, sol 18, üst 48 |
| **Widget: Analog saat** (küçük) | Cam kart (yarı saydam bulanık); beyaz kadran, siyah rakamlar 1–12, siyah akrep/yelkovan, turuncu saniye | 180×180, takvimin sağında 18 px boşluk |
| **Widget: Fotoğraf** (orta) | Fotoğraf kartı, köşe ~22, kenarsız | 378×180, takvimin altında |
| **Dock** | **Liquid Glass**: çok saydam, bulanık arka, üst kenarda parlak ince çizgi, yumuşak gölge, köşe ~26 | ikon 52, yükseklik 72, alttan 8 |
| Dock içeriği | Finder · **Uygulamalar** (ızgara ikonu = Launchpad'in yerini alan) · tarayıcı · Mesajlar · Mail · Haritalar · Fotoğraflar · FaceTime · Telefon · Takvim · Kişiler · Anımsatıcılar · Notlar · TV · Müzik · … · App Store · iPhone · Ayarlar · ayraç · İndirilenler · Çöp | çalışan uygulamada altta nokta |
| **Duvar kâğıdı** | Golden Gate, gün batımı, kayalık kıyı | özgür lisanslı benzer foto (Apple'ınki kullanılmaz) |
| **Pencereler** | macOS 26 Tahoe: büyük köşe, trafik ışıkları solda, başlık ortada | MacTahoe GTK + xfwm4 |
| **İkonlar** | macOS 26 tarzı (cam/parlak kare ikonlar) | MacTahoe icon theme |

## 3. Mimari (her şey `~/Desktop/macbook` içinde)
Dil: **Python 3 + GTK3 + cairo** (Mint'te hazır; PySide/pip YOK). Hepsi bizim kodumuz.
Dış bileşenler (sadece görsel varlık): MacTahoe GTK teması, MacTahoe ikonları, WhiteSur imleçleri,
Inter yazı tipi, özgür lisanslı Golden Gate fotoğrafı.

```
macbook/
  PLAN.md                 ← bu dosya
  README.md
  install.sh              ← bağımlılıklar (apt), temalar, yedek, ayarlar, autostart
  uninstall.sh            ← yedekten tam geri dönüş
  liquid/                 ← Python paketi
    core/                 ← ortak: tasarım sabitleri, glass çizimi, duvar kâğıdı bulanıklığı,
                            daemon/pid/sinyal, uygulama eşleme, i18n (tr/en)
    bar.py                ← saydam menü çubuğu + global menü + sağ durum ikonları
    dock.py               ← Liquid Glass dock
    apps.py               ← "Uygulamalar" (Launchpad) tam ekran ızgara + arama
    widgets.py            ← masaüstü widget'ları (takvim, analog saat, fotoğraf)
    controlcenter.py      ← Control Center (GTK)
    spotlight.py          ← Spotlight (GTK, cam kapsül)
    session.py            ← tüm bileşenleri başlatan/izleyen bekçi (tek autostart girdisi)
  assets/                 ← kendi SVG'lerimiz (Apps ikonu, glifler), duvar kâğıdı
  tools/                  ← ekran görüntüsü/karşılaştırma yardımcıları
```

## 4. Adımlar
1. [x] PNG'yi analiz et, ölç (bölüm 2)
2. [x] `macbook` klasörünü boşalt
3. [x] Proje iskeleti + git init + PLAN.md
4. [x] `core/`: tasarım sabitleri, glass çizici, wallpaper blur, daemon yardımcıları, app eşleme
5. [x] Bağımlılıkları kur (apt — sudo parolasını kullanıcı terminalde girer)
6. [x] MacTahoe GTK + ikonlar + imleç + Inter + duvar kâğıdı (indir, `~/.themes`, `~/.local/share/icons`)
7. [ ] `bar.py` — saydam menü çubuğu (PNG ile ölçerek karşılaştır)
8. [x] `dock.py` — Liquid Glass dock (önizlemede MacTahoe ikonlarıyla doğrulandı)
9. [x] `widgets.py` — takvim, analog saat, fotoğraf (önizlemede doğrulandı)
10. [x] `launcher.py` — Uygulamalar ızgarası (bellek çiziminde doğrulandı)
11. [x] `controlcenter.py`, `spotlight.py` (GTK, bellek çiziminde doğrulandı)
12. [x] `session.py` + `ctl.py` + `bin/liquid` + autostart + `install.sh` / `uninstall.sh`
    (her değiştirilen xfconf özelliğinin eski değeri backup/values.tsv'de; uninstall sadece onları döndürür)
13. [ ] Tam ekran görüntüsü al, PNG ile yan yana karşılaştır, farkları listele ve kapat
14. [ ] Kullanıcıya göster

## 5. Öğrenilen tuzaklar (önceki denemelerden — TEKRARLAMA)
- **Daemon'ları benim Bash aracımdan başlatma**: araç bitince süreçler ölüyor. Kalıcı süreçler
  kullanıcının terminal sekmesinden (`run_in_terminal`) ya da autostart ile başlamalı.
- **Sinyal maskesi miras kalır**: terminalden başlayan süreçlerde SIGUSR1 engelli geliyor → her
  daemon başında `signal.pthread_sigmask(SIG_UNBLOCK, {SIGUSR1})`.
- **appmenu-gtk-module** bir süreçteki `Gtk.MenuBar`'ı gizler → bar sürecinde `GTK_MODULES`'tan
  çıkar, `UBUNTU_MENUPROXY=0` (Gtk import'tan ÖNCE).
- Menü popup'ı **tetikleyici olaysız** açılmaz ("no trigger event") → `Gtk.get_current_event()` ver,
  uzun iş (nmcli tarama) popup'tan önce yapılmasın.
- `xfce4-panel --quit` süreci de "xfce4-panel" adını taşır → döngüde çalıştırma (onlarca GDBus
  hata penceresi açılmıştı). Paneli kapatmak için gerçek panel PID'ine SIGTERM, bir kez.
- Panel yokken `xfce4-panel -r` **bekleyip kilitler** → önce `pgrep -x xfce4-panel`.
- `pkill -f <desen>` kendi bash komut satırını da öldürür → PID'lerle tek tek.
- `set -e` + `x="$(cat yok)"` betiği sessizce bitirir → `|| true`.
- `Gio.DesktopAppInfo.new()` olmayan uygulamada TypeError atar → try/except.
- `GIO_LAUNCHED_DESKTOP_FILE` alt süreçlere miras kalır → `_PID` eşleşirse güven.
- `nmcli` çıktısı: `LC_ALL=C.UTF-8` (C → Türkçe karakter bozulur), `--rescan no` (yoksa 3+ sn).
- Kullanıcının `~/.config/gtk-3.0/gtk.css` dosyasında panel kuralları var (`background-image: none`);
  ona dokunmadan bizim pencerelerimizde kendi CSS sağlayıcımızı kullan (USER+ öncelik).
- Kullanıcının kendi kısayolları: ses tuşları → `~/.local/bin/linuxhelper-ses`, Super_L → linuxhelper.
  **Ses tuşlarına ve Super'e dokunma** (sormadan). Print tuşu: `xfce4-screenshooter`.
- Orijinal ayar yedeği olmadan hiçbir xfconf değişikliği yapma; kaldırma betiği yedekten dönmeli
  ve önce test edilmeli.
- Duvar kâğıdını değiştirmek görünümü macOS yapmaz; ama bu hedefte duvar kâğıdı tasarımın parçası.

## 6. Kararlar
- Proje adı: **Liquid** (Apple adı/markası kullanılmaz; "Finder" vb. sadece menü metni).
- Dock büyütmesi (magnification): macOS varsayılanı **kapalı** → kapalı, ayarla açılabilir.
- Duvar kâğıdı: Apple'ın görseli kopyalanmaz; özgür lisanslı Golden Gate gün batımı fotoğrafı.
- Uygulama eşleme (macOS adı → Linux uygulaması): Finder=Thunar, tarayıcı=Firefox, Mail=Thunderbird,
  Müzik=Rhythmbox, Ayarlar=XFCE Ayarlar Yöneticisi, App Store=mintinstall, Terminal=xfce4-terminal.
  Kurulu olmayanlar dock'a konmaz.

## 6b. Kullanıcıya sorulacaklar (sona bırakıldı)
- Masaüstü klasör simgeleri widget'ların arkasında kalıyor; hedefte masaüstü simgesi yok →
  gizlensin mi (xfdesktop `/desktop-icons/style 0`), yoksa widget'lar başka yere mi?

## 7. Durum
- Şu an: adım 5–6. Masaüstü: kullanıcının orijinal XFCE düzeni (alt panel, Mint-L-Teal,
  Robu-Light). Cupertino tamamen kaldırıldı; Cupertino'nun 33 apt paketi 16:06'da **kaldırıldı**
  (kullanıcıya yanlışlıkla "iptal edildi" dedim, düzeltildi).
- Kurulu: `~/.local/share/icons/MacTahoe{,-light,-dark}`, `~/.local/share/icons/WhiteSur-cursors`,
  duvar kâğıdı `assets/wallpaper/golden-gate.jpg` (Levi Clancy, CC BY-SA 4.0 — atıf zorunlu).
- apt ile kuruldu (16:2x): sassc libxml2-utils fonts-inter xdotool playerctl brightnessctl
  appmenu-gtk2-module appmenu-gtk3-module appmenu-registrar (+ python3-gi-cairo, wnck, dbusmenu zaten vardı).
- MacTahoe GTK/xfwm4: **/usr/share/themes/MacTahoe-{Light,Dark}** (sudo ile, sistem geneli).
- Kullanıcı: "sudo gereksin sorun yok, çekinme" → sudo gereken adımları terminalde başlat, parolayı o girer.
- `liquid/bar.py` ilk sürüm çalışıyor (saydam, beyaz yazı, global menü, sağ glifler, saat).

## 8. Günlük
- 16:1x — PLAN.md oluşturuldu, macbook boşaltıldı, MacTahoe GTK/ikon depoları erişilebilir doğrulandı.
- 16:16 — Duvar kâğıdı: Wikimedia "North Marshall Beach with Golden Gate Bridge 03" (CC BY-SA 4.0),
  16:9 kırpma + sıcak ton → assets/wallpaper/golden-gate.jpg (+CREDITS.md).
- 16:2x — core/ (design, wallpaper, daemon, apps, i18n), bar.py, glyphs.py, applemenu.py yazıldı;
  bar ekranda test edildi: saydam + beyaz yazı + "Claude Dosya Düzen…" + pil/wifi/arama/CC/saat.
- MacTahoe GTK betiği sudo'suz kullanıcı modunda hata gizleyip duruyordu → root ile kuruldu.
- dock.py: önizleme (tools/preview.py dock) — MacTahoe ikonları, cam gövde, ayraç, İndirilenler, Çöp OK.
  Not: Takvim ikonu "Tue" İngilizce (ikonun kendisi), Hesap Makinesi ikonu biraz büyük görünüyor.
- widgets.py: takvim/saat/fotoğraf önizlemede hedefe yakın. Fotoğraf: NOAA kamu malı (assets/widgets).
- launcher.py, controlcenter.py, spotlight.py yazıldı (GTK, PySide yok); bellek çizimleri doğru.
- session.py (bekçi + XFCE panelini SIGTERM ile kapatma), ctl.py, bin/liquid, install.sh, uninstall.sh.
- Sırada: install.sh'yi kullanıcının terminalinde çalıştır, tam ekran görüntüsünü PNG ile karşılaştır.
