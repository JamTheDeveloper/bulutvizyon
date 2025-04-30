const CACHE_NAME = 'bulutvizyon-cache-v1';
const MEDIA_CACHE_NAME = 'bulutvizyon-media-cache-v1';

// Önbelleğe alınacak temel URL'ler (isteğe bağlı)
// const urlsToCache = [
//   '/',
//   '/static/styles.css', 
//   '/static/script.js'
// ];

// Yükleme olayı: Temel dosyaları önbelleğe al (opsiyonel)
self.addEventListener('install', event => {
  console.log('Service Worker: Installing...');
  // event.waitUntil(
  //   caches.open(CACHE_NAME)
  //     .then(cache => {
  //       console.log('Service Worker: Caching app shell');
  //       return cache.addAll(urlsToCache);
  //     })
  // );
   // Yeni SW'nin beklemeden aktif olmasını sağla
   event.waitUntil(self.skipWaiting());
});

// Aktivasyon olayı: Eski önbellekleri temizle
self.addEventListener('activate', event => {
  console.log('Service Worker: Activating...');
  const cacheWhitelist = [CACHE_NAME, MEDIA_CACHE_NAME];
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheWhitelist.indexOf(cacheName) === -1) {
            console.log('Service Worker: Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
    // Aktif olduktan sonra sayfaları kontrol etmesini sağla
    .then(() => self.clients.claim())
  );
});

// Fetch olayı: Ağ isteklerini yakala
self.addEventListener('fetch', event => {
  const requestUrl = new URL(event.request.url);

  // Sadece belirli domainlerden veya path'lerden gelen medya isteklerini önbelleğe al
  // Örnek: Kendi sunucunuzdan gelen /media/ veya /static/uploads/ gibi path'ler
  // VEYA belirli dosya uzantıları (.jpg, .png, .mp4 vb.)
  const isMediaRequest = requestUrl.pathname.startsWith('/media/') || 
                         requestUrl.pathname.endsWith('.jpg') ||
                         requestUrl.pathname.endsWith('.jpeg') ||
                         requestUrl.pathname.endsWith('.png') ||
                         requestUrl.pathname.endsWith('.gif') ||
                         requestUrl.pathname.endsWith('.mp4') ||
                         requestUrl.pathname.endsWith('.webm');

  // API isteklerini veya HTML sayfalarını önbelleğe alma (genellikle)
  const isApiRequest = requestUrl.pathname.startsWith('/api/');
  const isHtmlRequest = event.request.headers.get('accept').includes('text/html');

  if (isMediaRequest && !isApiRequest && event.request.method === 'GET') {
    console.log('Service Worker: Handling fetch for media:', event.request.url);
    event.respondWith(
      // 1. Önbelleği kontrol et
      caches.open(MEDIA_CACHE_NAME).then(cache => {
        return cache.match(event.request).then(cachedResponse => {
          if (cachedResponse) {
            console.log('Service Worker: Serving from MEDIA cache:', event.request.url);
            return cachedResponse;
          }

          // 2. Önbellekte yoksa, ağdan getir
          console.log('Service Worker: Fetching from network:', event.request.url);
          return fetch(event.request).then(networkResponse => {
            // Başarılı yanıtları (200 OK) önbelleğe al
            if (networkResponse && networkResponse.ok) {
              // URL şemasını kontrol et
              const requestUrlCheck = new URL(event.request.url);
              if (requestUrlCheck.protocol === 'http:' || requestUrlCheck.protocol === 'https:') {
                    // Sadece http veya https şemalı istekleri önbelleğe al
                    console.log('Service Worker: Caching new media response:', event.request.url);
                    const responseToCache = networkResponse.clone();
                     // cache.put'u try-catch içine almak da iyi bir pratik olabilir
                    try {
                        cache.put(event.request, responseToCache);
                    } catch (e) {
                         console.error('Service Worker: Error putting item in cache:', e, event.request.url);
                    }
                } else {
                    console.log('Service Worker: Skipping cache for non-http(s) request:', event.request.url);
                }
            }
            return networkResponse;
          }).catch(error => {
            // Ağ hatası durumunda (çevrimdışı)
            console.warn('Service Worker: Network fetch failed for media. Trying cache again just in case...', event.request.url, error);
            // Ağ hatası olsa bile, belki önbellekte vardır diye SON BİR KEZ kontrol et.
            return cache.match(event.request).then(cachedResponseAgain => {
                if (cachedResponseAgain) {
                    console.log('Service Worker: Serving from MEDIA cache after network failure:', event.request.url);
                    return cachedResponseAgain;
                }
                // Önbellekte hala yoksa, boş bir OK yanıtı dön (oynatıcı belki bunu daha iyi yönetir)
                console.error('Service Worker: Media not found in cache and network failed. Returning empty response.', event.request.url);
                return new Response('', { status: 200, statusText: 'OK (Offline Fallback)' }); 
            });
             // Eski Hatalı Yanıt: return new Response(null, { status: 503, statusText: 'Service Unavailable' });
          });
        });
      })
    );
  } else if (!isApiRequest && !isHtmlRequest && event.request.method === 'GET'){
      // Diğer GET istekleri (CSS, JS vb. eğer varsa) için Cache First stratejisi (opsiyonel)
        event.respondWith(
            caches.match(event.request)
                .then(response => {
                    return response || fetch(event.request);
                })
        );
  } else {
      // API istekleri, HTML veya diğer metodlar (POST vb.) doğrudan ağa gitsin
      // console.log('Service Worker: Ignoring fetch:', event.request.url);
      // event.respondWith(fetch(event.request)); // Bu satır gerekli değil, varsayılan davranış
  }
}); 

// Sayfadan gelen mesajları dinle
self.addEventListener('message', event => {
    console.log('Service Worker: Message received:', event.data);
    if (event.data && event.data.type === 'CACHE_URLS') {
        const urlsToCache = event.data.payload;
        console.log('Service Worker: Received URLs to pre-cache:', urlsToCache);
        
        event.waitUntil(
            caches.open(MEDIA_CACHE_NAME).then(cache => {
                const promises = urlsToCache.map(url => {
                    // Önce önbellekte var mı diye kontrol et
                    return cache.match(url).then(response => {
                        if (!response) {
                             // Önbellekte yoksa, ağdan getirip ekle
                            console.log('Service Worker: Pre-caching URL:', url);
                            return fetch(url).then(networkResponse => {
                                if (networkResponse && networkResponse.ok) {
                                    // Yanıtı klonla
                                    return cache.put(url, networkResponse.clone());
                                } else {
                                     console.warn(`Service Worker: Pre-cache fetch failed for ${url}: Status ${networkResponse.status}`);
                                     return Promise.resolve(); // Hatayı yoksay, diğerlerine devam et
                                }
                            }).catch(error => {
                                console.error(`Service Worker: Pre-cache fetch error for ${url}:`, error);
                                return Promise.resolve(); // Hatayı yoksay
                            });
                        } else {
                            console.log('Service Worker: URL already cached, skipping pre-cache:', url);
                            return Promise.resolve(); // Zaten varsa bir şey yapma
                        }
                    });
                });
                // Tüm önbellekleme işlemlerinin bitmesini bekle (hatalara rağmen)
                return Promise.all(promises).then(() => {
                    console.log('Service Worker: Pre-caching process completed.');
                });
            })
        );
    }
}); 