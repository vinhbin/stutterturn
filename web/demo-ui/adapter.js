/* StutterTurn demo UI — adapter boundary.
 *
 * STATUS: live integration BLOCKED. agent/CONTRACT.md (owner: Guttuu) does not
 * exist yet, so no endpoint, port, path or message format is invented here.
 * The UI runs against one of two adapters:
 *
 *   - BlockedAdapter (default): refuses to start runs and reports why.
 *   - PreviewAdapter: a development fixture that emits a fixed, synthetic event
 *     sequence so the display can be exercised. It is labeled on screen at all
 *     times, has NO audio, involves NO recording, and encodes NO model
 *     behavior. Never use it as evidence.
 *
 * PROPOSED upstream contract (PLAN.md "Shared contracts" — PROPOSED, not an
 * implemented service):
 *   websocket JSON events: {t, state: "speaking"|"silence"|"holding"|"agent",
 *                           prob, model}
 *
 * Extensions this UI needs, to be agreed with Guttuu before wiring a
 * LiveAdapter (PLAN.md already anticipates: "Add run identity, time origin and
 * cancellation/response timings by agreement"):
 *   - run_id on every event (attribution to the correct run/configuration)
 *   - explicit time origin for t (proposal: seconds since run start)
 *   - event kinds distinguishing internal completion DECISIONS from first
 *     AUDIBLE agent response (and cancellations/timeouts)
 *   - source recording identity/provenance (SEP-28k clip ID) per run
 *   - run-control: how the UI requests a fresh run with a chosen
 *     configuration, and how it stops/cancels one
 *
 * Adapter interface consumed by app.js:
 *   adapter.mode            'blocked' | 'preview' | 'live'
 *   adapter.sourceLabel     string shown as the event-source in the run panel
 *   adapter.getConfigurations() -> [{id, label, available, note}]
 *   adapter.start(configId, handlers) -> startInfo | throws
 *       startInfo: {runId, runIdNote, sourceRecording}
 *       handlers:  {onEvent(evt), onEnd(), onError(message)}
 *       evt: {t, kind: 'state'|'decision'|'audible'|'info',
 *             state?, prob?, model?, detail}
 *   adapter.stop()          stop/cancel the active run (idempotent)
 */

'use strict';

// Single source of truth for arm labels. Availability is honest: nothing is
// available without a backend; the STUTTERTURN candidate additionally needs a
// real model artifact (model/CONTRACT.md, owner: Niko).
var DEMO_ARMS = [
  {
    id: 'stock',
    label: 'STOCK',
    detail: 'Smart Turn v3.2, stock settings',
  },
  {
    id: 'stutterturn',
    label: 'STUTTERTURN',
    detail: 'fine-tuned candidate — requires a real exported model artifact',
  },
  {
    id: 'patient',
    label: 'PATIENT',
    detail: 'stock agent, patient/wait configuration (fallback comparison arm if the model gate fails) — a longer wait, not a trained model',
  },
];

function BlockedAdapter() {
  this.mode = 'blocked';
  this.sourceLabel = 'blocked (no backend contract)';
}

BlockedAdapter.prototype.getConfigurations = function () {
  return DEMO_ARMS.map(function (arm) {
    var note;
    if (arm.id === 'stutterturn') {
      note = 'UNAVAILABLE — no model artifact and no backend (model/CONTRACT.md and agent/CONTRACT.md missing)';
    } else {
      note = 'UNAVAILABLE — backend not connected (agent/CONTRACT.md missing)';
    }
    return { id: arm.id, label: arm.label, detail: arm.detail, available: false, note: note };
  });
};

BlockedAdapter.prototype.start = function () {
  throw new Error(
    'BLOCKED: no agent backend contract is published (agent/CONTRACT.md missing, owner: Guttuu). ' +
    'This UI does not invent endpoints. Enable the development preview to exercise the display.'
  );
};

BlockedAdapter.prototype.stop = function () {};

/* Development preview fixture.
 * The sequence below is IDENTICAL for every configuration on purpose: it
 * exercises the display and encodes no model behavior, no speech and no
 * recording. prob values are arbitrary synthetic numbers. */
var PREVIEW_SCRIPT = [
  { t: 0.0, kind: 'info',     detail: 'fixture run started (synthetic — development preview)' },
  { t: 0.0, kind: 'state',    state: 'speaking', detail: 'caller channel active (synthetic)' },
  { t: 1.2, kind: 'state',    state: 'silence',  detail: 'caller channel silent (synthetic)' },
  { t: 1.7, kind: 'decision', prob: 0.93,        detail: 'internal completion decision (synthetic prob — not a model output)' },
  { t: 1.9, kind: 'state',    state: 'holding',  detail: 'agent holding, not responding (synthetic)' },
  { t: 3.0, kind: 'state',    state: 'speaking', detail: 'caller channel active again (synthetic)' },
  { t: 4.1, kind: 'state',    state: 'silence',  detail: 'caller channel silent (synthetic)' },
  { t: 4.6, kind: 'decision', prob: 0.97,        detail: 'internal completion decision (synthetic prob — not a model output)' },
  { t: 4.8, kind: 'state',    state: 'agent',    detail: 'agent response begins (synthetic)' },
  { t: 5.4, kind: 'audible',  detail: 'first audible agent response (synthetic — nothing is actually audible)' },
  { t: 6.2, kind: 'info',     detail: 'fixture sequence complete' },
];

function PreviewAdapter() {
  this.mode = 'preview';
  this.sourceLabel = 'development preview fixture (synthetic — not live, not evidence)';
  this._timers = [];
  this._runCounter = 0;
}

PreviewAdapter.prototype.getConfigurations = function () {
  return DEMO_ARMS.map(function (arm) {
    return {
      id: arm.id,
      label: arm.label,
      detail: arm.detail,
      available: true,
      note: 'PREVIEW ONLY — selects a label; the fixture sequence is identical for every configuration',
    };
  });
};

PreviewAdapter.prototype.start = function (configId, handlers) {
  var self = this;
  this.stop();
  this._runCounter += 1;
  var modelField = 'preview-fixture (' + configId + ' label only)';

  PREVIEW_SCRIPT.forEach(function (step) {
    var timer = setTimeout(function () {
      handlers.onEvent({
        t: step.t,
        kind: step.kind,
        state: step.state,
        prob: step.prob,
        model: modelField,
        detail: step.detail,
      });
      if (step === PREVIEW_SCRIPT[PREVIEW_SCRIPT.length - 1]) {
        handlers.onEnd();
      }
    }, step.t * 1000);
    self._timers.push(timer);
  });

  return {
    runId: 'preview-' + this._runCounter,
    runIdNote: 'local preview id — not a backend run',
    sourceRecording:
      'None — synthetic fixture, no audio, no recording involved (development preview). ' +
      'Real runs must display the SEP-28k clip identity supplied by the backend.',
  };
};

PreviewAdapter.prototype.stop = function () {
  this._timers.forEach(clearTimeout);
  this._timers = [];
};

/* LiveAdapter placeholder — intentionally NOT implemented.
 * When Guttuu publishes agent/CONTRACT.md, implement the interface above here
 * (websocket connect, run control, event mapping, reconnection) and leave
 * BlockedAdapter/PreviewAdapter untouched. Until then any attempt to use it
 * fails loudly instead of pretending to work. */
function LiveAdapterPlaceholder() {
  throw new Error('LiveAdapter not implemented: waiting on agent/CONTRACT.md (owner: Guttuu).');
}

window.StutterTurnAdapters = {
  blocked: BlockedAdapter,
  preview: PreviewAdapter,
  live: LiveAdapterPlaceholder,
};
