/**
 * Service Worker for offline support and caching
 */

const CACHE_NAME = 'hhs-scraper-v1';
const STATIC_CACHE = 'hhs-scraper-static-v1';
const API_CACHE = 'hhs-scraper-api-v1';

// Assets to cache on install
const STATIC_ASSETS = [
    '/',
    '/static/css/dashboard.css',
    '/static/js/dashboard.js',
    '/templates/dashboard.html'
];

// Install event - cache static assets
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(STATIC_CACHE).then((cache) => {
            return cache.addAll(STATIC_ASSETS);
        })
    );
    self.skipWaiting();
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames
                    .filter((name) => name !== STATIC_CACHE && name !== API_CACHE)
                    .map((name) => caches.delete(name))
            );
        })
    );
    return self.clients.claim();
});

// Fetch event - serve from cache, fallback to network
self.addEventListener('fetch', (event) => {
    const { request } = event;
    const url = new URL(request.url);

    // API requests - cache with network-first strategy
    if (url.pathname.startsWith('/api/')) {
        event.respondWith(networkFirstStrategy(request));
        return;
    }

    // Static assets - cache-first strategy
    if (url.pathname.startsWith('/static/') || url.pathname === '/') {
        event.respondWith(cacheFirstStrategy(request));
        return;
    }

    // Default - network only
    event.respondWith(fetch(request));
});

// Network-first strategy for API requests
async function networkFirstStrategy(request) {
    const cache = await caches.open(API_CACHE);
    
    try {
        const response = await fetch(request);
        if (response.ok) {
            cache.put(request, response.clone());
        }
        return response;
    } catch (error) {
        const cached = await cache.match(request);
        if (cached) {
            return cached;
        }
        throw error;
    }
}

// Cache-first strategy for static assets
async function cacheFirstStrategy(request) {
    const cache = await caches.open(STATIC_CACHE);
    const cached = await cache.match(request);
    
    if (cached) {
        return cached;
    }
    
    try {
        const response = await fetch(request);
        if (response.ok) {
            cache.put(request, response.clone());
        }
        return response;
    } catch (error) {
        // Return offline page if available
        const offline = await cache.match('/');
        return offline || new Response('Offline', { status: 503 });
    }
}

// Message handler for cache management
self.addEventListener('message', (event) => {
    if (event.data && event.data.type === 'CLEAR_CACHE') {
        caches.delete(API_CACHE).then(() => {
            event.ports[0].postMessage({ success: true });
        });
    }
});

