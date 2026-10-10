/* StutterTurn console. The adapter owns transport; this file owns display state. */
'use strict';

(function () {
  var $ = function (id) { return document.getElementById(id); };
  var el = {};
  [
    'preview-banner', 'connection-chip', 'status-banner', 'config-group',
    'backend-url', 'btn-connect', 'btn-disconnect', 'source-select', 'source-note',
    'btn-start', 'btn-stop', 'btn-reset', 'run-phase', 'run-id', 'run-config',
    'run-source', 'start-note', 'source-label', 'current-state', 'state-strip',
    'first-decision', 'first-audible', 'decision-gap', 'event-body', 'event-scroll',
    'event-caption', 'preview-toggle', 'metadata-body', 'summary-body',
    'summary-note', 'run-alert', 'audio-note', 'agent-contract-status',
    'model-contract-status'
  ].forEach(function (id) { el[id] = $(id); });

  var state = {
    adapter: new window.StutterTurnAdapters.blocked(),
    configs: [], sources: [], health: null, discovered: false, selectedConfig: 'stock',
    runPhase: 'idle', run: null, connecting: false, connectToken: null
  };
  var EMPTY = '—';
  var DEFAULT_SOURCE = 'No source recording loaded. Source identity and provenance must come from the backend. No audio plays in this console.';

  function isSynthetic() {
    return state.adapter.mode === 'preview' || state.adapter.mode === 'mock' || !!(state.health && state.health.mock);
  }
  function isConnected() { return !!state.adapter.connected; }
  function isActive() { return state.runPhase === 'starting' || state.runPhase === 'running'; }
  function selectedConfig() {
    return state.configs.find(function (cfg) { return cfg.id === state.selectedConfig; }) || null;
  }
  function selectedSource() {
    return state.sources.find(function (source) { return source.file === el['source-select'].value; }) || null;
  }
  function fmtT(value) {
    return typeof value === 'number' && isFinite(value) ? value.toFixed(2) : EMPTY;
  }
  function seconds(value) { return fmtT(value) === EMPTY ? 'Not reported' : fmtT(value) + ' s'; }
  function valueText(value) {
    if (value === undefined || value === null) { return 'Not reported'; }
    if (typeof value === 'boolean') { return value ? 'Yes' : 'No'; }
    if (Array.isArray(value)) { return value.length ? value.map(valueText).join(', ') : 'None reported'; }
    return typeof value === 'object' ? JSON.stringify(value) : String(value);
  }
  function triggerText(trigger) {
    if (trigger === 'smart_turn') { return 'Model decision (smart_turn)'; }
    if (trigger === 'fallback_timeout') { return 'Silence fallback (fallback_timeout)'; }
    return valueText(trigger);
  }
  function setStatus(kind, message) {
    el['status-banner'].className = 'status-banner ' + kind;
    el['status-banner'].textContent = message;
  }

  function refreshChrome() {
    var preview = state.adapter.mode === 'preview';
    var mock = !preview && isSynthetic();
    el['preview-banner'].hidden = !isSynthetic();
    el['preview-banner'].textContent = (preview ? 'DEVELOPMENT PREVIEW' : 'MOCK BACKEND') +
      ' — synthetic events. No audio. No real recording is played. Not model output or benchmark evidence.';
    el['preview-toggle'].checked = preview;
    el['connection-chip'].className = 'chip ' + (isSynthetic() ? 'chip-preview' : isConnected() ? 'chip-live' : 'chip-blocked');
    el['connection-chip'].textContent = state.connecting ? 'CONNECTING…' : preview ? 'DEVELOPMENT PREVIEW — NOT LIVE' :
      mock ? (isConnected() ? 'MOCK BACKEND — SYNTHETIC' : 'MOCK BACKEND — DISCONNECTED') : isConnected() ? 'BACKEND CONNECTED — PLAYBACK UNVERIFIED' : state.discovered ? 'BACKEND DISCONNECTED' : 'LIVE INTEGRATION: BLOCKED';
    el['run-source'].textContent = state.adapter.sourceLabel || 'Backend not connected';
    el['audio-note'].textContent = isSynthetic()
      ? 'Synthetic timing only. No audio plays; even overlap and interruption events are fixtures, never evidence.'
      : 'Audio timestamps are backend-reported. The current engine reports audio receipt, not verified speaker playback. No audio plays in this console.';
    el['agent-contract-status'].textContent = isConnected()
      ? (mock ? 'Mock transport connected; real replay acceptance pending.' : 'Transport connected; real audio playback acceptance pending.')
      : 'Proposed v0.1 contract; real server and replay acceptance pending.';
    var candidate = state.configs.find(function (cfg) { return cfg.id === 'candidate' || cfg.id === 'stutterturn'; });
    el['model-contract-status'].textContent = preview ? 'Preview labels only; no model artifact is exercised.' :
      candidate && candidate.available ? 'Candidate reported available by the backend; exact model is recorded per run.' :
        'Candidate unavailable unless the backend reports an exported artifact.';
    if (state.connecting) { setStatus('warn', 'Connecting to backend and loading configurations and sources…'); }
    else if (preview) { setStatus('warn', 'Development preview: synthetic fixture only. No audio, no model behavior, no benchmark evidence.'); }
    else if (state.discovered && !isConnected()) { setStatus('warn', 'Backend disconnected. Start a fresh run to reconnect, or use Connect to reload sources. ' + (mock ? 'Mock data is synthetic, with no audio or benchmark evidence.' : 'Audio playback remains unverified.')); }
    else if (mock) { setStatus('warn', 'Mock backend connected: synthetic transport test only. No real audio or model behavior; not evidence.'); }
    else if (isConnected()) { setStatus('ok', 'Backend connected. Select a source and configuration for a fresh run. Audio playback remains unverified.'); }
    else { setStatus('warn', 'Live integration is blocked until a backend is connected. Connect to the proposed v0.1 service or enable the labeled development preview.'); }
  }

  function refreshControls() {
    var locked = isActive() || state.connecting;
    var cfg = selectedConfig();
    var preview = state.adapter.mode === 'preview';
    var ready = !!(cfg && cfg.available && (preview || (state.discovered && selectedSource())));
    el['btn-start'].disabled = locked || !ready;
    el['btn-start'].firstChild.textContent = state.runPhase === 'starting' ? 'Starting… ' : 'Start fresh run ';
    el['btn-stop'].disabled = !isActive();
    el['btn-connect'].disabled = locked || isConnected();
    el['btn-connect'].textContent = state.connecting ? 'Connecting…' : 'Connect';
    el['btn-disconnect'].disabled = !state.connecting && !isConnected();
    el['backend-url'].disabled = locked || isConnected();
    el['source-select'].disabled = locked || !state.discovered || !state.sources.length;
    el['config-group'].querySelectorAll('input').forEach(function (input) {
      var config = state.configs.find(function (item) { return item.id === input.value; });
      input.disabled = locked || !config || !config.available;
    });
    el['start-note'].hidden = ready && !locked;
    el['start-note'].textContent = state.connecting ? 'Wait for the connection, or cancel with Disconnect or Reset.' :
      isActive() ? 'Source and configuration are locked for this run. Stop, Reset or Disconnect cancels it.' :
      !cfg || !cfg.available ? 'Start is disabled: no available configuration. Connect a backend or enable development preview.' :
      !preview && !state.sources.length ? 'Start is disabled: the backend has no available source recordings.' :
      'Select a source recording before starting.';
  }

  function renderConfigs() {
    state.configs = state.adapter.getConfigurations();
    var chosen = selectedConfig();
    if (!chosen || !chosen.available) {
      var available = state.configs.find(function (cfg) { return cfg.available; });
      state.selectedConfig = available ? available.id : chosen ? chosen.id : '';
    }
    el['config-group'].querySelectorAll('.config-option').forEach(function (node) { node.remove(); });
    state.configs.forEach(function (cfg, index) {
      var label = document.createElement('label');
      label.className = 'config-option' + (cfg.available ? '' : ' unavailable');
      var input = document.createElement('input');
      input.type = 'radio'; input.name = 'config'; input.value = cfg.id;
      input.checked = cfg.id === state.selectedConfig;
      input.addEventListener('change', function () {
        if (input.checked && !isActive() && !state.connecting) { state.selectedConfig = cfg.id; refreshControls(); }
      });
      var name = document.createElement('span'); name.className = 'cfg-label'; name.textContent = cfg.label;
      var key = document.createElement('kbd'); key.textContent = String(index + 1);
      var badge = document.createElement('span');
      badge.className = 'badge ' + (!cfg.available ? 'badge-unavailable' : isSynthetic() ? 'badge-preview' : 'badge-available');
      badge.textContent = !cfg.available ? 'unavailable' : isSynthetic() ? 'synthetic only' : 'available';
      var note = document.createElement('span'); note.className = 'cfg-note';
      note.textContent = [cfg.detail, cfg.note].filter(Boolean).join(' — ');
      label.append(input, name, key, badge, note);
      el['config-group'].appendChild(label);
    });
  }

  function renderSources() {
    var previous = el['source-select'].value;
    state.sources = typeof state.adapter.getSources === 'function' ? state.adapter.getSources() : [];
    el['source-select'].replaceChildren();
    if (!state.sources.length) {
      var empty = document.createElement('option'); empty.value = '';
      empty.textContent = state.adapter.mode === 'preview' ? 'No recording — synthetic fixture' : 'No backend sources available';
      el['source-select'].appendChild(empty);
    }
    state.sources.forEach(function (source) {
      var option = document.createElement('option'); option.value = source.file;
      option.textContent = (source.source_id || source.file) +
        (typeof source.duration_s === 'number' ? ' · ' + seconds(source.duration_s) : '') +
        (source.category ? ' · ' + source.category : '');
      el['source-select'].appendChild(option);
    });
    if (state.sources.some(function (source) { return source.file === previous; })) { el['source-select'].value = previous; }
    renderSourceNote();
  }

  function renderSourceNote() {
    var source = selectedSource();
    el['source-note'].textContent = source ? (source.rights_note || 'Recording rights/provenance note not supplied by the backend.') :
      state.adapter.mode === 'preview' ? 'The preview contains no audio and no recording.' : 'The source list comes from the connected backend.';
    refreshControls();
  }
  function setRunPhase(phase) {
    state.runPhase = phase;
    el['run-phase'].textContent = phase;
    refreshControls();
  }
  function renderPairs(target, rows) {
    target.replaceChildren();
    rows.forEach(function (row) {
      var group = document.createElement('div');
      var term = document.createElement('dt'); term.textContent = row[0];
      var value = document.createElement('dd'); value.textContent = valueText(row[1]);
      group.append(term, value); target.appendChild(group);
    });
  }

  function renderMetadata(metadata) {
    if (!metadata) { el['metadata-body'].replaceChildren(); return; }
    var source = metadata.source || {};
    renderPairs(el['metadata-body'], [
      ['Backend configuration ID', metadata.config], ['Model', metadata.model],
      ['Model SHA-256', metadata.model_sha256], ['Parameters', metadata.params],
      ['Services', metadata.services === 'off' ? 'OFF — model-only; no response audio' : metadata.services],
      ['Source ID', source.source_id], ['Source duration', seconds(source.duration_s)],
      ['Source offset', seconds(source.source_offset_s)], ['Backend commit', metadata.commit],
      ['Run time origin (UTC)', metadata.t0_wall], ['Contract version', metadata.v]
    ]);
    if (metadata.services === 'off') {
      el['audio-note'].textContent = (isSynthetic() ? 'Synthetic run. ' : '') +
        'Services OFF — model-only run; no response audio. Audio playback is unverified.';
    }
  }

  function clearEvents() {
    el['event-scroll'].tabIndex = -1;
    var row = document.createElement('tr'); row.className = 'empty-row';
    var cell = document.createElement('td'); cell.colSpan = 6; cell.textContent = 'No events. Start a fresh run.';
    row.appendChild(cell); el['event-body'].replaceChildren(row);
    var empty = document.createElement('span'); empty.className = 'strip-empty'; empty.textContent = 'No state events yet.';
    el['state-strip'].replaceChildren(empty);
    el['state-strip'].setAttribute('aria-label', 'No state events yet.');
    el['current-state'].textContent = 'no run'; el['current-state'].className = 'state-badge state-none';
    ['first-decision', 'first-audible', 'decision-gap'].forEach(function (id) { el[id].textContent = EMPTY; });
    el['run-alert'].textContent = ''; el['run-alert'].className = 'run-alert';
    el['metadata-body'].replaceChildren(); el['summary-body'].replaceChildren();
    el['summary-note'].textContent = 'No final summary received.';
  }

  function eventDetail(evt) {
    var details = [];
    if (evt.detail) { details.push(evt.detail); }
    if (evt.state) { details.push('state → ' + evt.state); }
    if (evt.trigger) { details.push(triggerText(evt.trigger)); }
    if (typeof evt.threshold === 'number') { details.push('threshold ' + evt.threshold); }
    if (typeof evt.before_audible === 'boolean') { details.push('before_audible: ' + evt.before_audible); }
    if (evt.service) { details.push('service: ' + evt.service); }
    if (typeof evt.overlap_s === 'number') { details.push('overlap: ' + seconds(evt.overlap_s)); }
    return details.join(' · ');
  }
  function appendEventRow(run, evt) {
    el['event-scroll'].tabIndex = 0;
    var empty = el['event-body'].querySelector('.empty-row'); if (empty) { empty.remove(); }
    var row = document.createElement('tr');
    row.className = ['state', 'decision', 'audible', 'info', 'error'].indexOf(evt.kind) >= 0 ? 'kind-' + evt.kind : 'kind-info';
    var kind = evt.name || evt.kind || 'event';
    if (evt.name === 'agent_audio_start') { kind += ' (reported)'; }
    [run.id + ' · ' + run.configLabel, fmtT(evt.t), kind, eventDetail(evt),
      typeof evt.prob === 'number' ? evt.prob.toFixed(2) : EMPTY, evt.model || EMPTY
    ].forEach(function (content) {
      var cell = document.createElement('td'); cell.textContent = content; row.appendChild(cell);
    });
    el['event-body'].appendChild(row);
  }
  function appendStateSegment(run, evt) {
    if (['speaking', 'silence', 'holding', 'agent'].indexOf(evt.state) < 0) { return; }
    var empty = el['state-strip'].querySelector('.strip-empty'); if (empty) { empty.remove(); }
    var previous = el['state-strip'].lastElementChild;
    if (previous && typeof run.lastT === 'number' && typeof evt.t === 'number') {
      previous.style.flexGrow = String(Math.max(evt.t - run.lastT, 0.2));
    }
    var segment = document.createElement('span'); segment.className = 'strip-seg state-' + evt.state;
    segment.style.flexGrow = '0.4'; segment.textContent = evt.state + ' @' + fmtT(evt.t) + 's';
    el['state-strip'].appendChild(segment); run.lastT = evt.t;
    el['state-strip'].setAttribute('aria-label', 'Turn states: ' + el['state-strip'].textContent);
    el['current-state'].textContent = evt.state; el['current-state'].className = 'state-badge state-' + evt.state;
  }
  function updateTimingSummary(run) {
    var qualifier = isSynthetic() ? ' (synthetic)' : '';
    el['first-decision'].textContent = run.firstDecision === null ? EMPTY : seconds(run.firstDecision) + qualifier + ' · ' + triggerText(run.trigger);
    el['first-audible'].textContent = run.firstAudible === null ? EMPTY : seconds(run.firstAudible) +
      (isSynthetic() ? ' (synthetic; no audio)' : ' (backend-reported; playback unverified)');
    el['decision-gap'].textContent = run.firstDecision !== null && run.firstAudible !== null
      ? seconds(run.firstAudible - run.firstDecision) + qualifier : EMPTY;
  }
  function showEventAlert(evt) {
    var message = '';
    if (evt.name === 'overlap') { message = isSynthetic() ? 'Synthetic overlap event — no audio, not interruption evidence.' : 'Backend reports overlap — speaker playback and audible interruption remain unverified.'; }
    if (evt.name === 'speaker_resumed') { message = 'Caller speech resumed after a completion decision.'; }
    if (evt.name === 'cancelled') { message = 'Response cancelled' + (evt.before_audible === true ? ' before reported audio start.' : evt.before_audible === false ? ' after reported audio start.' : '.'); }
    if (evt.name === 'no_response') { message = 'No response reported for this run.'; }
    if (evt.name === 'timeout') { message = 'Service timeout: ' + (evt.service || 'unspecified service') + '.'; }
    if (!message) { return; }
    el['run-alert'].className = 'run-alert ' + (evt.name === 'overlap' || evt.name === 'timeout' ? 'error' : 'warn');
    el['run-alert'].textContent = (isSynthetic() && evt.name !== 'overlap' ? 'Synthetic event: ' : '') + message;
  }
  function renderSummary(ended) {
    var summary = ended && ended.summary;
    if (!summary) {
      el['summary-note'].textContent = isSynthetic() ? 'Synthetic sequence ended. No backend result or benchmark evidence.' : 'Run ended without a final summary.';
      return;
    }
    el['summary-note'].textContent = (isSynthetic() ? 'SYNTHETIC SUMMARY — not evidence. ' : 'Backend-reported summary; playback unverified. ') +
      'End reason: ' + valueText(ended.reason) + '. Log: ' + valueText(ended.log);
    renderPairs(el['summary-body'], [
      ['First turn complete', seconds(summary.first_turn_complete_t)], ['Decision trigger', triggerText(summary.trigger)],
      ['First agent audio (reported)', seconds(summary.first_agent_audio_t)], ['LLM latency', seconds(summary.llm_latency_s)],
      ['TTS first audio latency', seconds(summary.tts_first_audio_s)], ['Caller resumed after decision', summary.speaker_resumed_after_decision],
      ['Audible interruption (reported; unverified)', summary.audible_interruption], ['Overlap (reported)', seconds(summary.overlap_s)],
      ['Cancelled', summary.cancelled], ['No response', summary.no_response], ['Timeouts', summary.timeouts],
      ['Services', summary.services === 'off' ? 'OFF — model-only; no response audio' : summary.services]
    ]);
  }

  function stopAdapter() {
    // A stop may synchronously call a handler. Invalidate before cleanup.
    if (state.run) { state.run.token = null; }
    state.adapter.stop();
  }
  function clearRun() {
    state.run = null; clearEvents();
    el['run-id'].textContent = EMPTY; el['run-config'].textContent = EMPTY;
    el['event-caption'].textContent = 'Events for the current run. A fresh run clears this table.';
    el['source-label'].textContent = DEFAULT_SOURCE;
    setRunPhase('idle');
  }
  function disconnectCurrent() {
    state.connectToken = null; state.connecting = false;
    stopAdapter();
    if (typeof state.adapter.disconnect === 'function') { state.adapter.disconnect(); }
    state.health = null; state.discovered = false;
  }
  function setAdapter(mode) {
    disconnectCurrent();
    state.adapter = new window.StutterTurnAdapters[mode]();
    renderConfigs(); renderSources(); clearRun(); refreshChrome(); refreshControls();
  }

  async function connectBackend() {
    if (state.connecting || isConnected() || isActive()) { return; }
    disconnectCurrent();
    var adapter;
    try { adapter = new window.StutterTurnAdapters.live({ baseUrl: el['backend-url'].value.trim() }); }
    catch (error) { setAdapter('blocked'); setStatus('error', 'Connection error: ' + valueText(error.message || error)); return; }
    state.adapter = adapter;
    adapter.onConnectionChange = function (connection) {
      if (state.adapter !== adapter || state.connecting || isActive()) { return; }
      refreshChrome(); refreshControls();
      if (!connection.connected && connection.reason !== 'stopped' && connection.reason !== 'disconnected') {
        setStatus('error', 'Backend disconnected: ' + connection.reason + '. Start a fresh run to reconnect.');
      }
    };
    var token = {}; state.connectToken = token; state.connecting = true;
    renderConfigs(); renderSources(); clearRun(); refreshChrome(); refreshControls();
    try {
      var info = await adapter.connect();
      if (state.connectToken !== token || state.adapter !== adapter) { return; }
      state.connectToken = null; state.connecting = false; state.health = info.health || null; state.discovered = true;
      renderConfigs(); renderSources(); refreshChrome(); refreshControls();
    } catch (error) {
      if (state.connectToken !== token || state.adapter !== adapter) { return; }
      setAdapter('blocked');
      setStatus('error', 'Connection failed: ' + valueText(error.message || error));
    }
  }

  async function startRun() {
    if (isActive() || state.connecting) { return; }
    var cfg = selectedConfig(); var source = selectedSource();
    if (!cfg || !cfg.available || (state.adapter.mode !== 'preview' && (!state.discovered || !source))) {
      setStatus('error', 'Cannot start: connect a backend and select an available configuration and source, or enable development preview.'); return;
    }
    stopAdapter(); clearEvents(); refreshChrome();
    var token = {};
    var run = { token: token, configId: cfg.id, configLabel: cfg.label, lastT: null,
      firstDecision: null, firstAudible: null, trigger: null, id: null, idNote: '' };
    state.run = run;
    el['run-id'].textContent = 'Waiting for backend run identity…';
    el['run-config'].textContent = cfg.label + (cfg.detail ? ' — ' + cfg.detail : '');
    el['source-label'].textContent = source ? 'Requested source: ' + (source.source_id || source.file) : 'Synthetic fixture — no recording and no audio.';
    setRunPhase('starting');
    var started = false; var pending = [];
    var guard = function (fn) {
      return function dispatch(value) {
        if (state.run !== run || run.token !== token) { return; }
        if (!started) { pending.push(function () { dispatch(value); }); return; }
        fn(value);
      };
    };
    var handlers = {
      onEvent: guard(function (evt) {
        appendEventRow(run, evt);
        if (evt.kind === 'state' && evt.state) { appendStateSegment(run, evt); }
        if (evt.name === 'turn_complete' && run.firstDecision === null && typeof evt.t === 'number') {
          run.firstDecision = evt.t; run.trigger = evt.trigger || null;
        }
        if (evt.name === 'agent_audio_start' && run.firstAudible === null && typeof evt.t === 'number') { run.firstAudible = evt.t; }
        updateTimingSummary(run); showEventAlert(evt);
      }),
      onEnd: guard(function (ended) {
        stopAdapter(); renderSummary(ended); setRunPhase('ended');
        el['current-state'].textContent = 'run ended'; el['current-state'].className = 'state-badge state-none';
        setStatus(isSynthetic() ? 'warn' : 'ok', isSynthetic() ? 'Synthetic run ended. No audio or benchmark evidence.' : 'Run ended. Final values below are backend-reported; audio playback is unverified.');
      }),
      onError: guard(function (message) {
        stopAdapter(); setRunPhase('error'); refreshChrome();
        setStatus('error', 'Run error: ' + String(message));
        appendEventRow(run, { t: NaN, kind: 'error', detail: String(message) });
        el['summary-note'].textContent = 'Run failed. No final summary received.';
      })
    };
    try {
      var info = await state.adapter.start(cfg.id, handlers, source ? source.file : undefined);
      if (state.run !== run || run.token !== token) { return; }
      run.id = info.runId; run.idNote = info.runIdNote || '';
      el['run-id'].textContent = run.id + (run.idNote ? ' (' + run.idNote + ')' : '');
      el['event-caption'].textContent = 'Events attributed to run ' + run.id + ', configuration ' + cfg.label + '. A fresh run clears this table.';
      if (info.sourceRecording) { el['source-label'].textContent = 'Source: ' + info.sourceRecording; }
      refreshChrome(); renderMetadata(info.metadata);
      setRunPhase('running'); started = true;
      pending.forEach(function (deliver) { deliver(); }); pending = [];
    } catch (error) {
      if (state.run !== run || run.token !== token) { return; }
      stopAdapter(); setRunPhase('error'); refreshChrome();
      el['run-id'].textContent = 'Not assigned';
      setStatus('error', 'Start failed: ' + valueText(error.message || error));
      el['summary-note'].textContent = 'Run did not start. No final summary received.';
    }
  }
  function stopRun() {
    if (!isActive()) { return; }
    stopAdapter(); setRunPhase('stopped'); refreshChrome();
    el['current-state'].textContent = 'stopped'; el['current-state'].className = 'state-badge state-none';
    el['summary-note'].textContent = 'Stopped locally. No final summary accepted after cancellation.';
    setStatus('warn', 'Run stopped. Start a fresh run to replay the selected source.');
  }
  function resetAll() {
    if (state.connecting) { setAdapter('blocked'); return; }
    stopAdapter(); clearRun(); refreshChrome(); refreshControls();
  }

  el['btn-connect'].addEventListener('click', connectBackend);
  el['btn-disconnect'].addEventListener('click', function () { setAdapter('blocked'); });
  el['source-select'].addEventListener('change', renderSourceNote);
  el['preview-toggle'].addEventListener('change', function () { setAdapter(el['preview-toggle'].checked ? 'preview' : 'blocked'); });
  el['btn-start'].addEventListener('click', startRun);
  el['btn-stop'].addEventListener('click', stopRun);
  el['btn-reset'].addEventListener('click', resetAll);
  document.addEventListener('keydown', function (event) {
    if (event.ctrlKey || event.metaKey || event.altKey || event.repeat) { return; }
    var target = event.target;
    if (target && (target.isContentEditable || /^(SELECT|TEXTAREA)$/.test(target.tagName))) { return; }
    if (target && target.tagName === 'INPUT' && ['radio', 'checkbox', 'button'].indexOf(target.type) < 0) { return; }
    var key = event.key.toLowerCase();
    if (key === 's') { event.preventDefault(); startRun(); }
    else if (key === 'x') { event.preventDefault(); stopRun(); }
    else if (key === 'r') { event.preventDefault(); resetAll(); }
    else if (key === 'p') { event.preventDefault(); setAdapter(state.adapter.mode === 'preview' ? 'blocked' : 'preview'); }
    else if (/^[1-9]$/.test(key) && !isActive() && !state.connecting) {
      var cfg = state.configs[Number(key) - 1];
      if (cfg && cfg.available) {
        event.preventDefault(); state.selectedConfig = cfg.id;
        el['config-group'].querySelectorAll('input').forEach(function (input) {
          input.checked = input.value === cfg.id;
          if (input.checked) { input.focus(); }
        });
        refreshControls();
      }
    }
  });
  renderConfigs(); renderSources(); clearRun(); refreshChrome(); refreshControls();
})();
