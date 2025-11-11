const CACHE_NAME = 'fantamatrimonio-v11-' + new Date().getTime();
const STATIC_CACHE = [
  '/static/default.png',
  '/static/bkground.jpg',
];

// ============================================================================
// INSTALL: Cacha le risorse statiche essenziali
// ============================================================================
self.addEventListener('install', (event) => {
  console.log('✅ Service Worker: Installazione in corso...');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('📦 Cache aperta:', CACHE_NAME);
        return cache.addAll(STATIC_CACHE);
      })
      .then(() => {
        console.log('✅ Risorse statiche cachate');
        return self.skipWaiting();
      })
      .catch(err => console.error('❌ Errore durante install:', err))
  );
});

// ============================================================================
// ACTIVATE: Pulisci cache vecchie e prendi controllo delle pagine
// ============================================================================
self.addEventListener('activate', (event) => {
  console.log('✅ Service Worker: Attivazione in corso...');
  event.waitUntil(
    caches.keys()
      .then(cacheNames => {
        return Promise.all(
          cacheNames.map(cache => {
            if (cache !== CACHE_NAME) {
              console.log('🗑️ Eliminazione cache vecchia:', cache);
              return caches.delete(cache);
            }
          })
        );
      })
      .then(() => {
        console.log('✅ Service Worker attivato e cache pulita');
        return self.clients.claim();
      })
      .catch(err => console.error('❌ Errore durante activate:', err))
  );
});

// ============================================================================
// FETCH: Strategia "Network First" per HTML, "Cache First" per static
// ============================================================================
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);
  
  // NON cachare mai pagine HTML, API calls o richieste non-GET
  if (url.pathname === '/' || 
      url.pathname.startsWith('/api/') ||
      url.pathname.startsWith('/league/') ||
      !url.pathname.startsWith('/static/') ||
      event.request.method !== 'GET') {
    // Network First - sempre dal server per contenuti dinamici
    event.respondWith(fetch(event.request));
    return;
  }

  // Cache First per risorse statiche (/static/*)
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        if (response) {
          // Trovato in cache
          return response;
        }
        
        // Non in cache, scarica da rete
        return fetch(event.request).then(networkResponse => {
          // Non cachare risposte non valide
          if (!networkResponse || networkResponse.status !== 200 || networkResponse.type !== 'basic') {
            return networkResponse;
          }
          
          // Clona la risposta e mettila in cache
          const responseToCache = networkResponse.clone();
          caches.open(CACHE_NAME)
            .then(cache => cache.put(event.request, responseToCache))
            .catch(err => console.error('❌ Errore caching:', err));
          
          return networkResponse;
        });
      })
      .catch(err => {
        console.error('❌ Errore fetch:', err);
        // Ritorna una risposta di fallback se disponibile
        return caches.match('/static/default.png');
      })
  );
});

// ============================================================================
// PUSH: Gestione notifiche push in arrivo
// ============================================================================
self.addEventListener('push', (event) => {
  console.log('📬 Push ricevuto:', event);
  
  let data = {
    title: 'FantaMatrimonio',
    body: 'Hai una nuova notifica',
    icon: '/static/images/icon-192.png',
    badge: '/static/images/badge-72.png',
    url: '/',
    tag: 'notification'
  };
  
  // Parse dei dati se presenti
  if (event.data) {
    try {
      data = event.data.json();
      console.log('📬 Dati push:', data);
    } catch (e) {
      console.error('❌ Errore parsing push data:', e);
    }
  }
  
  const options = {
    body: data.body,
    icon: data.icon || '/static/images/icon-192.png',
    badge: data.badge || '/static/images/badge-72.png',
    tag: data.tag || 'notification',
    data: {
      url: data.url || '/'
    },
    vibrate: [200, 100, 200],
    requireInteraction: false,
    actions: data.actions || []
  };
  
  event.waitUntil(
    self.registration.showNotification(data.title, options)
      .then(() => console.log('✅ Notifica mostrata'))
      .catch(err => console.error('❌ Errore mostrando notifica:', err))
  );
});

// ============================================================================
// NOTIFICATION CLICK: Gestione click sulle notifiche
// ============================================================================
self.addEventListener('notificationclick', (event) => {
  console.log('🖱️ Click su notifica:', event.notification.tag);
  
  event.notification.close();
  
  const urlToOpen = event.notification.data?.url || '/';
  
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true })
      .then(clientList => {
        console.log('🔍 Finestre aperte:', clientList.length);
        
        // Cerca una finestra già aperta
        for (let client of clientList) {
          if (client.url.includes(urlToOpen) && 'focus' in client) {
            console.log('✅ Finestra trovata, focus');
            return client.focus();
          }
        }
        
        // Altrimenti apri una nuova finestra
        if (clients.openWindow) {
          console.log('🆕 Apro nuova finestra:', urlToOpen);
          return clients.openWindow(urlToOpen);
        }
      })
      .catch(err => console.error('❌ Errore click notifica:', err))
  );
});

// ============================================================================
// MESSAGE: Gestione messaggi dal client (evita errori promise)
// ============================================================================
self.addEventListener('message', (event) => {
  console.log('💬 Messaggio ricevuto nel SW:', event.data);
  
  if (event.data && event.data.type === 'SKIP_WAITING') {
    console.log('⏩ Skip waiting richiesto');
    self.skipWaiting();
  }
  
  // Rispondi sempre per evitare l'errore "message channel closed"
  if (event.ports && event.ports[0]) {
    event.ports[0].postMessage({ received: true, timestamp: Date.now() });
  }
});

// ============================================================================
// PUSH SUBSCRIPTION CHANGE: Gestione cambio subscription
// ============================================================================
self.addEventListener('pushsubscriptionchange', (event) => {
  console.log('🔄 Push subscription cambiata');
  event.waitUntil(
    self.registration.pushManager.subscribe(event.oldSubscription.options)
      .then(subscription => {
        console.log('✅ Nuova subscription:', subscription);
        // Qui potresti inviare la nuova subscription al server
        return fetch('/api/push-subscription', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(subscription)
        });
      })
      .catch(err => console.error('❌ Errore re-subscription:', err))
  );
});

console.log('🚀 Service Worker caricato');
self.addEventListener('push', function(event) {
  if (!event.data) return;

  const data = event.data.json();
  
  const options = {
    body: data.body,
    icon: data.icon || '/static/images/icon-192.png',  // Icona personalizzata
    badge: data.badge || '/static/images/badge-72.png', // Badge piccolo
    vibrate: [200, 100, 200],
    tag: data.tag || 'default',
    data: {
      url: data.url || '/'
    },
    requireInteraction: false,
    silent: false
  };

  event.waitUntil(
    self.registration.showNotification(data.title, options)
  );
});