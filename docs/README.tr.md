# Pear

Linux Mint Xfce'nin **X11 oturumu** için Python 3, GTK 3 ve cairo ile geliştirilmiş,
macOS'tan esinlenen masaüstü arayüzü. Saydam menü çubuğu, cam dock, widget'lar,
uygulama ekranı, arama, Bildirim Merkezi ve Control Center içerir.

Proje deneyseldir; bir Linux dağıtımı veya pencere yöneticisi değildir. Wayland ve
diğer masaüstleri desteklenmez. Ayrıntılı teknik bilgiler: [English README](../README.md).

## .deb paketiyle kurulum

Debian/Ubuntu tabanlı, **XFCE ve X11** kullanan test sisteminde, indirilen dosyanın
bulunduğu klasörde çalıştır:

```bash
sudo apt install ./pear-desktop_0.1.0~alpha1_all.deb
pear-setup
```

`pear-setup` komutunu sudo kullanmadan, kendi grafik oturumunda çalıştır. Uygulama
menüsündeki **Pear Kurulumu** da aynı işlemi yapar. İlk etkinleştirmede dış temalar
için internet gerekir; sistem teması için sudo istenebilir. Ardından oturumu kapatıp
aç. Paket kurulumu tek başına masaüstü ayarlarını değiştirmez.

Kaldırmadan önce masaüstünü geri al:

```bash
pear-reset
sudo apt remove pear-desktop
```

Paket alfa/test sürümüdür. Geliştirme ortamı Linux Mint Xfce; diğer Debian/Ubuntu
tabanlı sistemlerde grafik testleri henüz yapılmadı. Fedora, Arch, Wayland veya
XFCE dışındaki masaüstleri için uygun değildir. Paket kaldırma kullanıcı ayarlarını
otomatik geri almaz; önce `pear-reset` çalıştır.

Kaynak koddan paket oluşturmak için `python3 tools/build_deb.py` çalıştır. `.deb` ve
SHA-256 dosyası `dist/` altında oluşur. Ayrıntılar: [README.Debian](../packaging/debian/README.Debian).

## Kaynak koddan kurulum

Depoyu klonla veya kaynak arşivini aç; proje klasöründe kendi kullanıcınla çalıştır:

```bash
./install.sh
```

Betik gerekli apt paketlerini kurar, belirli Git sürümlerindeki dış temaları indirir
ve masaüstü ayarlarını değiştirir. Paketler, sistem teması ve duvar kâğıdı için sudo
isteyebilir. Global menüler için kurulumdan sonra oturumu kapatıp aç.

```bash
./install.sh --no-apt              # paketlerin tamamı önceden kurulu olmalı
LIQUID_NO_PICOM=1 ./install.sh      # picom'u etkinleştirme
```

`--no-apt` tema indirmeyi veya tema için sudo kullanımını kapatmaz. Proje klasörünü
silme veya taşıma; otomatik başlatma ve kısayollar buradaki dosyalara bağlıdır.
Taşırsan yeni konumdan kurulum betiğini tekrar çalıştır.

Kurulum; tema, ikon, imleç, yazı tipi, pencere düğmeleri, duvar kâğıdı, bildirimler
ve altı kısayolu ayarlar. Pear çalışırken XFCE panelini kapatır. `.xprofile` içine
işaretli bir blok, otomatik başlatma girdisi ve Thunar widget eylemi ekler.
GTK 4 stillerini yedekler. Desteklenen Firefox profilinde tercih ve stil ekler;
tarayıcı sonraki açılışta uygular. Var olan `userChrome.css` korunur.

Geri alma yedekleri **`~/.local/share/liquid/backups/`** altında tutulur. Firefox ve
compositor durumu `~/.config/liquid/` içindedir; bunları depoya ekleme.
Uygulamanın adı Pear; mevcut kurulumların çalışması için iç Python modülü ve ayar
dizinlerinin `liquid` adı korunur.

## Kaldırma

```bash
./uninstall.sh
./uninstall.sh --themes
```

Kaldırma, kayıtlı XFCE ayarlarını mevcut değerler Pear'in değerleriyle eşleşiyorsa
geri yükler. Kendi başlangıç/menü girdilerini kaldırır, GTK 4 yedeğini geri yükler ve
XFCE panelini açar. Firefox tercihleri sonraki açılışta geri uygulanır. Apt paketleri
ve sistem GTK teması kalır. `--themes`, adlandırılmış kullanıcı ikon/imleç dizinlerini
ve duvar kâğıdını da siler; bu dizinler Pear'den önce varsa onları da kaldırır.

## Kullanım

| Eylem | Sonuç |
| --- | --- |
| Super+Space | Aramayı aç/kapat |
| Ctrl+Super+F | Pear tam ekranını aç/kapat |
| Super+Q / Super+H / Alt+Super+H / Super+M | Çık / gizle / diğerlerini gizle / küçült |
| Menü çubuğundaki saat | Bildirim Merkezi |
| Masaüstünde sağ tık | Widget'ları düzenle |
| Dock üzerinde sağ tık | Pencere işlemleri ve sabitleme |

```bash
bin/pear --help
bin/pear status
bin/pear start
bin/pear stop
bin/pear toggle spotlight
bin/pear widgets edit
bin/pear compositor xfwm
bin/pear compositor picom
```

Dock ayarları: `~/.config/liquid/dock.ini` (`items`, `icon_size`, `magnify`).
Widget ayarları: `~/.config/liquid/widgets.ini`. Günlükler: `~/.cache/liquid/`.
`stop` tüm ayarları geri almaz; eski masaüstüne dönmek için kaldırma betiğini kullan.

## Bilinen sınırlamalar

Arayüz birincil monitörde çalışır; ikinci monitöre ayrı çubuk/dock eklenmez. Global
menü, uygulamanın menülerini dışa aktarmasına bağlıdır. Eski XEmbed tepsi simgeleri
desteklenmez. Parlaklık, Bluetooth, pil tahmini ve medya kontrolleri donanım, servis
ve izinlere bağlıdır. Flatpak/Snap Firefox profilleri otomatik bulunmaz. picom ve
tam ekran davranışını kendi donanımında doğrula.

## Katkı ve lisans

`./tools/check.sh` sözdizimi ve regresyon kontrollerini masaüstünü değiştirmeden
çalıştırır. Katkı süreci: [CONTRIBUTING.md](../CONTRIBUTING.md).
Kaynak kod: [GPL-3.0-only](../LICENSE). Görsellerin ayrı lisansları ve kaynakları:
[THIRD_PARTY.md](../THIRD_PARTY.md). Proje Apple veya diğer üreticilerle bağlantılı değildir.
