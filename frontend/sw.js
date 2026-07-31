const CACHE_NAME = 'facecontrol-v2';
const STATIC_ASSETS = [
    '/',
    '/index.html',
    '/css/style.css',
    '/js/api.js',
    '/js/camera.js',
    '/js/app.js',
    '/manifest.json',
];

// Install - cache static assets
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.addAll(STATIC_ASSETS);
        })
    );
    self.skipWaiting();
});

// Activate - clean old caches
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames
                    .filter((name) => name !== CACHE_NAME)
                    .map((name) => caches.delete(name))
            );
        })
    );
    self.clients.claim();
});

// Fetch - network first, fallback to cache (static assets only)
self.addEventListener('fetch', (event) => {
    const url = new URL(event.request.url);

    // Skip ALL backend API calls
    if (url.hostname !== location.hostname) {
        return;
    }

    // Skip non-GET requests
    if (event.request.method !== 'GET') {
        return;
    }

    event.respondWith(
        fetch(event.request)
            .then((response) => {
                const responseClone = response.clone();
                caches.open(CACHE_NAME).then((cache) => {
                    cache.put(event.request, responseClone);
                });
                return response;
            })
            .catch(() => {
                return caches.match(event.request).then((response) => {
                    return response || caches.match('/');
                });
            })
    );
});
