const CACHE_NAME = 'parse-calc-v3';

// We intercept all requests. For standard app assets, we cache them.
// For Pyodide CDN assets, we cache them dynamically as they are requested.
self.addEventListener('install', event => {
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== CACHE_NAME) {
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
});

self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);

  // We want to cache GET requests only
  if (event.request.method !== 'GET') return;

  // Cache First, Network Fallback strategy
  event.respondWith(
    caches.match(event.request).then(cachedResponse => {
      if (cachedResponse) {
        return cachedResponse;
      }
      return fetch(event.request).then(networkResponse => {
        // Cache successful responses
        if (networkResponse && networkResponse.status === 200) {
          const responseToCache = networkResponse.clone();
          caches.open(CACHE_NAME).then(cache => {
            cache.put(event.request, responseToCache);
          });
        }
        return networkResponse;
      }).catch(err => {
        console.warn('[Service Worker] Fetch failed, and not in cache:', event.request.url, err);
        // Fallback or ignore
      });
    })
  );
});
