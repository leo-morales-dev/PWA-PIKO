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

// Inyecta el precache del build (lo hace Workbox)
precacheAndRoute(self.__WB_MANIFEST || []);

// SPA fallback para rutas navegables
const navHandler = createHandlerBoundToURL('/index.html');
registerRoute(new NavigationRoute(navHandler));

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
  const action = event.action;
  const data = event.notification?.data || {};
  const id = data.id;

  event.notification.close();

  if (!id) return;

  // Confirmación: marcamos el pedido como "confirmado"
  if (action === 'confirm') {
    event.waitUntil(fetch(`http://127.0.0.1:9000/api/pedidos/${id}/estado`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ estado: 'confirmado' })
    }));
    return;
  }

  // Abrir la página de estado
  if (action === 'open' || action === '') {
    event.waitUntil(clients.openWindow(`/status.html?pedido=${id}`));
  }
});

self.addEventListener('notificationclick', (event) => {
  const action = event.action;                // 'confirm' | 'open' | ''
  const data = event.notification?.data || {};
  const id = data.id;
  event.notification.close();
  if (!id) return;

  if (action === 'confirm') {
    // ⚠️ IMPORTANTE: origen del front
    event.waitUntil(fetch(`http://127.0.0.1:9000/api/pedidos/${id}/estado`, {
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
