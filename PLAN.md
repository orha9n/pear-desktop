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
7. [x] `bar.py` — saydam menü çubuğu (PNG ile ölçerek karşılaştır)
8. [x] `dock.py` — Liquid Glass dock (önizlemede MacTahoe ikonlarıyla doğrulandı)
9. [x] `widgets.py` — takvim, analog saat, fotoğraf (önizlemede doğrulandı)
10. [x] `launcher.py` — Uygulamalar ızgarası (bellek çiziminde doğrulandı)
11. [x] `controlcenter.py`, `spotlight.py` (GTK, bellek çiziminde doğrulandı)
12. [x] `session.py` + `ctl.py` + `bin/liquid` + autostart + `install.sh` / `uninstall.sh`
    (her değiştirilen xfconf özelliğinin eski değeri backup/values.tsv'de; uninstall sadece onları döndürür)
13. [x] Tam ekran görüntüsü al, PNG ile yan yana karşılaştır, farkları listele ve kapat
14. [x] Kullanıcıya göster (16:43 ekran görüntüsü)

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

## 6b. Kullanıcı kararları
- Masaüstü simgeleri: **kalsın, kullanıcı nereye koyduysa orada** ("macOS'ta klasörler her yerde
  olabilir", "sağ üstten dizmek diye bir şey yok"). Simgeleri ASLA otomatik dizme/taşıma
  (`xfdesktop --arrange`, gravity YOK). 16:42'de yanlışlıkla dizdim → orijinal row/col'ler
  icons.screen0-1904x1015.rc'den geri yüklendi (16:44).

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
- 16:36 — install.sh kullanıcının terminalinde (c7) çalıştı: 7 bileşen ayakta, XFCE paneli kapalı.
  Tam ekran görüntüsü PNG'ye çok yakın. Farklar: kullanıcının masaüstü klasör simgeleri (karar
  kullanıcıda), dock takvim ikonu "Tue" → kendi canlı takvim ikonumuz ("Cum 23"), Finder noktası.
- Sinyal testleri: CC ve Spotlight açılıyor. Uygulamalar ekranı Claude penceresinin ALTINDA kalıyordu:
  kullanıcının Claude penceresi "her zaman üstte" ve xfwm4 fullscreen'de bizim ABOVE bayrağını
  düşürüyordu → launcher artık DIALOG tipi + ekran boyutu (fullscreen yok); hepsine show sonrası
  set_keep_above + raise. Doğrulandı.

- 16:43 — HATA: simgeleri sağ üste dizdim; kullanıcı istemedi → 16:44 orijinal konumlar geri yüklendi,
  gravity ayarı kaldırıldı, install.sh'den çıkarıldı.
- Açık noktalar: masaüstü simge etiketleri açık gökyüzünde zor okunuyor (xfdesktop yazısına gölge
  için kullanıcının gtk.css'ine dokunmak gerekir → sorulmadan YAPMA); global menüler için oturumu
  kapatıp açmak gerekiyor; GTK uygulama pencerelerinin trafik ışıkları ekranda henüz gözle doğrulanmadı.

- 16:49 — Kullanıcı: "eski Linux Mint arkaplanları nerede" → silinmemişlerdi; XFCE Masaüstü ayarları
  sadece geçerli resmin klasörünü listeliyor. Duvar kâğıdı /usr/share/xfce4/backdrops/
  liquid-golden-gate.jpg'ye taşındı (sudo); install/uninstall güncellendi. Widget'ları ve dock'tan
  Chrome/Müzik'i kullanıcı KENDİSİ kaldırdı → geri koyma.

## 5b. Yeni tuzaklar
- xfwm4: fullscreen() olan pencerede _NET_WM_STATE_ABOVE düşüyor; kullanıcının "her zaman üstte"
  pencereleri öne geçer. Tam ekran katmanları için DIALOG + ekran boyutu kullan.
- Duvar kâğıdını ayrı klasöre koyma: XFCE ayarlarında diğer duvar kâğıtları kaybolmuş görünür.
- Bekçi (session.py) bir bileşeni öldürünce 5 sn içinde YENİ koduyla açar → kod değişince
  `kill $(cat $XDG_RUNTIME_DIR/liquid/<ad>.pid)` yeterli.

- 20:3x — problems.md yazıldı (35 madde). Düzeltilenler: (1) Wnck segfault — bar/dock Wnck.Window'u
  öznitelikte tutmuyor, XID tutuyor; (2) çöp boşaltma onayı (`applemenu.confirm_empty_trash`);
  (3) widget süreci widget'sız da ayakta, SIGUSR1 yutuluyor; uyarı kartlarının saydam arka planı.

## 5c. Yeni tuzaklar
- **Wnck.Window'u Python özniteliğinde/listede SAKLAMA**: pencere kapanınca libwnck nesneyi yok eder,
  Python referansı sonradan bırakınca `g_object_unref → g_hash_table_remove` segfault (bar+dock aynı
  anda düşüyordu). XID sakla, `Wnck.Window.get(xid)` ile o an al.
- İşleyicisi olmayan süreçlere SIGUSR1 gönderme: varsayılan davranış süreci öldürmek.
- `set_app_paintable(True)` pencerede GTK CSS arka planı çizilmez → arka planı draw'da kendin çiz.
- Bileşen kodunu test ederken pencereyi kullanıcının ekranında açma/tıklama: kullanıcı aynı anda
  masaüstünü kullanıyor olabilir.
- 20:5x — macOS tam ekranı (`liquid/fullscreen.py`): xfwm4 yeşil düğmesi (ve Claude gibi kendi
  düğmesini çizen kenarlıksız uygulamaların ☐ düğmesi) büyütme anında imleç trafik ışığı
  bölgesindeyse tam ekrana çevrilir; klavye/çift tık büyütmesi "Doldur" olarak kalır. Tam ekranda
  bar+dock saydam/tıklanamaz; üst kenarda trafik ışıklı başlık şeridi (yeşil = çık), alt kenarda dock.
  ⌃⌘F (`<Primary><Super>f` → `liquid fullscreen`, yedekli). Test: 4 senaryo geçti, çökme yok.
- Claude uygulaması kenarlıksız (`_MOTIF_WM_HINTS` dekorasyon=0); ✕ – ☐ düğmelerini uygulama çiziyor →
  tema yeşile boyayamaz (asar yaması güncellemede silinir; zorla xfwm çerçevesi = çift başlık).

## 5d. Yeni tuzaklar
- xfwm4 tam ekran pencereyi DOCK tipindeki çubuk/dock'un ALTINDA bırakıyor → tam ekranda kendimiz
  gizliyoruz. Unmap ETME (strut kalkar, büyütülmüş pencereler yeniden boyutlanır): opacity 0 + boş input shape.
- Wnck'de büyütme durumu ile geometry-changed sırası belirsiz → yeşil tık kontrolünde ~120 ms
  önceki geometri kullanılır.
- 21:0x — Kullanıcı düzeltmesi: macOS'ta yeşil düğme pencereyi menü çubuğunun ÜSTÜNE büyütmez; menü
  şeridi düz açık/koyu renge döner, pencere altından ekranın en altına (dock alanı dahil) uzar.
  → Yeşil düğme artık X tam ekranı DEĞİL, "macOS tam ekranı": istemci (0, 30, 1920, 1050), xfwm4 başlık
  çubuğu opak menü çubuğunun arkasında; çubuk düz renk (koyu temada koyu), dock gizli/altta belirir,
  çubuk üzerinde 0,6 sn bekleyince altında trafik ışıklı şerit. Durum: $XDG_RUNTIME_DIR/liquid/
  fullscreen.json (bar yeniden başlarsa korunur; dock SIGUSR2 ile haber alır). ⌃⌘F → bar'a SIGUSR2.
  Uygulamanın kendi tam ekranı (F11/video) ayrı: çubuk+dock gizli, şerit en üstte. Test: 6 adım + F11 geçti.

## 5e. Yeni tuzaklar
- xfwm4 `_NET_MOVERESIZE_WINDOW` (wnck set_geometry) konumuna çerçeve kalınlığını bir kez DAHA ekliyor:
  istek = istemci − 2×kenar. Başlık çubuğunu üst strut'un altına sokmuyor → yerleştirirken bar
  strut'u ~0,4 sn kaldırılır; geri gelince pencere yerinde kalır.
- GTK pencerede `_MOTIF_WM_HINTS` değiştirip unmap/map yapmak başlığı kaldırmıyor (GTK haritalarken
  kendi ipucunu yeniden yazıyor).
- 21:0x — HATA (kullanıcı ekranda gördü): Claude ☐ ile macOS tam ekranına girince pencere y=0'a
  kaydı (üst 30 px menünün arkasında, altta 30 px duvar kâğıdı boşluğu). Düzeltme: kenarlıksız
  pencerelerde bar strut'u kaldırılmıyor + 0,7 sn sonra konum doğrulanıp gerekirse yeniden yerleştiriliyor.
  Gerçek Claude penceresinde ☐ çıkış/giriş test edildi: (0, 30, 1920, 1050).
- Tuzak: Electron, çalışma alanı (strut) değişince kendi sınırlarını yeniden uygular → kenarlıksız
  pencerelerde strut'a dokunma; yerleştirmeden sonra her zaman doğrula.
- 21:07 — Kullanıcı: macOS tam ekranında üst şerit YALNIZCA düz renk olmalı (menü, simge, saat yok).
  → mac modunda bar'ın içeriği gizleniyor (`get_child().set_visible`). Normal pencereye geçince geri geliyor (test edildi).
- 21:09 — Kullanıcı: imleç en üst çubuğa gelince menü içeriği GÖRÜNMELİ (macOS). → mac modunda 100 ms
  imleç yoklaması: çubuktayken içerik görünür; menü açıkken (uygulama/Elma/pil/Wi-Fi) ya da imleç alttaki
  başlık şeridindeyken açık kalır; aşağı inince düz renk. Claude tam ekranında ekran görüntüsüyle doğrulandı.
- 21:2x — problems.md 1. grup düzeltildi (6, 8, 11, 12, 14–19, 21, 23, 27, 30–32, 34, 35). Tüm bileşenler +
  bekçi yeniden başlatıldı. Kullanıcı: testlerde fareyi/ekranı KULLANMA (xdotool tıklaması reddedildi) →
  bundan sonra doğrulama ekran dışı (birim test, kuru çalıştırma, süreç sayımı) ya da kullanıcıya sorarak.
- 21:3x — problems.md 2. grup düzeltildi (4, 5, 9, 13, 20, 24, 28, 29). Karanlık Mod paleti `core/design.py`'de;
  yeni renk yazarken sabit (0,0,0,a) yerine `design.ink(a)` vb. kullan (gölge/karartma hariç).
- 21:4x — problems.md 3. grup: tepsi (XApp monitör + xapp-sn-watcher, MATE ortamıyla), GTK4 teması
  (~/.config/gtk-4.0, sassc), monitör değişince yeniden başlatma. İkinci monitör çubuğu açık.
## 5f. Yeni tuzaklar
- xapp-sn-watcher yalnız org.x.apps.statusicon status-notifier-enabled-desktops (MATE, Cinnamon) içinde
  çalışır, XFCE'de sessizce çıkar → ayarı değiştirme, süreç ortamında XDG_CURRENT_DESKTOP=MATE.
- MacTahoe SCSS'i derlemek için önce _theme-options-temp.scss ve _gtk-base-temp.scss kopyaları gerekir.
- GObject.BindingFlags (GLib.BindingFlags DEĞİL).
- 21:4x — Bellek (26): bileşen başına ~270 MB'ın nedeni 9600×5400 progressive JPEG (libjpeg küçük ölçekte de
  tüm katsayıları tutuyor). draft + malloc_trim + ekran boyutlu PNG disk önbelleği (flock ile tek çözüm).
  PSS toplamı 1370 → 219 MB. Ölçümde RSS değil PSS'e (smaps_rollup) bak.
- 21:5x — Gerçek cam (25): picom 10 (glx, dual_kawase). `liquid/compositor.py` + `liquid/picom.conf`; seçim
  ~/.config/liquid/compositor.json (önceki xfwm4 use_compositing değeriyle), bekçi picom'u ayakta tutar,
  2 dk'da 4 düşüşte xfwm4'e döner. Blur yalnız WM_WINDOW_ROLE=liquid-glass pencerelerde; bulanıklık/gölge
  pencerenin X şeklini izler (compositor.shape). Dock: altında ayrı DockGlass penceresi (tam genişlik
  şerit, şekli cam; _NET_RESTACK ile hep dock'un ALTINDA), ton/kenar dock penceresinde.
## 5g. Yeni tuzaklar
- picom koşulunda olmayan özellik karşılaştırması yanlış döner: `role != 'x'` rolsüz pencerelerde de false
  → "hariç tut" için `! role = 'x'` yaz.
- Popen ile başlatılan picom kapanınca toplanmazsa zombi kalır, /proc/comm hâlâ "picom" der → setsid -f ile
  başlat, /proc/PID/stat durumunda Z'yi say(ma).
- compositor xfwm'e dönerken ÖNCE seçimi kaydet, sonra picom'u durdur (yoksa bekçi arada geri açar).
- 24.10 — Kullanıcı: (1) açılır menülerde yazı beyaz + siyah gölge; (2) menü açıkken ses/Print tuşları
  çalışmıyor. (1) GTK3'te menubar'a bağlı popup'ın CSS düğümü tetikleyici menuitem'in ALTINDA →
  `#lbar menubar > menuitem label` alt menü etiketlerine de uyuyordu (ID özgüllüğü menu_css'i eziyordu).
  Bar seçicileri `> label` / `> image` yapıldı. (2) Açık Gtk.Menu klavyeyi X grab'ıyla alıyor, xfsettingsd
  kısayolu göremiyor → `applemenu.forward_shortcut_keys()` (install_css("menu") ile bar/dock/widgets'ta):
  bu sürece gelen XF86*/Print basışı kullanıcının kendi `/commands/custom/<accel>` komutuyla çalışır
  (kısayollar değiştirilmedi). Başka uygulamaların menüleri (tepsi, Electron) açıkken hâlâ çalışmaz.
## 5h. Yeni tuzaklar
- Alt menüye sızmasın: bar CSS'inde torun (` label`) değil çocuk (`> label`) seçici kullan; text-shadow kalıtsal.
  dbusmenu/fallback öğeleri `menuitem > box > label` (bar.item) → o yolu da ekle (24.10 19:16 büyük yazı hatası).
- GDK 3.24'te `keyval_name(XF86AudioRaiseVolume)` = "AudioRaiseVolume" (önek yok); xfconf "XF86…" bekler.
- Menü çubuğu dikey hiza: Inter yazısı ortalanınca büyük harfler 1 px yukarıda kalıyor → etiketlere padding-top 2px; ölçüm: yazı/elma/simge merkezi 14,5 px (30 px çubuk).
- Tepsi simgesi sembolik değilse CSS rengi almaz → `tray.template()` tek renkli pixbuf.ı alfa korunarak çubuk rengine boyar; renkli simgeye dokunmaz.
- 24.10 — Kullanıcı: "widget ekleme yerini takvime (saate) basınca görünecek şekilde koymuşsun, Apple'da böyle değil".
  macOS 26 davranışı: saat/tarih tıklaması → **Bildirim Merkezi** (sağda cam panel, bildirimler; en altta
  "Widget'ları Düzenle…"). Widget galerisi ekranın **altında ortada** geniş cam sayfa: canlı önizlemeler,
  tıkla = masaüstüne ekle, sağ altta "Bitti". Düzenleme modunda masaüstü widget'larının sol üst köşesinde
  "−" rozeti (tıkla = kaldır). Widget sağ tık → "Widget'ları Düzenle…" de galeriyi açar.
  Bildirimler: xfce4-notifyd geçmişi ~/.cache/xfce4/notifyd/log.sqlite (yalnız OKU).
  Yapılmayan: masaüstü (xfdesktop) sağ tık menüsüne öğe ekleme (xfdesktop'un menüsü).
