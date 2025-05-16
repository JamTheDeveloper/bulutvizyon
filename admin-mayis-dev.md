# Admin Panel Geliştirme Planı - Mayıs 2025

Bu belge, BulutVizyon admin panelinde yapılacak değişiklikleri adım adım listelemektedir.

## Yapılacaklar

### 1. Hızlı İşlemler Bölümünün Taşınması
- [x] Hızlı işlemler kartını dashboard.html dosyasından keserek en üste taşı
- [x] İlgili CSS düzenlemelerini kontrol et
- [x] Diğer kart bölümlerinin aralarındaki boşlukları düzenle

### 2. Son Kullanıcılar Listesinin Sıralanması
- [x] admin.py dosyasındaki dashboard fonksiyonunda recent_users değişkenini güncelle
- [x] Kullanıcıları oluşturma tarihine göre sırala, en son oluşturulanlar en üstte olacak

### 3. Son Medyalar Listesinin Sıralanması
- [x] admin.py dosyasındaki dashboard fonksiyonunda recent_media değişkenini güncelle
- [x] Medyaları oluşturma tarihine göre sırala, en son oluşturulanlar en üstte olacak

### 4. Son Playlist Listesinin Sıralanması
- [x] admin.py dosyasındaki dashboard fonksiyonunda recent_playlists değişkenini güncelle
- [x] Playlistleri oluşturma tarihine göre sırala, en son oluşturulanlar en üstte olacak

### 5. Canlı Log Görüntüleme Ekleme
- [x] dashboard.html'de son playlistler yanına canlı log alanı ekle
- [x] Son 5 log kaydını getirecek endpoint oluştur (admin.py içinde)
- [x] Log kayıtlarını AJAX ile periyodik olarak yenileyecek JavaScript ekle

### 6. Sistem Performans Değerlerinin Eklenmesi
- [x] Disk kullanımı, RAM durumu ve CPU kullanımını ölçecek fonksiyonlar ekle (admin.py)
- [x] Performans değerlerini gösterecek yeni bir kart bölümü oluştur
- [x] Sadece admin kullanıcılarına gösterilecek şekilde ayarla

### 7. Nöbetmatik Pro Kullanıcısı Seçeneği Ekleme
- [x] create_user.html'de yeni seçenek ekle (checkbox ile)
- [x] User modeline "is_nobetmatik_pro" alanı ekle (Boolean)
- [x] Kullanıcı oluşturma fonksiyonunu güncelle (admin.py)

### 8. Terminal No Input Alanı Ekleme
- [x] Nöbetmatik Pro seçiliyse gösterilen Terminal No input alanı ekle
- [x] JavaScript ile checkbox değerine göre input'u gizle/göster
- [x] User modeline "terminal_no" alanı ekle (String)

### 9. İşletme İsmi Alanı Ekleme
- [x] create_user.html'de İşletme İsmi input alanı ekle
- [x] User modeline "business_name" alanı ekle (String)
- [x] Kullanıcı oluşturma fonksiyonunu güncelle (admin.py)