'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');

const source = fs.readFileSync(path.join(__dirname, '..', 'adapter.js'), 'utf8');
const configurations = [
  { id: 'stock', label: 'Stock', detail: '0.2 s silence', available: true, note: '', params: { vad_stop_s: 0.2 } },
  { id: 'patient', label: 'Patient', detail: '1.0 s silence', available: true, note: '' },
  { id: 'candidate', label: 'Candidate', detail: 'Export pending', available: false, note: 'Missing artifact' },
];
const sources = [{ source_id: 'clip-id', file: 'clip.wav', duration_s: 3, category: 'unreviewed', rights_note: 'Local test fixture' }];
const copy = value => JSON.parse(JSON.stringify(value));

function harness(options = {}) {
  const sockets = [];
  const requests = [];
  class Socket {
    constructor(url) {
      this.url = url;
      this.readyState = 0;
      this.sent = [];
      sockets.push(this);
      if (!options.stallSocket) queueMicrotask(() => this.open());
    }
    open() { this.readyState = 1; if (this.onopen) this.onopen({}); }
    send(data) { this.sent.push(JSON.parse(data)); }
    close() { this.readyState = 3; if (this.onclose) this.onclose({ code: 1000 }); }
    receive(data) { if (this.onmessage) this.onmessage({ data: typeof data === 'string' ? data : JSON.stringify(data) }); }
    fail() { this.readyState = 3; if (this.onclose) this.onclose({ code: 1006 }); }
  }
  const fetch = async (url, init) => {
    requests.push({ url, init });
    if (options.fetch) return options.fetch(url, init);
    const body = url.endsWith('/health') ? { ok: true, contract: '0.1', commit: 'test-sha', ...(options.health || {}) }
      : url.endsWith('/configurations') ? (options.configurations || configurations) : (options.sources || sources);
    return { ok: true, status: 200, json: async () => copy(body) };
  };
  const window = {};
  vm.runInNewContext(source, { window, setTimeout, clearTimeout, URL, AbortController, console });
  const adapter = new window.StutterTurnAdapters.live({ baseUrl: 'http://127.0.0.1:8765/', fetch, WebSocket: Socket, connectTimeoutMs: 35, startTimeoutMs: 35, onConnectionChange: options.onConnectionChange });
  return { adapter, sockets, requests, adapters: window.StutterTurnAdapters };
}

function started(overrides = {}) {
  return { v: '0.1', type: 'run_started', run_id: 'run-1', seq: 0, config: 'stock',
    params: { vad_stop_s: 0.2 }, model: 'stock-model', model_sha256: 'abc', commit: 'test-sha',
    t0_wall: '2026-10-10T18:00:00.000Z', services: 'off',
    source: { source_id: 'clip-id', duration_s: 3, source_offset_s: 0 }, ...overrides };
}
function event(overrides = {}) {
  return { v: '0.1', type: 'event', run_id: 'run-1', seq: 1, t: 0.8, kind: 'decision', name: 'turn_incomplete', prob: 0.3, ...overrides };
}
function callbacks() {
  const events = [], ends = [], errors = [];
  return { events, ends, errors, handlers: { onEvent: value => events.push(value), onEnd: value => ends.push(value), onError: value => errors.push(value) } };
}
async function active(options) {
  const h = harness(options);
  await h.adapter.connect();
  const cb = callbacks();
  const pending = h.adapter.start('stock', cb.handlers, 'clip.wav');
  await Promise.resolve();
  h.sockets.at(-1).receive(started(options && options.health && options.health.mock ? { mock: true } : {}));
  const info = await pending;
  return { ...h, ...cb, info };
}

test('discovers v0.1 configuration and source truth before enabling runs', async () => {
  const h = harness();
  const found = await h.adapter.connect();
  assert.equal(h.adapter.connected, true);
  assert.equal(found.health.contract, '0.1');
  assert.equal(h.adapter.getConfigurations()[2].id, 'candidate');
  assert.equal(h.adapter.getConfigurations()[2].available, false);
  assert.equal(h.adapter.getSources()[0].file, 'clip.wav');
  assert.equal(h.sockets[0].url, 'ws://127.0.0.1:8765/v0/ws');
  assert.match(h.adapter.sourceLabel, /playback unverified/i);
  h.adapter.disconnect();
});

test('start waits for acknowledgement and preserves source, run and services metadata', async () => {
  const h = harness();
  await h.adapter.connect();
  const cb = callbacks();
  let settled = false;
  const pending = h.adapter.start('stock', cb.handlers, 'clip.wav').then(x => { settled = true; return x; });
  await Promise.resolve();
  assert.equal(settled, false);
  assert.equal(h.sockets[0].sent[0].source, 'clip.wav');
  h.sockets[0].receive(started());
  const info = await pending;
  assert.equal(info.runId, 'run-1');
  assert.match(info.sourceRecording, /clip-id/);
  assert.equal(info.metadata.services, 'off');
  assert.equal(info.metadata.params.vad_stop_s, 0.2);
  h.adapter.disconnect();
});

