/* StutterTurn console. The adapter owns transport; this file owns display state. */
'use strict';

(function () {
  var $ = function (id) { return document.getElementById(id); };
  var el = {};
  [
    'preview-banner', 'connection-chip', 'status-banner', 'config-group',
    'backend-url', 'btn-retry', 'btn-connect', 'btn-disconnect', 'source-select', 'source-note',
    'btn-start', 'btn-stop', 'btn-reset', 'run-phase', 'run-id', 'run-config',
    'run-source', 'start-note', 'source-label', 'current-state', 'state-strip',
    'first-decision', 'first-audible', 'decision-gap', 'event-body', 'event-scroll',
    'event-caption', 'preview-toggle', 'metadata-body', 'summary-body',
    'summary-note', 'run-alert', 'audio-note', 'audio-status', 'audio-volume', 'reply-text', 'agent-contract-status',
    'model-contract-status', 'tally', 'tally-note', 'tally-config', 'run-clock', 'timeline-mode', 'timeline-scroll-hint'
  ].forEach(function (id) { el[id] = $(id); });

  var hosted = window.location.protocol === 'https:' && !['localhost', '127.0.0.1', '[::1]'].includes(window.location.hostname);
  var state = {
    adapter: new window.StutterTurnAdapters.blocked(),
    configs: [], sources: [], health: null, discovered: false, selectedConfig: 'stock',
    runPhase: 'idle', run: null, connecting: false, connectToken: null, reconnectOnStart: false
  };
  var EMPTY = '—';
  var DEFAULT_SOURCE = 'No source recording loaded. Source identity and provenance must come from the backend.';

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

  function setTally(name, label, note) {
    el['tally'].dataset.state = name;
    el['current-state'].className = 'state-badge state-' + name;
    el['current-state'].textContent = label;
    el['tally-note'].textContent = note;
  }

  function clockText(t) {
    var value = Math.max(0, t || 0);
    return String(Math.floor(value / 60)).padStart(2, '0') + ':' + (value % 60).toFixed(2).padStart(5, '0');
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
      mock ? (isConnected() ? 'MOCK BACKEND — SYNTHETIC' : 'MOCK BACKEND — DISCONNECTED') : isConnected() ? (state.health && state.health.browser_audio === 'pcm16-v1' ? 'BACKEND CONNECTED — BROWSER AUDIO' : 'BACKEND CONNECTED — PLAYBACK UNVERIFIED') : state.reconnectOnStart ? 'READY TO REPLAY' : state.discovered ? 'BACKEND DISCONNECTED' : hosted ? 'NOT CONNECTED' : 'LIVE INTEGRATION: BLOCKED';
    el['run-source'].textContent = state.adapter.sourceLabel || 'Backend not connected';
    el['audio-note'].textContent = isSynthetic()
      ? 'Synthetic timing only. No audio or benchmark evidence.'
      : state.health && state.health.browser_audio === 'pcm16-v1'
          ? 'Browser sound enabled on Start. Timing uses a server sample schedule plus a 250 ms browser buffer; it is not measured speaker output.'
          : 'Backend-reported audio receipt. This backend does not provide browser audio.';
    el['timeline-mode'].textContent = isSynthetic() ? 'SYNTHETIC · NO AUDIO' : state.run ? 'REPORTED EVENTS' : 'Awaiting events';
    el['agent-contract-status'].textContent = isConnected()
      ? (mock ? 'Mock transport connected; real replay acceptance pending.' : (state.health && state.health.browser_audio === 'pcm16-v1' ? 'Browser audio transport connected. Timings are server schedules.' : 'Transport connected; browser audio unavailable.'))
      : 'Agent contract v0.1; backend disconnected. Real audio playback acceptance pending.';
    var candidate = state.configs.find(function (cfg) { return cfg.id === 'candidate' || cfg.id === 'stutterturn'; });
    el['model-contract-status'].textContent = preview ? 'Preview labels only; no model artifact is exercised.' :
      candidate && candidate.available ? 'Candidate reported available by the backend; exact model is recorded per run.' :
        'Candidate unavailable unless the backend reports an exported artifact.';
    if (state.connecting) { setStatus('warn', 'Connecting and loading configurations and sources…'); }
    else if (preview) { setStatus('warn', 'Synthetic preview ready. Choose a configuration, then start a fresh run.'); }
    else if (state.reconnectOnStart && state.discovered) { setStatus('ok', 'Ready for another replay. Start reconnects automatically.'); }
    else if (state.discovered && !isConnected()) { setStatus('warn', 'Connection lost. Use Retry connection to reconnect. ' + (mock ? 'Mock data is synthetic, with no audio or benchmark evidence.' : 'Audio playback remains unverified.')); }
    else if (mock) { setStatus('warn', 'Mock backend connected. Choose a synthetic scenario to exercise the console.'); }
    else if (isConnected()) { setStatus('ok', 'Connected. Choose a recording and model, then Start to hear the replay.'); }
    else { setStatus('warn', hosted ? 'Not connected. Use Retry connection to load recordings and models.' : 'Live integration blocked. Connect a backend or enable development preview in the control desk.'); }
  }

  function refreshControls() {
    var locked = isActive() || state.connecting;
    var cfg = selectedConfig();
    var preview = state.adapter.mode === 'preview';
    el['tally-config'].textContent = state.run ? 'Run configuration: ' + state.run.configLabel :
      cfg && cfg.available ? 'Next run: ' + cfg.label : 'No available configuration';
    var ready = !!(cfg && cfg.available && (preview || (state.discovered && selectedSource())));
    el['btn-start'].disabled = locked || !ready;
    el['btn-start'].firstChild.textContent = state.runPhase === 'starting' ? 'Starting… ' : 'Start fresh run ';
    el['btn-stop'].disabled = !isActive();
    el['btn-retry'].hidden = preview || isConnected() || state.reconnectOnStart;
    el['btn-retry'].disabled = locked;
    el['btn-retry'].textContent = state.connecting ? 'Connecting…' : 'Retry connection';
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
    el['start-note'].textContent = state.connecting ? 'Connecting. Reset or Disconnect to cancel.' :
      isActive() ? 'Source and configuration locked. Stop or Reset to cancel.' :
      !cfg || !cfg.available ? (hosted ? 'Recordings and models load when connected. Use Retry connection if needed.' : 'Connect a backend or enable development preview.') :
      !preview && !state.sources.length ? 'Start is disabled: the backend has no available source recordings.' :
      'Select a source recording before starting.';
  }

  function renderConfigs() {
    state.configs = state.adapter.getConfigurations();
    if (!state.presetConfigApplied && state.configs.some(function (cfg) { return cfg.available; })) {
      var requestedConfig = new URLSearchParams(location.search).get('config');
      if (state.configs.some(function (cfg) { return cfg.id === requestedConfig && cfg.available; })) {
        state.selectedConfig = requestedConfig;
      }
      state.presetConfigApplied = true;
    }
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
      note.textContent = [cfg.detail, !cfg.available ? cfg.note : null].filter(Boolean).join(' — ');
      label.title = [cfg.detail, cfg.note].filter(Boolean).join(' — ');
      label.append(input, name, key, badge, note);
      el['config-group'].appendChild(label);
    });
  }

  function renderSources() {
    var previous = el['source-select'].value;
    state.sources = typeof state.adapter.getSources === 'function' ? state.adapter.getSources() : [];
    if (!state.presetSourceApplied && state.sources.length) {
      var requestedSource = new URLSearchParams(location.search).get('source');
      if (state.sources.some(function (source) { return source.file === requestedSource; })) { previous = requestedSource; }
      state.presetSourceApplied = true;
    }
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
    el['state-strip'].dataset.running = isActive() ? 'true' : 'false';
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
        'Services OFF — model-only; no response audio. Playback unverified.';
    }
  }

  function clearEvents() {
    el['event-scroll'].tabIndex = -1;
    var row = document.createElement('tr'); row.className = 'empty-row';
    var cell = document.createElement('td'); cell.colSpan = 6; cell.textContent = 'No events. Start a fresh run.';
    row.appendChild(cell); el['event-body'].replaceChildren(row);
    renderTimeline(null);
    setTally('none', 'no run', 'Choose a source and configuration. Then start a fresh run.');
    el['run-clock'].textContent = clockText(0);
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
  function timelineData(run) {
    var data = { caller: [], agent: [], decisions: [], overlaps: [], holding: [] };
    if (!run) { return data; }
    var caller = null; var audio = null; var overlap = null; var holding = null;
    var audioEnds = new Set(run.events.filter(function (evt) { return evt.name === 'agent_audio_end'; }).map(function (evt) { return evt.t; }));
    function callerState(name, t) {
      if (caller && caller.state === name) { return; }
      if (caller) { caller.end = t; data.caller.push(caller); }
      caller = { state: name, start: t, end: null };
    }
    // Engine events may report an earlier source timestamp after service work.
    // Sequence order remains the stable tie-breaker for equal timestamps.
    run.events.slice().sort(function (a, b) { return a.t - b.t; }).forEach(function (evt) {
      if ((evt.name === 'turn_incomplete' || (evt.kind === 'state' && evt.state === 'holding')) && !holding) { holding = { start: evt.t, end: null }; }
      if (holding && (evt.name === 'turn_complete' || evt.name === 'speech_start' || evt.name === 'speaker_resumed' || (evt.kind === 'state' && evt.state === 'speaking'))) {
        holding.end = evt.t; data.holding.push(holding); holding = null;
      }
      if (evt.name === 'speech_start' || evt.name === 'speaker_resumed' || (evt.kind === 'state' && evt.state === 'speaking')) { callerState('speaking', evt.t); }
      // The engine also emits display silence after agent audio ends. That alone
      // cannot close caller speech; require speech_stop when those times coincide.
      if (evt.name === 'speech_stop' || (evt.kind === 'state' && evt.state === 'silence' && !audioEnds.has(evt.t))) { callerState('silence', evt.t); }
      if (evt.name === 'agent_audio_start' && !audio) { audio = { state: 'agent', start: evt.t, end: null }; }
      if (evt.name === 'overlap' && !overlap) { overlap = { start: evt.t, end: null }; }
      if (evt.name === 'speech_stop' && overlap) {
        overlap.end = evt.t; data.overlaps.push(overlap); overlap = null;
      }
      if (evt.name === 'agent_audio_end') {
        if (audio) { audio.end = evt.t; data.agent.push(audio); audio = null; }
        if (overlap) { overlap.end = evt.t; data.overlaps.push(overlap); overlap = null; }
      }
      if (evt.name === 'turn_complete' || evt.name === 'turn_incomplete') { data.decisions.push(evt); }
    });
    if (caller) { data.caller.push(caller); }
    if (audio) { data.agent.push(audio); }
    if (overlap) { data.overlaps.push(overlap); }
    if (holding) { data.holding.push(holding); }
    return data;
  }

  function renderTimeline(run) {
    var data = timelineData(run);
    var latest = run ? run.observedT : 0;
    var horizon = Math.ceil(Math.max(6, run ? run.duration || 0 : 0, latest) * 2) / 2;
    var step = Math.max(0.5, Math.ceil(horizon / 200 * 2) / 2);
    var canvas = document.createElement('div'); canvas.className = 'timeline-canvas';
    canvas.style.minWidth = Math.min(1800, Math.max(580, horizon * 60 + 70)) + 'px';
    var accessible = [];
    function row(className, labelText) {
      var item = document.createElement('div'); item.className = className;
      var label = document.createElement('span'); label.className = 'lane-label'; label.textContent = labelText;
      var plot = document.createElement('div'); plot.className = 'timeline-plot';
      item.append(label, plot); return { element: item, plot: plot };
    }
    function position(node, start, end) {
      node.style.left = (start / horizon * 100) + '%';
      node.style.width = (Math.max(0, end - start) / horizon * 100) + '%';
    }
    var ruler = row('ruler-row', 'SECONDS');
    for (var t = 0; t <= horizon + 0.001; t += step) {
      var tick = document.createElement('span'); tick.className = 'ruler-tick';
      tick.style.left = (t / horizon * 100) + '%'; tick.dataset.t = String(t);
      var number = document.createElement('span'); number.textContent = t.toFixed(t % 1 ? 1 : 0);
      if (t === 0) { tick.classList.add('first'); }
      if (Math.abs(t - horizon) < 0.001) { tick.classList.add('last'); }
      tick.appendChild(number); ruler.plot.appendChild(tick);
    }
    canvas.appendChild(ruler.element);
    var decisions = row('decision-row', 'DECISION');
    data.decisions.forEach(function (evt, index) {
      var flag = document.createElement('span');
      flag.className = 'decision-flag ' + (evt.name === 'turn_complete' ? 'complete' : 'incomplete');
      flag.dataset.t = String(evt.t); flag.dataset.name = evt.name;
      flag.style.left = (evt.t / horizon * 100) + '%';
      flag.style.top = (index % 2 ? 27 : 2) + 'px';
      flag.textContent = evt.name === 'turn_complete' ? 'COMPLETE' : 'WAIT';
      if (typeof evt.prob === 'number' && isFinite(evt.prob)) { flag.textContent += ' ' + evt.prob.toFixed(2); }
      flag.title = evt.name + ' at ' + seconds(evt.t) + (evt.trigger ? ' · ' + triggerText(evt.trigger) : '');
      accessible.push(flag.title); decisions.plot.appendChild(flag);
    });
    if (!data.decisions.length) {
      var undecided = document.createElement('span'); undecided.className = 'track-empty'; undecided.textContent = 'No decision'; decisions.plot.appendChild(undecided);
    }
    canvas.appendChild(decisions.element);
    var tracks = document.createElement('div'); tracks.className = 'timeline-tracks';
    ['caller', 'agent'].forEach(function (laneName) {
      var track = row('lane-row', laneName.toUpperCase());
      track.plot.id = laneName + '-lane'; track.plot.classList.add('timeline-lane'); track.plot.dataset.lane = laneName;
      track.plot.style.backgroundSize = (step / horizon * 100) + '% 100%';
      data[laneName].forEach(function (interval) {
        var segment = document.createElement('span'); segment.className = 'timeline-segment state-' + interval.state;
        var end = interval.end === null ? Math.max(interval.start, latest) : interval.end;
        segment.dataset.start = String(interval.start); segment.dataset.end = interval.end === null ? '' : String(interval.end);
        segment.dataset.state = interval.state;
        if (interval.end === null) { segment.dataset.open = 'true'; }
        position(segment, interval.start, end);
        var label = interval.state === 'speaking' ? 'Speaking' : interval.state === 'agent' ? (isSynthetic() ? 'Synthetic audio' : 'Reported audio') : 'Silence';
        segment.textContent = label;
        segment.title = label + ' from ' + seconds(interval.start) + (interval.end === null ? '; end not reported' : ' to ' + seconds(interval.end));
        accessible.push(segment.title); track.plot.appendChild(segment);
      });
      if (!data[laneName].length) {
        var empty = document.createElement('span'); empty.className = 'track-empty' + (!run && laneName === 'caller' ? ' strip-empty' : '');
        empty.textContent = laneName === 'caller' ? 'No caller state events' : 'No reported audio'; track.plot.appendChild(empty);
      }
      if (laneName === 'caller') {
        data.holding.forEach(function (interval) {
          var span = document.createElement('span'); span.className = 'holding-span';
          span.dataset.start = String(interval.start); span.dataset.end = interval.end === null ? '' : String(interval.end);
          if (interval.end === null) { span.dataset.open = 'true'; }
          position(span, interval.start, interval.end === null ? Math.max(interval.start, latest) : interval.end);
          span.title = (isSynthetic() ? 'Synthetic holding' : 'Holding reported') + ' from ' + seconds(interval.start) +
            (interval.end === null ? '; end not reported' : ' to ' + seconds(interval.end));
          accessible.push(span.title); track.plot.appendChild(span);
        });
      }
      tracks.appendChild(track.element);
    });
    var collisions = document.createElement('div'); collisions.className = 'collision-overlay';
    data.overlaps.forEach(function (interval) {
      var band = document.createElement('span');
      band.className = interval.end === null ? 'collision-onset' : 'collision-band';
      band.dataset.start = String(interval.start); band.dataset.end = interval.end === null ? '' : String(interval.end);
      position(band, interval.start, interval.end === null ? interval.start : interval.end);
      band.title = (isSynthetic() ? 'Synthetic overlap' : 'Reported overlap') + ' at ' + seconds(interval.start) +
        (interval.end === null ? '; end not reported' : ' to ' + seconds(interval.end) + ' · ' + seconds(interval.end - interval.start));
      if (interval.end !== null) {
        var label = document.createElement('span'); label.className = 'collision-label';
        label.textContent = (isSynthetic() ? 'FIXTURE ' : 'REPORTED ') + seconds(interval.end - interval.start);
        band.appendChild(label);
      }
      accessible.push(band.title); collisions.appendChild(band);
    });
    tracks.appendChild(collisions); canvas.appendChild(tracks);
    el['state-strip'].replaceChildren(canvas);
    el['state-strip'].setAttribute('aria-label', (isSynthetic() ? 'Synthetic event timeline. No audio. ' : 'Backend-reported timeline. Playback unverified. ') +
      (accessible.length ? accessible.join('. ') : 'No state events yet.'));
    el['state-strip'].tabIndex = 0;
    updateTimelineScrollHint();
  }

  function updateTimelineScrollHint() {
    el['timeline-scroll-hint'].hidden = el['state-strip'].scrollWidth <= el['state-strip'].clientWidth + 1;
  }

  function recordTimelineEvent(run, evt) {
    if (typeof evt.t !== 'number' || !isFinite(evt.t) || evt.t < 0) { return; }
    run.events.push(evt); run.observedT = Math.max(run.observedT, evt.t);
    el['run-clock'].textContent = clockText(run.observedT);
    if (evt.kind === 'state' && ['speaking', 'silence', 'holding', 'agent'].indexOf(evt.state) >= 0) {
      run.lastState = evt.state;
      if (!run.hadOverlap) {
        var note = { speaking: 'Caller speaking. The turn stays open.', silence: 'Caller silence reported. Waiting for the next decision.',
          holding: isSynthetic() ? 'Synthetic incomplete-turn event. Giving the caller room.' : 'The model said incomplete. Giving the caller room.',
          agent: 'Agent state reported. Audio timing is shown separately.' }[evt.state];
        setTally(evt.state, evt.state, note);
      }
    }
    if (evt.name === 'speaker_resumed' && !run.hadOverlap) { setTally('speaking', 'speaking', 'Caller resumed after a completion decision.'); }
    if (evt.name === 'agent_audio_start' && !run.hadOverlap) { setTally('agent', 'agent', isSynthetic() ? 'Synthetic audio-start marker. No audio is playing.' : 'Generated reply started on the server timeline.'); }
    if (evt.name === 'overlap') {
      run.hadOverlap = true;
      setTally('overlap', 'interrupted', isSynthetic() ? 'SYNTHETIC OVERLAP · no audio, not evidence.' : 'OVERLAP REPORTED · audible playback unverified.');
    }
    renderTimeline(run);
  }

  function timingValue(target, value, note) {
    var number = document.createElement('span'); number.className = 'timing-value'; number.textContent = value;
    var qualifier = document.createElement('span'); qualifier.className = 'timing-qualifier'; qualifier.textContent = note ? ' ' + note : '';
    target.replaceChildren(number, qualifier);
  }
  function updateTimingSummary(run) {
    timingValue(el['first-decision'], run.firstDecision === null ? EMPTY : seconds(run.firstDecision),
      run.firstDecision === null ? '' : (isSynthetic() ? 'Synthetic · ' : '') + triggerText(run.trigger));
    timingValue(el['first-audible'], run.firstAudible === null ? EMPTY : seconds(run.firstAudible),
      run.firstAudible === null ? '' : isSynthetic() ? 'Synthetic · no audio' : 'Reported · playback unverified');
    timingValue(el['decision-gap'], run.firstDecision !== null && run.firstAudible !== null ? seconds(run.firstAudible - run.firstDecision) : EMPTY,
      run.firstDecision === null || run.firstAudible === null ? '' : isSynthetic() ? 'Synthetic timing' : 'Backend timing');
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
    el['reply-text'].textContent = 'No reply yet.';
    el['run-id'].textContent = EMPTY; el['run-config'].textContent = EMPTY;
    el['event-caption'].textContent = 'Events for the current run. A fresh run clears this table.';
    el['source-label'].textContent = DEFAULT_SOURCE;
    setRunPhase('idle');
  }
  function disconnectCurrent() {
    state.connectToken = null; state.connecting = false;
    stopAdapter();
    if (typeof state.adapter.disconnect === 'function') { state.adapter.disconnect(); }
    state.health = null; state.discovered = false; state.reconnectOnStart = false;
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
    try { adapter = new window.StutterTurnAdapters.live({ baseUrl: el['backend-url'].value.trim(), connectTimeoutMs: hosted ? 15000 : 5000,
      onAudioStatus: function (message) { el['audio-status'].textContent = message; } });
      adapter.setVolume(Number(el['audio-volume'].value)); }
    catch (error) { setAdapter('blocked'); setStatus('error', 'Connection error: ' + valueText(error.message || error)); return; }
    state.adapter = adapter;
    adapter.onConnectionChange = function (connection) {
      if (state.adapter !== adapter) { return; }
      state.reconnectOnStart = !connection.connected && connection.reason === 'stopped';
      if (state.connecting || isActive()) { return; }
      refreshChrome(); refreshControls();
      if (!connection.connected && connection.reason !== 'stopped' && connection.reason !== 'disconnected') {
        setStatus('error', 'Backend disconnected: ' + connection.reason + '. Use Retry connection to reconnect.');
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
    el['reply-text'].textContent = 'No reply yet.';
    var token = {};
    var run = { token: token, configId: cfg.id, configLabel: cfg.label,
      firstDecision: null, firstAudible: null, trigger: null, id: null, idNote: '',
      events: [], observedT: 0, duration: 0, lastState: null, hadOverlap: false };
    state.run = run;
    el['run-id'].textContent = 'Waiting for backend run identity…';
    el['run-config'].textContent = cfg.label + (cfg.detail ? ' — ' + cfg.detail : '');
    el['source-label'].textContent = source ? 'Requested source: ' + (source.source_id || source.file) : 'Synthetic fixture — no recording and no audio.';
    setRunPhase('starting'); setTally('none', 'starting', 'Waiting for the backend to confirm a fresh run.');
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
        recordTimelineEvent(run, evt);
        if (evt.name === 'agent_audio_start' && evt.detail) { el['reply-text'].textContent = evt.detail; }
        if (evt.name === 'turn_complete' && run.firstDecision === null && typeof evt.t === 'number') {
          run.firstDecision = evt.t; run.trigger = evt.trigger || null;
        }
        if (evt.name === 'agent_audio_start' && run.firstAudible === null && typeof evt.t === 'number') { run.firstAudible = evt.t; }
        updateTimingSummary(run); showEventAlert(evt);
      }),
      onEnd: guard(function (ended) {
        stopAdapter(); renderSummary(ended); setRunPhase('ended');
        if (ended && typeof ended.t === 'number') { run.observedT = Math.max(run.observedT, ended.t); }
        el['run-clock'].textContent = clockText(run.observedT); renderTimeline(run);
        if (run.hadOverlap || (ended && ended.summary && ended.summary.audible_interruption === true)) {
          setTally('overlap', 'interrupted', (isSynthetic() ? 'SYNTHETIC OVERLAP · no audio, not evidence.' : 'OVERLAP REPORTED · playback unverified.') +
            (run.lastState ? ' Final state: ' + run.lastState + '.' : ' Run ended.'));
        } else { setTally('none', 'run ended', 'Final report below. ' + (isSynthetic() ? 'Synthetic fixture; no audio.' : 'Speaker playback remains unverified.')); }
        setStatus(isSynthetic() ? 'warn' : 'ok', isSynthetic() ? 'Synthetic run ended. No audio or benchmark evidence.' : 'Run ended. Final values below are server-reported timings, not measured speaker output.');
      }),
      onError: guard(function (message) {
        stopAdapter(); setRunPhase('error'); refreshChrome();
        setTally('none', 'run error', 'Reset or start a fresh run to try again.');
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
      var metadata = info.metadata || {};
      run.duration = metadata.source && typeof metadata.source.duration_s === 'number' ? metadata.source.duration_s : 0;
      refreshChrome(); renderMetadata(info.metadata); renderTimeline(run);
      setTally('none', 'ready', 'Run confirmed. Waiting for source events.');
      setRunPhase('running'); started = true;
      pending.forEach(function (deliver) { deliver(); }); pending = [];
    } catch (error) {
      if (state.run !== run || run.token !== token) { return; }
      stopAdapter(); setRunPhase('error'); refreshChrome();
      setTally('none', 'start failed', 'Review the connection and try a fresh run.');
      el['run-id'].textContent = 'Not assigned';
      setStatus('error', 'Start failed: ' + valueText(error.message || error));
      el['summary-note'].textContent = 'Run did not start. No final summary received.';
    }
  }
  function stopRun() {
    if (!isActive()) { return; }
    stopAdapter(); setRunPhase('stopped'); refreshChrome();
    setTally('none', 'stopped', 'Run cancelled. The last reported events stay on the timeline.');
    el['summary-note'].textContent = 'Stopped locally. No final summary accepted after cancellation.';
    setStatus('warn', 'Run stopped. Start a fresh run to replay the selected source.');
  }
  function resetAll() {
    if (state.connecting) { setAdapter('blocked'); return; }
    stopAdapter(); clearRun(); refreshChrome(); refreshControls();
  }

  el['audio-volume'].addEventListener('input', function () {
    if (state.adapter.setVolume) { state.adapter.setVolume(Number(el['audio-volume'].value)); }
  });
  el['btn-retry'].addEventListener('click', connectBackend);
  el['btn-connect'].addEventListener('click', connectBackend);
  el['btn-disconnect'].addEventListener('click', function () { setAdapter('blocked'); });
  el['source-select'].addEventListener('change', renderSourceNote);
  el['preview-toggle'].addEventListener('change', function () { setAdapter(el['preview-toggle'].checked ? 'preview' : 'blocked'); });
  el['btn-start'].addEventListener('click', startRun);
  el['btn-stop'].addEventListener('click', stopRun);
  el['btn-reset'].addEventListener('click', resetAll);
  window.addEventListener('resize', updateTimelineScrollHint);
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
  if (hosted) {
    document.querySelector('.connection-settings').open = false;
    document.querySelector('.connection-settings summary').textContent = 'Advanced settings';
    el['backend-url'].value = window.location.origin;
  }
  renderConfigs(); renderSources(); clearRun(); refreshChrome(); refreshControls();
  if (hosted) { connectBackend(); }
})();
