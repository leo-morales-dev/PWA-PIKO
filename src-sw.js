// src-sw.js
import {clientsClaim, setCacheNameDetails} from 'workbox-core';
import {precacheAndRoute, createHandlerBoundToURL} from 'workbox-precaching';
import {registerRoute, NavigationRoute} from 'workbox-routing';
import {NetworkFirst, StaleWhileRevalidate} from 'workbox-strategies';
import {ExpirationPlugin} from 'workbox-expiration';
import {CacheableResponsePlugin} from 'workbox-cacheable-response';
import {BackgroundSyncPlugin} from 'workbox-background-sync';

clientsClaim();
setCacheNameDetails({ prefix: 'cafeteria' });

const LOCAL_BACKEND = 'http://127.0.0.1:9000';
const normalizeOrigin = (value) => String(value || '').trim().replace(/\/+$/, '');
function resolveBackendOrigin() {
  const forced = (typeof self.__BACKEND_ORIGIN__ === 'string' ? self.__BACKEND_ORIGIN__.trim() : '');
  if (forced) return normalizeOrigin(forced);
  const { hostname, origin } = self.location;
  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    return LOCAL_BACKEND;
  }
  return normalizeOrigin(origin);
}
let BACKEND_ORIGIN = resolveBackendOrigin();
self.__BACKEND_ORIGIN__ = BACKEND_ORIGIN;
const apiUrl = (path) => {
  const clean = path.startsWith('/') ? path : `/${path}`;
  return `${BACKEND_ORIGIN}${clean}`;
};

self.addEventListener('message', (event) => {
  const data = event?.data;
  if (!data || typeof data !== 'object') return;
  if (data.type === 'SET_BACKEND_ORIGIN') {
    const value = (data.value || '').trim();
    if (value) {
      BACKEND_ORIGIN = normalizeOrigin(value);
      self.__BACKEND_ORIGIN__ = BACKEND_ORIGIN;
    }
  }
});

// Inyecta el precache del build (lo hace Workbox)
precacheAndRoute(self.__WB_MANIFEST || []);

// SPA fallback para rutas navegables
const defaultNavHandler = createHandlerBoundToURL('/index.html');
const navigationHandlers = new Map([
  ['/', defaultNavHandler],
  ['/index.html', defaultNavHandler],
  ['/menu', createHandlerBoundToURL('/menu.html')],
  ['/menu.html', createHandlerBoundToURL('/menu.html')],
  ['/status', createHandlerBoundToURL('/status.html')],
  ['/status.html', createHandlerBoundToURL('/status.html')],
  ['/barista', createHandlerBoundToURL('/barista.html')],
  ['/barista.html', createHandlerBoundToURL('/barista.html')]
]);

const normalizePathname = (value) => {
  const trimmed = value.replace(/\/+$/, '');
  return trimmed === '' ? '/' : trimmed;
};

registerRoute(new NavigationRoute((options) => {
  const { url } = options;
  const handler = navigationHandlers.get(normalizePathname(url.pathname));
  return (handler || defaultNavHandler)(options);
}));

// ====== Estrategias en runtime ======

// GET de API (menú, pedidos): NetworkFirst con timeout y fallback a cache
registerRoute(
  ({url, request}) => url.pathname.startsWith('/api/') && request.method === 'GET',
  new NetworkFirst({
    cacheName: 'api-dinamica',
    networkTimeoutSeconds: 5,
    plugins: [
      new CacheableResponsePlugin({ statuses: [0, 200] }),
      new ExpirationPlugin({ maxEntries: 100, maxAgeSeconds: 60 * 60 })
    ]
  })
);

// Imágenes: rápido y se actualiza en background
registerRoute(
  ({request}) => request.destination === 'image',
  new StaleWhileRevalidate({
    cacheName: 'imagenes',
    plugins: [new ExpirationPlugin({ maxEntries: 200 })]
  })
);

// ====== Cola offline para pedidos (POST) ======
// Nota: Si tu API corre en otro host/puerto, no pasa nada. El SW verá el request absoluto.
const pedidosQueue = new BackgroundSyncPlugin('cola-pedidos', {
  maxRetentionTime: 24 * 60 // reintentos hasta 24h
});

// Intercepta POST /api/pedidos: intenta red; si falla, encola y responde 202 {queued:true}
self.addEventListener('fetch', (event) => {
  const req = event.request;
  const url = new URL(req.url);

  if (req.method === 'POST' && url.pathname.startsWith('/api/pedidos')) {
    event.respondWith((async () => {
      try {
        // intenta enviar normalmente
        return await fetch(req.clone());
      } catch (err) {
        // sin red: guarda para enviar después
        const clone = await req.clone().blob();
        const reqForQueue = new Request(req, { body: clone });
        await pedidosQueue.pushRequest({ request: reqForQueue });
        return new Response(JSON.stringify({ queued: true }), {
          status: 202,
          headers: { 'Content-Type': 'application/json' }
        });
      }
    })());
  }
});

// En tu service worker (src-sw.js o el que estés usando)
self.addEventListener('notificationclick', (event) => {
  const action = event.action;                // 'confirm' | 'open' | ''
  const data = event.notification?.data || {};
  const id = data.id;
  event.notification.close();
  if (!id) return;

  if (action === 'confirm') {
    // ⚠️ IMPORTANTE: origen del front
    event.waitUntil(fetch(apiUrl(`/api/pedidos/${id}/estado`), {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ estado: 'confirmado' })
    }));
    return;
  }

  // Click en la noti (o botón "Ver"): abrir status.html
  if (action === 'open' || action === '') {
    event.waitUntil(clients.openWindow(`/status.html?pedido=${id}`));
  }
});
