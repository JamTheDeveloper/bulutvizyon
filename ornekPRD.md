# BulutVizyon - Ürün Gereksinim Dokümanı (PRD)
Bu proje; Led ekran ve raspbery bağlı monitörlerde reklam gösterme yazılımı olacak. Kullanıcılar video ekleyebilecek, reklamlarını oynatabilecek, döviz kurlarını 
girebilecek, Benzin mazot fiyatlarını girebilecek vb.. işlemler yapabilecek kullanacağı sektöre göre üyelik tabanlı bir site yönetimi olacak.Veri tabanı mongoDB olacak
Kolleksiyon un adı bulutvizyon
## 1. Yapıldı

## 2. Yapılacaklar
- **Kullancı Kısmı**
  - Bu kısım projenin yönetim kısmı olmalı.
  - Flask kullanarak ve FastApi ile yazılmalı. 
  - Kullanıcıları admin oluşturacak.
  - Oluşturulan kullanıcılara hoşgeldin maili ve geçici 6 karakterli random bir şifre yollanacak.
  - Kullanıcılar ilk kez girdiğinde sisteme şifre değişikliği istenecek.
  - Kullanıcılar kendi bilgilerini düzenleyebilicek.
  - Kullanıcılar Ekran oluşturabilecek ancak üyelik paketi kadar oluşturabilecek.Stanndart Paket 3 ekran Pro Paket 10 Ekran Kurumsal Paket sınırsız ekran gibi
  - Kullanıcıların Yönetici -  Denetmen - Kullanıcı rolleri olacak.
    - **Kullanıcı Sistemi**
    - Yönetici  : Tüm yetkiye sahip eklenen, her ekranı ve her kullanıcı ve denetçinin haraketlerini takip edebilen ve yöneten kişi.
    - Denetmen  : Bu her kullanıcı için geçerli olamyacak. sadece yöneticinin atadığı kişilere bu yetki verilecek, belli kullanıcılar denetleyebilecek ve paylaşılan 
    içeriği onaylayabilecek. Bu yetki kullanılmasada bu role Yöneticiyi de atanabilecek.
    - Kullanıcı : Video veya resim upload edebilmeli. Sürükle bırak tekniği de aktif olmalı. Kendi bilgilerini düzenleyebilmeli.
  - Yönetici Her Ekranı, Her Denetmeni ve her kullanıcıyı ve her medyayı Aktif Pasif yapabilecek. Kullanıcıları silebilecek. Medyaları silip düzenleyebilecek.
- **Medya Kısımı**
  - Medyaların boyut sınırı olmalı.
  - Yüklenen Medya yataysa yatay olan ekrana atanabilmeli Dikeyse Dikey ekrana atanabilmeli (Yatay dikey ayrımı pixel girişine göre belirlenecek.)
  - Yüklenen Medya ister resim isterse de video olabilir.
  - Video ileriki bir tarihte yayaınlanabilir(Kampanya gibi saatlik veya günlük de olabilir.)
  - Medya listesinde medyanın çözünürlüğü boyutu gibi bilgiler görünmeli
  - Medyaların ön izlemesi mutlaka olmalı uygun bir sayfada ama muhtemelen ekrana atanmadan önce olmalı
  - Medyaları tek seferde bir çok ekrana atayabilmek gerekebilir.(sürükle bırak da kullanılabilir. ekranın üstüne atıp listeye ekleme gibi)
  - Kullanıcı haraketleri ve medyaların loglarının tutulması gerekli kim nezaman hangi ipden hangi isimli videoyu eklemiş görmek gerekebilir.
  - Medyanın ekrana eklendikçe ekranda kalma süresi gerekli
  - Hangi tarihler arasında kaç kez gösterim aldığı müşterinin görmesi gerekebilir.
- **Denetmen Kısmı**
  - Denetmenler sadece videonun yayınlanmasına izin vermeli.
  - Denetmenleri yönetici atamalı
  - denetmen ekranı sade ve şık olmalı
- **Preview Kısmı**
  - Bu kısım bir api adresi olacak ve api no ile girecek
  - api no 11 karakterden oluşmalı
  - previewde olacak olan slider çoklu animasyonu desteklemeli
  - chromium browserda sorunsuz çalışmalı
  - Medyayı ortalamalı