test('forwards named events and final summary while rejecting callbacks after termination', async () => {
  const h = await active();
  h.sockets[0].receive(event());
  h.sockets[0].receive(event({ seq: 2, t: 1.1, name: 'turn_complete', trigger: 'fallback_timeout', prob: null }));
  h.sockets[0].receive({ v: '0.1', type: 'run_ended', run_id: 'run-1', seq: 3, t: 8, reason: 'completed', summary: { services: 'off', no_response: false } });
  h.sockets[0].receive(event({ seq: 4 }));
  assert.deepEqual(h.events.map(e => e.name), ['turn_incomplete', 'turn_complete']);
  assert.equal(h.ends[0].summary.services, 'off');
  assert.equal(h.errors.length, 0);
  h.adapter.disconnect();
});

test('rejects unavailable configuration and unlisted recording without starting', async () => {
  const h = harness();
  await h.adapter.connect();
  await assert.rejects(h.adapter.start('candidate', callbacks().handlers, 'clip.wav'), /unavailable/i);
  await assert.rejects(h.adapter.start('stock', callbacks().handlers, 'other.wav'), /source|recording/i);
  assert.equal(h.sockets[0].sent.length, 0);
  h.adapter.disconnect();
});

test('pending reset rejects start and isolates an acknowledgement from the old socket', async () => {
  const h = harness();
  await h.adapter.connect();
  const old = callbacks();
  const pending = h.adapter.start('stock', old.handlers, 'clip.wav');
  const rejected = assert.rejects(pending, error => error.name === 'AbortError');
  await Promise.resolve();
  const staleMessage = h.sockets[0].onmessage;
  h.adapter.stop();
  await rejected;
  staleMessage({ data: JSON.stringify(started()) });
  assert.equal(old.events.length + old.ends.length + old.errors.length, 0);
  const next = callbacks();
  const fresh = h.adapter.start('patient', next.handlers, 'clip.wav');
  await new Promise(resolve => setImmediate(resolve));
  h.sockets.at(-1).receive(started({ run_id: 'run-2', config: 'patient' }));
  assert.equal((await fresh).runId, 'run-2');
  h.adapter.disconnect();
});

test('active stop sends one stop and stale messages cannot affect later runs', async () => {
  const h = await active();
  const oldMessage = h.sockets[0].onmessage;
  h.adapter.stop();
  h.adapter.stop();
  assert.equal(h.sockets[0].sent.filter(x => x.type === 'stop').length, 1);
  assert.equal(h.sockets[0].sent.at(-1).run_id, 'run-1');
  oldMessage({ data: JSON.stringify(event()) });
  assert.equal(h.events.length, 0);
  h.adapter.disconnect();
});

test('ignores messages attributed to another run', async () => {
  const h = await active();
  h.sockets[0].receive(event({ run_id: 'old-run', seq: 97 }));
  h.sockets[0].receive(event());
  assert.equal(h.events.length, 1);
  assert.equal(h.errors.length, 0);
  h.adapter.disconnect();
});

test('late events from a completed run cannot reject a new pending start on the same socket', async () => {
  const h = await active();
  h.sockets[0].receive({ v: '0.1', type: 'run_ended', run_id: 'run-1', seq: 1, t: 8, reason: 'completed', summary: {} });
  const next = callbacks();
  const pending = h.adapter.start('stock', next.handlers, 'clip.wav');
  await Promise.resolve();
  h.sockets[0].receive(event({ seq: 2 }));
  h.sockets[0].receive(started({ run_id: 'run-2' }));
  assert.equal((await pending).runId, 'run-2');
  assert.equal(next.events.length + next.errors.length, 0);
  h.adapter.disconnect();
});

for (const alteration of [{ seq: 3 }, { seq: 0 }, { v: '9.0' }, { t: -1 }, { t: '1' }, { kind: 'unknown' }]) {
  test('surfaces invalid current-run event ' + JSON.stringify(alteration), async () => {
    const h = await active();
    h.sockets[0].receive(event(alteration));
    assert.equal(h.events.length, 0);
    assert.equal(h.errors.length, 1);
    h.sockets[0].receive(event());
    assert.equal(h.events.length, 0);
    h.adapter.disconnect();
  });
}

for (const alteration of [{ config: 'patient' }, { source: { source_id: 'another', duration_s: 3, source_offset_s: 0 } }, { seq: 2 }, { v: '2.0' }]) {
  test('rejects mismatched start ' + JSON.stringify(alteration), async () => {
    const h = harness();
    await h.adapter.connect();
    const pending = h.adapter.start('stock', callbacks().handlers, 'clip.wav');
    await Promise.resolve();
    h.sockets[0].receive(started(alteration));
    await assert.rejects(pending, /contract|version|config|source|sequence/i);
    h.adapter.disconnect();
  });
}

test('a server error before acknowledgement rejects the pending start', async () => {
  const h = harness();
  await h.adapter.connect();
  const pending = h.adapter.start('stock', callbacks().handlers, 'clip.wav');
  await Promise.resolve();
  h.sockets[0].receive({ v: '0.1', type: 'error', run_id: null, seq: -1, message: 'Model missing' });
  await assert.rejects(pending, /Model missing/);
  h.adapter.disconnect();
});

