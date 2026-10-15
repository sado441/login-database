# SADO Link

İki Windows bilgisayarı arasında tuş/fare aktarımı ve aynı bilgisayarda
bir ana pencereden diğer iki pencereye yerel aktarım prototipi.

Windows paketi: [SADO-Link.zip](SADO-Link.zip). ZIP'i tamamen çıkarıp arkadaşın
çevrimdışıyken `TEST_BASLAT.bat` ile iki pencereli yerel deneme yapabilirsin.
İnternet bağlantısı için `PROGRAM_BASLAT.bat` kullanılır. Paket içindeki
`OKU_BENI.md` ayrıntılı istemci yönergesidir.

## SEGE kaynağı esas alınan yerel mod (sürüm 4)

İlk verilen SEGE-MACRO kaynağındaki multi/background girdi yolları incelendi.
Yerel moda **SEGE uyumlu klavye** eklendi: keyboard.hook ile ham scan code,
tekrarlanan key-down ve her tuştan önce WM_ACTIVATE bildirimi. Seçenek ilk
oyun denemesinde varsayılan olarak açıktır. Kaynaktaki sol/sağ tıkla W/X
takip davranışı da ayrı, isteğe bağlı seçenek olarak bulunur.

[Kaynak karşılaştırması](desktop/SOURCE_COMPARISON_TR.md) ve upstream lisans
bildirimleri istemci kaynaklarında ve ZIP içinde yer alır. 38 istemci testi
geçti; gerçek Windows oyun uyumluluğu henüz doğrulanmadı. İlk denemede fare
seçeneklerini kapatıp tek beceri tuşunu dene; Son oturum tanılaması durduktan
sonra da kalır. Güncel yerel pencerenin başlığında **v4** görünür.

## Interception alıcı desteği (sürüm 3)

Güncel ZIP'te internet alıcısı için **Interception** çıktı yöntemi vardır.
Klavye ve fare hareketi/tıklama/tekerlek olayları resmi Interception C API
üzerinden gönderilir. Varsayılan alıcı yöntemi Interception'dır; sürücü
yoksa hata gösterilir, standart yönteme sessiz geçiş yapılmaz.

Alıcı bilgisayarda önce `INTERCEPTION_HAZIRLA.bat` çalıştırılır. Resmi
upstream arşivi ve DLL'ler SHA-256 ile doğrulanır. Sürücü kurulu değilse
`INTERCEPTION_SURUCU_KUR.bat` yönetici onayıyla çalıştırılır ve Windows
yeniden başlatılır. Ardından `PROGRAM_BASLAT.bat` → receiver → CİHAZLARI BUL
ile bağlı cihazlar kontrol edilir. Göndericiye sürücü kurmak gerekmez.
Tüm adımlar ve lisans bağlantısı paket içindeki `OKU_BENI.md` dosyasında.

Interception entegrasyon testleri geçti; gerçek Windows sürücüsü ve oyun uyumluluğu Linux'ta
doğrulanamadı. Yerel çoklu pencere modu PostMessage kullanır; Interception
yalnız internet üzerinden gelen girdiyi alıcıya uygulayan yönteme eklendi.

## Aynı bilgisayarda üç client (sürüm 2)

Güncel ZIP'i yeni bir klasöre çıkarıp `YEREL_COKLU_BASLAT.bat` aç.
Önce `3 PENCERELİ TEST` ile bir ana pencereden iki alıcıya olay
yönlendirmesini dene. Ardından üç oyun penceresini aç; ana pencereyi ve
diğer iki alıcıyı listeden seç. Aynı başlıklı pencereleri, üç saniye içinde
ilgili pencereye geçerek seçen düğmeler de var. Yerel aktarım için sunucuya
bağlanmak gerekmez. F12 durdurur.

Bu özellik PostMessage kullanır; oyunun arka plandaki girdiyi kabul etmesi
Windows üzerinde ayrıca doğrulanmalıdır. Üç test penceresinin çalışması
oyun uyumluluğu anlamına gelmez. İstemci kaynakları `desktop/` altında;
sunucu dağıtım dosyaları depo kökündedir.

