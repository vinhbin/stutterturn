/* Proposed agent contract v0.1 transport. This UI plays no audio. */
'use strict';

var DEMO_ARMS = [
  { id: 'stock', label: 'STOCK', detail: 'Smart Turn v3.2, stock settings' },
  { id: 'stutterturn', label: 'STUTTERTURN', detail: 'Candidate requires a real exported model artifact' },
  { id: 'patient', label: 'PATIENT', detail: 'Longer wait with the stock model; not a trained model' },
];
function BlockedAdapter() {
  this.mode = 'blocked';
  this.sourceLabel = 'Disconnected — proposed v0.1 contract published; backend not connected';
}
BlockedAdapter.prototype.getConfigurations = function () {
  return DEMO_ARMS.map(function (arm) {
    return Object.assign({}, arm, { available: false, note: 'UNAVAILABLE — connect to discover configurations' });
  });
};
BlockedAdapter.prototype.getSources = function () { return []; };
BlockedAdapter.prototype.start = function () { throw new Error('Backend not connected. Connect explicitly, or enable the labeled development preview.'); };
BlockedAdapter.prototype.stop = function () {};
BlockedAdapter.prototype.disconnect = function () {};

// Every arm uses these same synthetic fixtures. Nothing here is model output,
// a recording, actual playback or benchmark evidence.
var PREVIEW_SCRIPT = [
  { t: 0, kind: 'info', name: 'speech_start', detail: 'Fixture started; no recording or audio' },
  { t: 0, kind: 'state', state: 'speaking' },
  { t: 1.2, kind: 'state', state: 'silence' },
  { t: 1.7, kind: 'decision', name: 'turn_incomplete', prob: 0.3 },
  { t: 1.9, kind: 'state', state: 'holding' },
  { t: 3, kind: 'state', state: 'speaking' },
  { t: 4.1, kind: 'state', state: 'silence' },
  { t: 4.6, kind: 'decision', name: 'turn_complete', trigger: 'smart_turn', prob: 0.97 },
  { t: 4.7, kind: 'info', name: 'response_requested' },
  { t: 4.8, kind: 'state', state: 'agent' },
  { t: 5.4, kind: 'audible', name: 'agent_audio_start', detail: 'Synthetic audio-start marker; nothing is playing' },
  { t: 5.7, kind: 'info', name: 'speaker_resumed' },
  { t: 5.7, kind: 'audible', name: 'overlap' },
  { t: 5.9, kind: 'audible', name: 'agent_audio_end', overlap_s: 0.2 },
  { t: 5.9, kind: 'info', name: 'cancelled', before_audible: false },
  { t: 6.2, kind: 'info', name: 'fixture_complete' },
];
function PreviewAdapter() {
  this.mode = 'preview';
  this.sourceLabel = 'Development preview — synthetic fixtures; no audio; not evidence';
  this._timers = [];
  this._runCounter = 0;
}
PreviewAdapter.prototype.getConfigurations = function () {
  return DEMO_ARMS.map(function (arm) {
    return Object.assign({}, arm, { available: true, note: 'PREVIEW ONLY — every label uses the same synthetic sequence' });
  });
};
PreviewAdapter.prototype.getSources = function () { return []; };
PreviewAdapter.prototype.start = function (configId, handlers) {
  this.stop();
  var runId = 'preview-' + (++this._runCounter);
  var metadata = { v: '0.1', type: 'run_started', run_id: runId, seq: 0, config: configId,
    model: 'preview-fixture', services: 'off', synthetic: true,
    source: { source_id: 'No recording — synthetic fixture', duration_s: 6.2, source_offset_s: 0 },
    params: { threshold: 0.5, fallback_s: 3 } };
  var self = this;
  PREVIEW_SCRIPT.forEach(function (step, index) {
    self._timers.push(setTimeout(function () {
      handlers.onEvent(Object.assign({ v: '0.1', type: 'event', run_id: runId, seq: index + 1,
        model: 'preview-fixture', synthetic: true, detail: 'Synthetic fixture — no audio or model output' }, step));
      if (index === PREVIEW_SCRIPT.length - 1) {
        handlers.onEnd({ v: '0.1', type: 'run_ended', run_id: runId, seq: index + 2,
          t: step.t, reason: 'completed', synthetic: true,
          summary: { synthetic: true, services: 'off', first_turn_complete_t: 4.6,
            first_agent_audio_t: 5.4, trigger: 'smart_turn', speaker_resumed_after_decision: true,
            cancelled: true, audible_interruption: true, overlap_s: 0.2, no_response: false,
            timeouts: [], chars_used: 0, turns: 1 } });
      }
    }, step.t * 1000));
  });
  return { runId: runId, runIdNote: 'Synthetic preview ID — not a backend run',
    sourceRecording: 'None — synthetic fixture; no audio or recording involved', metadata: metadata };
};
PreviewAdapter.prototype.stop = function () { this._timers.forEach(clearTimeout); this._timers = []; };
PreviewAdapter.prototype.disconnect = PreviewAdapter.prototype.stop;

