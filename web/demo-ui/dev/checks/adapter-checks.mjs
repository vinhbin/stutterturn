/* Reproducible adapter checks for web/demo-ui/adapter.js.
 *
 * Run from the repository root with no dependencies:
 *   node web/demo-ui/dev/checks/adapter-checks.mjs
 *
 * The adapter is loaded as-is and driven through stubbed fetch/WebSocket
 * transports. These checks exercise contract validation and lifecycle logic
 * only: no audio, model, recording or benchmark evidence is involved, and a
 * pass does not satisfy any real-integration acceptance gate.
 */
'use strict';

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const here = path.dirname(fileURLToPath(import.meta.url));
const adapterSource = readFileSync(path.join(here, '..', '..', 'adapter.js'), 'utf8');

function loadAdapters() {
  const windowObject = {};
  new Function('window', adapterSource)(windowObject);
  return windowObject.StutterTurnAdapters;
}
const Adapters = loadAdapters();

/* ---------- tiny harness ---------- */
let passed = 0;
const failures = [];
function assert(condition, message) {
  if (!condition) { throw new Error(message || 'assertion failed'); }
}
async function rejects(promise, pattern, message) {
  try { await promise; }
  catch (error) {
    const text = String((error && error.message) || error);
    assert(pattern.test(text), (message || 'rejection text mismatch') + ': got "' + text + '"');
    return error;
  }
  throw new Error(message || 'expected rejection, promise resolved');
}
async function test(name, fn) {
  try { await fn(); passed += 1; console.log('ok   ' + name); }
  catch (error) {
    failures.push({ name, error });
    console.log('FAIL ' + name + ' — ' + ((error && error.message) || error));
  }
}
const tick = () => new Promise((resolve) => setTimeout(resolve, 0));
const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

/* ---------- transport stubs ---------- */
function fetchStub(routes) {
  return function (url) {
    const pathname = new URL(url).pathname;
    const value = routes[pathname];
    if (value === undefined) { return Promise.resolve({ ok: false, status: 404, json: () => Promise.resolve({}) }); }
    if (value === 'hang') { return new Promise(() => {}); }
    return Promise.resolve({ ok: true, json: () => Promise.resolve(JSON.parse(JSON.stringify(value))) });
  };
}
class SocketStub {
  constructor(url) {
    this.url = url;
    this.readyState = 0;
    this.sent = [];
    this.onopen = this.onmessage = this.onerror = this.onclose = null;
    queueMicrotask(() => { if (this.readyState === 0) { this.readyState = 1; if (this.onopen) { this.onopen(); } } });
  }
  send(data) { this.sent.push(JSON.parse(data)); }
  close() { this.readyState = 3; }
  receive(message) { if (this.onmessage) { this.onmessage({ data: JSON.stringify(message) }); } }
}

const GOOD_HEALTH = { ok: true, contract: '0.1', commit: 'check-suite' };
const GOOD_CONFIGS = [
  { id: 'stock', label: 'STOCK', available: true },
  { id: 'patient', label: 'PATIENT', available: true },
  { id: 'candidate', label: 'STUTTERTURN', available: false, note: 'no exported artifact' },
];
const GOOD_SOURCES = [{ source_id: 'clip-a', file: 'clip_a.wav', duration_s: 3 }];

