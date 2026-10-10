# Tiger Data integration: run logs as a time series

Every agent run is a time series: the replay agent logs ordered, timestamped
events — VAD, turn decisions, cancellations, first agent audio — as JSONL
(`agent/CONTRACT.md` v0.1). This folder ingests the committed evidence logs
into TigerData (managed Postgres/TimescaleDB), asks the judge questions as
named SQL views, and renders the answers on a static chart block whose every
number traces back to those queries over real committed logs.

**Status: embedded at `/judge/`; database path remains unverified.**
`ingest.py --dry-run` validates the logs and `snapshot.py --offline` computes
the per-run numbers locally. The committed chart visibly labels this source
"Local snapshot · No Tiger Data query" on every figure. A saved database
export is labeled "Snapshot from Tiger Data queries"; neither label reports
a current database connection or backend health.

## Files

| File | Role |
|---|---|
| `schema.sql` | `runs` table + `events` hypertable + the judge queries as views. Idempotent. |
| `ingest.py` | Loads every `agent/evidence/**/*.jsonl`; `--dry-run` needs no DB or deps. |
| `snapshot.py` | Runs the views, writes `snapshot.json`; `--offline` for the labeled local fallback. |
| `chart.js` / `chart.css` | Self-contained block (no libraries) that renders `snapshot.json`. |
| `EMBED.md` | The judge-page integration and source-status behavior. |
| `preview.html` | Dev-only preview page. Not a judge route; `preview.png` is the original pre-integration capture. |
| `requirements.txt` | `psycopg[binary]` only — needed only for a live connection. |

## Setup (once, tonight)

1. **Sign up:** mlh.link/tigerdata (free credits for MLH hackers).
2. **Create a service** in the Tiger console (smallest tier is fine; it is
   TimescaleDB, so `create_hypertable` is available out of the box).
3. **Copy the service connection string** (looks like
   `postgres://user:password@host:port/tsdb?sslmode=require`) into **one** of:
   - environment variable `TIGER_SERVICE_URL`, or
   - the file `~/.tiger_conn` (on this machine `C:/Users/Binep/.tiger_conn`),
     the URL alone on one line.

   The connection string lives only there — never in code, never committed.
4. **Install the one dependency:** `pip install -r web/tiger/requirements.txt`
   (kept out of every root manifest on purpose).

## Commands (from the repo root)

```bash
python web/tiger/ingest.py --dry-run    # validate all committed logs, no DB
python web/tiger/ingest.py              # apply schema.sql + upsert all logs
python web/tiger/snapshot.py            # query the views -> snapshot.json
python web/tiger/snapshot.py --offline  # same JSON from the JSONLs, labeled offline
python -m http.server --directory web   # then open /tiger/preview.html
```

The dry run and offline snapshot never connect to a database. The non-dry
ingest creates database objects and upserts logs on `(run_id, seq, ts)`;
run it only against the intended service. Snapshot generation replaces
`snapshot.json` in either mode. After a real ingest and database snapshot,
the chart's label changes to "Snapshot from Tiger Data queries" from the
generated provenance — do not flip it by hand. This remains a static export,
not a live database connection from the browser.

## Why a hypertable

Run logs are append-only streams of timestamped events, and every question a
judge asks is a time question: *when* did each configuration first decide the
turn was complete, did the speaker resume *before* the reply became audible,
how long from decision to first audio. TimescaleDB partitions the `events`
table by time (`ts = run t0_wall + t`) and keeps per-run ordering via
`(run_id, seq)`, so those windows and `DISTINCT ON`/ordered scans are the
native access pattern rather than a bolted-on index. The judge queries are
named views in `schema.sql` — `run_decision_timeline`,
`clip_first_completion`, `decision_to_audio_gap`, `cancelled_before_audio`,
`run_outcomes` — so the page's numbers are reproducible one `SELECT` at a
time, and the event-derived views can be cross-checked against the agent's
own `run_ended` summaries (`run_outcomes`).

## Honesty rules this folder enforces

- **Real logs only.** Rows come from committed JSONLs; the chart renders only
  `snapshot.json`; a missing snapshot shows an instruction, never mock data.
- **Superseded data stays marked.** The 2026-10-10-first-replay logs (faulty
  model input, per its README) are ingested with `superseded = true` and
  excluded from analysis views — visible, never silently dropped.
- **No rates from n=5.** Five clips, one run per configuration per clip: per-clip values only,
  with the caveats rendered beside them.
- **Decision framing.** These are turn decisions and cancelled replies, not
  observed audible interruptions; first audio is the reported
  `agent_audio_start` event, including Gemini + ElevenLabs latency. Speaker
  playback remains unverified; the chart does not play audio. These excerpts
  do not establish completed-turn response delay.
- **Offline fallback is always labeled**, on every figure.
- **Unknown provenance does not imply database use.** Missing source metadata
  shows an unavailable-data message; no figure or database badge is drawn.
- **Later decisions have a distinct marker.** The snapshot does not carry
  their triggers, so they are not labeled as model decisions or fallbacks.

## Local verification (2026-10-10)

- `python web/tiger/ingest.py --dry-run`: 20 logs / 302 events parsed; 10
  current runs / 150 events and 10 superseded runs / 152 events. No DB touched.
- `python web/tiger/snapshot.py --offline`: five clips, ten current runs,
  ten superseded runs excluded; saved values remain from replay v2.
- `node web/demo-ui/dev/checks/site-checks.mjs`: 52/52 passed, including chart
  data, missing-data and missing-provenance handling, an injected database
  snapshot response, no-JavaScript fallback, and phone/desktop containment.
  The injected response checks the label branch only; it is not a database
  integration test. Requests are limited to loopback and no backend is used.

## Devpost disclosure (paste when — and only when — the live path has run)

> **Tiger Data:** our replay agent's run logs (turn decisions, cancellations,
> speech events and first-audio timings from the committed evidence runs) are
> ingested into a TimescaleDB `events` hypertable on Tiger Data, and the
> judges-page chart renders a snapshot generated from named SQL views over
> that service (`web/tiger/`). Superseded runs are kept but flagged; the
> five-clip evidence set is shown as per-clip values, not rates.

If the live ingest has not actually run by submission time, do **not** enter
the Tiger Data prize or paste the sentence above — per `docs/claims-ledger.md`
L-34, only sponsor integrations with actual disclosed use are entered.
