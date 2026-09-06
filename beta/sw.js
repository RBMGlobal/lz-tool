/* LZ Brief offline worker — BETA BUILD, scope /lz-tool/beta/.
   Cache storage is per-ORIGIN, not per-scope, so the shell cache name must
   differ from the live build's or the two overwrite each other. OCR_CACHE is
   deliberately the SAME name: identical immutable files, one download shared.
   The app shell is cached so the tool opens with no signal. Satellite tiles and
   metadata are deliberately NOT cached: stale imagery presented as current is the
   exact failure this tool exists to prevent. With no signal you get the tool, the
   parser, the grid conversions and the compass — on a blank map background. */
const CACHE = "lz-brief-BETA-v1";   // must differ from the live shell cache
const SHELL = [
  "./", "./index.html", "./manifest.webmanifest",
  "./icon-192.png", "./icon-512.png", "./apple-touch-icon.png"
];
/* The OCR pack (Tesseract.js engine and worker, WASM core, English model —
   about 7 MB) sits in its own cache so it survives app-shell version bumps and
   is fetched once. Cached best-effort at install; if the download fails the app
   still installs and the pack is cached the first time "Read a screen photo"
   runs. */
const OCR_CACHE = "lz-brief-ocr-v1";
const OCR = [
  "./vendor/tesseract.min.js", "./vendor/worker.min.js",
  "./vendor/tesseract-core-simd-lstm.wasm.js", "./vendor/eng.traineddata.gz"
];

self.addEventListener("install", e => {
  e.waitUntil(Promise.all([
    caches.open(CACHE).then(c => c.addAll(SHELL)),
    caches.open(OCR_CACHE).then(c => Promise.all(OCR.map(u => c.add(u).catch(() => {}))))
  ]).then(() => self.skipWaiting()));
});

self.addEventListener("activate", e => {
  /* Only ever evict caches from THIS build's own family. Cache storage is
     per-ORIGIN, not per-scope, so a blanket "delete everything that is not
     mine" wipes the sibling build's offline shell: opening the beta would
     leave a crew with no cached copy of the live tool, which is the one thing
     the service worker exists to prevent. FAMILY covers this build's own older
     versions and nothing else. */
  const FAMILY = "lz-brief-BETA-";
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys
        .filter(k => k.startsWith(FAMILY) && k !== CACHE)
        .map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;      // tiles & metadata: always live

  // the OCR pack never changes under one name: cache-first, fill on first use
  if (url.pathname.includes("/vendor/")) {
    e.respondWith(caches.open(OCR_CACHE).then(c => c.match(req).then(hit => hit ||
      fetch(req).then(res => { if (res.ok) c.put(req, res.clone()); return res; }))));
    return;
  }

  // network-first for the shell, so an update lands as soon as there is signal
  e.respondWith(
    fetch(req)
      .then(res => {
        const copy = res.clone();
        caches.open(CACHE).then(c => c.put(req, copy));
        return res;
      })
      .catch(() => caches.match(req).then(r => r || caches.match("./index.html")))
  );
});
