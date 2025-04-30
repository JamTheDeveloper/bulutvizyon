# BulutVizyon Dijital Ekran Yönetim Sistemi PRD

## Genel Bakış

BulutVizyon, işletmelerin dijital ekranlarını yönetmelerini sağlayan bir web uygulamasıdır. Kullanıcılar, uygulamaya medya yükleyebilir, içerikleri ekranlara atayabilir ve içerik programlaması yapabilir.

## Kullanıcı Rolleri

1. **Admin**: Tüm sistemi yönetir, kullanıcıları ve ekranları onaylar.
2. **Supervisor**: İçerikleri onaylar, kullanıcılara yardımcı olur.
3. **User**: İçerik yükler, ekranlarını yönetir.

## Backend Mimari

- Flask web framework
- MongoDB veritabanı 
- JWT veya session tabanlı kimlik doğrulama
- Flask-WTF ile CSRF koruması
- Dosya depolama: Yerel depolama veya S3 benzeri bulut depolama
- RESTful API
- Socket.IO gerçek zamanlı iletişim (2. fazda)

## Veritabanı Yapısı

MongoDB veritabanı aşağıdaki koleksiyonlardan oluşmaktadır:

1. **users**: Kullanıcı bilgileri
   - _id: ObjectId
   - email: String
   - password_hash: String
   - name: String
   - role: String ('admin', 'supervisor', 'user')
   - package: String ('basic', 'standard', 'premium')
   - status: String ('active', 'inactive', 'pending')
   - supervisor_id: ObjectId (opsiyonel)
   - created_at: DateTime
   - updated_at: DateTime
   - last_login: DateTime

2. **screens**: Ekran bilgileri
   - _id: ObjectId
   - name: String
   - description: String
   - location: String
   - api_key: String
   - resolution: String
   - orientation: String ('horizontal', 'vertical')
   - status: String ('active', 'inactive', 'pending')
   - user_id: ObjectId
   - playlist_id: ObjectId (opsiyonel)
   - created_at: DateTime
   - updated_at: DateTime
   - last_access: DateTime

3. **media**: Medya dosyaları
   - _id: ObjectId
   - title: String
   - description: String
   - filename: String
   - file_path: String
   - file_type: String ('image', 'video', 'webpage', 'custom')
   - file_size: Number
   - width: Number
   - height: Number
   - duration: Number (video için, saniye)
   - display_time: Number (görüntülenme süresi, saniye)
   - category: String
   - tags: Array
   - orientation: String ('horizontal', 'vertical')
   - status: String ('active', 'inactive', 'pending')
   - is_public: Boolean
   - views: Number
   - user_id: ObjectId
   - created_at: DateTime
   - updated_at: DateTime

4. **screen_media**: Ekran ve medya ilişkisi
   - _id: ObjectId
   - screen_id: ObjectId
   - media_id: ObjectId
   - order: Number (sıralama)
   - display_time: Number (opsiyonel, medya gösterim süresi)
   - status: String ('active', 'inactive')
   - created_at: DateTime
   - updated_at: DateTime

5. **media_shares**: Medya paylaşımları
   - _id: ObjectId
   - media_id: ObjectId
   - user_id: ObjectId (paylaşılan kullanıcı)
   - assigned_by: ObjectId (paylaşan kullanıcı)
   - created_at: DateTime

6. **playlists**: Oynatma listeleri
   - _id: ObjectId
   - name: String
   - description: String
   - user_id: ObjectId
   - status: String ('active', 'inactive')
   - created_at: DateTime
   - updated_at: DateTime

7. **playlist_media**: Oynatma listesi ve medya ilişkisi
   - _id: ObjectId
   - playlist_id: ObjectId
   - media_id: ObjectId
   - order: Number (sıralama)
   - display_time: Number (opsiyonel)
   - created_at: DateTime
   - updated_at: DateTime

8. **logs**: Sistem log kayıtları
   - _id: ObjectId
   - action: String
   - user_id: ObjectId
   - details: Object
   - ip_address: String
   - created_at: DateTime

## Frontend

- HTML, CSS, JavaScript
- Bootstrap 5 framework
- FontAwesome ikonları
- Sürükle-bırak işlemleri için JavaScript

