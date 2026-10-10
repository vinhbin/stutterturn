# StutterTurn demo surface (`web/demo-ui/`)

Vinh's minimal demo UI for the stock ↔ StutterTurn comparison rig. **Passive shell:
live integration is BLOCKED** until Guttuu publishes `agent/CONTRACT.md` — this page
invents no endpoints. Owner: Vinh. Only this directory; Kareem owns the rest of `web/`.

## Run it

From the repo root (any static file server works; no build, no dependencies):

```bash
python -m http.server 8010 --directory web/demo-ui
```

Then open <http://localhost:8010/>. Opening `web/demo-ui/index.html` directly from disk
(`file://`) also works — plain scripts, no modules, no fetch.

## What it shows

- **Configuration** — STOCK / STUTTERTURN / PATIENT radio toggle. Availability comes from
  the adapter: with no backend, every arm is marked UNAVAILABLE; STUTTERTURN is
  additionally gated on a real model artifact (`model/CONTRACT.md`, Niko). If the model
  gate fails, the comparison falls back to STOCK vs PATIENT labeling — a nonexistent
  candidate model is never presented as available. Configuration changes apply only to a
  **fresh run**; radios are disabled mid-run (never switch weights mid-call).
- **Run panel** — run status, run ID, run configuration, event source. A fresh run resets
  all prior events; every event row is attributed to its run ID + configuration, and late
  events from a stopped/reset run are dropped.
- **Source recording** — provenance line. Real runs must display the SEP-28k clip identity
  supplied by the backend. The demo only ever plays real, labeled recordings; **nobody
  imitates stuttering, ever.** The preview explicitly states no audio/recording is involved.
- **Caller/agent state** — current state badge plus a timeline strip:
  `speaking / silence / holding / agent`.
- **Observed timing events** — table of events; **internal completion decisions** (model
  output) are reported separately from the **first audible agent response**, with the gap
  between them summarized.
- **Failure visibility** — persistent BLOCKED banner, inline error banner on failed
  starts, run-status `error` phase, and a one-tap **Reset**.

## Development preview (labeled, never evidence)

The "Enable development preview" checkbox swaps in a fixture adapter that replays one
fixed synthetic event sequence so the display can be exercised. While active, a
persistent banner reads "DEVELOPMENT PREVIEW — synthetic fixture events. Not live agent
output. Not benchmark evidence." The sequence is **identical for every configuration**,
contains no audio, no recording, no model output and no real probabilities. Do not
screenshot or cite it as a result.

## Adapter boundary (for Guttuu / future LiveAdapter)

All backend coupling lives in `adapter.js`. The UI consumes this interface:

```
adapter.mode                       'blocked' | 'preview' | 'live'
adapter.getConfigurations()        [{id, label, detail, available, note}]
adapter.start(configId, handlers)  -> {runId, runIdNote, sourceRecording} | throws
    handlers.onEvent({t, kind: 'state'|'decision'|'audible'|'info', state?, prob?, model?, detail})
    handlers.onEnd()
    handlers.onError(message)
adapter.stop()
```

**PROPOSED upstream contract** (PLAN.md "Shared contracts" — proposed, not an
implemented service): websocket JSON events
`{t, state: speaking|silence|holding|agent, prob, model}`.

**Extensions this UI needs, to be agreed with Guttuu before a LiveAdapter is written**
(PLAN.md: "Add run identity, time origin and cancellation/response timings by agreement"):

1. `run_id` on every event (attribution to the correct run/configuration).
2. Explicit time origin for `t` (proposal: seconds since run start).
3. Event kinds separating internal completion **decisions** from first **audible**
   response, plus cancellation/timeout events.
4. Source recording identity/provenance (SEP-28k clip ID) per run.
5. Run control: how the UI requests a fresh run with a chosen configuration, and how it
   stops/cancels one.

Status: **BLOCKED** — `agent/CONTRACT.md` does not exist yet. `LiveAdapterPlaceholder`
throws rather than pretending to connect. When the contract lands, implement it in
`adapter.js` and leave `BlockedAdapter`/`PreviewAdapter` untouched.

## How Kareem embeds or links this surface

- **Link** (preferred, simplest): serve the repo's `web/` directory and link to
  `/demo-ui/` — the page is self-contained (relative paths only: `styles.css`,
  `adapter.js`, `app.js`).
- **Embed**: `<iframe src="/demo-ui/" title="StutterTurn demo surface" style="width:100%;height:900px;border:0"></iframe>`
- Do not restyle or script-inject into this directory; ping Vinh for changes. Shared
  types or root-manifest changes go through Vinh per the handoff doc.

## Keyboard controls

| Key | Action |
|---|---|
| `Tab` / `Shift+Tab` | Move between controls (all controls are native elements) |
| `←` / `→` | Change configuration inside the radio group |
| `1` `2` `3` | Jump to configuration 1–3 (when available, not mid-run) |
| `S` | Start fresh run |
| `X` | Stop current run |
| `R` | Reset (one tap: stop + clear events + back to idle) |
| `P` | Toggle development preview |

## Files

| File | Purpose |
|---|---|
| `index.html` | Page structure |
| `styles.css` | Minimal styling (polish deferred until the core proof passes) |
| `adapter.js` | Adapter boundary: BlockedAdapter (default), PreviewAdapter (labeled fixture), LiveAdapter placeholder |
| `app.js` | Run lifecycle, event attribution, keyboard handling |
