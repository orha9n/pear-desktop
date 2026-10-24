# Liquid — tespit edilen sorunlar

Tarih: 23 Ekim 2026 · İncelenen: `~/Desktop/macbook` (tüm kod, install/uninstall betikleri), çalışan oturum
(`liquid status`, `~/.cache/liquid/*.log`, `journalctl`, `coredumpctl`) ve canlı ekran görüntüleri.

Önem: 🔴 kritik (çökme / veri kaybı) · 🟠 yüksek (özellik bozuk) · 🟡 orta · ⚪ düşük / kozmetik

---

## 🔴 Kritik

### 1. ✅ DÜZELTİLDİ — Menü çubuğu ve dock birlikte sürekli çöküyor (segfault)
> 23.10 20:3x: bar/dock artık `Wnck.Window` değil XID saklıyor (`Bar._window()`, `Item.wins`).
> Test: önce 8 pencere aç/kapa döngüsünde dock çöktü; düzeltmeden sonra 25 döngüde 0 segfault.
- **Kanıt:** `journalctl`: `python3[...]: segfault ... in libglib-2.0.so` — 20:14:03, 20:14:28, 20:15:54
  (3 dakikada 3 kez, her seferinde bar + dock **aynı anda**). `coredumpctl` 16:46'dan beri 10 çekirdek dökümü.
  Yığın: `g_object_unref → g_hash_table_remove` ← Python `PyObject_SetAttr`.
  Loglarda öncü uyarı: `g_hash_table_remove_internal: assertion 'hash_table != NULL' failed`.
- **Yer:** [bar.py:396](liquid/bar.py:396) `self.window = w ...`, [dock.py:182](liquid/dock.py:182)
  `it.windows = running.pop(...)`.
- **Neden:** Kapanmış bir `Wnck.Window` nesnesine Python referansı tutuluyor; pencere kapanınca libwnck
  nesneyi yok ediyor, Python eski referansı bıraktığında ölü nesneye `unref` → çökme. Bir pencere
  kapandığında iki süreç de aynı anda düşüyor.
- **Etkisi:** Çubuk ve dock birkaç dakikada bir kaybolup ~5 sn sonra geri geliyor (bekçi yeniden açıyor);
  açık menüler kapanıyor, global menü sıfırlanıyor.
- **Öneri:** `Wnck.Window` nesnelerini saklama; XID tut (`w.get_xid()`), gerektiğinde
  `Wnck.Window.get(xid)` ile al. `window-closed` sinyalinde ilgili referansları hemen temizle.

### 2. ✅ DÜZELTİLDİ — Çöp Kutusu onaysız ve geri dönüşsüz boşaltılıyor
> Dock ve Finder menüsü artık `applemenu.confirm_empty_trash()` onay kartını açıyor (geri sayım yok).
- **Yer:** [dock.py:540](liquid/dock.py:540) (Dock → Çöp sağ tık → "Çöp Kutusunu Boşalt"),
  [bar.py:542](liquid/bar.py:542) (Finder menüsü → "Çöp Kutusunu Boşalt…").
- `gio trash --empty` doğrudan çalışıyor. Menü metnindeki "…" bir onay penceresi açılacağını vaat ediyor
  ama açılmıyor. macOS'ta bu işlem her zaman onay ister. Yanlış tık = kalıcı veri kaybı.
