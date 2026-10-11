/* Authenticated PCM transport. Sample schedules are not acoustic measurements. */
'use strict';
(function () {
  function BrowserAudio(options) {
    options = options || {};
    this.context = options.context || new (window.AudioContext || window.webkitAudioContext)();
    this.output = this.context.createGain();
    this.output.connect(this.context.destination);
    this.onStatus = options.onStatus || function () {};
    this.nodes = new Set();
    this.cancelled = new Set();
    this.runId = null;
    this.epoch = null;
    this.finished = false;
    this.stats = { sourceSamples: 0, agentSamples: 0, lateSamples: 0, cancellations: 0 };
  }
  BrowserAudio.prototype.prepare = function () {
    var self = this;
    return this.context.resume().then(function () {
      if (self.context.state !== 'running') { throw new Error('Audio is blocked. Click Start again to enable sound.'); }
    });
  };
  BrowserAudio.prototype.setVolume = function (value) {
    if (Number.isFinite(value)) { this.output.gain.value = Math.max(0, Math.min(1, value)); }
  };
  BrowserAudio.prototype.begin = function (id) {
    this.stop(); this.runId = id; this.epoch = null; this.finished = false;
    this.cancelled.clear();
    this.stats = { sourceSamples: 0, agentSamples: 0, lateSamples: 0, cancellations: 0 };
    this.onStatus('Sound enabled. Waiting for recording…');
  };
  BrowserAudio.prototype.stop = function () {
    this.runId = null;
    this.nodes.forEach(function (entry) { entry.node.stop(); entry.node.disconnect(); entry.resolve(); });
    this.nodes.clear();
    this.onStatus('Audio stopped.');
  };
  BrowserAudio.prototype.receive = function (message) {
    if (!this.runId || message.run_id !== this.runId) { return; }
    if (message.sample_rate !== 16000) { throw new Error('Unsupported audio sample rate'); }
    var action = message.action, self = this;
    if (action === 'stop') { this.stop(); return; }
    if (action === 'finish') { this.finished = true; return; }
    if (this.finished) { throw new Error('Audio received after finish'); }
    if (!Number.isInteger(message.sample) || message.sample < 0 || message.sample > 16000 * 180) {
      throw new Error('Invalid audio sample offset');
    }
    if (action === 'cancel' || action === 'agent') {
      if (!Number.isInteger(message.generation) || message.generation < 0) { throw new Error('Invalid audio generation'); }
    }
    if (action === 'cancel') {
      this.cancelled.add(message.generation); this.stats.cancellations++;
      this.nodes.forEach(function (entry) {
        if (entry.generation === message.generation) {
          entry.node.stop(Math.max(self.context.currentTime, self.epoch + message.sample / 16000));
        }
      });
      return;
    }
    if (action !== 'source' && action !== 'agent') { throw new Error('Unknown browser audio action'); }
    if (action === 'source' && (this.epoch !== null || message.sample !== 0)) { throw new Error('Duplicate or displaced source audio'); }
    if (action === 'agent' && this.epoch === null) { throw new Error('Agent audio arrived before source'); }
    if (action === 'agent' && this.cancelled.has(message.generation)) { return; }
    var limit = action === 'source' ? 16000 * 90 : 8000;
    if (typeof message.pcm !== 'string' || message.pcm.length > Math.ceil(limit * 2 / 3) * 4) {
      throw new Error('Audio payload exceeds playback bounds');
    }
    var bytes = window.atob(message.pcm);
    if (!bytes.length || bytes.length % 2 || bytes.length / 2 > limit) { throw new Error('Invalid PCM payload'); }
    if (this.nodes.size >= 128) { throw new Error('Browser audio queue is full'); }
    var buffer = this.context.createBuffer(1, bytes.length / 2, 16000);
    var channel = buffer.getChannelData(0);
    for (var i = 0; i < channel.length; i++) {
      var sample = bytes.charCodeAt(i * 2) | bytes.charCodeAt(i * 2 + 1) << 8;
      channel[i] = (sample >= 32768 ? sample - 65536 : sample) / 32768;
    }
    if (action === 'source') { this.epoch = this.context.currentTime + 0.25; }
    var scheduled = this.epoch + message.sample / 16000;
    var late = Math.max(0, this.context.currentTime - scheduled);
    this.stats.lateSamples += Math.min(channel.length, Math.floor(late * 16000));
    this.stats[action === 'source' ? 'sourceSamples' : 'agentSamples'] += channel.length;
    if (late >= buffer.duration) { return; }
    var node = this.context.createBufferSource(); node.buffer = buffer; node.connect(this.output);
    var entry = { node: node, generation: action === 'agent' ? message.generation : null };
    entry.done = new Promise(function (resolve) { entry.resolve = resolve; });
    this.nodes.add(entry);
    node.onended = function () { self.nodes.delete(entry); node.disconnect(); entry.resolve(); };
    node.start(Math.max(this.context.currentTime, scheduled), late);
    this.onStatus('Playing recording and generated replies. Use Stop to silence both.');
  };
  BrowserAudio.prototype.drain = function () {
    var self = this;
    if (!this.finished) { return Promise.reject(new Error('Audio stream ended without a finish marker')); }
    return new Promise(function (resolve, reject) {
      var timer = setTimeout(function () {
        self.stop(); reject(new Error('Browser audio did not finish. Keep this tab active and retry.'));
      }, 10000);
      Promise.all(Array.from(self.nodes, function (entry) { return entry.done; })).then(function () {
        clearTimeout(timer); self.onStatus('Audio finished.'); resolve();
      });
    });
  };
  window.StutterTurnBrowserAudio = BrowserAudio;
}());
