/* eslint-env serviceworker */
/*
 * FinTrack Pro service worker.
 *
 * Caching policy, and the reasoning behind it:
 *
 *   Static shell (JS/CSS/icons)  -> cache-first.  Hashed filenames from Vite mean
 *                                   a cached file can never be stale: a new build
 *                                   produces a new URL, so cache-first is safe
 *                                   and makes repeat loads instant/offline.
 *
 *   API responses (/api/*)       -> NEVER cached.  This is the important one. A
 *                                   finance app must not serve a stale balance,
 *                                   a stale holding price, or another session's
 *                                   data from disk. Showing yesterday's net worth
 *                                   as though it were current is worse than
 *                                   showing an error, so API traffic always goes
 *                                   to the network and fails honestly when offline.
 *
 *   Navigations                  -> network-first, falling back to the cached
 *                                   shell so a refresh while offline still opens
 *                                   the app (which then reports it can't reach
 *                                   the server) instead of the browser's error page.
 */
const CACHE = 'fintrack-shell-v1';
const SHELL = ['/', '/index.html', '/manifest.webmanifest'];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE)
      // Individual addAll failures would reject the whole install, so tolerate
      // a missing optional file rather than leaving the SW permanently uninstalled.
      .then((c) => Promise.allSettled(SHELL.map((u) => c.add(u))))
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  // Never touch the API or the WebSocket upgrade — see policy note above.
  if (url.pathname.startsWith('/api')) return;

  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request).catch(() => caches.match('/index.html').then((r) => r || Response.error())),
    );
    return;
  }

  event.respondWith(
    caches.match(request).then((hit) => {
      if (hit) return hit;
      return fetch(request).then((res) => {
        // Only cache successful, same-origin, basic responses.
        if (res.ok && res.type === 'basic') {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(request, copy));
        }
        return res;
      });
    }),
  );
});
