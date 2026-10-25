/* Beta app shell only. Cache storage is shared by every page on this origin:
   never cache unrelated pages, imagery, metadata or arbitrary vendor paths. */
const CACHE = "lz-brief-BETA-v2";
const BASE = new URL("./", self.location.href);
const SHELL = [
  "./", "./index.html", "./manifest.webmanifest",
  "./icon-192.png", "./icon-512.png", "./apple-touch-icon.png"
].map(path => new URL(path, BASE).href);
const SHELL_URLS = new Set(SHELL);
const DOCUMENTS = new Set([BASE.href, new URL("index.html", BASE).href]);
// The app loads these existing shared assets from the parent directory.
const OCR_CACHE = "lz-brief-ocr-v1";
const OCR = [
  "../vendor/tesseract.min.js", "../vendor/worker.min.js",
  "../vendor/tesseract-core-simd-lstm.wasm.js", "../vendor/eng.traineddata.gz"
].map(path => new URL(path, BASE).href);
const OCR_URLS = new Set(OCR);

self.addEventListener("install", event => {
  event.waitUntil(Promise.all([
    caches.open(CACHE).then(cache => cache.addAll(SHELL)),
    caches.open(OCR_CACHE).then(cache =>
      Promise.all(OCR.map(url => cache.add(url).catch(() => {}))))
  ]).then(() => self.skipWaiting()));
});

self.addEventListener("activate", event => {
  event.waitUntil(caches.keys()
    .then(keys => Promise.all(keys
      .filter(key => key.startsWith("lz-brief-BETA-") && key !== CACHE)
      .map(key => caches.delete(key))))
    .then(() => self.clients.claim()));
});

async function remember(cache, key, response) {
  // HTTP errors and redirects must not replace a working offline copy.
  if (response.status === 200 && !response.redirected) {
    // Quota/private-mode failures must not discard a successful network result.
    try { await cache.put(key, response.clone()); } catch (_) {}
  }
}

async function cachedResponse(cache, key) {
  try { return cache && await cache.match(key); } catch (_) { return undefined; }
}

async function shellResponse(request, key) {
  // Cache storage may be unavailable even when the service worker is running.
  const cache = await caches.open(CACHE).catch(() => null);
  const cached = async () => await cachedResponse(cache, key) ||
    (request.mode === "navigate" && DOCUMENTS.has(key)
      ? await cachedResponse(cache, new URL("index.html", BASE).href) : undefined);
  try {
    const response = await fetch(request);
    if (response.ok) {
      if (cache) await remember(cache, key, response);
      return response;
    }
    return await cached() || response;
  } catch (error) {
    const fallback = await cached();
    if (fallback) return fallback;
    throw error;
  }
}

async function sharedAssetResponse(request, key) {
  const cache = await caches.open(OCR_CACHE).catch(() => null);
  const hit = await cachedResponse(cache, key);
  if (hit) return hit;
  const response = await fetch(request);
  if (cache) await remember(cache, key, response);
  return response;
}

self.addEventListener("fetch", event => {
  const request = event.request;
  if (request.method !== "GET" || request.headers.has("range")) return;
  const url = new URL(request.url);
  if (url.origin !== BASE.origin) return;
  // Ignore query strings only for known static files: one bounded cache entry
  // per asset, including home-screen and cache-busting navigation URLs.
  url.search = "";
  url.hash = "";
  const key = url.href;
  if (OCR_URLS.has(key)) {
    event.respondWith(sharedAssetResponse(request, key));
  } else if (SHELL_URLS.has(key)) {
    event.respondWith(shellResponse(request, key));
  }
});
