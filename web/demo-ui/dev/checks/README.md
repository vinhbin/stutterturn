# Committed demo-ui check suite

Reproducible checks for the call console, replacing the PR #12 scratch-directory
harnesses that nobody else could re-run. The adapter and console suites drive
**synthetic fixtures only**. Site checks also render the committed replay
snapshot and inject unavailable/malformed/database-provenance responses to
exercise chart states. A pass verifies UI behavior and honest labeling; it is
never new audio, model, efficacy, database-use or benchmark evidence. F2/I1
and candidate acceptance gates are unaffected.

No `package.json` or other manifest exists or is needed. Run both suites from
the **repository root**.

## 1. Adapter checks (Node, no dependencies)

```sh
node web/demo-ui/dev/checks/adapter-checks.mjs
```

Loads `web/demo-ui/adapter.js` unmodified and drives it with stubbed
`fetch`/`WebSocket` transports. 38 checks: `validSourceFile` acceptance
(bare names per contract v0.1 af2813d; relative paths tolerated only for
pre-af2813d compatibility) and rejection (separators, roots, URLs, encoding,
controls, padding, duplicates), discovery validation, start acknowledgement,
`v`/`seq`/`kind`/`prob` validation, mock-provenance matching in both
directions, retired-run filtering, unavailable-candidate gating,
stop/disconnect lifecycle, and blocked/preview adapter labeling.

Requires Node 18+ (verified on Node 24). Exit code 0 means all passed; the
last line prints the exact count.

## 2. Browser checks (Playwright chromium)

One-time browser install, then run:

```sh
npx -y playwright@1.64.0 install chromium
node web/demo-ui/dev/checks/browser-checks.mjs
```

If `playwright` is not resolvable as a module (this repository deliberately
has no manifest), the script also searches the npm/npx cache; populate it or
force it explicitly with:

```sh
npx -y -p playwright@1.64.0 node web/demo-ui/dev/checks/browser-checks.mjs
```

The script needs no servers started by hand: it serves `web/demo-ui/` itself
on a free port and spawns the committed dev mock
(`python web/demo-ui/dev/mock-agent-server.py --speed 8`), so Python 3.9+ must
be on `PATH`. 20 checks across three modes:

- **Blocked**: blocked chip, no banner, all arms (including STUTTERTURN)
  unavailable, keyboard `S` cannot start a run.
- **Development preview** (`P`): labeled banner/chip, synthetic-only badges,
  synthetic run identity, not-evidence summary, synthetic timing qualifiers,
  overlap tally, `X` stop, `R` reset clearing events/identity/clock.
- **Mock backend**: real HTTP discovery + WebSocket run against the dev mock;
  MOCK labeling everywhere, five fixtures, candidate still unavailable,
  per-row run attribution, `agent_audio_start (reported)`, services-OFF
  metadata, reset keeps the connection, a second (patient/cancelled) run gets
  a fresh id, URL-field keystrokes never trigger shortcuts, and zero uncaught
  page errors for the whole session.

Exit code 0 = all passed; 1 = check failures; 2 = environment missing
(Playwright module or chromium binary), with the install command printed.

## 3. Site interactions and responsive integration (Playwright chromium)

```sh
node web/demo-ui/dev/checks/site-checks.mjs
```

Uses the same Playwright/Chromium installation and cache discovery as the browser
suite above. It serves the full `web/` directory on an ephemeral loopback port;
no Python server, agent backend, API credentials, or paid services are involved.
External requests and WebSocket connections are blocked and fail the check.
No screenshots are captured.

The 52 checks cover:

- Reduced-motion initial state, explicit Play, keyboard Pause, and native range
  scrubbing to Pause/Continuing/Reply while playback is active.
- Automatic offscreen pause/resume and manual pause persisting across scroll.
  Hidden-page behavior is exercised by injecting the browser visibility signal;
  headless tab focus alone does not reliably produce a hidden document.
- Complete, visible concept illustration and usable navigation without
  JavaScript; illustration/no-audio disclosures stay explicit.
