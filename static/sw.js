const CACHE_NAME = 'fantamatrimonio-v11-' + new Date().getTime();
const STATIC_CACHE = [
  '/static/default.png',
  '/static/bkground.jpg',
];

// Installazione: cacha solo risorse statiche
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(STATIC_CACHE))
      .then(() => self.skipWaiting())
  );
});

// Attivazione: pulisci cache vecchie
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cache => {
          if (cache !== CACHE_NAME) {
            return caches.delete(cache);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// Fetch: strategia "Network First" per HTML, "Cache First" per static
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);
  
  // NON cachare mai pagine HTML o API calls
  if (url.pathname === '/' || 
      !url.pathname.startsWith('/static/') ||
      event.request.method !== 'GET') {
    // Network First - sempre dal server per pagine dinamiche
    event.respondWith(fetch(event.request));
    return;
  }
  self.addEventListener('activate', event => {
  event.waitUntil(clients.claim());
});

  // Cache First per risorse statiche
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        if (response) {
          return response;
        }
        return fetch(event.request).then(response => {
          if (!response || response.status !== 200) {
            return response;
          }
          const responseToCache = response.clone();
          caches.open(CACHE_NAME)
            .then(cache => cache.put(event.request, responseToCache));
          return response;
        });
      })
  );
});