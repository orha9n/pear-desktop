# Liquid

Linux Mint XFCE için macOS 26/27 görünümü: saydam menü çubuğu, Liquid Glass dock, masaüstü widget'ları,
Uygulamalar ekranı, Spotlight, Control Center ve macOS tarzı tam ekran. Python 3 + GTK3 + cairo ile
sıfırdan yazıldı; dış bileşenler yalnızca görsel varlıklardır (MacTahoe GTK teması ve ikonları,
WhiteSur imleçleri, Inter yazı tipi).

## Kurulum ve kaldırma

```bash
./install.sh            # paketler (sudo sorar), temalar, ayarlar, otomatik başlatma
./install.sh --no-apt   # paket adımını atla
./uninstall.sh          # Liquid'in değiştirdiği ayarları eski haline döndürür
./uninstall.sh --themes # + kullanıcı temalarını ve duvar kâğıdını siler
```

Kurulum, değiştirdiği her xfconf ayarının önceki değerini `backup/values.tsv` dosyasına (ve
`~/.local/share/liquid/values.tsv` kopyasına) yazar. Kaldırma yalnızca bu ayarları geri yükler; kurulumdan
sonra kendin değiştirdiğin bir ayara (ör. başka bir duvar kâğıdı) dokunmaz. Global menüler için kurulumdan
sonra bir kez oturumu kapatıp aç.

Dokunulmayanlar: ses/medya tuşları, Super tuşu, Print tuşu, `~/.config/gtk-3.0/gtk.css`.

## Kullanım

| | |
|---|---|
| **Menü çubuğu** | Elma menüsü · etkin uygulamanın menüleri · pil, Wi-Fi, Spotlight, Control Center, saat |
| **Dock** | Tıkla: aç / öne getir · sağ tık: pencereler, Yeni Pencere, Dock'ta Tut/Kaldır, Çık · sürükle: sırala |
| **⌘Space** (Super+Space) | Spotlight: uygulama, dosya, hesap makinesi (`3,5*2`), web araması |
| **Yeşil düğme** | macOS tam ekranı: pencere menü çubuğunun altına, ekranın en altına kadar yerleşir; şerit düz renk, imleç gelince menüler görünür; dock en altta belirir |
| **⌃⌘F** (Ctrl+Super+F) | Tam ekrana gir / çık |
| Başlığa çift tık | Doldur (normal büyütme) |

Komut satırı:

```bash
bin/liquid status                     # bileşenler çalışıyor mu
bin/liquid start | stop               # oturum bekçisi + tüm bileşenler
bin/liquid toggle spotlight|launcher|controlcenter
bin/liquid fullscreen                 # etkin pencere için ⌃⌘F
```

## Yapı

```
liquid/
  core/          tasarım sabitleri, cam çizimi, duvar kâğıdı, süreç yönetimi, uygulama eşleme, metinler
  bar.py         menü çubuğu (global menü: GTK GMenuModel + dbusmenu/AppMenu.Registrar)
  dock.py        dock
  widgets.py     takvim, analog saat, fotoğraf widget'ları
  launcher.py    Uygulamalar ekranı
  spotlight.py   Spotlight
  controlcenter.py
  fullscreen.py  yeşil düğme / macOS tam ekranı
  wifi.py        Wi-Fi listesi ve şifre kartı
  session.py     oturum bekçisi: bileşenleri başlatır, kapanırsa yeniden açar
```

Ayarlar: `~/.config/liquid/dock.ini` (`items`, `icon_size`, `magnify`), `~/.config/liquid/widgets.ini`.

## Sorun giderme

- Loglar: `~/.cache/liquid/<bileşen>.log` (512 KB'ı aşınca `.log.1`'e döner).
- Çökmeler ve yeniden başlatmalar: `~/.cache/liquid/session.log`; çekirdek dökümü için
  `coredumpctl info <PID>`.
- Bir bileşeni yeni koduyla yeniden başlatmak: `kill $(cat $XDG_RUNTIME_DIR/liquid/<ad>.pid)` —
  bekçi 5 saniye içinde yeniden açar.
- Bilinen sorunlar ve yapılacaklar: [problems.md](problems.md); tasarım kararları ve tuzaklar: [PLAN.md](PLAN.md).

## Lisans notları

- Duvar kâğıdı: Levi Clancy, CC BY-SA 4.0 — [assets/wallpaper/CREDITS.md](assets/wallpaper/CREDITS.md)
- Widget fotoğrafı: NOAA, kamu malı — [assets/widgets/CREDITS.md](assets/widgets/CREDITS.md)
- "Finder", "App Store", elma logosu vb. yalnızca kişisel kullanım içindir; Apple'ın ticari markalarıdır.