function makeLive(routes, options = {}) {
  const sockets = [];
  class TrackedSocket extends SocketStub {
    constructor(url) { super(url); sockets.push(this); }
  }
  const adapter = new Adapters.live(Object.assign({
    baseUrl: 'http://127.0.0.1:8765',
    fetch: fetchStub(routes),
    WebSocket: TrackedSocket,
    connectTimeoutMs: 400,
    startTimeoutMs: 400,
  }, options));
  return { adapter, sockets };
}
function routesWith(overrides = {}) {
  return Object.assign({
    '/v0/health': GOOD_HEALTH,
    '/v0/configurations': GOOD_CONFIGS,
    '/v0/sources': GOOD_SOURCES,
  }, overrides);
}
async function connected(overrides = {}, options = {}) {
  const { adapter, sockets } = makeLive(routesWith(overrides), options);
  const info = await adapter.connect();
  return { adapter, sockets, socket: sockets[0], info };
}
async function sourceAccepted(file) {
  const { adapter } = makeLive(routesWith({ '/v0/sources': [{ source_id: 'probe', file, duration_s: 1 }] }));
  try { await adapter.connect(); adapter.disconnect(); return true; }
  catch (error) {
    adapter.disconnect();
    if (/Invalid source discovery/.test(String(error.message))) { return false; }
    throw error;
  }
}
function recorder() {
  const record = { events: [], ends: [], errors: [] };
  record.handlers = {
    onEvent: (event) => record.events.push(event),
    onEnd: (message) => record.ends.push(message),
    onError: (message) => record.errors.push(message),
  };
  return record;
}
function ack(extra = {}) {
  return Object.assign({
    v: '0.1', type: 'run_started', run_id: 'run-1', seq: 0, config: 'stock',
    source: { source_id: 'clip-a', duration_s: 3, source_offset_s: 0 },
    model: 'check-stub', params: {}, services: 'off',
  }, extra);
}
function runEvent(seq, extra = {}) {
  return Object.assign({ v: '0.1', type: 'event', run_id: 'run-1', seq, t: 1, kind: 'info', name: 'speech_start' }, extra);
}
async function startAcked(adapter, socket, extra = {}) {
  const record = recorder();
  const startPromise = adapter.start(extra.config || 'stock', record.handlers, extra.source || 'clip_a.wav');
  startPromise.catch(() => {}); // surfaced through `rejects` or `info` by each caller
  await tick();
  socket.receive(ack(extra.ack || {}));
  const info = await startPromise;
  return { record, info };
}

/* ---------- validSourceFile (via /v0/sources discovery validation) ---------- */
await test('source file: accepts a bare name (contract v0.1, af2813d)', async () => {
  assert(await sourceAccepted('HeStutters_2_57.wav'), 'bare name should be accepted');
});
await test('source file: tolerates a relative path (pre-af2813d compatibility only)', async () => {
  assert(await sourceAccepted('clips/sample.wav'), 'relative path should still be tolerated');
});
await test('source file: rejects separators and roots (backslash, leading /, .., .)', async () => {
  assert(!(await sourceAccepted('clips\\sample.wav')), 'backslash path accepted');
  assert(!(await sourceAccepted('/etc/passwd')), 'absolute path accepted');
  assert(!(await sourceAccepted('../secret.wav')), 'parent traversal accepted');
  assert(!(await sourceAccepted('./clip.wav')), 'single-dot segment accepted');
});
await test('source file: rejects URLs, percent-encoding, query and fragment', async () => {
  assert(!(await sourceAccepted('https://example.com/a.wav')), 'URL accepted');
  assert(!(await sourceAccepted('clip%2e%2e.wav')), 'percent-encoded name accepted');
  assert(!(await sourceAccepted('clip.wav?x=1')), 'query accepted');
  assert(!(await sourceAccepted('clip.wav#frag')), 'fragment accepted');
});
await test('source file: rejects control chars, padding, trailing dot, empty, oversized', async () => {
  assert(!(await sourceAccepted('clip\u0000.wav')), 'NUL accepted');
  assert(!(await sourceAccepted(' clip.wav')), 'leading space accepted');
  assert(!(await sourceAccepted('clip.wav.')), 'trailing dot accepted');
  assert(!(await sourceAccepted('')), 'empty name accepted');
  assert(!(await sourceAccepted('a'.repeat(4097))), 'oversized name accepted');
});
await test('source file: rejects duplicate files in one discovery list', async () => {
  const { adapter } = makeLive(routesWith({ '/v0/sources': [
    { source_id: 'a', file: 'same.wav', duration_s: 1 },
    { source_id: 'b', file: 'same.wav', duration_s: 2 },
  ] }));
  await rejects(adapter.connect(), /Invalid source discovery/);
  adapter.disconnect();
});