## Render ile sunucu kurma

[Render'da kurulumu aç](https://render.com/deploy?repo=https://github.com/sado441/login-database)

1. Render hesabınla giriş yap. Bu bağlantı depodaki `render.yaml` dosyasını
   kullanan Blueprint kurulumunu açar. Gerekirse GitHub bağlantısı kurup bu
   depoya erişim ver.
2. Blueprint için `sado-link` gibi bir ad gir. Hizmet ayarlarında Free plan
   seçildiğini kontrol et; farklı bir ücretli plan otomatik seçilmişse
   kendi tercihin olmadan ilerleme.
3. Arayüzün gösterdiği `Deploy` / `Apply` düğmesiyle kurulumu başlat.
4. Hizmetin durumu `Live` olana kadar bekle. Hizmetin sayfasındaki gerçek
   `https://...onrender.com` adresini kopyala. Adresin tam adı Render tarafından
   belirlenir; örnek adresleri kullanma.
5. Bu adrese tarayıcıda girince `SADO Link sunucusu calisiyor.` yazmalı.
   `/healthz` yolunda `ok` yanıtı gelir.
6. İki istemcide de `https://` yerine `wss://` kullanarak bu adresi Sunucu
   alanına yaz. Alan adına `:8765` veya `/healthz` ekleme.
7. Birinde sender, diğerinde receiver seç; göndericinin ürettiği uzun oturum
   kodunu alıcıya da gir. İlk internet denemesinde GERÇEK GİRDİ kapalı kalsın.
8. İkisini de bağla. Önce alıcıda, sonra göndericide aktarımı etkinleştir.
   Göndericinin test alanında W/fare olaylarını deneyip alıcıda doğrula.

## Blueprint kullanmadan elle kurulum

Render Dashboard → New → Web Service → GitHub deposunu bağla.

| Alan | Değer |
|---|---|
| Repository | `sado441/login-database` |
| Branch | `main` |
| Runtime / Language | Python |
| Root Directory | Boş bırak |
| Build Command | `pip install -r requirements-server.txt` |
| Start Command | `python -u relay.py --host 0.0.0.0 --port $PORT` |
| Health Check Path | `/healthz` |
| Instance | İlk deneme için Free |
| Instances | 1 |

TLS sertifikasını ve WebSocket yönlendirmesini Render sağlar; oyuncuların
modeminde port açılmaz. Alan adı veya özel sır eklemen gerekmez; eşleşme
istemcilerin paylaştığı rastgele oturum koduyla yapılır. Kodu yalnızca
bağlanacak kişiyle paylaş.

Oda bilgisi RAM'dedir; tek instance kullanılmalıdır. Sunucu yeniden
başladığında odalar ve onaylar sıfırlanır. Ücretsiz hizmetin uyku/kaynak
sınırları olabilir; ilk bağlantı gecikebilir. Sunucu uyanınca istemcide
Bağlan düğmesini tekrar kullan. Bu prototipte otomatik yeniden aktarım yoktur.

## Gerçek oyun girdisi

İnternet testinden sonra bağlantıyı iki tarafta da kes. İkiniz de GERÇEK
GİRDİ seçeneğini açıp kendi oyun pencerenizin başlığından bir parça girin.
Yeniden bağlanın; önce alıcı aktarımı etkinleştirip oyununa geçsin, ardından
gönderici aktarımı açıp kendi oyununa geçsin. F12 durdurur. Windows girdisinin
oyun tarafından kabul edilmesi ayrıca doğrulanmalıdır. Yerel testin başarılı
olması oyun uyumluluğunu kanıtlamaz.

## Sunucu doğrulaması

```sh
python -m pip install -r requirements-server.txt
python -m unittest discover -s tests -v
```

Sunucu onay, oda ayrımı, tuş/fare aktarımı, kopuş ve HTTP sağlık kontrolü
testleri içerir. GitHub'a yüklenmesi, Render'da dağıtımın tamamlandığını veya
iki ev arasındaki bağlantının test edildiğini göstermez. Render hesabını
bağlama ve dağıtımı başlatma işlemleri hesap sahibi tarafından yapılır.