## Temel Özellikler

### Yapıldı

- MongoDB entegrasyonu
- Model yapıları (User, Media, Screen, ScreenMedia, Log)
- Kullanıcı girişi ve kaydı
- Admin route'ları
- Admin panel: Kullanıcıları görüntüleme ve yönetme
- Admin panel: Kullanıcı detay sayfası
- Admin panel: Medya dosyaları onaylama ve yönetme
- Supervisor panel: Dashboard
- Supervisor panel: Medya listeleme ve onaylama
- Supervisor panel: Medya detay sayfası
- Supervisor panel: Profil yönetimi
- User panel: Dashboard
- User panel: Profil yönetimi 
- User panel: Medya yönetimi
- User panel: Ekran yönetimi
- User panel: Paket yükseltme sistemi
- Kullanıcı profil ayarları ve şifre değiştirme
- Screen-Media ilişki modeli
- CSRF koruması
- Log sistemi
- Form doğrulama ve hata yönetimi
- Email şablonları ve bildirim sistemi
  - Hoş geldiniz email'i
  - Şifre sıfırlama email'i
  - Medya onay bildirimi
  - Medya red bildirimi
  - Ekran durum değişikliği bildirimi
- Email bildirim sisteminin yaşam döngüsüne entegrasyonu:
  - Yeni kullanıcı oluşturulduğunda hoşgeldiniz e-postası
  - Şifremi unuttum ve şifre sıfırlama
  - Medya onaylandığında/reddedildiğinde bildirim
  - Ekran durumu değiştiğinde bildirim
- Medya detaylı görüntüleme sayfası
- Medya düzenleme sayfası
- Medya silme işlemi ve onay mekanizması
- Medya dosyalarının sunulması için /uploads endpoint'i
- Ekranlarda medya kullanım kontrolü ve uyarı sistemi
- Kullanıcılara supervisor atama sistemi
- Supervisorlar tarafından medya onaylama workflow'u
- Supervisor olmayan kullanıcılar için otomatik medya onaylama
- Kullanıcı kısmında public kütüphane listesi eklenmesi (public_library.html)
- Admin in video ekleyebilmesi 
- Adminin eklediği videoların public kütüphaneye yada herhangi bir kullanıcıya atayabilmesi
- Playlist oluşturma ve ekranlara playlist atama sistemi
- Ekran içerik yönetimi sayfasında ağaç yapısı (playlist ve medya ilişkisi)
- Playlist silme ve düzenleme özelliği
- Playlist'lerin içerdiği medyaların ağaç yapısında görüntülenmesi
- Video ve görsel için otomatik/manuel görüntülenme süresi ayarlama
- API sisteminde ekleme ve düzenlemeler
- İstatistik ve analitikte medya görüntülenme sayılarının tutulması
- Player önizleme sayfası ve ekran içeriği yönetimi
- Kullanıcıların bir ekrana birden fazla playlist atayabilmesi
- Kullanıcıların Ekranlara video ataması
- Bir videoyu çoklu ekrana atayabilme
- Medya içeriklerinin API üzerinden dağıtılması
- Player API endpoint'lerinin oluşturulması
- Ekran görüntüleme arayüzü (viewer.html) iyileştirmeleri
  - Responsive tasarım desteği
  - Video oynatma mekanizmasının iyileştirilmesi
  - Geçiş efektleri eklenmesi
  - Hata ve yükleme ekranlarının geliştirilmesi
  - Ekran boyutlarına uygun hale getirilmesi
  - **Çevrimdışı Mod Desteği:** Service Worker kullanılarak medya dosyalarının önbelleğe alınması ve internet bağlantısı kesildiğinde bile oynatılabilmesi.
  - **Gelişmiş Video Oynatma ve Geçiş:** Video zamanlayıcıları ve `onended` olayları ile daha güvenilir video geçişleri, yalnızca fade efekti kullanılarak basitleştirilmiş geçişler.
  - **Landing Page:** Projeyi tanıtan basit bir ana sayfa (`index.html`).
