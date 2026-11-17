// Offline support for the installed app. The page itself: network first (new lessons arrive as soon as you are
// online), the copy in the cache when offline. Recordings, icons and fonts: cache first, kept once played or loaded.
// 粵字's side file: cache first, under its content hash.
const VERSION = '__BUILD__';
// own names: the Taigi app (tsehtu) on the same site uses tshehtu-*, and each app deletes its own old caches by prefix
const SHELL = 'pyue-shell-' + VERSION, MEDIA = 'pyue-media-1';
const PRECACHE = ['./', 'manifest.webmanifest', 'icon-192.png', 'icon-512.png', 'apple-touch-icon.png'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(SHELL).then(c => c.addAll(PRECACHE)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => (k.startsWith('pyue-shell-') && k !== SHELL) || (k.startsWith('pyue-media-') && k !== MEDIA)).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});
self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (req.mode === 'navigate') {
    e.respondWith(fetch(req).then(r => { const copy = r.clone(); caches.open(SHELL).then(c => c.put('./', copy)); return r; })
      .catch(() => caches.match('./')));
    return;
  }
  // 粵字's side file (yuezi-more.json?v=content hash), fetched by the page the first time 粵字 is opened: kept with
  // the page's own version, so it works offline from then on; a new build names a new file
  if (url.origin === location.origin && /\/yuezi-more\.json$/.test(url.pathname)) {
    e.respondWith(caches.open(SHELL).then(c => c.match(req).then(hit => hit || fetch(req).then(r => { if (r.ok) c.put(req, r.clone()); return r; }))));
    return;
  }
  if (url.hostname === 'api.github.com') return;   // private exam files: the page caches those itself
  const media = /\/audio\/.*\.mp3$/.test(url.pathname) || /fonts\.(googleapis|gstatic)\.com$/.test(url.hostname) || /\.png$/.test(url.pathname);
  if (media) {
    e.respondWith(caches.open(MEDIA).then(c => c.match(req).then(hit => hit || fetch(req).then(r => { if (r.ok || r.type === 'opaque') c.put(req, r.clone()); return r; }))));
  }
});
