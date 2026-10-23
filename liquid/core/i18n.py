"""Liquid — metinler (Türkçe + İngilizce; diğer dillerde İngilizce)."""
import os

S = {
    # uygulama adları
    "app_music": ("Music", "Müzik"), "app_settings": ("System Settings", "Sistem Ayarları"),
    "app_calendar": ("Calendar", "Takvim"), "app_contacts": ("Contacts", "Kişiler"),
    "app_photos": ("Photos", "Fotoğraflar"), "app_calculator": ("Calculator", "Hesap Makinesi"),
    "app_activity": ("Activity Monitor", "Etkinlik Monitörü"), "app_apps": ("Apps", "Uygulamalar"),
    "trash": ("Trash", "Çöp Kutusu"), "downloads": ("Downloads", "İndirilenler"),
    # menü çubuğu
    "m_file": ("File", "Dosya"), "m_edit": ("Edit", "Düzen"), "m_view": ("View", "Görüntü"),
    "m_go": ("Go", "Git"), "m_window": ("Window", "Pencere"), "m_help": ("Help", "Yardım"),
    "about_app": ("About {}", "{} Hakkında"), "hide_app": ("Hide {}", "{} Uygulamasını Gizle"),
    "hide_others": ("Hide Others", "Diğerlerini Gizle"),
    "enter_fullscreen": ("Enter Full Screen", "Tam Ekrana Geç"),
    "exit_fullscreen": ("Exit Full Screen", "Tam Ekrandan Çık"), "quit_app": ("Quit {}", "{} Uygulamasından Çık"),
    "settings_dots": ("Settings…", "Ayarlar…"),
    "new_finder": ("New Finder Window", "Yeni Finder Penceresi"), "new_folder": ("New Folder", "Yeni Klasör"),
    "find": ("Find", "Bul"), "undo": ("Undo", "Geri Al"), "redo": ("Redo", "Yinele"),
    "cut": ("Cut", "Kes"), "copy": ("Copy", "Kopyala"), "paste": ("Paste", "Yapıştır"),
    "select_all": ("Select All", "Tümünü Seç"), "as_icons": ("as Icons", "Simge Olarak"),
    "as_list": ("as List", "Liste Olarak"), "go_home": ("Home", "Ev"), "go_desktop": ("Desktop", "Masaüstü"),
    "go_documents": ("Documents", "Belgeler"), "go_downloads": ("Downloads", "İndirilenler"),
    "go_computer": ("Computer", "Bilgisayar"), "go_network": ("Network", "Ağ"),
    "go_apps": ("Applications", "Uygulamalar"), "minimize_all": ("Minimize All", "Tümünü Küçült"),
    "empty_trash": ("Empty Trash", "Çöp Kutusunu Boşalt"), "untitled_folder": ("untitled folder", "adsız klasör"),
    # Elma menüsü
    "a_about": ("About This Mac", "Bu Mac Hakkında"), "a_settings": ("System Settings…", "Sistem Ayarları…"),
    "a_appstore": ("App Store", "App Store"), "a_recent": ("Recent Items", "Son Kullanılanlar"),
    "a_no_recent": ("No Recent Items", "Son Kullanılan Yok"), "a_clear": ("Clear Menu", "Menüyü Temizle"),
    "a_forcequit": ("Force Quit…", "Zorla Çık…"), "a_sleep": ("Sleep", "Uyku"),
    "a_restart": ("Restart…", "Yeniden Başlat…"), "a_shutdown": ("Shut Down…", "Kapat…"),
    "a_lock": ("Lock Screen", "Ekranı Kilitle"), "a_logout": ("Log Out {}…", "Oturumu Kapat: {}…"),
    "q_restart": ("Are you sure you want to restart your computer now?",
                  "Bilgisayarı şimdi yeniden başlatmak istediğinizden emin misiniz?"),
    "q_shutdown": ("Are you sure you want to shut down your computer now?",
                   "Bilgisayarı şimdi kapatmak istediğinizden emin misiniz?"),
    "q_logout": ("Are you sure you want to quit all applications and log out now?",
                 "Tüm uygulamalardan çıkıp şimdi oturumu kapatmak istediğinizden emin misiniz?"),
    "q_detail": ("If you do nothing, this will happen automatically in {} seconds.",
                 "Hiçbir şey yapmazsanız bu {} saniye içinde otomatik olarak gerçekleşecek."),
    "q_empty_trash": ("Are you sure you want to permanently erase the items in the Trash?",
                      "Çöp Kutusundaki öğeleri kalıcı olarak silmek istediğinizden emin misiniz?"),
    "q_no_undo": ("You can’t undo this action.", "Bu işlemi geri alamazsınız."),
    "a_chip": ("Chip", "Çip"), "a_memory": ("Memory", "Bellek"), "a_disk": ("Startup Disk", "Başlangıç Diski"),
    "a_kernel": ("Kernel", "Çekirdek"),
    "do_restart": ("Restart", "Yeniden Başlat"), "do_shutdown": ("Shut Down", "Kapat"),
    "do_logout": ("Log Out", "Oturumu Kapat"), "cancel": ("Cancel", "Vazgeç"),
    # durum menüleri
    "battery": ("Battery", "Pil"), "power_source": ("Power Source", "Güç Kaynağı"),
    "power_adapter": ("Power Adapter", "Güç Adaptörü"), "battery_settings": ("Battery Settings…", "Pil Ayarları…"),
    "wifi_settings": ("Wi-Fi Settings…", "Wi-Fi Ayarları…"),
    "wifi_password": ("The Wi-Fi network “{}” requires a password.", "“{}” Wi-Fi ağı bir şifre gerektiriyor."),
    "wifi_failed": ("Couldn’t join “{}”.", "“{}” ağına katılınamadı."),
    "password": ("Password", "Şifre"), "join": ("Join", "Katıl"), "other_networks": ("Other Networks", "Diğer Ağlar"),
    # Uygulamalar ekranı / Spotlight / CC
    "search": ("Search", "Ara"), "no_results": ("No Results", "Sonuç Yok"),
    "spotlight": ("Spotlight Search", "Spotlight'ta Ara"), "web_search": ("Search the web for “{}”", "Web'de “{}” ara"),
    "on": ("On", "Açık"), "off": ("Off", "Kapalı"), "not_connected": ("Not Connected", "Bağlı Değil"),
    "focus": ("Focus", "Odak"), "dnd": ("Do Not Disturb", "Rahatsız Etme"),
    "display": ("Display", "Ekran"), "sound": ("Sound", "Ses"), "not_playing": ("Not Playing", "Çalmıyor"),
    "dark_mode": ("Dark Mode", "Karanlık Mod"), "screenshot": ("Screenshot", "Ekran Görüntüsü"),
    "open": ("Open", "Aç"), "new_window": ("New Window", "Yeni Pencere"), "keep_in_dock": ("Keep in Dock", "Dock'ta Tut"),
    "remove_from_dock": ("Remove from Dock", "Dock'tan Kaldır"), "quit": ("Quit", "Çık"),
    # widget'lar
    "edit_widget": ("Edit Widget", "Widget'ı Düzenle"), "remove_widget": ("Remove Widget", "Widget'ı Kaldır"),
    "choose_photo": ("Choose Photo…", "Fotoğraf Seç…"),
}


def _lang():
    """gettext sırası: LANGUAGE en öncelikli — ama yerel ayar C/POSIX ise gettext onu yok sayar."""
    loc = next((os.environ[v] for v in ("LC_ALL", "LC_MESSAGES", "LANG") if os.environ.get(v)), "")
    if loc.split(".")[0] in ("", "C", "POSIX"):
        return "en"
    val = os.environ.get("LANGUAGE") or loc
    return val.split(":")[0].split(".")[0].split("_")[0].lower()


LANG = _lang()


def fold(s):
    """Arama için büyük/küçük harf katlama. str.lower() "İ"yi "i̇" (i + birleşik nokta) yapar ve
    "İstanbul" "ist" ile eşleşmez; ı/i/I/İ hepsi "i" sayılır (Türkçe ve İngilizce adlar birlikte bulunur)."""
    return (s or "").replace("İ", "i").replace("I", "i").replace("ı", "i").casefold().replace("i\u0307", "i")


def t(key):
    e = S.get(key)
    if not e:
        return key
    return e[1] if LANG == "tr" else e[0]
