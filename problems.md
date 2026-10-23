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

### 4. Kaldırılan widget'ı geri eklemenin yolu yok
- Sağ tık → "Widget'ı Kaldır" `hidden=1` yazıyor ([widgets.py:130](liquid/widgets.py:130)); hiçbir yerde
  "Widget Ekle / Widget'ları Düzenle" yok (`i18n`'deki `edit_widget` metni hiç kullanılmıyor).
  Geri getirmek için `widgets.ini` elle düzenlenmeli.

### 5. ✅ KISMEN DÜZELTİLDİ — Saate tıklamak widget sürecini öldürüyor
> SIGUSR1 artık yutuluyor (süreç ölmüyor, test edildi). Saate tıklamak şimdilik hiçbir şey yapmıyor;
> Bildirim Merkezi / widget ekleme (madde 4) için kullanılabilir.
- **Yer:** [bar.py:294](liquid/bar.py:294) saate tıklayınca `signal_component("widgets")` → SIGUSR1.
- `widgets.py` SIGUSR1 için işleyici kurmuyor ([widgets.py:325](liquid/widgets.py:325)); SIGUSR1'in
  varsayılan davranışı **süreci sonlandırmak**. Widget'lar açıkken saate tıklanınca hepsi kaybolur,
  5 sn sonra bekçi geri açar. (macOS'ta saat tıklaması Bildirim Merkezi'ni açar.)

### 6. Uygulama eşleme yanlış: Python betiği olan uygulamalar "Python (v3.12)" görünüyor
- **Kanıt:** Yazılım Yöneticisi (mintinstall) açıkken menü çubuğunda **"Python (v3.12)"** yazıyordu; dock'ta
  App Store yerine ayrı bir **Python** ikonu çalışıyor (noktalı) göründü.
- **Yer:** [core/apps.py:115-125](liquid/core/apps.py:115). WM_CLASS `mintinstall.py` eşleşmiyor,
  sonra `/proc/PID/exe` = `python3.12` → `python3.12.desktop` ile eşleşiyor. `_SKIP_EXE` yalnızca
  `.desktop` dizinini kurarken uygulanıyor, aday tarafında uygulanmıyor.
- **Etkilenen:** mintinstall, mintupdate, Mint araçlarının çoğu ve diğer Python/Java/Electron sarmalayıcı uygulamalar.
- **Öneri:** Adaylarda yorumlayıcıları (`python3*`, `java`, `node`, `electron`…) atla; WM_CLASS'tan `.py`
  sonekini sil; `/proc/PID/cmdline` içindeki betik adını da aday yap.

### 7. Sistem tepsisi (tray) yok: XFCE paneli zorla ve sürekli kapatılıyor
- [session.py:61](liquid/session.py:61) her 5 sn'de XFCE paneline SIGTERM gönderiyor; panel elle açılsa da
  kapanır. Yerine bir bildirim alanı (StatusNotifier/XEmbed) yok.
- **Etkisi:** Tepsi ikonu kullanan uygulamaların (ör. Claude, güncelleme yöneticisi, Bluetooth, klavye düzeni,
  Dropbox/Telegram vb.) ikonları ve menüleri tamamen kayboluyor. Ses düzeyi, klavye düzeni göstergesi de yok.
- **Öneri:** Çubuğun sağına StatusNotifierItem/XEmbed tepsi desteği ekle (ya da XFCE panelini yalnız tepsi
  eklentisiyle küçük ve saydam bırak).

### 8. Uygulamaların çıktıları Liquid loglarına akıyor ve loglar sınırsız büyüyor
- **Kanıt:** `~/.cache/liquid/dock.log` içinde Chrome'un `ssl_client_socket_impl` hataları,
  `gnome-calculator` uyarıları var.
- **Yer:** [core/daemon.py:63-66](liquid/core/daemon.py:63) bileşenin stdout/stderr'i log dosyası;
  [core/apps.py:128](liquid/core/apps.py:128) `launch()` ile açılan uygulamalar bunu miras alıyor
  (dock, Uygulamalar ekranı, Spotlight).
- Log döndürme (rotation) yok; uzun oturumda dosyalar şişer. Çökmeler (madde 1) ise loga hiç yazılmıyor.
- **Öneri:** Uygulamaları başlatırken stdout/stderr'i `/dev/null`'a ya da ayrı dosyaya yönlendir; logu boyutla
  sınırla; bekçi bir bileşen yeniden başlatınca çıkış kodu/sinyali loglasın.

### 9. Global menü çoğu uygulamada boş kalıyor
- Örn. Takvim (GNOME Calendar, GTK4) aktifken çubukta yalnız "Takvim" yazıyor, Dosya/Düzen/… yok.
  GTK4/libadwaita, çoğu Electron ve Firefox menülerini dışa aktarmıyor. macOS görünümünde sol taraf sık sık boş.
- `com.canonical.AppMenu.Registrar` sürekli çalışmıyor: `busctl --user list` → yalnızca "activatable";
  journal'da bar her yeniden başladığında yeniden etkinleştiriliyor (madde 1 ile birlikte). Kayıt
  hizmeti olmadığında Qt/Electron uygulamaları menülerini kaydedemez.
- **Öneri:** Menü dışa aktarmayan uygulamalar için en azından standart yedek menüler (Dosya: Yeni Pencere,
  Kapat; Pencere: Küçült/Büyüt; Yardım) göster; registrar'ı bar sürecinin içinde ya da kalıcı başlat.

### 10. GTK4/libadwaita uygulamaları temaya uymuyor
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

### 11. Control Center menü çubuğundan tıklayınca açık kalmıyor (gözlem — doğrulanmalı)
- `liquid toggle controlcenter` ile açılıp kapanıyor (doğrulandı). Ama menü çubuğundaki CC simgesine
  `xdotool` ile tıklandığında 1,5 sn sonra pencere `IsUnMapped` idi (2 deneme).
- Olası neden: açıldıktan hemen sonra gelen odak kaybı ([controlcenter.py:202](liquid/controlcenter.py:202)).
  Aynı desen Spotlight ve Uygulamalar ekranında da var: açıkken simgeye tıklamak **önce odak kaybıyla
  kapatıp sonra sinyalle yeniden açabilir** (aç/kapat çakışması).

### 12. Kaydırıcılar her fare hareketinde yeni süreç başlatıyor
- [controlcenter.py:384-388](liquid/controlcenter.py:384): sürüklerken her `motion` olayında
  `brightnessctl` ya da **iki** `pactl` süreci açılıyor (saniyede onlarca). Sıra garantisi yok;
  son değer bazen önceki komuttan önce uygulanıp ses/parlaklık "geri sıçrayabilir".
- **Öneri:** Değeri biriktir, 50–100 ms'de bir uygula (throttle), ya da PulseAudio/`/sys` API'sini doğrudan kullan.

### 13. Karanlık Mod Liquid bileşenlerini değiştirmiyor
- [controlcenter.py:89](liquid/controlcenter.py:89) yalnızca GTK/xfwm/ikon temasını değiştiriyor. Menü
  çubuğu menüleri, dock balonu, Control Center, Spotlight, onay kartları ve "Bu Mac Hakkında" sabit
  açık renkte çiziliyor ([applemenu.py:18](liquid/applemenu.py:18) `MENU_CSS` vb.). Karanlık modda
  uyumsuz görünür.

### 14. Spotlight: seçili satır görünmez olabiliyor
- Sonuç sayısı en fazla 1 (hesap) + 6 (uygulama) + 4 (dosya) + 1 (web) = 12; çizilen en fazla `MAXROWS = 9`.
  ↑/↓ seçimi `len(results)` üzerinden dönüyor ([spotlight.py:243](liquid/spotlight.py:243)) → seçim
  görünmeyen 10.–12. satırlara gidebiliyor; Enter görünmeyen öğeyi açar. "Web'de ara" satırı bu durumda hiç görünmez.

### 15. Spotlight hesaplayıcı büyük sayılarda hata veriyor
- `9^999` gibi bir giriş: üs sınırı (≤1000) geçiliyor, sonuç çok büyük tamsayı →
  [spotlight.py:67](liquid/spotlight.py:67) `f"{r:.6e}"` → `OverflowError` (yakalanmıyor; arama o tuşta güncellenmez).

### 16. Her tuşa/saniyeye alt süreç başlatılıyor
- `wallpaper.current()` her çağrıda `xrandr` + 2× `xfconf-query` çalıştırıyor
  ([core/wallpaper.py:21-43](liquid/core/wallpaper.py:21)). Çağrılan yerler:
  - Analog saat widget'ı **her saniye** ([widgets.py:135](liquid/widgets.py:135), [widgets.py:202](liquid/widgets.py:202)) → ~3 süreç/sn,
  - Spotlight **her tuş vuruşunda** ([spotlight.py:154](liquid/spotlight.py:154)),
  - dock her 2 sn, bar her 3 sn.
- **Öneri:** `xfconf-query -m` ile değişikliği izle (ya da xfconf D-Bus `PropertyChanged`) ve sonucu önbellekle.

### 17. Çalışma alanı değişince yanlış duvar kâğıdı kullanılıyor
- `wallpaper.current(workspace=0)` hep 0. çalışma alanını okuyor; bar/dock `active-workspace-changed`
  dinliyor ama yine workspace0'a bakıyor ([bar.py:224](liquid/bar.py:224), [dock.py:142](liquid/dock.py:142)).
  Çalışma alanlarında farklı duvar kâğıdı varsa dock camı ve menü çubuğu yazı rengi yanlış olur.
- Ayrıca stil 1 (ortala), 2 (döşe), 4 (ölçekle) "kapla" gibi hesaplanıyor → cam arka planı gerçek görüntüyle örtüşmez.

### 18. Uninstall, kurulumdan sonra yapılan duvar kâğıdı seçimlerini de eziyor
- `install.sh` başlığı "sonradan yaptığın ayarlara dokunmaz" diyor, ama `uninstall.sh` `values.tsv`'deki
  her özelliği koşulsuz eski değere yazıyor ([uninstall.sh:19-27](uninstall.sh:19)). Kullanıcı bugün duvar
  kâğıdını zaten değiştirdi (Mint çizgili duvar kâğıdı); kaldırma bunu ezecek.
- **Öneri:** Geri yüklemeden önce mevcut değerin hâlâ Liquid'in yazdığı değer olup olmadığını kontrol et.

### 19. Wi-Fi menüsü
- Şifreli ve kayıtlı olmayan ağa tıklamak `nmcli dev wifi connect <ad>` ile **şifre sormadan** başarısız
  oluyor, kullanıcıya hiçbir şey gösterilmiyor ([bar.py:350](liquid/bar.py:350)).
- Ağ listesi menü açılmadan önce ana iş parçacığında senkron `nmcli` ile alınıyor ([bar.py:335](liquid/bar.py:335));
  NetworkManager yavaşsa çubuk donar.
- Bağlı ağın satırına tıklamak bağlantıyı yeniden kuruyor (CheckMenuItem durumu da tersine dönüyor).

### 20. Menüdeki kısayollar sadece yazı
- ⌘Q, ⌘H, ⌥⌘H, ⌘N, ⇧⌘N, ⌘F, ⇧⌘G… menülerde yazıyor ama hiçbiri bağlı değil; yalnızca
  `Super+Space` → Spotlight kurulu. Finder menüsündeki Düzen (Geri Al, Kes, Kopyala…) ve Görüntü
  öğelerinin hepsi devre dışı (`None` geri çağrı) — işlevsiz menüler ([bar.py:550-552](liquid/bar.py:550)).
- `Super_L` tek başına kullanıcının `linuxhelper` kısayoluna bağlı; `Super+Space` ile çakışıp çakışmadığı
  (Super bırakılınca linuxhelper'ın da açılması) kontrol edilmeli.

### 21. Yardım menüsü olmayan dosyayı açıyor
- Finder → Yardım → "Liquid" `README.md` açıyor ([bar.py:561](liquid/bar.py:561)); depoda `README.md` yok
  (PLAN.md'de listelenmiş ama yazılmamış).

### 22. Çoklu monitör desteklenmiyor
- Bar, dock, widget'lar, Spotlight, CC yalnızca birincil monitörde (`screen_geometry()`); ikinci monitörde
  menü çubuğu/dock yok. Monitör takılıp çıkarılınca boyutlar yeniden hesaplanmıyor (yeniden başlatma gerekir).

---

## ⚪ Düşük / kozmetik

23. **Dock takvim ikonu gece yarısı güncellenmiyor:** gün sayısı yalnızca dock yeniden çizildiğinde
    değişiyor; zamanlayıcı yok ([dock.py:233](liquid/dock.py:233)). Fare dock'a gelene kadar dünün tarihi kalabilir.
24. **Dock tıklama davranışı macOS'tan farklı:** tek pencereli aktif uygulamanın ikonuna tıklamak
    pencereyi küçültüyor ([dock.py:511](liquid/dock.py:511)); macOS'ta bir şey olmaz.
25. **Sahte cam:** dock/CC/Spotlight camı yalnızca duvar kâğıdını bulanıklaştırıyor; arkadaki pencereler
    görünmüyor (dock'un arkasına sürüklenen pencere camda yok).
26. **Bellek:** 6 ayrı Python+GTK süreci ≈ 400 MB RSS (launcher 117 MB, dock 81 MB, spotlight 72 MB, bar 71 MB…).
27. **`.xprofile` GTK_MODULES'u ikiler:** Mint zaten `appmenu-gtk-module` ekliyor; oturumda
    `GTK_MODULES=appmenu-gtk-module:appmenu-gtk-module:gail:atk-bridge`.
28. **Uzun global menüler** sağdaki saat/simgelerle çakışabilir; menü çubuğunda taşma/kısaltma yok.
29. **Pencere (`win`) türü dock öğeleri** `.desktop` olmayan uygulamalarda Wnck'nin küçük ikonunu
    54 px'e büyütüyor → bulanık ikon; bu öğeler "Dock'ta Tut" yapılamıyor.
30. **Çöp dolu/boş algısı** yalnızca `~/.local/share/Trash` — diğer disklerdeki `.Trash-1000` dikkate alınmıyor.
31. **Dil algılama:** `i18n._lang()` `LANGUAGE`'ı en son kontrol ediyor; gettext'te en önceliklisi o.
32. **Türkçe arama:** `str.lower()` "İ"yi "i̇" yapıyor; İ ile başlayan uygulama/dosya adları bazen bulunmuyor.
33. **Marka riski:** PLAN "Apple adı/markası kullanılmaz" diyor, ama menü çubuğunda elma logosu çiziliyor
    ([glyphs.py:12](liquid/glyphs.py:12)) ve "Bu Mac Hakkında", "Finder", "App Store" adları kullanılıyor.
    Kişisel kullanım için sorun değil; paylaşılacaksa değiştirilmeli.
34. **Belgeler/depo:** PLAN.md adım 7 (bar) hâlâ `[ ]`; `backup/` `.gitignore`'da — tek geri dönüş kaydı
    (`values.tsv`) sürüm kontrolünde değil, klasör silinirse geri alma imkânsız.
35. **`install.sh`** içindeki `xset()` fonksiyonu X11'in `xset` komutunu gölgeliyor (betikte ileride
    gerçek `xset` gerekirse karışır).

---

## Önerilen düzeltme sırası
1. Wnck çökmesi (madde 1) — diğer birçok belirtiyi (menü sıfırlanması, registrar yeniden başlaması) de çözer.
2. Çöp onayı (2), widget döngüsü + saat tıklaması (3, 4, 5).
3. Uygulama eşleme (6), log yönlendirme (8), alt süreç fırtınası (12, 16).
4. Tepsi (7), global menü yedekleri (9), GTK4 teması (10).
5. Kalan orta/düşük maddeler.
