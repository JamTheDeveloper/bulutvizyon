# BulutVizyon

BulutVizyon, LED ekranlar ve Raspberry Pi bağlı monitörler için dijital içerik yönetim sistemidir. Kullanıcılar video/resim yükleyebilir, reklam yayınlayabilir ve özelleştirilmiş içerikler ekleyebilir.

## Özellikler

- Kullanıcı yönetimi: Admin, Denetmen ve Kullanıcı rolleri
- Medya yönetimi: Video ve resim yükleme, önizleme, kategori sistemi
- Ekran yönetimi: Yatay/dikey ekranlar, API tabanlı önizleme
- Onay sistemi: Denetmen onayı ile içerik yayınlama
- Sektörel içerik desteği: Eczane, Perakende, Restoran vb.

## Kurulum

### Ön Gereksinimler

- Python 3.8+
- MongoDB 4.4+
- pip

### Adımlar

1. Projeyi klonlayın:

```bash
git clone https://github.com/kullanici/bulutvizyon.git
cd bulutvizyon
```

2. Gerekli paketleri kurun:

```bash
pip install -r requirements.txt
```

3. `.env` dosyasını oluşturun (örnek):

```
SECRET_KEY=cok_gizli_anahtar
MONGO_URI=mongodb://localhost:27017/
MONGO_DB_NAME=bulutvizyon
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-email-password
MAIL_DEFAULT_SENDER=your-email@gmail.com
```

4. Uygulamayı çalıştırın:

```bash
python app.py
```

## Kullanım

Uygulama çalıştığında `http://localhost:5005` adresinden erişilebilir.

### Admin Paneli

- Kullanıcı, Ekran ve Medya yönetimi
- Denetmen atamaları
- İstatistikler

### Denetmen Paneli

- Medya onaylama/reddetme
- Kullanıcı içeriklerini inceleme

### Kullanıcı Paneli

- Medya yükleme ve yönetimi
- Ekran oluşturma ve yönetimi
- Profil yönetimi

## API Kullanımı

### Önizleme API

```
GET /api/preview/{api_key}
```

Ekran için medya listesini döndürür.

### Durum Bildirme API

```
POST /api/screen-status/{api_key}
```

Ekran durum bilgisi gönderir.

## Proje Yapısı

```
bulutvizyonServer/
├── app/
│   ├── models/         # Veritabanı modelleri
│   ├── routes/         # Route tanımları
│   ├── static/         # Statik dosyalar (CSS, JS)
│   ├── templates/      # HTML şablonları
│   └── utils/          # Yardımcı fonksiyonlar
├── uploads/            # Yüklenen dosyalar
├── app.py              # Ana uygulama dosyası
├── requirements.txt    # Gerekli paketler
└── prd.md              # Proje gereksinimleri
```

## Lisans

Bu proje özel lisans altında sunulmaktadır. Tüm hakları saklıdır. 