function abortError() { var error = new Error('Operation cancelled'); error.name = 'AbortError'; return error; }
function isObject(value) { return value !== null && typeof value === 'object' && !Array.isArray(value); }
function nonempty(value) { return typeof value === 'string' && value.length > 0 && value.length <= 4096; }
function validTime(value) { return typeof value === 'number' && Number.isFinite(value) && value >= 0; }
function bounded(promise, milliseconds, signal, label) {
  return new Promise(function (resolve, reject) {
    var timer = setTimeout(function () { finish(new Error(label + ' timed out')); }, milliseconds);
    function cancel() { finish(abortError()); }
    function finish(error, value) {
      clearTimeout(timer);
      signal.removeEventListener('abort', cancel);
      if (error) { reject(error); } else { resolve(value); }
    }
    signal.addEventListener('abort', cancel, { once: true });
    if (signal.aborted) { cancel(); }
    Promise.resolve(promise).then(function (value) { finish(null, value); }, finish);
  });
}

function LiveAdapter(options) {
  options = options || {};
  var url = new URL(options.baseUrl || 'http://127.0.0.1:8765');
  if (!/^https?:$/.test(url.protocol) || url.username || url.password || url.search || url.hash || url.pathname !== '/') {
    throw new Error('Backend URL must be an HTTP(S) origin without credentials, path, query or fragment');
  }
  this.baseUrl = url.origin;
  this.mode = 'live';
  this.sourceLabel = 'Backend-reported events — playback unverified; this UI plays no audio';
  this.connected = false;
  this.onConnectionChange = options.onConnectionChange || null;
  this._fetch = options.fetch || (window.fetch && window.fetch.bind(window));
  this._WebSocket = options.WebSocket || window.WebSocket;
  this._connectTimeout = options.connectTimeoutMs || 5000;
  this._startTimeout = options.startTimeoutMs || 15000;
  this._configurations = [];
  this._sources = [];
  this._health = null;
  this._ready = false;
  this._socket = null;
  this._opening = null;
  this._openingReject = null;
  this._connectPromise = null;
  this._controller = null;
  this._run = null;
  this._retiredRuns = new Set();
}
LiveAdapter.prototype.getConfigurations = function () { return this._configurations.slice(); };
LiveAdapter.prototype.getSources = function () { return this._sources.slice(); };
LiveAdapter.prototype.connect = function () {
  if (this._connectPromise) { return this._connectPromise; }
  var self = this;
  this.disconnect();
  var controller = new AbortController();
  this._controller = controller;
  function get(path) {
    var request = Promise.resolve().then(function () {
      if (typeof self._fetch !== 'function') { throw new Error('Fetch is unavailable in this browser'); }
      return self._fetch(self.baseUrl + path, { signal: controller.signal, cache: 'no-store' });
    }).then(function (response) {
      if (!response.ok) { throw new Error(path + ': HTTP ' + response.status); }
      return response.json();
    });
    return bounded(request, self._connectTimeout, controller.signal, 'Backend discovery');
  }
  var operation = Promise.all([get('/v0/health'), get('/v0/configurations'), get('/v0/sources')]).then(function (results) {
    if (controller.signal.aborted) { throw abortError(); }
    var health = results[0], configs = results[1], sources = results[2];
    if (!isObject(health) || health.ok !== true || health.contract !== '0.1') {
      throw new Error('Unsupported backend health or contract version; expected 0.1');
    }
    var ids = new Set();
    if (!Array.isArray(configs) || !configs.every(function (config) {
      if (!isObject(config) || !nonempty(config.id) || !/^[a-zA-Z0-9._-]+$/.test(config.id) ||
          !nonempty(config.label) || typeof config.available !== 'boolean' || ids.has(config.id)) { return false; }
      ids.add(config.id); return true;
    })) { throw new Error('Invalid configuration discovery response'); }
    var files = new Set();
    if (!Array.isArray(sources) || !sources.every(function (source) {
      if (!isObject(source) || !nonempty(source.source_id) || !nonempty(source.file) ||
          /[/\\\u0000-\u001f]/.test(source.file) || !validTime(source.duration_s) || files.has(source.file)) { return false; }
      files.add(source.file); return true;
    })) { throw new Error('Invalid source discovery response'); }
    self._health = health;
    self._configurations = configs;
    self._sources = sources;
    self.mode = health.mock === true ? 'mock' : 'live';
    self.sourceLabel = health.mock === true
      ? 'DEVELOPMENT MOCK — synthetic transport events; no audio; not evidence'
      : 'Backend-reported events — playback unverified; this UI plays no audio';
    return self._openSocket();
  }).then(function () {
    if (controller.signal.aborted) { throw abortError(); }
    self._ready = true;
    return { configurations: self.getConfigurations(), sources: self.getSources(), health: self._health };
  }).catch(function (error) {
    if (self._controller === controller) {
      controller.abort(); self._closeSocket(); self._ready = false;
      self._configurations = []; self._sources = [];
    }
    throw error;
  });
  this._connectPromise = operation;
  operation.then(cleanup, cleanup);
  function cleanup() { if (self._connectPromise === operation) { self._connectPromise = null; } }
  return operation;
};
LiveAdapter.prototype._openSocket = function () {
  if (this._socket && this._socket.readyState === 1) { return Promise.resolve(); }
  if (this._opening) { return this._opening; }
  var self = this;
  var operation = new Promise(function (resolve, reject) {
    var socket;
    try { socket = new self._WebSocket(self.baseUrl.replace(/^http/, 'ws') + '/v0/ws'); }
    catch (error) { reject(error); return; }
    self._socket = socket;
    var timer = setTimeout(function () { fail(new Error('WebSocket connection timed out')); }, self._connectTimeout);
    function fail(error) {
      clearTimeout(timer); self._openingReject = null;
      reject(error); self._closeSocket(error.message); self._failRun(error);
    }
    self._openingReject = function (error) { clearTimeout(timer); reject(error); };
    socket.onopen = function () {
      if (self._socket !== socket) { return; }
      clearTimeout(timer); self._openingReject = null; self.connected = true;
      self._connectionChanged('connected'); resolve();
    };
    socket.onmessage = function (event) { if (self._socket === socket) { self._message(event.data); } };
    socket.onerror = function () { if (self._socket === socket) { fail(new Error('WebSocket connection failed')); } };
    socket.onclose = function () { if (self._socket === socket) { fail(new Error('Backend disconnected; reconnect explicitly before another run')); } };
  });
  this._opening = operation;
  operation.then(cleanup, cleanup);
  function cleanup() { if (self._opening === operation) { self._opening = null; } }
  return operation;
};
LiveAdapter.prototype._connectionChanged = function (reason) {
  if (typeof this.onConnectionChange === 'function') {
    this.onConnectionChange({ connected: this.connected, reason: reason });
  }
};
LiveAdapter.prototype._closeSocket = function (reason) {
  var socket = this._socket;
  this._socket = null; this.connected = false; this._opening = null;
  if (this._openingReject) {
    var reject = this._openingReject; this._openingReject = null; reject(abortError());
  }
  if (socket) {
    socket.onopen = socket.onmessage = socket.onerror = socket.onclose = null; socket.close();
    this._connectionChanged(reason || 'disconnected');
  }
};
LiveAdapter.prototype.start = function (configId, handlers, sourceId) {
  var self = this;
  if (!this._ready) { return Promise.reject(new Error('Backend not connected; connect before starting')); }
  if (this._run) { return Promise.reject(new Error('A run is already starting or active')); }
  var config = this._configurations.find(function (value) { return value.id === configId; });
  var source = this._sources.find(function (value) { return value.file === sourceId; });
  if (!config || !config.available) { return Promise.reject(new Error('Selected configuration is unavailable')); }
  if (!source) { return Promise.reject(new Error('Choose a recording from the backend source list')); }
  return new Promise(function (resolve, reject) {
    var run = { config: configId, source: source, handlers: handlers, resolve: resolve, reject: reject,
      pending: true, id: null, seq: -1 };
    self._run = run;
    run.timer = setTimeout(function () {
      if (self._run === run) { self._failRun(new Error('Run start acknowledgement timed out')); self._closeSocket(); }
    }, self._startTimeout);
    self._openSocket().then(function () {
      if (self._run !== run) { return; }
      self._socket.send(JSON.stringify({ type: 'start', config: configId, source: sourceId }));
    }).catch(function (error) { if (self._run === run) { self._failRun(error); self._closeSocket(); } });
  });
};
LiveAdapter.prototype._failRun = function (error) {
  var run = this._run; this._run = null;
  if (!run) { return; }
  if (run.id) { this._retiredRuns.add(run.id); }
  clearTimeout(run.timer);
  if (run.pending) { run.reject(error); }
  else if (run.handlers.onError) { run.handlers.onError(error.message || String(error)); }
};
LiveAdapter.prototype._message = function (data) {
  var run = this._run;
  if (!run) { return; }
  try {
    var message = JSON.parse(data);
    if (!isObject(message)) { throw new Error('Invalid backend message'); }
    // Another run's delayed messages never become evidence for this run.
    if (this._retiredRuns.has(message.run_id)) { return; }
    if (!run.pending && message.run_id !== run.id && message.run_id !== null) { return; }
    if (message.v !== '0.1') { throw new Error('Unsupported message contract version'); }
    if ((message.mock === true) !== (this.mode === 'mock')) { throw new Error('Mock provenance mismatch in backend message'); }
    if (message.type === 'error') {
      if (message.seq !== -1 || !nonempty(message.message)) { throw new Error('Invalid backend error message'); }
      throw new Error(message.message);
    }
    if (!Number.isInteger(message.seq) || message.seq !== run.seq + 1) { throw new Error('Invalid run event sequence; stream may be incomplete or out of order'); }
    if (run.pending) {
      if (message.type !== 'run_started' || !nonempty(message.run_id)) { throw new Error('Expected run_started contract acknowledgement'); }
      if (message.config !== run.config) { throw new Error('Acknowledged configuration does not match requested configuration'); }
      if (!isObject(message.source) || (message.source.source_id !== run.source.source_id && message.source.source_id !== run.source.file) ||
          !validTime(message.source.duration_s) || !validTime(message.source.source_offset_s)) { throw new Error('Acknowledged source does not match requested recording'); }
      run.id = message.run_id; run.seq = message.seq; run.pending = false; clearTimeout(run.timer);
      run.resolve({ runId: message.run_id, runIdNote: this.mode === 'mock' ? 'MOCK run — no audio; not evidence' : 'Backend run — playback unverified',
        sourceRecording: message.source.source_id + ' (' + message.source.duration_s + ' s; offset ' + message.source.source_offset_s + ' s)', metadata: message });
      return;
    }
    if (message.run_id !== run.id || !validTime(message.t)) { throw new Error('Invalid run identity or event time'); }
    if (message.type === 'event') {
      if (!['state', 'decision', 'audible', 'info'].includes(message.kind)) { throw new Error('Unsupported event kind'); }
      if (message.kind === 'state' && !['speaking', 'silence', 'holding', 'agent'].includes(message.state)) { throw new Error('Invalid caller/agent state'); }
      if (message.kind !== 'state' && !nonempty(message.name)) { throw new Error('Event name is required by contract v0.1'); }
      if (message.prob != null && (typeof message.prob !== 'number' || !Number.isFinite(message.prob) || message.prob < 0 || message.prob > 1)) { throw new Error('Invalid event probability'); }
      run.seq = message.seq;
      if (run.handlers.onEvent) { run.handlers.onEvent(message); }
    } else if (message.type === 'run_ended') {
      if (!nonempty(message.reason) || !isObject(message.summary)) { throw new Error('Invalid run summary'); }
      this._retiredRuns.add(run.id);
      this._run = null;
      if (run.handlers.onEnd) { run.handlers.onEnd(message); }
    } else { throw new Error('Unexpected backend message type'); }
  } catch (error) { this._failRun(error); this._closeSocket(); }
};
LiveAdapter.prototype.stop = function () {
  var run = this._run;
  if (!run) { return; }
  this._run = null; clearTimeout(run.timer);
  if (run.id) { this._retiredRuns.add(run.id); }
  if (run.id && this._socket && this._socket.readyState === 1) {
    try { this._socket.send(JSON.stringify({ type: 'stop', run_id: run.id })); } catch (_) { /* Socket already closed. */ }
  }
  if (run.pending) { run.reject(abortError()); }
  // An unacknowledged run has no ID. Closing the socket isolates its late ack.
  this._closeSocket('stopped');
};
LiveAdapter.prototype.disconnect = function () {
  if (this._controller) { this._controller.abort(); this._controller = null; }
  this._connectPromise = null; this.stop(); this._closeSocket(); this._ready = false;
  this._configurations = []; this._sources = [];
};
window.StutterTurnAdapters = { blocked: BlockedAdapter, preview: PreviewAdapter, live: LiveAdapter };