- **Öneri:** `applemenu.confirm()` benzeri bir onay kartı ("Çöp Kutusundaki öğeleri kalıcı olarak silmek
  istediğinizden emin misiniz?").

---

## 🟠 Yüksek

### 3. ✅ DÜZELTİLDİ — Widget süreci her 5 saniyede bir boşuna başlatılıp kapanıyor
> Görünür widget olmasa da süreç ayakta kalıyor; PID kararlı olduğu doğrulandı.
- **Kanıt:** `liquid status` → `widgets —`; `ps` izlemesinde ~5 sn'de bir yeni `liquid.widgets` PID'i
  doğup ölüyor. `~/.config/liquid/widgets.ini`: üç widget da `hidden = 1`.
- **Yer:** [widgets.py:339-340](liquid/widgets.py:339) (görünür widget yoksa `return`) +
  [session.py:60-64](liquid/session.py:60) (bekçi her 5 sn'de eksik bileşeni yeniden başlatır).
- **Etkisi:** Sonsuz döngüde her seferinde Python + GTK yükleniyor (gereksiz CPU/pil tüketimi).
- **Öneri:** Widget yoksa da süreç ayakta kalsın (sinyal beklesin) ya da bekçi "bilerek kapandı"
  durumunu (çıkış kodu/işaret dosyası) tanısın.

### 4. ✅ DÜZELTİLDİ — Kaldırılan widget'ı geri eklemenin yolu yok
> Saate tıklayınca (ya da widget sağ tık → Widget'ları Düzenle…) sağ üstte "Widget'lar" galerisi: Takvim/Saat/Fotoğraf Ekle/Kaldır.
- Sağ tık → "Widget'ı Kaldır" `hidden=1` yazıyor ([widgets.py:130](liquid/widgets.py:130)); hiçbir yerde
  "Widget Ekle / Widget'ları Düzenle" yok (`i18n`'deki `edit_widget` metni hiç kullanılmıyor).
  Geri getirmek için `widgets.ini` elle düzenlenmeli.

### 5. ✅ DÜZELTİLDİ — Saate tıklamak widget sürecini öldürüyor
> Saat tıklaması artık Widget'lar galerisini açıyor (madde 4).
> SIGUSR1 artık yutuluyor (süreç ölmüyor, test edildi). Saate tıklamak şimdilik hiçbir şey yapmıyor;
> Bildirim Merkezi / widget ekleme (madde 4) için kullanılabilir.
- **Yer:** [bar.py:294](liquid/bar.py:294) saate tıklayınca `signal_component("widgets")` → SIGUSR1.
- `widgets.py` SIGUSR1 için işleyici kurmuyor ([widgets.py:325](liquid/widgets.py:325)); SIGUSR1'in
  varsayılan davranışı **süreci sonlandırmak**. Widget'lar açıkken saate tıklanınca hepsi kaybolur,
  5 sn sonra bekçi geri açar. (macOS'ta saat tıklaması Bildirim Merkezi'ni açar.)

### 6. ✅ DÜZELTİLDİ — Uygulama eşleme yanlış: Python betiği olan uygulamalar "Python (v3.12)" görünüyor
> Yorumlayıcı süreçlerde (python3.12 vb.) betik adına bakılıyor, WM_CLASS'tan `.py` atılıyor; sahte mintinstall penceresi "App Store" olarak eşlendi.
- **Kanıt:** Yazılım Yöneticisi (mintinstall) açıkken menü çubuğunda **"Python (v3.12)"** yazıyordu; dock'ta
  App Store yerine ayrı bir **Python** ikonu çalışıyor (noktalı) göründü.
- **Yer:** [core/apps.py:115-125](liquid/core/apps.py:115). WM_CLASS `mintinstall.py` eşleşmiyor,
  sonra `/proc/PID/exe` = `python3.12` → `python3.12.desktop` ile eşleşiyor. `_SKIP_EXE` yalnızca
  `.desktop` dizinini kurarken uygulanıyor, aday tarafında uygulanmıyor.
- **Etkilenen:** mintinstall, mintupdate, Mint araçlarının çoğu ve diğer Python/Java/Electron sarmalayıcı uygulamalar.
- **Öneri:** Adaylarda yorumlayıcıları (`python3*`, `java`, `node`, `electron`…) atla; WM_CLASS'tan `.py`
  sonekini sil; `/proc/PID/cmdline` içindeki betik adını da aday yap.

### 7. ✅ DÜZELTİLDİ — Sistem tepsisi (tray) yok: XFCE paneli zorla ve sürekli kapatılıyor
> `liquid/tray.py`: libxapp `XApp.StatusIconMonitor` + Mint'in SNI köprüsü `xapp-sn-watcher` (XFCE'de kendiliğinden çıktığı için yalnız kendi ortamında `XDG_CURRENT_DESKTOP=MATE` ile başlatılıyor). Blueman, Güncelleme Yöneticisi, sistem raporları görünüyor; nm-applet/güç yöneticisi çubuğun kendi simgelerini tekrarlamasın diye gizli. Köprü yokken başlamış SNI uygulamaları (ör. Claude) yeniden açılınca gelir. Eski XEmbed (_NET_SYSTEM_TRAY) ikonları desteklenmiyor.
- [session.py:61](liquid/session.py:61) her 5 sn'de XFCE paneline SIGTERM gönderiyor; panel elle açılsa da
  kapanır. Yerine bir bildirim alanı (StatusNotifier/XEmbed) yok.
- **Etkisi:** Tepsi ikonu kullanan uygulamaların (ör. Claude, güncelleme yöneticisi, Bluetooth, klavye düzeni,
  Dropbox/Telegram vb.) ikonları ve menüleri tamamen kayboluyor. Ses düzeyi, klavye düzeni göstergesi de yok.
- **Öneri:** Çubuğun sağına StatusNotifierItem/XEmbed tepsi desteği ekle (ya da XFCE panelini yalnız tepsi
  eklentisiyle küçük ve saydam bırak).

### 8. ✅ DÜZELTİLDİ — Uygulamaların çıktıları Liquid loglarına akıyor ve loglar sınırsız büyüyor
> Uygulamalar `launch_uris_as_manager` + `/dev/null` ile açılıyor (dock eylemleri, Spotlight `xdg-open` dahil); loglar 512 KB'ta `.log.1`'e dönüyor; bekçi kapanan bileşeni `session.log`'a yazıyor.
- **Kanıt:** `~/.cache/liquid/dock.log` içinde Chrome'un `ssl_client_socket_impl` hataları,
  `gnome-calculator` uyarıları var.
- **Yer:** [core/daemon.py:63-66](liquid/core/daemon.py:63) bileşenin stdout/stderr'i log dosyası;
  [core/apps.py:128](liquid/core/apps.py:128) `launch()` ile açılan uygulamalar bunu miras alıyor
  (dock, Uygulamalar ekranı, Spotlight).
- Log döndürme (rotation) yok; uzun oturumda dosyalar şişer. Çökmeler (madde 1) ise loga hiç yazılmıyor.
- **Öneri:** Uygulamaları başlatırken stdout/stderr'i `/dev/null`'a ya da ayrı dosyaya yönlendir; logu boyutla
  sınırla; bekçi bir bileşen yeniden başlatınca çıkış kodu/sinyali loglasın.

### 9. ✅ DÜZELTİLDİ — Global menü çoğu uygulamada boş kalıyor
> Menü gelmezse 0,7 sn sonra yedek menüler: Dosya (Yeni Pencere, Pencereyi Kapat), Düzen (tuşu uygulamaya gönderir), Görüntü (Tam Ekran), Pencere (Küçült, Doldur, Tümünü Öne Getir), Yardım. Registrar'ın kalıcı çalışması ayrıca ele alınmadı.
- Örn. Takvim (GNOME Calendar, GTK4) aktifken çubukta yalnız "Takvim" yazıyor, Dosya/Düzen/… yok.
  GTK4/libadwaita, çoğu Electron ve Firefox menülerini dışa aktarmıyor. macOS görünümünde sol taraf sık sık boş.
- `com.canonical.AppMenu.Registrar` sürekli çalışmıyor: `busctl --user list` → yalnızca "activatable";
  journal'da bar her yeniden başladığında yeniden etkinleştiriliyor (madde 1 ile birlikte). Kayıt
  hizmeti olmadığında Qt/Electron uygulamaları menülerini kaydedemez.
- **Öneri:** Menü dışa aktarmayan uygulamalar için en azından standart yedek menüler (Dosya: Yeni Pencere,
  Kapat; Pencere: Küçült/Büyüt; Yardım) göster; registrar'ı bar sürecinin içinde ya da kalıcı başlat.

### 10. ✅ DÜZELTİLDİ — GTK4/libadwaita uygulamaları temaya uymuyor
> install.sh MacTahoe'nun gtk-4.0 SCSS'ini `sassc` ile `~/.config/gtk-4.0`'a derliyor (MacTahoe betiği çalıştırılmadan; `.liquid` işaretiyle, uninstall geri alır); Karanlık Mod `gtk.css` bağlantısını değiştiriyor. Bu sistemde kuruldu; GTK4 uygulamalarında GÖRSEL OLARAK DOĞRULANMADI (GTK4 Python bağlaması / sanal ekran yok).
- `~/.config/gtk-4.0` yok. Dock'taki **Takvim** ve **Hesap Makinesi** (GTK4) Mint/Adwaita görünümünde
  açılıyor: turkuaz vurgu, farklı pencere düğmeleri (ekran görüntüsünde doğrulandı).
- **Öneri:** MacTahoe kurulumunda libadwaita/GTK4 seçeneğini (`-l`) kullan ya da `gtk-4.0/gtk.css`'i bağla
  (yedekle ve uninstall'da geri al).

---

## 🟡 Orta

### 10b. ✅ DÜZELTİLDİ — Uyarı kartları (Yeniden Başlat, Kapat, Oturumu Kapat, Bu Mac Hakkında) saydamdı
- Düzeltme sırasında bulundu: `_card_window` `app_paintable` olduğu için GTK, CSS'teki `#lcard` arka planını
  çizmiyordu; kart metni arkadaki pencerelerin üstünde yüzüyordu. Arka plan artık `_card_bg()` ile
  çiziliyor ([applemenu.py](liquid/applemenu.py)).

### 11. ✅ DÜZELTİLDİ — Control Center menü çubuğundan tıklayınca açık kalmıyor (gözlem — doğrulanmalı)
> Tekrar üretilemedi: tıklayınca açılıp açık kalıyor. İlk açılış ~1,2 sn sürüyordu (cam arka planı o an hesaplanıyor) → başlarken önceden hesaplanıyor.
- `liquid toggle controlcenter` ile açılıp kapanıyor (doğrulandı). Ama menü çubuğundaki CC simgesine
  `xdotool` ile tıklandığında 1,5 sn sonra pencere `IsUnMapped` idi (2 deneme).
- Olası neden: açıldıktan hemen sonra gelen odak kaybı ([controlcenter.py:202](liquid/controlcenter.py:202)).
  Aynı desen Spotlight ve Uygulamalar ekranında da var: açıkken simgeye tıklamak **önce odak kaybıyla
  kapatıp sonra sinyalle yeniden açabilir** (aç/kapat çakışması).

### 12. ✅ DÜZELTİLDİ — Kaydırıcılar her fare hareketinde yeni süreç başlatıyor
> `Applier`: anahtar başına tek işçi, yalnızca son değer uygulanıyor (50 hareket → 2 tur).
- [controlcenter.py:384-388](liquid/controlcenter.py:384): sürüklerken her `motion` olayında
  `brightnessctl` ya da **iki** `pactl` süreci açılıyor (saniyede onlarca). Sıra garantisi yok;
  son değer bazen önceki komuttan önce uygulanıp ses/parlaklık "geri sıçrayabilir".
- **Öneri:** Değeri biriktir, 50–100 ms'de bir uygula (throttle), ya da PulseAudio/`/sys` API'sini doğrudan kullan.

### 13. ✅ DÜZELTİLDİ — Karanlık Mod Liquid bileşenlerini değiştirmiyor
> `design.dark()/ink()/paper()/surface()/tile()/glass_tint()` paleti; menüler, kartlar, Control Center, Spotlight, dock balonu/noktası, takvim/saat widget'ları, tam ekran şeridi temaya uyuyor ve tema değişince anında yenileniyor (ekran dışı çizimle iki temada doğrulandı).
- [controlcenter.py:89](liquid/controlcenter.py:89) yalnızca GTK/xfwm/ikon temasını değiştiriyor. Menü
  çubuğu menüleri, dock balonu, Control Center, Spotlight, onay kartları ve "Bu Mac Hakkında" sabit
  açık renkte çiziliyor ([applemenu.py:18](liquid/applemenu.py:18) `MENU_CSS` vb.). Karanlık modda
  uyumsuz görünür.

### 14. ✅ DÜZELTİLDİ — Spotlight: seçili satır görünmez olabiliyor
> Sonuçlar 9 satırla sınırlı; web araması her zaman son satır.
- Sonuç sayısı en fazla 1 (hesap) + 6 (uygulama) + 4 (dosya) + 1 (web) = 12; çizilen en fazla `MAXROWS = 9`.
  ↑/↓ seçimi `len(results)` üzerinden dönüyor ([spotlight.py:243](liquid/spotlight.py:243)) → seçim
  görünmeyen 10.–12. satırlara gidebiliyor; Enter görünmeyen öğeyi açar. "Web'de ara" satırı bu durumda hiç görünmez.

### 15. ✅ DÜZELTİLDİ — Spotlight hesaplayıcı büyük sayılarda hata veriyor
> Büyük tamsayılar `Decimal` ile bilimsel gösterim (`9^999` → `1,942079e+953`).
- `9^999` gibi bir giriş: üs sınırı (≤1000) geçiliyor, sonuç çok büyük tamsayı →
  [spotlight.py:67](liquid/spotlight.py:67) `f"{r:.6e}"` → `OverflowError` (yakalanmıyor; arama o tuşta güncellenmez).

### 16. ✅ DÜZELTİLDİ — Her tuşa/saniyeye alt süreç başlatılıyor
> Duvar kâğıdı ayarları tek `xfconf-query -lv` ile 4 sn önbellekte, `xrandr --current` 30 sn; Liquid'in alt süreçleri ~45 → 8 / 15 sn.
- `wallpaper.current()` her çağrıda `xrandr` + 2× `xfconf-query` çalıştırıyor
  ([core/wallpaper.py:21-43](liquid/core/wallpaper.py:21)). Çağrılan yerler:
  - Analog saat widget'ı **her saniye** ([widgets.py:135](liquid/widgets.py:135), [widgets.py:202](liquid/widgets.py:202)) → ~3 süreç/sn,
  - Spotlight **her tuş vuruşunda** ([spotlight.py:154](liquid/spotlight.py:154)),
  - dock her 2 sn, bar her 3 sn.
- **Öneri:** `xfconf-query -m` ile değişikliği izle (ya da xfconf D-Bus `PropertyChanged`) ve sonucu önbellekle.

### 17. ✅ DÜZELTİLDİ — Çalışma alanı değişince yanlış duvar kâğıdı kullanılıyor
> Etkin çalışma alanı (ya da xfdesktop "tümüne uygula" numarası) kullanılıyor; ortala/döşe/uzat/sığdır/yakınlaştır stilleri doğru çiziliyor.
- `wallpaper.current(workspace=0)` hep 0. çalışma alanını okuyor; bar/dock `active-workspace-changed`
  dinliyor ama yine workspace0'a bakıyor ([bar.py:224](liquid/bar.py:224), [dock.py:142](liquid/dock.py:142)).
  Çalışma alanlarında farklı duvar kâğıdı varsa dock camı ve menü çubuğu yazı rengi yanlış olur.
- Ayrıca stil 1 (ortala), 2 (döşe), 4 (ölçekle) "kapla" gibi hesaplanıyor → cam arka planı gerçek görüntüyle örtüşmez.

### 18. ✅ DÜZELTİLDİ — Uninstall, kurulumdan sonra yapılan duvar kâğıdı seçimlerini de eziyor
> values.tsv'ye 5. sütun (Liquid'in yazdığı değerin deseni); uninstall değeri sonradan değişmişse dokunmuyor. Kuru çalıştırma: kullanıcının çizgili duvar kâğıdı korunuyor.
- `install.sh` başlığı "sonradan yaptığın ayarlara dokunmaz" diyor, ama `uninstall.sh` `values.tsv`'deki
  her özelliği koşulsuz eski değere yazıyor ([uninstall.sh:19-27](uninstall.sh:19)). Kullanıcı bugün duvar
  kâğıdını zaten değiştirdi (Mint çizgili duvar kâğıdı); kaldırma bunu ezecek.
- **Öneri:** Geri yüklemeden önce mevcut değerin hâlâ Liquid'in yazdığı değer olup olmadığını kontrol et.

### 19. ✅ DÜZELTİLDİ — Wi-Fi menüsü
> Liste arka planda (`wifi.scan`) alınıyor; kayıtlı ağa `nmcli con up`, yeni şifreli ağa şifre kartı + NetworkManager D-Bus (şifre komut satırında görünmez); bağlı ağa tıklamak bir şey yapmıyor; hata bildirimi. Gerçek bir yeni ağa bağlanma denenmedi.
- Şifreli ve kayıtlı olmayan ağa tıklamak `nmcli dev wifi connect <ad>` ile **şifre sormadan** başarısız
  oluyor, kullanıcıya hiçbir şey gösterilmiyor ([bar.py:350](liquid/bar.py:350)).
- Ağ listesi menü açılmadan önce ana iş parçacığında senkron `nmcli` ile alınıyor ([bar.py:335](liquid/bar.py:335));
  NetworkManager yavaşsa çubuk donar.
- Bağlı ağın satırına tıklamak bağlantıyı yeniden kuruyor (CheckMenuItem durumu da tersine dönüyor).

### 20. ✅ DÜZELTİLDİ — Menüdeki kısayollar sadece yazı
> ⌘Q ⌘H ⌥⌘H ⌘M global kısayolları (`liquid app quit|hide|hide-others|minimize`, yedekli); test penceresinde ⌘M/⌘Q doğrulandı. Finder Düzen menüsü masaüstünde seçim olmadığı için macOS'taki gibi devre dışı kalıyor.
- ⌘Q, ⌘H, ⌥⌘H, ⌘N, ⇧⌘N, ⌘F, ⇧⌘G… menülerde yazıyor ama hiçbiri bağlı değil; yalnızca
  `Super+Space` → Spotlight kurulu. Finder menüsündeki Düzen (Geri Al, Kes, Kopyala…) ve Görüntü
  öğelerinin hepsi devre dışı (`None` geri çağrı) — işlevsiz menüler ([bar.py:550-552](liquid/bar.py:550)).
- `Super_L` tek başına kullanıcının `linuxhelper` kısayoluna bağlı; `Super+Space` ile çakışıp çakışmadığı
  (Super bırakılınca linuxhelper'ın da açılması) kontrol edilmeli.

### 21. ✅ DÜZELTİLDİ — Yardım menüsü olmayan dosyayı açıyor
> README.md yazıldı.
- Finder → Yardım → "Liquid" `README.md` açıyor ([bar.py:561](liquid/bar.py:561)); depoda `README.md` yok
  (PLAN.md'de listelenmiş ama yazılmamış).

### 22. ◐ KISMEN — Çoklu monitör desteklenmiyor
> Monitör eklenince/çıkarılınca ya da çözünürlük değişince bileşenler yeni boyutla yeniden açılıyor (benzetimle test edildi). İkinci monitörde menü çubuğu HENÜZ YOK; tek monitörlü sistemde test edilemiyor.
- Bar, dock, widget'lar, Spotlight, CC yalnızca birincil monitörde (`screen_geometry()`); ikinci monitörde
  menü çubuğu/dock yok. Monitör takılıp çıkarılınca boyutlar yeniden hesaplanmıyor (yeniden başlatma gerekir).

---

## ⚪ Düşük / kozmetik

23. ✅ (Dock `_poll` gün değişince yeniden çiziyor.) **Dock takvim ikonu gece yarısı güncellenmiyor:** gün sayısı yalnızca dock yeniden çizildiğinde
    değişiyor; zamanlayıcı yok ([dock.py:233](liquid/dock.py:233)). Fare dock'a gelene kadar dünün tarihi kalabilir.
24. ✅ (Tıklama öne getirir, küçültmez; tümü küçültülmüşse sonuncuyu açar.) **Dock tıklama davranışı macOS'tan farklı:** tek pencereli aktif uygulamanın ikonuna tıklamak
    pencereyi küçültüyor ([dock.py:511](liquid/dock.py:511)); macOS'ta bir şey olmaz.
25. ✅ (xfwm4 compositor'ü yerine picom: Control Center, Spotlight, Uygulamalar ve dock artık arkadaki pencereleri gerçekten bulanıklaştırıyor. Dock'ta bulanıklığı ikonların altındaki ayrı bir cam penceresi (`DockGlass`) taşıyor, böylece büyüyen ikonlar ve ad baloncukları bulanıklaşmıyor. `liquid compositor xfwm` ile geri alınır; picom tutunamazsa bekçi kendiliğinden xfwm4'e döner ve cam eski duvar kâğıdı kopyasına geçer. Çubuk ve widget'ların arkasında yalnız duvar kâğıdı olduğundan onlar kopyayla kaldı) **Sahte cam:** dock/CC/Spotlight camı yalnızca duvar kâğıdını bulanıklaştırıyor; arkadaki pencereler
    görünmüyor (dock'un arkasına sürüklenen pencere camda yok).
26. ✅ (Asıl neden süreç sayısı değil, duvar kâğıdıydı: Mint'in 9600×5400 progressive JPEG'i her bileşende ayrı tam çözülüyor, ~270 MB kalıyordu. Artık küçük ölçekte çözülüp `malloc_trim` ile iade ediliyor ve ekran boyutundaki sonuç `~/.cache/liquid/wp/` ile paylaşılıyor. Toplam PSS ~1370 → 219 MB. Panelleri tek sürece birleştirmek ~50 MB daha kazandırırdı; çökme yalıtımı için yapılmadı.) **Bellek:** 6 ayrı Python+GTK süreci ≈ 400 MB RSS (launcher 117 MB, dock 81 MB, spotlight 72 MB, bar 71 MB…).
27. ✅ (`.xprofile` bloğu modül zaten varsa eklemiyor (install yeniden yazar; kullanıcının bloğu güncellendi).) **`.xprofile` GTK_MODULES'u ikiler:** Mint zaten `appmenu-gtk-module` ekliyor; oturumda
    `GTK_MODULES=appmenu-gtk-module:appmenu-gtk-module:gail:atk-bridge`.
28. ✅ (Sığmayan menüler » altına (`_fit`); 16 uzun menüyle doğrulandı.) **Uzun global menüler** sağdaki saat/simgelerle çakışabilir; menü çubuğunda taşma/kısaltma yok.
29. ✅ (Wnck ikonu dock boyutunda isteniyor; "Dock'ta Tut" komut satırından `liquid-*.desktop` üretiyor.) **Pencere (`win`) türü dock öğeleri** `.desktop` olmayan uygulamalarda Wnck'nin küçük ikonunu
    54 px'e büyütüyor → bulanık ikon; bu öğeler "Dock'ta Tut" yapılamıyor.
30. ✅ (Çöp durumu gvfs `trash:///` `item-count` ile (tüm diskler).) **Çöp dolu/boş algısı** yalnızca `~/.local/share/Trash` — diğer disklerdeki `.Trash-1000` dikkate alınmıyor.
31. ✅ (`LANGUAGE` önce; yerel ayar C/POSIX ise İngilizce.) **Dil algılama:** `i18n._lang()` `LANGUAGE`'ı en son kontrol ediyor; gettext'te en önceliklisi o.
32. ✅ (`i18n.fold()`: ı/i/I/İ katlanıyor; Uygulamalar ekranı ve Spotlight kullanıyor.) **Türkçe arama:** `str.lower()` "İ"yi "i̇" yapıyor; İ ile başlayan uygulama/dosya adları bazen bulunmuyor.
33. **Marka riski:** PLAN "Apple adı/markası kullanılmaz" diyor, ama menü çubuğunda elma logosu çiziliyor
    ([glyphs.py:12](liquid/glyphs.py:12)) ve "Bu Mac Hakkında", "Finder", "App Store" adları kullanılıyor.
    Kişisel kullanım için sorun değil; paylaşılacaksa değiştirilmeli.
34. ✅ (PLAN adım 7 işaretlendi; yedeğin kopyası `~/.local/share/liquid/values.tsv`'de (uninstall onu da kullanır).) **Belgeler/depo:** PLAN.md adım 7 (bar) hâlâ `[ ]`; `backup/` `.gitignore`'da — tek geri dönüş kaydı
    (`values.tsv`) sürüm kontrolünde değil, klasör silinirse geri alma imkânsız.
35. ✅ (`xset()` → `xfset()`.) **`install.sh`** içindeki `xset()` fonksiyonu X11'in `xset` komutunu gölgeliyor (betikte ileride
    gerçek `xset` gerekirse karışır).

---

## Önerilen düzeltme sırası
1. Wnck çökmesi (madde 1) — diğer birçok belirtiyi (menü sıfırlanması, registrar yeniden başlaması) de çözer.
2. Çöp onayı (2), widget döngüsü + saat tıklaması (3, 4, 5).
3. Uygulama eşleme (6), log yönlendirme (8), alt süreç fırtınası (12, 16).
4. Tepsi (7), global menü yedekleri (9), GTK4 teması (10).
5. Kalan orta/düşük maddeler.

## Kontrol turu (23 Eki, picom sonrası) — bulunan ve düzeltilenler
- ✅ **Menü çubuğu adında "liquid" geçen her pencereyi kendi penceresi sanıyordu** ([bar.py](liquid/bar.py) `_is_ours`):
  VS Code'da bu proje ("bar.py - liquid - …") ya da "Liquid Glass" başlıklı bir sekme açıkken global menü
  ve ⌃⌘F/yeşil düğme tam ekranı çalışmıyordu. Artık süreç komut satırına (`-m liquid.`) bakılıyor.
- ✅ **Tam ekranda dock'un cam penceresi bulanık bir şerit bırakıyordu:** picom saydamlığı 0 olan pencerenin
  arkasını da bulanıklaştırıyor → cam penceresi tam ekranda haritadan kaldırılıyor. Test penceresiyle doğrulandı.
- ✅ **Kartlar (Widget galerisi, Çöp onayı, Wi-Fi parolası) %97 opaktı:** arkadaki yazı bulanıklaşmadan
  sızıyordu → picom açıkken gerçek cam.
- ✅ **Control Center kaydırıcısı:** arkada beyaz pencere varken beyaz dolgu kayboluyordu → ince kenar.
- ✅ Beş modül GTK sürümü belirtmeden içe aktarıyordu (GTK4 bağları kurulursa yanlış sürüm yüklenebilirdi);
  kullanılmayan içe aktarmalar temizlendi. pyflakes temiz.
- Doğrulanamayan: tam ekranda fare ekranın altına inince dock'un belirmesi (fare kullanılmadan test edilemez).


---

## Tema analizi (24 Eki 19:50) — canlı ekran, süreçler, loglar, ayarlar, kod

### A1. 🟠 Uygulama eşleme: 6 uygulama yanlış .desktop'a bağlanıyor (Thunar = "ikinci Finder")
- **Kanıt:** Thunar penceresi açıkken dock'un sonunda ikinci bir Finder simgesi (noktalı) çıkıyor; ilk Finder'a
  nokta gitmiyor. `AppIndex.desktop_for(Thunar)` → `thunar-bulk-rename.desktop`.
- **Neden:** [core/apps.py](liquid/core/apps.py) `AppIndex` anahtarları `setdefault` ile dolduruyor; çalıştırılabilir
  adı ("thunar") ilk görülen dosyaya (Toplu Yeniden Adlandır, `Exec=thunar --bulk-rename`) gidiyor, asıl
  `thunar.desktop` kaybediyor.
- **Etkilenen:** thunar → thunar-bulk-rename, mintupdate → mintupdate-kde, mintreport → kde4-mintreport,
  mintwelcome → kde4-mintwelcome, mintstick → mintstick-format, xfce4-appfinder → xfce4-run.
  Menü çubuğundaki uygulama adı ve Finder menüsü de bu pencerelerde yanlış.
- **Öneri:** Dosya adından gelen anahtar (`thunar` ← `thunar.desktop`) ve StartupWMClass, Exec'ten gelen anahtarı ezsin.

### A2. 🟠 Bildirim Merkezi hep boş kalacak: xfce4-notifyd bildirimleri kaydetmiyor
- `~/.cache/xfce4/notifyd/log.sqlite` 0 satır; `xfce4-notifyd` kanalında `/notification-log` ayarı yok
  (varsayılan: kayıt kapalı). Saate tıklayınca her zaman "Bildirim Yok" görünür.
- **Öneri:** `/notification-log = true` (install.sh'de `xfset` ile, yedekli).

### A3. 🟡 Bildirim balonları macOS'a benzemiyor
- xfce4-notifyd teması `Default` (koyu gri dikdörtgen). macOS 26: sağ üstte, yuvarlak köşeli cam kart,
  uygulama simgesi solda, başlık kalın. Liquid'in kart tasarımıyla tutarsız.
- **Öneri:** `~/.local/share/themes/Liquid/xfce-notify-4.0/gtk.css` (açık/koyu) ve `/theme = Liquid`.

### A4. 🟡 Pencere köşeleri köşeli
- picom `corner-radius = 0`. MacTahoe xfwm4 teması yalnız üst köşeleri yuvarlıyor; alt köşeler ve kenarlıksız
  uygulamalar (Claude, VS Code, Electron) tamamen köşeli. macOS 26'da tüm pencerelerin 4 köşesi yuvarlak.
- **Öneri:** picom'da normal pencerelere `corner-radius ≈ 12`; dock/menü/tooltip/tam ekran/büyütülmüş hariç.

### A5. 🟡 Cumartesi kısaltması "Cts" (macOS: "Cmt")
- Menü çubuğu saati ve dock'taki Takvim ikonu glibc'nin `%a` kısaltmasını kullanıyor: "24 Eki Cts".
  macOS Türkçe: Paz Pzt Sal Çar Per Cum **Cmt**. Diğer günler aynı.
- **Öneri:** Türkçede gün kısaltmasını kendi tablomuzdan ver ([bar.py:485](liquid/bar.py:485), [dock.py:297](liquid/dock.py:297)).

### A6. ⚪ Dock ayarları yalnız dosyadan
- Otomatik gizleme, konum (sol/sağ/alt), boyut, büyütme macOS'ta Dock sağ tık menüsünde/Ayarlar'da;
  Liquid'de otomatik gizleme ve konum hiç yok, boyut/büyütme yalnız `dock.ini`'de.

### A7. ⚪ Küçük görünüm farkları
- Pencere/menü açılışında solma yok (picom `fading = false`); macOS kısa bir geçiş kullanır.
- Eş aralıklı yazı tipi `Ubuntu Mono 12` (macOS: SF Mono/Menlo benzeri).

### Sistem (temadan bağımsız, bilgi için)
- Açılışta Xorg iki kez çöküp üçüncüde açılıyor (19:03:47 ve :48, `FatalError` → `InitOutput`):
  lightdm, AMD GPU (`/dev/dri/card1`) hazır olmadan X'i başlatıyor ("open /dev/dri/card0: No such file").
  Açılışı ~1-2 sn geciktiriyor; Liquid'le ilgisi yok.

### Kontrol edildi, sorun yok
- Bugün çökme yok: bekçi kaydındaki yeniden başlatmaların hepsi benim düzeltme sonrası yeniden başlatmalarım;
  `coredumpctl`'de bugün Python çökmesi yok. Loglarda son başlatmalardan beri hata yok.
- Bellek (PSS) toplamı ~175 MB (bar 43, launcher 31, dock 27 …), picom 2 MB; CPU düşük (picom ~%2-3).
- GPU hızlandırma açık (AMD Radeon 610M, glamor); picom glx ile çalışıyor.
- Global menü kayıt servisi boşta kapanıyor ama çağrılınca açılıp kayıtları geri alıyor (Claude menüsü doğru).
- Açık kalan eski maddeler: 22 (ikinci monitörde çubuk yok), 33 (marka riski).

### Bu turda bakılamayan
- Normal uygulama pencerelerinin başlık çubuğu (Claude penceresinin altında kaldı, ekrandan alınamadı),
  Spotlight / Uygulamalar / Control Center görünümü bu turda yeniden incelenmedi.
