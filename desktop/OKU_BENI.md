# SADO Link — sürüm 4: SEGE kaynağına dayalı yerel girdi

## Kaynağı esas alan yerel mod güncellemesi

İlk gönderilen SEGE-MACRO arşivinin `multi.py`, `multi - canli.py`,
`background.py`, `clicksend.py` ve `interception.py` dosyaları yeniden
karşılaştırıldı. Ayrıntılar `SOURCE_COMPARISON_TR.md` dosyasında.

**İlk deneme:** ZIP'i yeni klasöre çıkar, `YEREL_COKLU_BASLAT.bat` aç.
Başlıkta v4 görünmeli. **SEGE uyumlu klavye** işaretli, **birebir fare
aktarımı** ve **SEGE fare takibi** kapalı kalsın. Üç pencereyi seçip
başlat, ana oyunda tek bir beceri tuşu ve W bas/bırak dene. Programa
döndüğünde Son oturum satırında SEGE uyumlu ve yakalanan/yönlendirilen
olayları görmelisin. Bu modda Interception sürücüsü gerekmez.

SEGE uyumlu klavye, kaynak gibi `keyboard.hook` ile ham scan code alır ve
hedeflere **WM_ACTIVATE → WM_KEYDOWN/WM_KEYUP** gönderir. Tuş basılıyken
gelen tekrar olayları da iletilir. Standart seçenek eski VK yolunu korur.

**Kaynakta bulunan fare kontrolünü denemek için:** durdur, **SEGE fare
takibi** kutusunu aç ve yeniden başlat. Ana oyun penceresinde sol tık,
alıcılar için W/X takibini açar; sağ tık kapatır. X 1.5 saniyede bir
yaklaşık 0.02 saniye basılır; W tutulup 2 saniyede yenilenir. Elle tuş
basılıyken takip duraklar; bütün elle basılan tuşlar bırakılınca devam eder.
Bu seçenek açıkken birebir fare konumu/tıklama aktarımı yerine bu davranış
kullanılır. Kamera veya gerçek karakter takibi garantisi yoktur.

**3 PENCERELİ TEST** yerel yönlendirmeyi simüle eder. SEGE fare takibi
işaretliyse bu testte de sol tık W/X'i başlatır, sağ tık durdurur. Native
WM_ACTIVATE/keyboard hook çağrıları bu simülasyonda çalışmaz.

38 test geçti: önceki 29 kontrol, 6 kaynak yakalama/takip kontrolü,
WM_ACTIVATE/scan code/tekrar/bırakma mesaj sırası, GUI takip kontrolü ve
dinleyici kapanırken hata olsa bile alıcıları bırakma kontrolü. Windows
API'leri testlerde sahte API ile temsil edildi; gerçek oyun uyumluluğu
doğrulanmadı. Oyunun mesajları kabul edip etmediği kullanıcı makinesinde
ayrıca denenmelidir.

Yerel tanılama güncellemesi: alttaki **Son oturum** satırı yakalanan ve
yönlendirilen olay sayısını, ana pencere odağının görülüp görülmediğini ve
son yönlendirilen olayı gösterir. F12 veya programa dönme nedeniyle aktarım
dursa da bu satır kalır. Bu sayılar oyunun girdiyi işlediğini kanıtlamaz.
Yakalanan 0 ise ana pencere/tuş yakalama tarafı incelenir. Yönlendirilen
artıyor ve karakterler tepki vermiyorsa hedef oyunun arka plan mesajlarını
işlemesi ayrıca kontrol edilir. Hata varsa üstteki durum satırıyla birlikte
bu satırı paylaş.

## Arkadaşının bilgisayarına Interception ile tuş/fare gönderme

1. İkiniz de güncel ZIP'i ayrı, yeni bir klasöre çıkarın.
2. **Alıcı olacak bilgisayarda** `INTERCEPTION_HAZIRLA.bat` açın. Resmi
   GitHub Interception 1.0.1 arşivi HTTPS ile indirilir ve SHA-256 kontrolü
   yapılır. DLL'ler ve resmi kurucu `drivers/Interception-1.0.1/` içine
   hazırlanır. Bu adım sürücüyü kurmaz ve bilgisayarı yeniden başlatmaz.
