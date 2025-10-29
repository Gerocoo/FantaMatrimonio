// Nome della cache (cambia versione per forzare aggiornamenti)
const CACHE_NAME = 'fantamatrimonio-cache-v1';

// File da memorizzare nella cache
const urlsToCache = [
  '/',
  '/static/manifest.json',
  '/static/fanta.css',
  '/static/logo.png'
];

// Installazione del Service Worker
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(urlsToCache))
  );
  self.skipWaiting(); // attiva subito il nuovo SW
});

// Gestione delle richieste
self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request).then(response => {
      // Usa la cache se disponibile, altrimenti prova a recuperare dalla rete
      return (
        response ||
        fetch(event.request).catch(() => {
          // Se offline e la richiesta è di navigazione, mostra la home
          if (event.request.mode === 'navigate') {
            return caches.match('/');
          }
        })
      );
    })
  );
});

// Attivazione e pulizia vecchie cache
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheNames =>
      Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== CACHE_NAME) {
            return caches.delete(cacheName);
          }
        })
      )
    )
  );
  self.clients.claim(); // attiva subito sui client aperti
});