/* ---------- discovery ---------- */
await test('constructor: rejects base URLs with path, query or credentials', async () => {
  for (const bad of ['http://127.0.0.1:8765/api', 'http://127.0.0.1:8765/?x=1', 'http://user:pw@127.0.0.1:8765', 'ftp://127.0.0.1:8765']) {
    let threw = false;
    try { new Adapters.live({ baseUrl: bad }); } catch (_) { threw = true; }
    assert(threw, 'accepted ' + bad);
  }
  assert(new Adapters.live({ baseUrl: 'http://127.0.0.1:8765' }).baseUrl === 'http://127.0.0.1:8765');
});
await test('connect: returns configurations, sources and health; mode stays live', async () => {
  const { adapter, info } = await connected();
  assert(info.health.commit === 'check-suite', 'health not surfaced');
  assert(info.configurations.length === 3 && info.sources.length === 1, 'discovery data missing');
  assert(adapter.mode === 'live' && adapter.connected === true, 'expected connected live mode');
  assert(/playback unverified/i.test(adapter.sourceLabel), 'live source label missing caveat');
  adapter.disconnect();
});
await test('connect: rejects wrong contract version and ok:false health', async () => {
  const bad1 = makeLive(routesWith({ '/v0/health': { ok: true, contract: '0.2' } }));
  await rejects(bad1.adapter.connect(), /contract version/i);
  const bad2 = makeLive(routesWith({ '/v0/health': { ok: false, contract: '0.1' } }));
  await rejects(bad2.adapter.connect(), /health or contract/i);
});
await test('connect: health.mock true switches to mock mode with a mock label', async () => {
  const { adapter } = await connected({ '/v0/health': Object.assign({}, GOOD_HEALTH, { mock: true }) });
  assert(adapter.mode === 'mock', 'expected mock mode');
  assert(/DEVELOPMENT MOCK/.test(adapter.sourceLabel), 'mock source label missing');
  adapter.disconnect();
});
await test('connect: rejects invalid configuration lists (duplicate id, bad id, missing label)', async () => {
  const dup = makeLive(routesWith({ '/v0/configurations': [GOOD_CONFIGS[0], GOOD_CONFIGS[0]] }));
  await rejects(dup.adapter.connect(), /Invalid configuration/);
  const badId = makeLive(routesWith({ '/v0/configurations': [{ id: '../x', label: 'X', available: true }] }));
  await rejects(badId.adapter.connect(), /Invalid configuration/);
  const noLabel = makeLive(routesWith({ '/v0/configurations': [{ id: 'stock', available: true }] }));
  await rejects(noLabel.adapter.connect(), /Invalid configuration/);
});
await test('connect: rejects invalid source rows (bad duration, missing source_id, non-array)', async () => {
  const badDuration = makeLive(routesWith({ '/v0/sources': [{ source_id: 'a', file: 'a.wav', duration_s: -1 }] }));
  await rejects(badDuration.adapter.connect(), /Invalid source discovery/);
  const noId = makeLive(routesWith({ '/v0/sources': [{ file: 'a.wav', duration_s: 1 }] }));
  await rejects(noId.adapter.connect(), /Invalid source discovery/);
  const notArray = makeLive(routesWith({ '/v0/sources': { file: 'a.wav' } }));
  await rejects(notArray.adapter.connect(), /Invalid source discovery/);
});
await test('connect: HTTP failure rejects and leaves no discovery data', async () => {
  const { adapter } = makeLive({ '/v0/health': GOOD_HEALTH, '/v0/configurations': GOOD_CONFIGS });
  await rejects(adapter.connect(), /HTTP 404/);
  assert(adapter.getConfigurations().length === 0 && adapter.getSources().length === 0, 'state not cleared');
});
await test('connect: discovery timeout is bounded', async () => {
  const { adapter } = makeLive(routesWith({ '/v0/sources': 'hang' }), { connectTimeoutMs: 40 });
  await rejects(adapter.connect(), /timed out/i);
});

