# Committed demo-ui check suite

Reproducible checks for the call console, replacing the PR #12 scratch-directory
harnesses that nobody else could re-run. Everything here drives **synthetic
fixtures only**: a pass verifies adapter/UI contract handling and honest
labeling, and is never audio, model, efficacy or benchmark evidence. F2/I1 and
candidate acceptance gates are unaffected.

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

## Recorded results

2026-10-10, Windows 11, Node 24.21.0, Python 3.12.10, Playwright 1.64.0
(chromium-headless-shell 1248): `adapter-checks` 38/38, `browser-checks`
20/20 — 58/58 total. Mutation sanity: disabling the adapter's mock-provenance
guard failed 2 adapter checks; removing the UI's `(reported)` audio-start
suffix failed 1 browser check; both originals restored and re-passed.
See `web/demo-ui/verification.md` for the dated record.
