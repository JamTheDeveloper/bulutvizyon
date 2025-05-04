# Paket Yönetimi Sistemi Geliştirme Planı

## Genel Bakış
Bu plan, BulutVizyon platformunda paket yönetiminin statik koddan dinamik veritabanı tabanlı bir sisteme dönüştürülmesi için adımları içerir.

## 1. Mevcut Durum Analizi
- Şu anda paketler kodda statik olarak tanımlı (standard, pro, enterprise)
- Kullanıcı ekran limitleri pakete bağlı (standard: 3 ekran, pro: 10 ekran, enterprise: sınırsız)
- Paket bilgileri çeşitli sayfalarda kontrol ediliyor

## 2. Veritabanı Tasarımı
- `Package` modeli oluşturulacak
  - id: Benzersiz tanımlayıcı
  - name: Paket adı (standard, pro, enterprise)
  - display_name: Görünür adı
  - description: Açıklama
  - screen_limit: Maksimum ekran sayısı (-1 sınırsız için)
  - price: Fiyat bilgisi
  - features: Paket özellikleri (JSON)
  - is_active: Paket aktif mi?
  - created_at: Oluşturulma tarihi
  - updated_at: Güncelleme tarihi

## 3. Model İşlemlerini Oluşturma
- Package model dosyasını oluştur
- Paket yönetimi için CRUD işlemleri

## 4. Admin Paneli Geliştirme
- Paket listeleme sayfası
- Paket ekleme formu
- Paket düzenleme formu
- Paket silme/devre dışı bırakma

## 5. Veritabanı Hazırlama
- İlk kurulum için varsayılan paketleri oluşturacak script
- Mevcut kullanıcıları yeni paket sistemiyle ilişkilendirme

## 6. Mevcut Kodun Uyarlanması
- `user` modelinde paket referansını güncelleme
- Ekran limitlerini statik değerler yerine veritabanından alma
- Template dosyalarını güncelleme
- Dashboard ve profil sayfalarını güncelleme

## 7. Hata Kontrolü ve Geriye Dönük Uyumluluk
- Olmayan paketlere atıfta bulunulduğunda varsayılan değerler döndürme
- Paket silindiğinde kullanıcı kontrolü

## 8. Test ve Doğrulama
- Yeni paketi ekleme/düzenleme/silme testi
- Kullanıcı paket atama testi
- Ekran limitlerinin doğrulanması
- Mevcut kullanıcıların sorunsuz geçişinin kontrolü

## 9. Dağıtım
- Veritabanı migrasyonlarını çalıştırma
- Admin için dokümantasyon hazırlama

## Uygulama Sırası
1. Veritabanı modeli oluştur
2. Admin paneli geliştir
3. Varsayılan paketleri ekle
4. Mevcut kodu adapte et
5. Test et ve hataları düzelt 