/* ---------- start / acknowledgement ---------- */
await test('start: rejected before connect', async () => {
  const { adapter } = makeLive(routesWith());
  await rejects(adapter.start('stock', recorder().handlers, 'clip_a.wav'), /not connected/i);
});
await test('start: unavailable candidate configuration is never started (gating)', async () => {
  const { adapter } = await connected();
  await rejects(adapter.start('candidate', recorder().handlers, 'clip_a.wav'), /unavailable/i);
  adapter.disconnect();
});
await test('start: source must come from the backend source list', async () => {
  const { adapter } = await connected();
  await rejects(adapter.start('stock', recorder().handlers, 'not_listed.wav'), /recording/i);
  adapter.disconnect();
});
await test('start: run_started acknowledgement resolves with run identity and metadata', async () => {
  const { adapter, socket } = await connected();
  const { info } = await startAcked(adapter, socket);
  assert(info.runId === 'run-1', 'run id not surfaced');
  assert(/playback unverified/i.test(info.runIdNote), 'live run note missing caveat');
  assert(/clip-a/.test(info.sourceRecording), 'source identity not surfaced');
  assert(info.metadata.type === 'run_started' && info.metadata.model === 'check-stub', 'metadata not passed through');
  assert(socket.sent.some((m) => m.type === 'start' && m.config === 'stock' && m.source === 'clip_a.wav'), 'start command not sent');
  adapter.disconnect();
});
await test('start: mock-mode acknowledgement must carry mock:true and labels the run MOCK', async () => {
  const { adapter, socket } = await connected({ '/v0/health': Object.assign({}, GOOD_HEALTH, { mock: true }) });
  const { info } = await startAcked(adapter, socket, { ack: { mock: true } });
  assert(/MOCK run/.test(info.runIdNote), 'mock run note missing');
  adapter.disconnect();
});
await test('start: acknowledgement mismatches reject (config, source, seq)', async () => {
  for (const [patch, pattern] of [
    [{ config: 'patient' }, /configuration does not match/i],
    [{ source: { source_id: 'other', duration_s: 3, source_offset_s: 0 } }, /source does not match/i],
    [{ seq: 1 }, /sequence/i],
  ]) {
    const { adapter, socket } = await connected();
    const startPromise = adapter.start('stock', recorder().handlers, 'clip_a.wav');
    startPromise.catch(() => {});
    await tick();
    socket.receive(ack(patch));
    await rejects(startPromise, pattern);
    adapter.disconnect();
  }
});
await test('start: acknowledgement timeout rejects; concurrent second start rejects', async () => {
  const { adapter, socket } = await connected({}, { startTimeoutMs: 40 });
  const first = adapter.start('stock', recorder().handlers, 'clip_a.wav');
  first.catch(() => {});
  await rejects(adapter.start('stock', recorder().handlers, 'clip_a.wav'), /already starting or active/i);
  await rejects(first, /timed out/i);
  assert(socket, 'socket should exist');
  adapter.disconnect();
});

