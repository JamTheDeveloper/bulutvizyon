# Basit Android Uyumlu Medya Slider PRD

## 1. Amaç

Düşük kaynaklı Android cihazlarda (LED ekranlar vb.) çalışmak üzere tasarlanmış, API üzerinden alınan bir oynatma listesindeki videoları ve resimleri sıralı olarak, rastgele geçiş efektleriyle gösterebilen, basit, hafif ve güvenilir bir HTML/CSS/JS tabanlı medya slider'ı oluşturmak. Sistemin aynı anda bağlanan çok sayıda ekranı sorunsuz bir şekilde desteklemesi hedeflenmektedir.

## 2. Temel Özellikler

*   **Sıralı Oynatma:** API'den (`/api/screen/API_KEY`) alınan oynatma listesindeki medya öğelerini (resim/video) belirtilen sırada gösterme.
*   **Rastgele Geçiş Efektleri:** Medya öğeleri arasında basit ve performanslı rastgele geçiş efektleri (örn: fade, basit slide).
*   **Android Optimizasyonu:** Düşük RAM'li Android cihazlar için optimize edilmiş kod yapısı (minimum DOM manipülasyonu, verimli kaynak yükleme, basit CSS).
*   **Hata Yönetimi:** Medya yükleme ve oynatma sırasında oluşabilecek temel hataları yakalama ve yönetme (örn: video oynatılamazsa sonraki öğeye geçme).
*   **Çoklu Ekran Desteği:** Frontend tarafında durum bilgisi tutmadan (stateless), her ekranın bağımsız olarak çalışabilmesi. Çoklu bağlantı yönetimi backend API sorumluluğundadır.
*   **API Entegrasyonu:** Oynatma listesini ve yapılandırma ayarlarını (API anahtarı, yenileme aralığı vb.) API üzerinden alma. Belirli aralıklarla API'yi kontrol ederek listeyi güncelleme.
*   **Basitlik:** Kod karmaşıklığından kaçınarak bakımı ve anlaşılması kolay bir yapı kurma.

## 3. Teknik Yaklaşım

*   **HTML:** Minimalist yapı: Ana konteyner, medya gösterim alanı, basit bir yükleniyor göstergesi.
*   **CSS:**
    *   Temel stiller ve konumlandırma.
    *   Basit geçiş efektleri için CSS `transition` veya `animation` kullanımı (örn: `opacity`, `transform: translateX`). Karmaşık efektlerden kaçınılacak.
*   **JavaScript:**
    *   `fetch` API ile oynatma listesini çekme.
    *   Mevcut medya öğesi indeksini takip etme.
    *   Bellek tasarrufu için sadece mevcut ve bir sonraki medya öğesini DOM'a ekleme/yükleme stratejisi.
    *   Basit DOM manipülasyonları ile medya gösterimi (örn: `<img>` ve `<video>` elementleri oluşturma/güncelleme).
    *   Rastgele geçiş efekti için CSS sınıflarını değiştirme.
    *   Video elementinin `ended`, `error` gibi olaylarını dinleme.
    *   API çağrıları ve medya yükleme için temel `try...catch` ve yeniden deneme mekanizmaları.
    *   `setInterval` veya `setTimeout` ile düzenli API kontrolü ve slayt geçişlerini yönetme.
    *   Global değişkenleri minimumda tutma.

## 4. Kapsam Dışı (İlk Aşama)

*   Karmaşık veya çok sayıda geçiş efekti.
*   Gelişmiş çevrimdışı (offline) çalışma ve önbellekleme (ihtiyaç halinde sonraki aşamada değerlendirilebilir).
*   Kullanıcı etkileşimi kontrolleri (durdur, atla vb.).
*   Ekranlar arası senkronizasyon (gerekirse backend tarafında ele alınmalı).

## 5. Başarı Kriterleri

*   Slider, belirtilen Android cihazlarda takılma veya yavaşlama olmadan akıcı çalışmalı.
*   Videolar ve resimler listedeki sırayla ve belirtilen sürelerle gösterilmeli.
*   Geçiş efektleri basit ve akıcı olmalı.
*   API bağlantı hataları veya medya yükleme hataları durumunda sistem kilitlenmemeli, sonraki adıma geçebilmeli.
*   Çok sayıda ekran bağlandığında sunucu veya istemci tarafında performans sorunu yaşanmamalı. 