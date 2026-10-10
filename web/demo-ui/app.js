/* StutterTurn demo UI — page logic. Depends on adapter.js (window.StutterTurnAdapters). */

'use strict';

(function () {
  var $ = function (id) { return document.getElementById(id); };

  var el = {
    previewBanner: $('preview-banner'),
    connectionChip: $('connection-chip'),
    statusBanner: $('status-banner'),
    configGroup: $('config-group'),
    btnStart: $('btn-start'),
    btnStop: $('btn-stop'),
    btnReset: $('btn-reset'),
    runPhase: $('run-phase'),
    runId: $('run-id'),
    runConfig: $('run-config'),
    runSource: $('run-source'),
    startNote: $('start-note'),
    sourceLabel: $('source-label'),
    currentState: $('current-state'),
    stateStrip: $('state-strip'),
    firstDecision: $('first-decision'),
    firstAudible: $('first-audible'),
    decisionGap: $('decision-gap'),
    eventBody: $('event-body'),
    eventCaption: $('event-caption'),
    previewToggle: $('preview-toggle'),
  };

  var DEFAULT_SOURCE_HTML = el.sourceLabel.innerHTML;
  var DEFAULT_STATUS_HTML = el.statusBanner.innerHTML;

  var state = {
    adapter: new window.StutterTurnAdapters.blocked(),
    configs: [],
    selectedConfig: 'stock',
    runPhase: 'idle',          // idle | running | stopped | ended | error
    run: null,                 // {id, idNote, configId, configLabel, token, lastT, firstDecision, firstAudible}
  };

  /* ---------- status + chrome ---------- */

  // For trusted static markup authored in this file only.
  function setStatus(kind, html) {
    el.statusBanner.className = 'status-banner ' + kind;
    el.statusBanner.innerHTML = html;
  }

  // For any runtime-supplied string (adapter/backend errors): rendered as text,
  // never as HTML, so a future LiveAdapter can relay backend messages safely.
  function setStatusText(kind, text) {
    el.statusBanner.className = 'status-banner ' + kind;
    el.statusBanner.textContent = text;
  }

  function refreshChrome() {
    var preview = state.adapter.mode === 'preview';
    el.previewBanner.hidden = !preview;
    el.previewToggle.checked = preview;
    if (preview) {
      el.connectionChip.textContent = 'DEVELOPMENT PREVIEW — NOT LIVE';
      el.connectionChip.className = 'chip chip-preview';
      setStatus('warn',
        'Development preview active: events below are a <strong>synthetic fixture</strong> — ' +
        'not live agent output and not benchmark evidence. Live integration remains ' +
        '<strong>BLOCKED</strong> on <code>agent/CONTRACT.md</code>.');
    } else {
      el.connectionChip.textContent = 'LIVE INTEGRATION: BLOCKED';
      el.connectionChip.className = 'chip chip-blocked';
      setStatus('warn', DEFAULT_STATUS_HTML);
    }
    el.runSource.textContent = state.adapter.sourceLabel;
  }

  /* ---------- configuration group ---------- */

  function renderConfigs() {
    state.configs = state.adapter.getConfigurations();
    el.configGroup.querySelectorAll('.config-option').forEach(function (n) { n.remove(); });

    state.configs.forEach(function (cfg, i) {
      var labelEl = document.createElement('label');
      labelEl.className = 'config-option' + (cfg.available ? '' : ' unavailable');

      var input = document.createElement('input');
      input.type = 'radio';
      input.name = 'config';
      input.value = cfg.id;
      input.checked = cfg.id === state.selectedConfig;
      input.disabled = !cfg.available || state.runPhase === 'running';
      input.addEventListener('change', function () {
        if (input.checked) { state.selectedConfig = cfg.id; }
      });

      var badge = document.createElement('span');
      badge.className = 'badge ' + (cfg.available
        ? (state.adapter.mode === 'preview' ? 'badge-preview' : 'badge-available')
        : 'badge-unavailable');
      badge.textContent = cfg.available
        ? (state.adapter.mode === 'preview' ? 'preview only' : 'available')
        : 'unavailable';

      var text = document.createElement('span');
      text.className = 'cfg-label';
      text.textContent = ' ' + cfg.label + ' ';

      var note = document.createElement('span');
      note.className = 'cfg-note';
      note.textContent = cfg.detail + ' — ' + cfg.note;

      var key = document.createElement('kbd');
      key.textContent = String(i + 1);

      labelEl.appendChild(input);
      labelEl.appendChild(text);
      labelEl.appendChild(key);
      labelEl.appendChild(badge);
      labelEl.appendChild(note);
      el.configGroup.appendChild(labelEl);
    });

    // If the selected arm is unavailable, fall back to the first available one
    // (or keep the selection visually, disabled, when nothing is available).
    var selected = state.configs.filter(function (c) { return c.id === state.selectedConfig; })[0];
    if ((!selected || !selected.available)) {
      var firstAvail = state.configs.filter(function (c) { return c.available; })[0];
      if (firstAvail) {
        state.selectedConfig = firstAvail.id;
        var radio = el.configGroup.querySelector('input[value="' + firstAvail.id + '"]');
        if (radio) { radio.checked = true; }
      }
    }
  }

  function selectedConfig() {
    return state.configs.filter(function (c) { return c.id === state.selectedConfig; })[0] || null;
  }

  /* ---------- run lifecycle ---------- */

  function setRunPhase(phase) {
    state.runPhase = phase;
    el.runPhase.textContent = phase;
    var running = phase === 'running';
    el.btnStop.disabled = !running;
    var anyAvailable = state.configs.some(function (c) { return c.available; });
    el.btnStart.disabled = running || !anyAvailable;
    el.startNote.hidden = anyAvailable;
    el.configGroup.querySelectorAll('input[type=radio]').forEach(function (r) {
      var cfg = state.configs.filter(function (c) { return c.id === r.value; })[0];
      r.disabled = running || !cfg || !cfg.available;
    });
  }

  function fmtT(t) {
    return (typeof t === 'number' && isFinite(t)) ? t.toFixed(2) : '—';
  }

  function clearEvents() {
    el.eventBody.innerHTML =
      '<tr class="empty-row"><td colspan="6">No events. Start a fresh run.</td></tr>';
    el.stateStrip.innerHTML = '<span class="strip-empty">No state events yet.</span>';
    el.currentState.textContent = 'no run';
    el.currentState.className = 'state-badge state-none';
    el.firstDecision.textContent = '—';
    el.firstAudible.textContent = '—';
    el.decisionGap.textContent = '—';
  }

  function appendEventRow(run, evt) {
    var empty = el.eventBody.querySelector('.empty-row');
    if (empty) { empty.remove(); }
    var tr = document.createElement('tr');
    tr.className = 'kind-' + evt.kind;
    var kindLabel = {
      state: 'STATE',
      decision: 'DECISION (internal)',
      audible: 'AUDIBLE RESPONSE',
      info: 'INFO',
      error: 'ERROR',
    }[evt.kind] || evt.kind.toUpperCase();
    var cells = [
      run.id + ' · ' + run.configLabel,
      fmtT(evt.t),
      kindLabel,
      evt.detail || (evt.state ? 'state → ' + evt.state : ''),
      (typeof evt.prob === 'number') ? evt.prob.toFixed(2) : '—',
      evt.model || '—',
    ];
    cells.forEach(function (c) {
      var td = document.createElement('td');
      td.textContent = c;
      tr.appendChild(td);
    });
    el.eventBody.appendChild(tr);
  }

  function appendStateSegment(run, evt) {
    var emptyNote = el.stateStrip.querySelector('.strip-empty');
    if (emptyNote) { emptyNote.remove(); }
    // Grow the previous segment in proportion to how long its state lasted.
    var prev = el.stateStrip.lastElementChild;
    if (prev && typeof run.lastT === 'number') {
      var dur = Math.max(evt.t - run.lastT, 0.2);
      prev.style.flexGrow = String(dur);
    }
    var seg = document.createElement('span');
    seg.className = 'strip-seg state-' + evt.state;
    seg.style.flexGrow = '0.4';
    seg.textContent = evt.state + ' @' + fmtT(evt.t) + 's';
    el.stateStrip.appendChild(seg);
    run.lastT = evt.t;

    el.currentState.textContent = evt.state;
    el.currentState.className = 'state-badge state-' + evt.state;
  }

  function updateTimingSummary(run) {
    el.firstDecision.textContent = run.firstDecision === null
      ? '—' : fmtT(run.firstDecision) + ' s (model output — not necessarily audible)';
    el.firstAudible.textContent = run.firstAudible === null
      ? '—' : fmtT(run.firstAudible) + ' s (what the caller hears)';
    el.decisionGap.textContent =
      (run.firstDecision !== null && run.firstAudible !== null)
        ? fmtT(run.firstAudible - run.firstDecision) + ' s'
        : '—';
  }

  function startRun() {
    var cfg = selectedConfig();
    if (!cfg || !cfg.available) {
      setStatus('error',
        'Cannot start: the selected configuration is unavailable. ' +
        (state.adapter.mode === 'blocked'
          ? 'Live integration is <strong>BLOCKED</strong> on <code>agent/CONTRACT.md</code>; ' +
            'enable the development preview to exercise the display.'
          : 'Pick an available configuration.'));
      return;
    }
    if (state.runPhase === 'running') { return; }

    // A fresh run resets prior events (handoff requirement).
    state.adapter.stop();
    clearEvents();

    var token = {};
    var run = {
      token: token,
      configId: cfg.id,
      configLabel: cfg.label,
      lastT: null,
      firstDecision: null,
      firstAudible: null,
      id: null,
      idNote: '',
    };
    state.run = run;

    var guard = function (fn) {
      return function (a) {
        if (state.run !== run || run.token !== token) { return; } // stale run: drop
        fn(a);
      };
    };

    var handlers = {
      onEvent: guard(function (evt) {
        appendEventRow(run, evt);
        if (evt.kind === 'state' && evt.state) { appendStateSegment(run, evt); }
        if (evt.kind === 'decision' && run.firstDecision === null) { run.firstDecision = evt.t; }
        if (evt.kind === 'audible' && run.firstAudible === null) { run.firstAudible = evt.t; }
        updateTimingSummary(run);
      }),
      onEnd: guard(function () {
        setRunPhase('ended');
        el.currentState.textContent = 'run ended';
        el.currentState.className = 'state-badge state-none';
      }),
      onError: guard(function (message) {
        setRunPhase('error');
        setStatusText('error', 'Run error: ' + String(message));
        appendEventRow(run, { t: NaN, kind: 'error', detail: String(message) });
      }),
    };

    var startInfo;
    try {
      startInfo = state.adapter.start(cfg.id, handlers);
    } catch (err) {
      state.run = null;
      setRunPhase('error');
      setStatusText('error', String(err && err.message ? err.message : err));
      return;
    }

    run.id = startInfo.runId;
    run.idNote = startInfo.runIdNote || '';
    el.runId.textContent = run.id + (run.idNote ? ' (' + run.idNote + ')' : '');
    el.runConfig.textContent = cfg.label + ' — ' + cfg.detail;
    el.eventCaption.textContent =
      'Events attributed to run ' + run.id + ', configuration ' + cfg.label +
      '. A fresh run clears this table.';
    if (startInfo.sourceRecording) {
      el.sourceLabel.textContent = 'Source: ' + startInfo.sourceRecording;
    }
    setRunPhase('running');
    refreshChrome(); // keep the preview labeling in view during the run
  }

  function stopRun() {
    if (state.runPhase !== 'running') { return; }
    state.adapter.stop();
    if (state.run) { state.run.token = null; } // drop late events from this run
    setRunPhase('stopped');
    el.currentState.textContent = 'stopped';
    el.currentState.className = 'state-badge state-none';
  }

  // One-tap reset: stop everything and return the surface to idle.
  function resetAll() {
    state.adapter.stop();
    if (state.run) { state.run.token = null; }
    state.run = null;
    clearEvents();
    el.runId.textContent = '—';
    el.runConfig.textContent = '—';
    el.eventCaption.textContent = 'Events for the current run. A fresh run clears this table.';
    el.sourceLabel.innerHTML = DEFAULT_SOURCE_HTML;
    setRunPhase('idle');
    refreshChrome();
  }

  /* ---------- adapter switching (blocked <-> preview) ---------- */

  function setAdapter(mode) {
    state.adapter.stop();
    state.adapter = new window.StutterTurnAdapters[mode]();
    resetAll();
    renderConfigs();
    setRunPhase('idle');
    refreshChrome();
  }

  el.previewToggle.addEventListener('change', function () {
    setAdapter(el.previewToggle.checked ? 'preview' : 'blocked');
  });

  /* ---------- controls ---------- */

  el.btnStart.addEventListener('click', startRun);
  el.btnStop.addEventListener('click', stopRun);
  el.btnReset.addEventListener('click', resetAll);

  document.addEventListener('keydown', function (e) {
    if (e.ctrlKey || e.metaKey || e.altKey) { return; }
    var tag = (e.target && e.target.tagName) || '';
    if (tag === 'TEXTAREA' || tag === 'SELECT') { return; }
    if (tag === 'INPUT') {
      // Only text-entry inputs swallow shortcuts; a keyboard user who just
      // arrowed through the config radios must still be able to press S/R.
      var type = String(e.target.type || '').toLowerCase();
      if (type !== 'radio' && type !== 'checkbox' && type !== 'button') { return; }
    }
    var k = e.key.toLowerCase();
    if (k === 's') { e.preventDefault(); startRun(); }
    else if (k === 'x') { e.preventDefault(); stopRun(); }
    else if (k === 'r') { e.preventDefault(); resetAll(); }
    else if (k === 'p') {
      e.preventDefault();
      el.previewToggle.checked = !el.previewToggle.checked;
      setAdapter(el.previewToggle.checked ? 'preview' : 'blocked');
    } else if (k === '1' || k === '2' || k === '3') {
      var idx = Number(k) - 1;
      var cfg = state.configs[idx];
      if (cfg && cfg.available && state.runPhase !== 'running') {
        state.selectedConfig = cfg.id;
        var radio = el.configGroup.querySelector('input[value="' + cfg.id + '"]');
        if (radio) { radio.checked = true; radio.focus(); }
      }
    }
  });

  /* ---------- boot ---------- */

  renderConfigs();
  setRunPhase('idle');
  refreshChrome();
})();