/* ---------- in-run message validation ---------- */
await test('events: valid messages pass through to onEvent unchanged', async () => {
  const { adapter, socket } = await connected();
  const { record } = await startAcked(adapter, socket);
  socket.receive(runEvent(1, { kind: 'state', state: 'speaking', name: undefined }));
  socket.receive(runEvent(2, { t: 1.94, kind: 'decision', name: 'turn_complete', prob: 0.81, trigger: 'smart_turn' }));
  socket.receive(runEvent(3, { t: 3.21, kind: 'audible', name: 'agent_audio_start' }));
  assert(record.events.length === 3 && record.errors.length === 0, 'expected 3 events, no errors');
  const decision = record.events[1];
  assert(decision.v === '0.1' && decision.seq === 2 && decision.t === 1.94 && decision.kind === 'decision' &&
    decision.name === 'turn_complete' && decision.prob === 0.81 && decision.trigger === 'smart_turn', 'event fields altered');
  adapter.disconnect();
});
await test('events: a sequence gap fails the run via onError', async () => {
  const { adapter, socket } = await connected();
  const { record } = await startAcked(adapter, socket);
  socket.receive(runEvent(3));
  assert(record.errors.length === 1 && /sequence/i.test(record.errors[0]), 'sequence gap not surfaced');
  assert(record.events.length === 0, 'event delivered despite gap');
  adapter.disconnect();
});
await test('events: wrong message contract version fails the run', async () => {
  const { adapter, socket } = await connected();
  const { record } = await startAcked(adapter, socket);
  socket.receive(runEvent(1, { v: '0.2' }));
  assert(record.errors.length === 1 && /version/i.test(record.errors[0]), 'version mismatch not surfaced');
  adapter.disconnect();
});
await test('provenance: mock:true on a live-mode message fails the run', async () => {
  const { adapter, socket } = await connected();
  const { record } = await startAcked(adapter, socket);
  socket.receive(runEvent(1, { mock: true }));
  assert(record.errors.length === 1 && /mock provenance/i.test(record.errors[0]), 'live/mock mismatch not surfaced');
  adapter.disconnect();
});
await test('provenance: a mock-mode message missing mock:true fails the run', async () => {
  const { adapter, socket } = await connected({ '/v0/health': Object.assign({}, GOOD_HEALTH, { mock: true }) });
  const { record } = await startAcked(adapter, socket, { ack: { mock: true } });
  socket.receive(runEvent(1));
  assert(record.errors.length === 1 && /mock provenance/i.test(record.errors[0]), 'missing mock flag not surfaced');
  adapter.disconnect();
});
await test('events: unknown kind, invalid state and missing name are all rejected', async () => {
  for (const [patch, pattern] of [
    [{ kind: 'audio' }, /kind/i],
    [{ kind: 'state', state: 'shouting', name: undefined }, /state/i],
    [{ kind: 'info', name: '' }, /name/i],
  ]) {
    const { adapter, socket } = await connected();
    const { record } = await startAcked(adapter, socket);
    socket.receive(runEvent(1, patch));
    assert(record.errors.length === 1 && pattern.test(record.errors[0]), 'not rejected: ' + JSON.stringify(patch));
    adapter.disconnect();
  }
});
await test('events: out-of-range probability and negative time are rejected', async () => {
  for (const patch of [{ prob: 1.5 }, { t: -0.1 }]) {
    const { adapter, socket } = await connected();
    const { record } = await startAcked(adapter, socket);
    socket.receive(runEvent(1, patch));
    assert(record.errors.length === 1, 'not rejected: ' + JSON.stringify(patch));
    adapter.disconnect();
  }
});
await test('errors: a backend error message surfaces through onError', async () => {
  const { adapter, socket } = await connected();
  const { record } = await startAcked(adapter, socket);
  socket.receive({ v: '0.1', type: 'error', run_id: 'run-1', seq: -1, message: 'MOCK: engine unavailable' });
  assert(record.errors.length === 1 && /engine unavailable/.test(record.errors[0]), 'error message not surfaced');
  adapter.disconnect();
});
await test('identity: messages for an unknown run_id are ignored during an active run', async () => {
  const { adapter, socket } = await connected();
  const { record } = await startAcked(adapter, socket);
  socket.receive(runEvent(1, { run_id: 'someone-else' }));
  assert(record.events.length === 0 && record.errors.length === 0, 'foreign run message not ignored');
  socket.receive(runEvent(1));
  assert(record.events.length === 1, 'run did not continue after ignored message');
  adapter.disconnect();
});