3. Interception sürücüsü zaten kurulu değilse aynı bilgisayarda
   `INTERCEPTION_SURUCU_KUR.bat` açın. Windows yönetici onayı ister;
   resmi kurucu `/install` ile çalışır. Kurulumdan sonra **Windows'u yeniden
   başlatın**. Betik kurucunun SHA-256 değerini çalıştırmadan önce tekrar
   doğrular. Kurulum başarısızsa konsoldaki hatayı paylaşın.
4. İkiniz de `PROGRAM_BASLAT.bat` açın. Varsayılan sunucu artık
   `wss://sado-link.onrender.com`. Sen sender, arkadaşın receiver seçsin;
   aynı oturum kodunu girin.
5. Arkadaşın bağlantı kurmadan önce **Alıcı girdi yöntemi = Interception**
   seçili bıraksın. **CİHAZLARI BUL** düğmesine bassın. Listede klavye ve
   fare varsa kurulum hazırdır; zaten kurulu sürücüyü yeniden kurmak gerekmez.
6. Klavye/fare için `Otomatik` ilk bağlı cihazı seçer. Birden fazla bağlı
   cihaz varsa listeden açık bir kimlik seçilebilir. Kimlikler resmi C API'ye
   göre klavye **1–10**, fare **11–20** aralığındadır. Cihaz bilgileri
   sunucuya gönderilmez.
7. İkiniz de GERÇEK GİRDİ'yi açıp bağlanın. Arkadaşının logunda
   **Alıcı Interception kullanıyor | Klavye … | Fare …** görünmeli.
8. Önce arkadaşın aktarımı etkinleştirip oyun penceresine geçsin; sonra
   sen gönderimi açıp kendi oyununa geç. Önce tek bir beceri tuşu dene.
   Tuş/fare olayları alıcıda Interception üzerinden uygulanır. **F12 durdurur.**

Gönderici fiziksel girdileri pynput ile yakalar; sadece gönderici olacak
bilgisayara Interception sürücüsü kurmak gerekmez. Standart Windows girdisi
seçeneği ayrıca durur. Interception seçildiğinde hata olursa standart yönteme
sessizce geçilmez; bağlantı başlatılmaz veya aktarım durdurulup hata gösterilir.
Sürücüyü kaldırmak gerekirse resmi kurucu yönetici olarak `/uninstall`
parametresiyle çalıştırılabilir; ardından Windows yeniden başlatılır.

Bu özellik **iki bilgisayar arasındaki internet alıcısına** eklendi.
Yerel çoklu pencere modu ayrı olarak PostMessage kullanmaya devam eder;
Interception fiziksel girdiyi belirli bir arka plan HWND'sine yönlendirmez.
Sanal ekranın tamamına göre mutlak fare koordinatları kullanılır; kamera
hareketleri veya oyun uyumluluğu garanti edilmez. Pause/Break aktarılmaz.

Interception kütüphanesi resmi C API ile çağrılır; uygulama klavye/fare
filtrelerini değiştirmez. DLL dosyalarının hash'i yüklenmeden önce doğrulanır.
Kaynak/lisans: https://github.com/oblitum/Interception (upstream LGPL ve diğer
lisans koşulları). Üçüncü taraf DLL/kurucu bu ZIP'e eklenmez; hazırlama
betiği doğrudan resmi sürümden indirir ve upstream lisansını yanında saklar.

Sürüm 3 doğrulaması: önceki 19 teste ek olarak 9 Interception testinde
C struct boyutları, scan code/E0, cihaz sınırları, sanal masaüstü konumu,
tuş/fare/tekerlek paketleri ve hata halinde bırakma/kapatma kontrol edildi.
Ek bir GUI testi alıcının Interception çıkışını seçip olayları bu çıkışa
aktarmasını ve bağlantı kapanınca kaynağı kapatmasını doğruladı: **29 test**.
Native DLL/driver çağrıları testlerde sahte C API ile temsil edildi. Resmi
arşivin hazırlanması, DLL/kurucu hash'leri ve tekrar çalıştırılabilirliği
gerçek resmi arşivle ayrıca doğrulandı. Windows 11 sürücüsü ve oyun içi
sonuç bu Linux ortamında test edilmedi.

## Yeni: aynı bilgisayarda üç oyun penceresi

Bu sürümde bir ana penceredeki elle verdiğin girdiler, seçtiğin diğer iki
pencereye gönderilebilir. Yerel modda Render sunucusu veya oturum kodu gerekmez.

