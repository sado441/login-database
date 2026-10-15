# SEGE kaynağı ile SADO Link girdi yollarının karşılaştırması

İncelenen arşiv: kullanıcının verdiği
https://codeload.github.com/s3rc4nn1/SEGE-MACRO/zip/refs/heads/main

Kaynağın ilgili dosyaları:

- `segesource/clicksend.py`: KeyboardDriver, MouseDriver, context.send
- `segesource/interception.py`: Interception aygıtlarına ctypes/IOCTL erişimi
- `segesource/macros/multi.py`: yerel/ağ çoklu client klavye aktarımı ve fareyle takip kontrolü
- `segesource/macros/multi - canli.py`: aynı yerel pencere yaklaşımı
- `segesource/macros/background.py`: WM_ACTIVATE + WM_KEYDOWN/WM_KEYUP

## Koddan doğrulanan ayrım

`clicksend.py` tek aktif masaüstüne Interception girdisi gönderir; API'sinde
HWND hedefi yoktur. Buna karşılık `multi.py` içindeki `send_background_key_direct`
Interception kullanmaz: `MapVirtualKey(scan_code, 1)`, ardından hedef HWND'ye
`PostMessage(WM_ACTIVATE, WA_ACTIVE, 0)` ve `WM_KEYDOWN`/`WM_KEYUP` gönderir.
Bizim önceki yerel sürümde WM_ACTIVATE adımı yoktu; ham scan code yerine
VK'den yeniden dönüşüm yapılıyordu ve tekrarlanan key-down olayları eleniyordu.

| Yol | İlk gönderilen kaynak | Güncel SADO Link |
|---|---|---|
| Yerel klavye yakalama | keyboard.hook; event.scan_code | SEGE uyumlu modda keyboard.hook; scan code korunur |
| Yerel klavye gönderme | WM_ACTIVATE → WM_KEYDOWN/UP | Aynı mesaj sırası; tekrarlanan key-down da iletilir |
| Genişletilmiş tuşlar | scan-code dönüşümüne bağlı | E0 yön tuşu ile sayısal tuş takımı ayrılır |
| Sol/sağ fare | Sol tık takip açar, sağ tık kapatır | Aynı işlev ayrı ve isteğe bağlı SEGE fare takibi seçeneği |
| Takip döngüsü | W tut; 1.5 saniyede X, 0.02 sn darbe; W'yi 2 sn yenile | Aynı aralıklar, durdurulabilir ve test edilebilir controller |
| Elle tuş basma | Takip geçici durur | Basılı tuş kümesiyle bütün elle basılan tuşlar bırakılana kadar durur |
| Birebir fare kopyalama | Multi modülü bunu yapmıyor | Önceki isteğe bağlı konum/tıklama aktarımı ayrıca korunur |
| Masaüstüne Interception | clicksend üzerinden | İnternet alıcısında resmi C API ile aynı tip tuş/fare paketleri |

SEGE fare takibi fare imlecini kopyalamaz, aynı hedefe kamera yöneltmez ve
karakterlerin birbirini gerçekten bulduğunu doğrulamaz. Yaptığı iş W/X
tuş dizisini çalıştırmaktır. Kaynaktaki bazı UI metinleri Z derken gerçek
SCAN_X değeri 0x2D'dir, yani X gönderilir; burada gerçek kod esas alındı.

## Korunan kontroller

Yalnız seçili ana HWND öndeyken yeni girdiler alınır. Alıcılar ayrı
HWND/PID'lerle doğrulanır. F12, odak kaybı, pencere kapanması ve mesaj
hatası basılı girdilerin bırakılmasını tetikler. Kaynaktaki `except: pass`
yerine hata gösterilir. Mesaj tabanlı aktivasyon kullanılır; gerçek
SetForegroundWindow ile pencereler arasında geçiş yapılmaz.

Yerel takip üretimi de aynı router üzerinden gider. Dolayısıyla yönlendirilen
olay sayısı, takip açıkken yakalanan fiziksel olay sayısından fazla olabilir.
Klavye seçeneğini veya takip modunu değiştirdikten sonra durdurup yeniden başlat.

Bu uyumluluk değişikliklerinin API çağrı sırası ve davranışı otomatik
testlerle kontrol edilir. Windows'ta oyun client'inin bu mesajları kabul
etmesi henüz doğrulanmadı. Kaynakta aynı yöntemin bulunması bu oyunda
çalıştığına dair tek başına kanıt değildir.