test('socket closure surfaces an active run failure without reconnecting or replaying', async () => {
  const h = await active();
  h.sockets[0].fail();
  assert.equal(h.errors.length, 1);
  assert.match(h.errors[0], /disconnect|closed/i);
  assert.equal(h.adapter.connected, false);
  assert.equal(h.sockets.length, 1);
});

test('connection observer reports idle closure without reconnecting or starting a run', async () => {
  const changes = [];
  const h = harness({ onConnectionChange: change => changes.push(change) });
  await h.adapter.connect();
  assert.equal(changes[0].connected, true);
  h.sockets[0].fail();
  assert.equal(changes[1].connected, false);
  assert.match(changes[1].reason, /disconnect|closed/i);
  assert.equal(h.sockets.length, 1);
  assert.equal(h.sockets[0].sent.length, 0);
});

test('a replaced socket cannot publish stale disconnection to an assigned observer', async () => {
  const changes = [];
  const h = harness();
  h.adapter.onConnectionChange = change => changes.push(change);
  await h.adapter.connect();
  const staleClose = h.sockets[0].onclose;
  const staleError = h.sockets[0].onerror;
  h.adapter.disconnect();
  await h.adapter.connect();
  const count = changes.length;
  staleClose({}); staleError({});
  assert.equal(changes.length, count);
  assert.equal(changes.at(-1).connected, true);
  h.adapter.disconnect();
  assert.equal(changes.at(-1).connected, false);
});

test('malformed JSON fails the active stream visibly', async () => {
  const h = await active();
  h.sockets[0].receive('{broken');
  assert.match(h.errors[0], /JSON|message/i);
  h.adapter.disconnect();
});

test('absent server, stalled socket and missing start acknowledgement are bounded', async () => {
  const absent = harness({ fetch: () => new Promise(() => {}) });
  await assert.rejects(absent.adapter.connect(), /timed out/i);
  assert.equal(absent.sockets.length, 0);
  const socket = harness({ stallSocket: true });
  await assert.rejects(socket.adapter.connect(), /timed out/i);
  socket.adapter.disconnect();
  const h = harness();
  await h.adapter.connect();
  await assert.rejects(h.adapter.start('stock', callbacks().handlers, 'clip.wav'), /timed out/i);
  h.adapter.disconnect();
});

test('disconnect cancels discovery and late fetches cannot reconnect', async () => {
  const resolves = [];
  const h = harness({ fetch: () => new Promise(resolve => resolves.push(resolve)) });
  const connecting = h.adapter.connect();
  const rejected = assert.rejects(connecting, error => error.name === 'AbortError');
  h.adapter.disconnect();
  await rejected;
  resolves.forEach(resolve => resolve({ ok: true, json: async () => ({ ok: true, contract: '0.1' }) }));
  await Promise.resolve();
  assert.equal(h.adapter.connected, false);
  assert.equal(h.sockets.length, 0);
});

test('refuses unknown health versions and malformed discovery availability', async () => {
  await assert.rejects(harness({ health: { contract: '2.0' } }).adapter.connect(), /version|contract/i);
  await assert.rejects(harness({ configurations: [{ ...configurations[0], available: 'true' }] }).adapter.connect(), /configuration/i);
});

test('mock provenance is persistent and every mock payload must be tagged', async () => {
  const h = await active({ health: { mock: true } });
  assert.equal(h.adapter.mode, 'mock');
  assert.match(h.adapter.sourceLabel, /MOCK/);
  assert.match(h.adapter.sourceLabel, /no audio/i);
  h.sockets[0].receive(event({ mock: true, model: 'mock' }));
  assert.equal(h.events.length, 1);
  h.sockets[0].receive(event({ seq: 2 }));
  assert.match(h.errors[0], /mock|provenance/i);
  h.adapter.disconnect();
});

test('a live connection refuses synthetic mock payloads', async () => {
  const h = await active();
  h.sockets[0].receive(event({ mock: true }));
  assert.match(h.errors[0], /mock|provenance/i);
  h.adapter.disconnect();
});

test('preview event names and summary identify synthetic data and services off', async () => {
  const window = {}, timers = [];
  vm.runInNewContext(source, { window, setTimeout: fn => { timers.push(fn); return timers.length; }, clearTimeout() {}, URL, AbortController });
  const preview = new window.StutterTurnAdapters.preview();
  const cb = callbacks();
  const info = preview.start('stock', cb.handlers);
  timers.forEach(fn => fn());
  assert.equal(info.metadata.services, 'off');
  assert.ok(cb.events.some(e => e.name === 'turn_incomplete'));
  assert.ok(cb.events.some(e => e.name === 'turn_complete'));
  assert.ok(cb.events.some(e => e.name === 'agent_audio_start'));
  assert.equal(cb.ends[0].summary.synthetic, true);
  preview.stop();
});