- **Medya Kategori ve Kütüphane Sistemi**
- Medya dosyaları kategorilendirilebilmeli
- Ortak kütüphane oluşturulabilmeli
- Her medyanın hangi ekranlara eklendiği ve hangi kullanıcılara ait olduğu görülebilmeli
- **Public Kütüphane Sistemi**:
  - Yüklenen medyalar public kütüphaneye eklenebilmeli
  - Public kütüphane kategorilere göre düzenlenmeli
  - Kullanıcılar kendi yükledikleri medyaları istedikleri public kütüphanelere atayabilmeli
  - Medya listeleme kategorilere göre filtrelenebilmeli
  - Her public kütüphane için erişim izinleri belirlenebilmeli

- **Sektörel Özelleştirmeler**

  - **Eczaneler**
    - Nöbetmatik entegrasyonu
    - Eczanelerin özel gün kutlama mesajları
    - Ürün tanıtımları
  - **Eczacı Odası Kullanıcı Tipi** (denetmen örneği):
  - İl bazlı yetkilendirme
  - İldeki içerikleri ve eczaneleri görüntüleme
  - Denetleme ve yayın onaylama özellikleri

  - **Perakende**
    - Ürün kampanyaları ve indirimler
    - Marka reklamları gösterme

  - **Restoranlar**
    - Dijital menü oluşturma
    - Günün özel teklifleri
    - Kampanyalı ürün yönetimi

  - **Kurumsal**
    - Firma tanıtım videoları
    - Kurum içi duyurular

  - **Sağlık (Hastaneler)**
    - Hasta bilgilendirme içerikleri
    - Doktor tanıtımları
    - Sağlık bilgileri

  - **AVM**
    - Mağaza rehberleri
    - Etkinlik duyuruları
    - AVM haritası

  - **Benzin İstasyonları**
    - Fiyat bilgisi gösterimi
    - Reklam yönetimi
    - **Fiyat Güncelleme Özelliği**:
      - Kullanıcılar fiyat girebilmeli
      - Fiyatların aktif olacağı tarih belirlenebilmeli

  - **Finans**
    - Veri gösterimleri
    - Döviz/altın fiyatları

  - **Ulaşım**
    - Sefer bilgisi
    - Durak bilgisi
    - Hat bilgisi


### 2.1 Sistem Genel Bakış
BulutVizyon, bulut tabanlı dijital ekran yönetim sistemidir. Kullanıcıların uzaktan dijital ekranları yönetmesine, içerik paylaşmasına ve programlamasına olanak tanır.

### 2.2 Mevcut Özellikler
- **Kullanıcı Yönetimi**
  - Kayıt ve giriş işlemleri
  - Profil yönetimi
  - Admin ve standart kullanıcı rolleri
  
- **Ekran Yönetimi**
  - Ekran ekleme ve yapılandırma
  - Ekran durumu izleme
  - API anahtar yönetimi
  
- **Medya Yönetimi**
  - Görsel ve video yükleme
  - Medya ataması yapma
  - Medya önizleme
  
- **İçerik Programlama**
  - Ekranlara medya atama
  - İçerik gösterim sırası ayarlama
  
- **Admin Paneli**
  - Kullanıcı yönetimi
  - Ekran takibi
  - Medya takibi
  - Destek talepleri yönetimi

## 3. Yapılacak Eklemeler


### 3.3 Kampanya Yönetimi
- Video ve görsellere kampanya tarihi atama
- Tarih/zaman bazlı içerik gösterimi
- Kampanya planlaması

## 4. Veritabanı Geliştirmeleri

## 5. Önceliklendirme

bulutvizyonServer/
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── media.py
│   │   ├── screen.py
│   │   └── logs.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── auth.py
│   │   ├── supervisor.py 
│   │   ├── user.py
│   │   └── api.py
│   ├── static/
│   │   ├── css/
│   │   ├── js/
│   │   └── uploads/
│   ├── templates/
│   │   ├── admin/
│   │   ├── supervisor/
│   │   ├── user/
│   │   └── auth/
│   └── utils/
│       ├── __init__.py
│       ├── email.py
│       └── helpers.py
├── instance/
├── uploads/
│   ├── images/
│   └── videos/
├── prd.md
├── app.py
├── requirements.txt
└── README.md