/* ---------- run end, retirement, stop, disconnect ---------- */
await test('run_ended: delivers reason and summary to onEnd and ends the run', async () => {
  const { adapter, socket } = await connected();
  const { record } = await startAcked(adapter, socket);
  socket.receive({ v: '0.1', type: 'run_ended', run_id: 'run-1', seq: 1, t: 8.02, reason: 'completed',
    summary: { first_turn_complete_t: 1.94, overlap_s: 0.62 } });
  assert(record.ends.length === 1 && record.ends[0].reason === 'completed', 'run_ended not delivered');
  assert(record.ends[0].summary.overlap_s === 0.62, 'summary not passed through');
  assert(record.errors.length === 0, 'run_ended surfaced an error');
  adapter.disconnect();
});
await test('retirement: an ended run\'s late events never reach the next pending run', async () => {
  const { adapter, socket } = await connected();
  const { record } = await startAcked(adapter, socket);
  socket.receive({ v: '0.1', type: 'run_ended', run_id: 'run-1', seq: 1, t: 2, reason: 'completed', summary: {} });
  const second = recorder();
  const startPromise = adapter.start('patient', second.handlers, 'clip_a.wav');
  startPromise.catch(() => {});
  await tick();
  socket.receive(runEvent(2)); // stale run-1 message while run 2 is pending
  assert(second.errors.length === 0 && second.events.length === 0, 'stale retired-run message leaked');
  socket.receive(ack({ run_id: 'run-2', config: 'patient' }));
  const info = await startPromise;
  assert(info.runId === 'run-2', 'second run did not acknowledge');
  assert(record.events.length === 0 && record.errors.length === 0, 'first run received post-end callbacks');
  adapter.disconnect();
});
await test('stop: sends stop, retires the run id, closes the socket, drops late messages', async () => {
  const { adapter, socket } = await connected();
  const { record } = await startAcked(adapter, socket);
  adapter.stop();
  assert(socket.sent.some((m) => m.type === 'stop' && m.run_id === 'run-1'), 'stop command not sent');
  assert(socket.readyState === 3 && socket.onmessage === null, 'socket not closed and detached');
  socket.receive(runEvent(1));
  assert(record.events.length === 0 && record.errors.length === 0, 'late message after stop leaked');
  adapter.disconnect();
});
await test('stop: during a pending start rejects the start promise with AbortError', async () => {
  const { adapter } = await connected();
  const startPromise = adapter.start('stock', recorder().handlers, 'clip_a.wav');
  startPromise.catch(() => {});
  adapter.stop();
  const error = await rejects(startPromise, /cancelled/i);
  assert(error.name === 'AbortError', 'expected AbortError, got ' + error.name);
  adapter.disconnect();
});
await test('disconnect: clears discovery state and readiness', async () => {
  const { adapter } = await connected();
  adapter.disconnect();
  assert(adapter.getConfigurations().length === 0 && adapter.getSources().length === 0, 'discovery data retained');
  assert(adapter.connected === false, 'still marked connected');
  await rejects(adapter.start('stock', recorder().handlers, 'clip_a.wav'), /not connected/i);
});

/* ---------- blocked and preview adapters ---------- */
await test('blocked adapter: every arm unavailable and start always throws', async () => {
  const blocked = new Adapters.blocked();
  const configs = blocked.getConfigurations();
  assert(configs.length === 3 && configs.every((c) => c.available === false), 'blocked arm reported available');
  let threw = false;
  try { blocked.start('stock', recorder().handlers); } catch (_) { threw = true; }
  assert(threw, 'blocked start did not throw');
  assert(blocked.getSources().length === 0, 'blocked adapter listed sources');
});
await test('preview adapter: synthetic labeling on configurations and run identity', async () => {
  const preview = new Adapters.preview();
  assert(preview.getConfigurations().every((c) => c.available && /PREVIEW ONLY/.test(c.note)), 'preview note missing');
  const record = recorder();
  const info = preview.start('stock', record.handlers);
  assert(/^preview-/.test(info.runId) && /Synthetic preview/.test(info.runIdNote), 'preview run identity not labeled synthetic');
  assert(info.metadata.synthetic === true && /No recording/.test(info.metadata.source.source_id), 'metadata not labeled synthetic');
  assert(/synthetic fixture/i.test(info.sourceRecording), 'source recording line not labeled synthetic');
  preview.stop();
});
await test('preview adapter: stop cancels all pending fixture events', async () => {
  const preview = new Adapters.preview();
  const record = recorder();
  preview.start('stock', record.handlers);
  preview.stop();
  await wait(60);
  assert(record.events.length === 0 && record.ends.length === 0, 'fixture events fired after stop');
});

/* ---------- report ---------- */
const total = passed + failures.length;
console.log('\nadapter-checks: ' + passed + '/' + total + ' passed');
if (failures.length) {
  for (const failure of failures) { console.log('  failed: ' + failure.name); }
  process.exit(1);
}
