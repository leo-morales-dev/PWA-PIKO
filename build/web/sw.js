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
precacheAndRoute([{"revision":"992ba04d5892193176350dad1f95a2ec","url":"assets/AssetManifest.bin.json"},{"revision":"5515896244b15ec7f3fc5ce45479796d","url":"assets/AssetManifest.json"},{"revision":"dc3d03800ccca4601324923c0b1d6d57","url":"assets/FontManifest.json"},{"revision":"7748a45cd593f33280669b29c2c8919a","url":"assets/packages/wakelock_plus/assets/no_sleep.js"},{"revision":"89803d980ef5e286de2d9aac1f7ced25","url":"barista.html"},{"revision":"86e461cf471c1640fd2b461ece4589df","url":"canvaskit/canvaskit.js"},{"revision":"34beda9f39eb7d992d46125ca868dc61","url":"canvaskit/chromium/canvaskit.js"},{"revision":"d1326ceef381ad382ab492ba5d96f04d","url":"canvaskit/skwasm_st.js"},{"revision":"f2ad9363618c5f62e813740099a80e63","url":"canvaskit/skwasm.js"},{"revision":"dd018003369bee3e244a8cc59f119e5f","url":"favicon.png"},{"revision":"5f7b1ae461290d7e3d67a168c6903be3","url":"flutter_bootstrap.js"},{"revision":"7df784bb132f330ed76a3991e735eaa4","url":"flutter_service_worker.js"},{"revision":"76f08d47ff9f5715220992f993002504","url":"flutter.js"},{"revision":"817caa1985cf73eaaa8dd02dda218970","url":"icons/Icon-192.png"},{"revision":"1b5e2bffe69da59cfd351c35c744bcdc","url":"icons/Icon-512.png"},{"revision":"817caa1985cf73eaaa8dd02dda218970","url":"icons/Icon-maskable-192.png"},{"revision":"1b5e2bffe69da59cfd351c35c744bcdc","url":"icons/Icon-maskable-512.png"},{"revision":"79f0d07d6c0a15b2b8c995a1e1df45f5","url":"index.html"},{"revision":"44902d0b5d7d1775c1bb8467fab83906","url":"manifest.json"},{"revision":"1528daf8a46cafabe731f4e232f17f76","url":"menu.html"},{"revision":"c807c238e7b517beb2fe42617dc6e999","url":"python-worker.js"},{"revision":"40e27f3a5ec9f91a07ad358b82b88857","url":"python.js"},{"revision":"802a821237035fabb9f246a4adfb30ff","url":"splash/img/dark-1x.png"},{"revision":"1b5e2bffe69da59cfd351c35c744bcdc","url":"splash/img/dark-2x.png"},{"revision":"724603f1bcb62aec13a09970332f7533","url":"splash/img/dark-3x.png"},{"revision":"dc457e3fab5b7baf6c32171f81af1260","url":"splash/img/dark-4x.png"},{"revision":"802a821237035fabb9f246a4adfb30ff","url":"splash/img/light-1x.png"},{"revision":"1b5e2bffe69da59cfd351c35c744bcdc","url":"splash/img/light-2x.png"},{"revision":"724603f1bcb62aec13a09970332f7533","url":"splash/img/light-3x.png"},{"revision":"dc457e3fab5b7baf6c32171f81af1260","url":"splash/img/light-4x.png"},{"revision":"6f2505c9238d761c25c1bcda3c4254a1","url":"status.html"},{"revision":"ae4f6dc6a1cfe4a2576c55519571f5a3","url":"test-order.html"},{"revision":"c1fca7123e552985ccf1b489d2f61287","url":"version.json"}] || []);

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
