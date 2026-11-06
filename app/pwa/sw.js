// Offline support for the installed app. The page itself: network first (new lessons arrive as soon as you are
// online), the copy in the cache when offline. Recordings, icons and fonts: cache first, kept once played or loaded.
const VERSION = '__BUILD__';
const SHELL = 'tshehtu-shell-' + VERSION, MEDIA = 'tshehtu-media-2';
const PRECACHE = ['./', 'manifest.webmanifest', 'icon-192.png', 'icon-512.png', 'apple-touch-icon.png'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(SHELL).then(c => c.addAll(PRECACHE)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => (k.startsWith('tshehtu-shell-') && k !== SHELL) || (k.startsWith('tshehtu-media-') && k !== MEDIA)).map(k => caches.delete(k))))
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
  if (url.hostname === 'api.github.com') return;   // private exam files: the page caches those itself
  const media = /\/audio\/.*\.mp3$/.test(url.pathname) || /fonts\.(googleapis|gstatic)\.com$/.test(url.hostname) || /\.png$/.test(url.pathname);
  if (media) {
    e.respondWith(caches.open(MEDIA).then(c => c.match(req).then(hit => hit || fetch(req).then(r => { if (r.ok || r.type === 'opaque') c.put(req, r.clone()); return r; }))));
  }
});
