const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const html = fs.readFileSync(path.join(__dirname, '../beta/index.html'), 'utf8');
const source = html.match(/<script>\s*([\s\S]*?)<\/script>/)[1];
const escapeSource = source.slice(source.indexOf('const escapeHTML='), source.indexOf('if("serviceWorker"'));
const showFix = source.slice(source.indexOf('function showFix('), source.indexOf('async function quickLook('));
const fileHandler = source.slice(source.indexOf('$("file").onchange='), source.indexOf('/* ─────────────── waypoint exports'));
const payload = '<img src=x onerror="alert(1)">';

function context() {
  const elements = new Map();
  const $ = id => {
    if (!elements.has(id)) elements.set(id, {
      innerHTML: '', value: '', textContent: '', children: [],
      classList: { remove() {}, add() {} }, querySelectorAll() { return []; },
      querySelector() { return { textContent: '' }; }
    });
    return elements.get(id);
  };
  const c = vm.createContext({ $, FIX: null, CANDIDATES: [], rose() {},
    quickLook() {}, metaLook() {}, toMGRS: () => 'grid', ddm: () => 'DDM', dms: () => 'DMS',
    showFix() {}, readPhoto() {} });
  vm.runInContext(escapeSource, c);
  return { c, $ };
}

test('entire page JavaScript still parses', () => {
  assert.doesNotThrow(() => new vm.Script(source));
});

test('selected imported labels, notes and filenames display as text', () => {
  const { c, $ } = context();
  vm.runInContext(showFix, c);
  c.fix = { lat: 0, lon: 0, src: payload, note: payload, label: payload };
  vm.runInContext('showFix(fix)', c);
  assert.ok(!$('meta').innerHTML.includes('<img'));
  assert.equal(($('meta').innerHTML.match(/&lt;img/g) || []).length, 3);
  assert.equal($('nm').value, payload, 'input value retains original text');
});

test('multiple-file result labels and source filenames cannot create elements', async () => {
  const { c, $ } = context();
  c.parseFile = async () => [
    { lat: 0, lon: 0, label: payload, src: payload },
    { lat: 1, lon: 1, label: 'A & B', src: 'ordinary.gpx' }
  ];
  vm.runInContext(fileHandler, c);
  await $('file').onchange({ target: { files: [{ name: 'example.gpx', type: '' }], value: 'x' } });
  assert.ok(!$('pts').innerHTML.includes('<img'));
  assert.equal(($('pts').innerHTML.match(/&lt;img/g) || []).length, 2);
  assert.match($('pts').innerHTML, /A &amp; B/);
});

test('damaged file parsing reports a recoverable error instead of an unhandled rejection', async () => {
  const { c, $ } = context();
  c.parseFile = async () => { throw new RangeError('Offset outside DataView'); };
  vm.runInContext(fileHandler, c);
  await $('file').onchange({ target: { files: [{ name: 'damaged.zip', type: '' }], value: 'x' } });
  assert.equal($('perr').textContent, 'Could not read that file. Check the file is complete and try again.');
  assert.equal($('pts').innerHTML, '');
});

test('raw recognized display text is escaped without changing recognition logic', () => {
  const { c, $ } = context();
  const start = source.indexOf('$("pts").innerHTML=pts.map(');
  const end = source.indexOf(';', source.indexOf('.join("")', start)) + 1;
  c.pts = [{ tag: '', lat: 0, lon: 0, n: 1, line: payload }];
  c.runs = 1; c.isA = () => false;
  vm.runInContext(source.slice(start, end), c);
  assert.ok(!$('pts').innerHTML.includes('<img'));
  assert.match($('pts').innerHTML, /&lt;img/);
});


test('quoted display values do not truncate their copy-text HTML attribute', () => {
  const { c, $ } = context();
  c.dms = () => 'value with "quotes" & symbols';
  vm.runInContext(showFix, c);
  c.fix = { lat: 0, lon: 0 };
  vm.runInContext('showFix(fix)', c);
  assert.match($('cd').innerHTML,
    /data-c="value with &quot;quotes&quot; &amp; symbols"/);
});