1. ZIP'i yeni bir klasöre çıkar ve **YEREL_COKLU_BASLAT.bat** aç. İnternet
   programındaki **YEREL ÇOKLU PENCERE** düğmesi de aynı modu açar; mevcut
   internet oturumunu kapatır.
2. Önce **3 PENCERELİ TEST** düğmesine bas. Üç küçük pencere açılır. ANA
   pencerenin iç alanında W'ye basıp bırak, tıkla ve fareyi hareket ettir.
   İki ALICI penceresinde de aynı olaylar görünmeli. F12 ikisini durdurur.
   Bu test yönlendirmeyi simüle eder; Windows oyun girdisi uygulamaz.
3. Oyun denemesi için test pencerelerini kapat. Üç oyun client'ini pencere
   veya kenarlıksız pencere modunda aç. Alıcıları küçültme; arkada kalabilirler.
4. Başlık filtresine oyun pencerenizin başlığından bir parça yaz (`Knight`
   varsayılan) ve **PENCERELERİ YENİLE** düğmesine bas.
5. Elle oynayacağın ana pencereyi açılır listeden seç. Başlıklar aynıysa
   **ÖNDEKİ PENCEREYİ ANA SEÇ (3 sn)** düğmesine basıp üç saniye içinde
   ana karakterin oyun penceresine geç; program o pencereyi seçer.
6. Diğer iki pencereyi alıcı listesinde Ctrl ile seç. Alternatif olarak
   **ÖNDEKİ PENCEREYİ ALICIYA EKLE (3 sn)** düğmesini her bir alıcı için
   kullanıp ilgili karakterin penceresine geç. Ana pencere alıcı olamaz.
7. Önce yalnız tuşları denemek için fare seçeneğini kapatabilirsin.
   **YEREL AKTARIMI BAŞLAT** düğmesine basıp onayla ve seçtiğin ana oyun
   penceresine geç. Bir beceri tuşunu deneyip diğer iki karakterde kontrol et.
8. **F12** aktarımı durdurur. Ana pencere odağı kaybolursa veya seçili bir
   pencere kapanır/küçültülürse aktarım durur ve basılı girdiler bırakılmaya
   çalışılır. Yeniden başlatmak için kontrole dönüp BAŞLAT'a bas.

Yerel mod seçilen HWND/PID'lere Win32 **PostMessage** ile girdi gönderir;
alıcıyı öne getirmez, fiziksel fareyi alıcıya taşımaz. Tuş basma/bırakma,
istemci alanına orantılanan fare konumu/tıklama/tekerlek desteklenir. Mesajın
Windows kuyruğuna kabul edilmesi, oyunun o mesajı işlediğini kanıtlamaz.
Raw Input / DirectInput veya arka plan girdisini kabul etmeyen oyunlarda
çalışmayabilir. Serbest kamera ve aynı hedefe tıklama garantisi yoktur.
Oyunların benzer çözünürlük, arayüz ve beceri düzeninde olması önerilir.
Sohbet metni yazdırmak bu modun doğrulanmış bir özelliği değildir.

Pencereler listelenmezse gerçek başlığa göre filtreyi değiştir veya filtreyi
boş bırakıp yenile. Windows erişim hatası verirse program ile oyunların
yetki seviyesini kontrol et; Windows daha yüksek yetkili hedeflere mesajı
engelleyebilir. Sürücü kurulmaz ve uygulama kendiliğinden yönetici yapılmaz.

Bu özellik Linux'ta yönlendirme, Win32 mesaj oluşturma (sahte API) ve üç
gerçek Tk test penceresiyle denendi. Windows'ta gerçek oyun client'leriyle
henüz doğrulanmadı. Oyun girdiyi kabul etmezse gerçek durumu raporla; test
pencerelerinin çalışması oyun uyumluluğunu göstermez.

Sürüm 2 doğrulaması: 11 yerel yönlendirme/arayüz/yakalama testi ve 8 mevcut
internet istemci/protokol testi geçti. Yerel testler iki alıcıya fan-out,
odak kaybı, pencere kaybı, çıktı hatasında bütün alıcıları bırakma, F12,
fare konum oranlaması ve kapatılan arayüzlerin temizliğini kapsar.