- **Dark Theme Tasarım:** Koyu tema üzerine kurulu modern, gradient efektli kullanıcı arayüzü.
  - Admin, Supervisor ve User panelleri için dark tema uygulaması
  - Tablo başlıkları, kartlar, form elemanları ve butonlar için özelleştirilmiş görünüm
  - Tüm bileşenler için renk paletleri ve tutarlı stil uygulaması
- **Responsive Footer:** Tüm sayfalar için ortak, mobil cihazlarda optimize edilmiş site altbilgisi.
- **İçerik Sayfaları Tasarımı:** Gizlilik Politikası, İade Politikası gibi içerik sayfaları için tutarlı tasarım şablonu.
- **Sayfa Header Tasarımı:** Davis temalı modern başlık bileşeni.
- **Mobil Uyumlu Görünüm:** Tüm ekran boyutlarında düzgün çalışan responsive tasarım.

### Yapılacaklar

- Adminin supervisora yükleme yapabilme yetkisi vermesi
- Kullanıcının paket bilgilerinin veritabanına entegrasyonu
- Ekranların otomatik içerik listeleri oluşturma
- Cihaz yönetimi ekranı
- Uzaktan cihaz kontrolleri
- İstatistik ve raporlama geliştirmeleri
- Arayüz geliştirmeleri
    - Admin dashboard için modern veri görselleştirme kartları
    - Kullanıcı ve ekran yönetim sayfaları için filtrelenebilir data tabloları 
    - Yüklenmiş medya içerikleri için grid/liste görünüm seçenekleri
    - Hızlı eylem butonları ve onay/red modülleri için modern dialog kutuları
    - Onay bekleyen medya içerikleri için önizleme kartları
    - Media yükleme ve yönetim arayüzünün modernizasyonu
    - Ekran-içerik ilişkisi için sürükle bırak arayüzü
  - Mobil uyumlu admin panel geliştirmesi
- Frontend kodlarının optimize edilmesi
- Dokümantasyon
- Paket sistemi
- Ödeme altyapısı

## Öncelikler

1. Email template oluşturma
2. Paket sisteminin tam entegrasyonu
3. Player API endpoint'lerinin oluşturulması
4. Cihaz yönetim paneli geliştirme
5. İstatistik ve raporlama sistemi

## Medya Tipleri

1. Görsel (JPEG, PNG, GIF)
2. Video (MP4, WEBM)
3. Web sayfası URL (iframe olarak gösterilecek)
4. HTML içeriği (özel tasarlanmış içerikler)

## Ekran İçerik Yönetimi

- Ekranlar için içerik sıralaması
- Görüntüleme süresi ayarları
- İçerik geçişleri için efekt seçenekleri
- İçeriklerin programlanması (belirli saatlerde gösterilmesi)
- Acil durum mesajları (tüm içerikleri geçersiz kılarak gösterilir)

## Paket Sistemi

Sistem üç temel pakete sahiptir:
1. **Temel Paket**: 3 ekran, 50 medya ve 500 MB depolama - 99 TL/ay
2. **Standart Paket**: 10 ekran, 150 medya ve 2 GB depolama - 199 TL/ay
3. **Premium Paket**: 30 ekran, 500 medya ve 5 GB depolama - 399 TL/ay

## API Endpoint Yapısı

1. `/api/v1/auth`: Kimlik doğrulama ve kullanıcı yönetimi
2. `/api/v1/screens`: Ekran yönetimi
3. `/api/v1/media`: Medya yönetimi
4. `/api/v1/player`: Oynatıcı API'si (ekranlar için)

## Güvenlik Gereksinimleri

- CSRF koruması (Flask-WTF)
- Tüm API istekleri için JWT doğrulaması
- Medya dosyaları için güvenli URL'ler
- Rate limiting
- Dosya türü ve boyutu doğrulama
- Ekran kimlik doğrulama sistemi

## İleri Aşama Özellikleri

- Gerçek zamanlı analitikler
- Gelişmiş ekran içeriği programlama
- Kullanıcı davranış analizi
- AI tabanlı içerik önerileri
- Mobil uygulama

## Proje Klasör Yapısı

