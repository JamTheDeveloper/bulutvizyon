# Dashboard Playlist Listesi Geliştirme Yol Haritası

## Genel Bakış
User dashboard ekranına mevcut 4 kartın altına tüm genişlikte bir playlist listesi eklenecek. Tablonun header kısmında "Playlist Oluştur" ve "Playlistleri Düzenle" butonları bulunacak. Bu liste responsive tasarımı bozmadan entegre edilecek.

## Adımlar

### 1. User Dashboard Template Düzenlenmesi
- `/app/templates/user/dashboard.html` dosyasına mevcut 4 kartın altına playlist listesi bölümü eklenecek
- Tablo tasarımı mevcut dashboard stillerine uygun olacak
- Responsive tasarım kurallarına uygun olarak düzenlenecek

### 2. Playlist Veri Erişimi
- User dashboard controller'ında playlist verilerini çekme mantığı eklenecek
- Kullanıcıya ait playlist verileri, model üzerinden alınacak
- Verilerin sıralanması ve gerekli formatta hazırlanması sağlanacak

### 3. Tablo Tasarımı ve Özelleştirme
- Playlist tablosu eklenecek
- Header kısmında "Playlist Oluştur" ve "Playlistleri Düzenle" butonları
- Her playlist satırında medya sayısı, oluşturulma tarihi gibi bilgiler
- Playlist görüntüleme bağlantısı

### 4. Butonlar ve İşlevsellik
- "Playlist Oluştur" butonu `/user/playlists/create` sayfasına yönlendirilecek
- "Playlistleri Düzenle" butonu `/user/playlists` sayfasına yönlendirilecek

### 5. Testler
- Playlist verilerinin doğru şekilde yüklendiğini kontrol etme
- Responsive tasarımın farklı ekran boyutlarında çalıştığından emin olma
- Butonların doğru çalıştığını ve yönlendirmelerin doğru olduğunu kontrol etme

## Teknik Detaylar
- Mevcut MongoDB bağlantısı kullanılacak
  - MONGO_URI=mongodb://localhost:27017/bulutvizyonDB
- Playlist model sınıfı: `/app/models/playlist.py`
- Dashboard controller: `/app/routes/user.py` içindeki dashboard fonksiyonu
- Template: `/app/templates/user/dashboard.html` 