Windows 11 / Python **3.10 veya üzeri**. Bu bağımsız bir tuş/fare aktarım prototipidir;
eski SEGE programının içine kurulmaz. Warrior veya Mage kombosu üretmez: senin
elle bastığın tuşları ve fare olaylarını aktarır. Python'un resmi Windows
kurulumunda gelen tkinter arayüzünü kullanır.

## Arkadaşın çevrimdışıyken hemen dene

1. ZIP dosyasını tamamen bir klasöre çıkar. ZIP içinden çalıştırma.
2. `TEST_BASLAT.bat` dosyasına çift tıkla. İlk açılışta internetten Python
   bağımlılıkları indirilir; sonraki açılışlarda mevcut kurulum kullanılır.
3. **GÖNDERİCİ** ve **ALICI** başlıklı iki pencere açılır, otomatik bağlanır.
   Üst üste açılırlarsa yan yana taşı.
4. Önce **ALICI** penceresinde **AKTARIMI ETKİNLEŞTİR** düğmesine bas.
5. Sonra **GÖNDERİCİ** penceresinde **AKTARIMI ETKİNLEŞTİR** düğmesine bas.
6. Göndericinin yeşil çerçeveli **TEST ALANINA** tıkla. W/A/S/D, 1/2/3,
   sağ/sol fare ve tekerleği dene. Fareyi bu alanın içinde hareket ettir.
7. Alıcıda olay sayısının artmasını, fare işaretinin hareket etmesini ve
   BASILDI/BIRAKILDI kayıtlarını gör. Örneğin **W = VK 87**, **1 = VK 49**.
8. W'yi basılı tutup bırak: alıcıdaki basılı tuş listesine eklenip çıkmalı.
9. **F12** veya **DURDUR**: aktarım durmalı, basılı tuşlar listesi boşalmalı.
   Yeniden başlatırken gerekirse önce alıcı onayını, sonra göndericiyi aç.
10. Bir pencereyi kapat: diğerinde eşleşme/onay kapanmalı. İki pencereyi de
    kapatınca yerel sunucu ve başlatma konsolu sonlanır.

Bu modda gerçek klavye veya fare kontrolü uygulanmaz. Gerçek girdi seçeneği
özellikle kilitlidir. Test alanından başka yere tıklamak basılı tuş durumunu
sıfırlar; bilgisayarındaki diğer uygulamalarda yazdıkların aktarılmaz.
Test ekranındaki olay kayıtları diske kaydedilmez.

## Arkadaşın geldiğinde internetten kullanım

Yerel test sunucusu yalnızca **bu bilgisayarda** çalışır. `127.0.0.1` adresini
arkadaşına göndererek bağlanamazsın. İki ev arasında kullanım için ayrıca
ulaşılabilir bir **WSS/TLS aracı sunucu** kurulmalıdır. Bu pakette sunucu kodu
var; hazır barındırılan sunucu veya canlı internet adresi yoktur.

Aracı sunucu hazırlandıktan sonra:

1. İkiniz de `PROGRAM_BASLAT.bat` açın.
2. Aynı `wss://...` sunucu adresini girin.
3. Sen `sender`, arkadaşın `receiver` seçsin. Senin pencerenin ürettiği
   uzun oturum kodunu yalnızca arkadaşınla paylaş; ikiniz aynı kodu kullanın.
4. Önce test modu ile iki ev arasında olayların geldiğini doğrulayın.
5. Bağlantıyı kesin. İkiniz de **GERÇEK GİRDİ** seçeneğini açıp hedef oyun
   pencere başlığından ayırt edici bir parça girin (varsayılan `Knight`).
   Yeniden bağlanıp gösterilen gerçek girdi onayını kabul edin.
6. Önce alıcı aktarımı etkinleştirsin ve oyun penceresine geçsin; sonra sen
   gönderimi etkinleştirip kendi oyun pencerene geç.
7. Tuş basma/bırakma, fare hareketi, sol/sağ/orta tık ve tekerlek aktarılır.

**F12** gerçek girdi modunda iki tarafta da global durdurmadır ve karşıya
aktarılmaz. Alıcı oyun penceresi odağını kaybederse onay kapanır. Gönderici
odağı kaybederse basılı girdiler sıfırlanır; oyun dışındaki yeni girdiler
aktarılmaz. Pencereleri kapatırken veya bağlantı kaybolunca programın bastığı
tuşlar/fare düğmeleri bırakılır. Yanıt vermeyen sunucu uygulama heartbeat'iyle
yaklaşık 4 saniyede fark edilir; ağ/işletim sistemi koşulları süreyi uzatabilir.
Bağlantı geri gelse bile otomatik yeniden aktarım yapılmaz.