- Distinct overview, judge guide, and live workspace navigation; the judge guide
  provides evaluation steps and pinned evidence without embedding run controls.
  The legacy `/judges/` link redirects to `/judge/`, retaining its fragment,
  and offers a usable link without JavaScript.
- The guide's dated replay-v2 facts, separate execution/artifact revisions, and
  label/playback limitations. This checks the published snapshot against its
  fixed expected values; it does not rerun or validate the experiment.
- The embedded run-log chart's ten saved runs and per-figure offline labels,
  reported-audio limits, and distinct later-decision markers. Missing data or
  provenance produces no chart or database claim. An injected database export
  checks the saved-snapshot label only; it does not query a database. The
  no-JavaScript guide links directly to saved JSON evidence.
- Landing, judge guide, live workspace, and standalone console containment at
  360, 390, 1280, and 1440 pixels, including header navigation.
- At 360/390 pixels: the visible setup jump moves keyboard focus to its target;
  the ledger caption stays outside horizontal scrolling, wraps inside the
  viewport, and describes the table; the left-aligned empty message is readable
  at the initial scroll position. Populated ledgers expose their keyboard hint
  and scroll with ArrowRight while the caption stays in place.
- The phone landing diagram keeps a 520px content width inside its own
  keyboard-scrollable region, displays scroll instructions, and preserves
  functional phase text at 11px or above without widening the page.
- Live iframe sizing after preview starts, embedded-console mode, synthetic
  provenance, and the no-response-audio notice.
- Enabled Start action within the first 900 vertical pixels on desktop after
  preview is selected; no uncaught browser errors, external page requests, or
  automatic backend connections.

This suite checks behavior and layout containment, not exact colors or screenshot
pixels. It does not establish real playback, voice-agent efficacy, or visual
quality. Exit codes match the browser suite: 0 passed, 1 check failure, 2 missing
Playwright/Chromium. On October 10, 2026, the first studio-refresh run passed
30/30, the expanded review-fix suite passed 38/38, and the judge/live route-split
suite passed 48/48. The Tiger chart integration suite passed 52/52.

## Recorded results

2026-10-10, Windows 11, Node 24.21.0, Python 3.12.10, Playwright 1.64.0
(chromium-headless-shell 1248): `adapter-checks` 38/38, `browser-checks`
20/20 — 58/58 total. Mutation sanity: disabling the adapter's mock-provenance
guard failed 2 adapter checks; removing the UI's `(reported)` audio-start
suffix failed 1 browser check; both originals restored and re-passed.
See `web/demo-ui/verification.md` for the dated record.


## Browser audio extension — October 11

`node web/demo-ui/dev/checks/audio-checks.mjs` runs eight synthetic playback and
adapter lifecycle checks: shared timeline, generation cancellation, Stop, stale
runs, bounded payloads, late chunks, and draining before the final summary.

`python web/demo-ui/dev/checks/audio-browser-check.py` renders synthetic PCM in
Chromium's OfflineAudioContext, checking source/reply mixing, cancellation and
silence after Stop. Requires Python Playwright plus Chromium.

For authenticated real-provider smoke runs, pass `--access-file PRIVATE_JSON
--out OUTPUT_DIR`. The private JSON contains `url`, `username`, `password`. This
mode incurs provider usage; it measures source/reply/mixed digital Web Audio peaks,
Stop during generated speech, Reset during a restarted source, and saves event
logs without PCM or credentials. A pass does not verify human listening or
acoustic latency. The [hosted packet](../../../../docs/proofs/vultr-browser-audio/README.md)
records the deployed result, including an earlier Gemini timeout.

Latest regression counts: 38 adapter, 20 console, 52 site, eight audio lifecycle.
The site test now expects the committed Tiger Data query snapshot's provenance,
while still distinguishing the saved chart from a live database connection.


## Hosted automatic connection

`python web/demo-ui/dev/checks/connection-browser-check.py` intercepts HTTPS and
WebSocket traffic in Chromium. It checks automatic source/model discovery with
Advanced settings collapsed, recovery from HTTP503 and HTTP401, a dropped socket,
and that opening the page starts no paid replay. Local HTTP development continues
to use explicit Connect. Hosted discovery allows15seconds; source/reply audio
still starts only on the user's Start action.