```
/bulutvizyonServer/
│
├── run.py                     # Uygulamayı başlatan ana dosya
├── requirements.txt           # Bağımlılıklar
├── prd.md                     # Proje gereksinim dokümanı
│
├── app/                       # Uygulama klasörü
│   ├── __init__.py            # Flask uygulamasını başlatır
│   │
│   ├── models/                # Veritabanı modelleri
│   │   ├── __init__.py
│   │   ├── user.py            # Kullanıcı modeli
│   │   ├── screen.py          # Ekran modeli
│   │   ├── media.py           # Medya modeli
│   │   ├── screen_media.py    # Ekran-Medya ilişki modeli
│   │   └── logs.py            # Log modeli
│   │
│   ├── routes/                # Route modülleri
│   │   ├── __init__.py
│   │   ├── auth.py            # Kimlik doğrulama route'ları
│   │   ├── admin.py           # Admin paneli route'ları
│   │   ├── supervisor.py      # Supervisor paneli route'ları
│   │   ├── user.py            # Kullanıcı paneli route'ları
│   │   └── api.py             # API route'ları
│   │
│   ├── static/                # Statik dosyalar
│   │   ├── css/               # CSS dosyaları
│   │   │   └── style.css      # Ana stil dosyası
│   │   │
│   │   ├── js/                # JavaScript dosyaları
│   │   │   └── script.js      # Ana JavaScript dosyası
│   │   │
│   │   ├── images/            # Görsel dosyaları
│   │   │   ├── logobulut.png  # Ana logo
│   │   │   └── yataylogobulut.png  # Yatay logo
│   │   │
│   │   └── uploads/           # Yüklenen dosyalar
│   │
│   ├── templates/             # HTML şablonları
│   │   ├── auth/              # Kimlik doğrulama şablonları
│   │   │   ├── login.html
│   │   │   ├── register.html
│   │   │   ├── forgot_password.html  # Şifre sıfırlama
│   │   │   └── reset_password.html   # Şifre sıfırlama
│   │   │
│   │   ├── admin/             # Admin panel şablonları
│   │   │   ├── dashboard.html
│   │   │   ├── users.html
│   │   │   ├── screens.html
│   │   │   ├── media.html
│   │   │   └── ...
│   │   │
│   │   ├── supervisor/        # Supervisor panel şablonları
│   │   │   ├── dashboard.html
│   │   │   ├── media.html
│   │   │   └── ...
│   │   │
│   │   ├── user/              # Kullanıcı panel şablonları
│   │   │   ├── dashboard.html
│   │   │   ├── screens.html
│   │   │   ├── media.html
│   │   │   ├── profile.html
│   │   │   ├── packages.html
│   │   │   ├── public_library.html   # Public kütüphane sayfası
│   │   │   └── ...
│   │   │
│   │   ├── pages/             # İçerik sayfaları
│   │   │   ├── about.html     # Hakkımızda sayfası
│   │   │   ├── faq.html       # Sıkça Sorulan Sorular
│   │   │   ├── delivery.html  # Teslimat Bilgileri
│   │   │   ├── privacy.html   # Gizlilik Politikası
│   │   │   ├── refund.html    # İade Politikası
│   │   │   └── terms.html     # Kullanım Şartları
│   │   │
│   │   ├── errors/            # Hata sayfaları
│   │   │   ├── 404.html
│   │   │   └── 500.html
│   │   │
│   │   ├── base.html          # Ana şablon (header + footer)
│   │   └── index.html         # Ana sayfa (landing page)
│   │
│   ├── utils/                 # Yardımcı fonksiyonlar
│   │   ├── __init__.py
│   │   ├── decorators.py      # Yetkilendirme dekoratörleri
│   │   ├── helpers.py         # Genel yardımcı fonksiyonlar
│   │   └── email.py           # E-posta gönderme fonksiyonları
│   │
│   └── config.py              # Yapılandırma ayarları
│
├── tests/                     # Test klasörü (gelecekte eklenecek)
│   ├── __init__.py
│   └── test_*.py              # Test dosyaları
│
└── docs/                      # Dokümantasyon klasörü (gelecekte eklenecek)
    └── api_docs.md            # API dokümantasyonu
```