Fare konumu, gönderenin oyun penceresinin iç alanındaki orana göre alıcı
penceresine uyarlanır. İkinizde aynı oyun arayüzü, kamera ve beceri düzeni
olması gerekir. Aynı tıklama farklı karakter/hedef konumlarında farklı sonuç
verebilir. İnternet gecikmesi vardır; tam eşzamanlılık garantisi yoktur.

Gerçek girdide alıcı yöntemi Interception veya Standart Windows seçilebilir.
Interception kurulumu yukarıdadır. Oyunun seçilen girdiyi kabul etmesi
Windows üzerinde ayrıca denenmelidir. Sürücü kurulumu veya yerel testin
geçmesi tek başına oyun uyumluluğunu doğrulamaz.

## Sunucu yöneticisi için

Python 3.10+ ile bağımlılıkları kur:

```sh
python -m venv .venv
# Windows: .venv\Scripts\python.exe
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python relay.py --host 127.0.0.1 --port 8765
```

TLS sonlandıran bir reverse proxy'yi `wss://alan-adiniz` üzerinden bu yerel
porta yönlendir; WebSocket Upgrade ve uzun bağlantıları desteklesin. TLS
sertifikasının doğrulanmasını kapatma. Kullanıcı makinelerindeki istemciler
uzak sunucu için yalnız `wss://` kabul eder. Yerel `ws://` istisnası loopback
adresleriyle sınırlıdır. Oyun oynayan bilgisayarlarda port açılması gerekmez.

Oturum kodu 192 bit rastgelelik taşır; kodu bilen biri odaya katılabilir.
Her odada en fazla bir gönderici ve bir alıcı bulunur. Sunucu olayları
görebilir; aktarım uçtan uca şifrelenmiş değildir, iki TLS bağlantısı kullanır.
Kodları ve girdi içeriklerini reverse proxy loglarına eklemeyin. Sunucu
genel kullanıma açılacaksa bağlantı oran sınırlaması ve işletim izlemesi de
yapılmalıdır. Bu paket bu barındırma işlemlerini otomatik yapmaz.

## Kontroller ve sınırlar

```sh
.venv/bin/python -m unittest discover -s tests -v
```

Relay testleri: alıcı onayı öncesi olay engelleme, tuş/fare/tekerlek aktarımı,
sıfırlama, kopuşta onay kapatma, tekrar bağlantıda yeni onay, oda ayrımı,
aynı rolün ikinci kez bağlanmasını reddetme, bozuk olayları/F12'yi reddetme
ve uzak bağlantıda TLS zorunluluğunu doğrular.

İlk sürüm Linux'ta **8 başarılı testle** doğrulanmıştı. Bunlardan biri sanal
ekranda iki gerçek Tk penceresi ve gerçek WebSocket bağlantısı kullanarak
W basma/bırakma, fare hareketi/tıklaması, F12 ve kopuş davranışını denedi.
Ayrı bir test, bağlantı açık kalsa bile sunucu uygulaması yanıt vermediğinde
istemcinin heartbeat süresi sonunda bağlantıyı kapattığını doğruladı.
Windows 11'de gerçek girdi ve oyun uyumluluğu henüz doğrulanmamıştır. İlk
kullanıcı denemesi için yukarıdaki yerel TEST modunu kullan.

## Sorun giderme

- Python bulunamazsa Python 3.10+ kurulumunu kontrol et. `.bat` önce `py -3`,
  sonra `python` komutunu dener. Hata olursa konsol açık kalır.
- Pencereler açılmıyorsa konsoldaki tam hata mesajını paylaş.
- Alıcıda olay yoksa ikisinin de eşleştiğini, alıcı onayını ve gönderim
  durumunu kontrol et. Testte tuşları yalnız yeşil alan odaktayken dene.
- Gerçek girdide karakter tepki vermiyorsa önce hedef pencere başlığını
  kontrol et. Testte başarı, oyunun girdiyi kabul ettiğini kanıtlamaz.
