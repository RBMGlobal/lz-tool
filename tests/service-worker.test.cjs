const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const ROOT = 'https://rbmglobal.co.uk/lz-tool/';
const BASE = ROOT + 'beta/';
const SHELL = 'lz-brief-BETA-v2';
const OCR = 'lz-brief-ocr-v1';

function harness() {
  const handlers = {}, buckets = new Map(), downloads = [];
  let network = async () => new Response('fresh');
  let failPut = false, failOpen = false, failMatch = false;
  const cache = name => {
    if (!buckets.has(name)) buckets.set(name, new Map());
    const entries = buckets.get(name);
    return {
      async match(key) { if (failMatch) throw new Error('cache read failed'); const r = entries.get(key.url || key); return r && r.clone(); },
      async put(key, response) {
        if (failPut) throw new Error('quota');
        entries.set(key.url || key, response.clone());
      },
      async add(url) { downloads.push(url); entries.set(url, new Response('installed')); },
      async addAll(urls) { for (const url of urls) await this.add(url); }
    };
  };
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../beta/sw.js'), 'utf8'), {
    URL, Set, Promise, self: {
      location: new URL(BASE + 'sw.js'),
      addEventListener(type, handler) { handlers[type] = handler; },
      async skipWaiting() {}, clients: { async claim() {} }
    },
    caches: {
      async open(name) { if (failOpen) throw new Error('private mode'); return cache(name); },
      async keys() { return [...buckets.keys()]; },
      async delete(name) { return buckets.delete(name); }
    }, fetch: (...args) => network(...args)
  });
  return {
    buckets, downloads, cache,
    network(fn) { network = fn; }, failPut() { failPut = true; }, failOpen() { failOpen = true; }, failMatch() { failMatch = true; },
    async lifecycle(type) { let done; handlers[type]({ waitUntil(p) { done = p; } }); await done; },
    dispatch(url, mode = 'cors', method = 'GET', headers = {}) {
      let response;
      handlers.fetch({ request: { url, mode, method, headers: new Headers(headers) }, respondWith(p) { response = p; } });
      return response;
    }
  };
}

test('installation preloads existing shared files, not missing beta/vendor files', async () => {
  const h = harness(); await h.lifecycle('install');
  assert.equal(h.downloads.length, 10);
  for (const url of h.downloads) {
    assert.ok(!url.includes('/beta/vendor/'));
    const relative = new URL(url).pathname.replace('/lz-tool/', '');
    assert.ok(fs.existsSync(path.join(__dirname, '..', relative)), url);
  }
  assert.equal(h.downloads.filter(u => u.startsWith(ROOT + 'vendor/')).length, 4);
});

test('activation removes old beta shells and preserves all sibling/shared caches', async () => {
  const h = harness();
  for (const name of [SHELL, 'lz-brief-BETA-v1', 'ped-beta-v2', 'lz-brief-v1', OCR]) h.cache(name);
  await h.lifecycle('activate');
  assert.deepEqual([...h.buckets.keys()], [SHELL, 'ped-beta-v2', 'lz-brief-v1', OCR]);
});

test('500 response preserves and serves the last good shell', async () => {
  const h = harness(); await h.cache(SHELL).put(BASE + 'index.html', new Response('good'));
  h.network(async () => new Response('bad gateway', { status: 500 }));
  assert.equal(await (await h.dispatch(BASE + 'index.html', 'navigate')).text(), 'good');
  assert.equal(await (await h.cache(SHELL).match(BASE + 'index.html')).text(), 'good');
});

test('successful response is retained at a canonical bounded cache key', async () => {
  const h = harness();
  assert.equal(await (await h.dispatch(BASE + '?v=2', 'navigate')).text(), 'fresh');
  await h.dispatch(BASE + '?v=3', 'navigate');
  assert.deepEqual([...h.buckets.get(SHELL).keys()], [BASE]);
});

test('offline document fallback never returns HTML for missing icons or unknown paths', async () => {
  const h = harness(); await h.cache(SHELL).put(BASE + 'index.html', new Response('good'));
  h.network(async () => { throw new Error('offline'); });
  assert.equal(await (await h.dispatch(BASE + '?source=home', 'navigate')).text(), 'good');
  await assert.rejects(h.dispatch(BASE + 'icon-192.png'), /offline/);
  assert.equal(h.dispatch(BASE + 'missing.js'), undefined);
  assert.equal(h.dispatch(BASE + 'missing.html', 'navigate'), undefined);
});

test('unrelated same-origin, arbitrary vendor and external requests remain untouched', () => {
  const h = harness();
  for (const url of [ROOT + 'vendor/unknown.js', BASE + 'vendor/worker.min.js',
    'https://rbmglobal.co.uk/sentiment/', 'https://example.com/tiles/1.png']) {
    assert.equal(h.dispatch(url), undefined, url);
  }
  assert.equal(h.dispatch(BASE, 'navigate', 'POST'), undefined);
});

test('shared files are cache-first and HTTP failures are never stored', async () => {
  const h = harness(), url = ROOT + 'vendor/worker.min.js';
  h.network(async () => new Response('missing', { status: 404 }));
  assert.equal((await h.dispatch(url)).status, 404);
  assert.equal(await h.cache(OCR).match(url), undefined);
  await h.cache(OCR).put(url, new Response('worker'));
  h.network(async () => { throw new Error('offline'); });
  assert.equal(await (await h.dispatch(url)).text(), 'worker');
});

test('cache quota/storage failure does not discard working online responses', async () => {
  for (const failure of ['failPut', 'failOpen', 'failMatch']) {
    const h = harness(); h[failure]();
    assert.equal(await (await h.dispatch(BASE, 'navigate')).text(), 'fresh');
    assert.equal(await (await h.dispatch(ROOT + 'vendor/worker.min.js')).text(), 'fresh');
  }
});

test('redirects cannot replace an installed shell', async () => {
  const h = harness(); await h.cache(SHELL).put(BASE, new Response('good'));
  const response = new Response('redirect destination');
  Object.defineProperty(response, 'redirected', { value: true });
  h.network(async () => response);
  await h.dispatch(BASE, 'navigate');
  assert.equal(await (await h.cache(SHELL).match(BASE)).text(), 'good');
});


test('partial requests bypass worker and partial responses cannot poison complete files', async () => {
  const h = harness(), url = ROOT + 'vendor/worker.min.js';
  assert.equal(h.dispatch(BASE, 'navigate', 'GET', { Range: 'bytes=0-5' }), undefined);
  assert.equal(h.dispatch(url, 'cors', 'GET', { Range: 'bytes=0-5' }), undefined);
  h.network(async () => new Response('part', { status: 206 }));
  assert.equal((await h.dispatch(url)).status, 206);
  assert.equal(await h.cache(OCR).match(url), undefined);
  await h.cache(SHELL).put(BASE, new Response('complete'));
  assert.equal((await h.dispatch(BASE, 'navigate')).status, 206);
  assert.equal(await (await h.cache(SHELL).match(BASE)).text(), 'complete');
});

test('failed cache reads preserve the original HTTP error response', async () => {
  const h = harness(); h.failMatch();
  h.network(async () => new Response('gateway failure', { status: 503 }));
  assert.equal((await h.dispatch(BASE, 'navigate')).status, 503);
});
