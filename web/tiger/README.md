# Tiger Data integration: run logs as a time series

Every agent run is a time series: the replay agent logs ordered, timestamped
events — VAD, turn decisions, cancellations, first agent audio — as JSONL
(`agent/CONTRACT.md` v0.1). This folder ingests the committed evidence logs
into TigerData (managed Postgres/TimescaleDB), asks the judge questions as
named SQL views, and renders the answers on a static chart block whose every
number traces back to those queries over real committed logs.

**Status: credential-gated.** Everything here runs today except the live
database connection. Until a service URL exists, `ingest.py --dry-run`
validates the logs and `snapshot.py --offline` computes the same numbers
locally — and the chart visibly labels that snapshot "LOCAL SNAPSHOT — NOT
YET SERVED FROM TIGERDATA". Nothing claims TigerData is serving until it is.

## Files

| File | Role |
|---|---|
| `schema.sql` | `runs` table + `events` hypertable + the judge queries as views. Idempotent. |
| `ingest.py` | Loads every `agent/evidence/**/*.jsonl`; `--dry-run` needs no DB or deps. |
| `snapshot.py` | Runs the views, writes `snapshot.json`; `--offline` for the labeled local fallback. |
| `chart.js` / `chart.css` | Self-contained block (no libraries) that renders `snapshot.json`. |
| `EMBED.md` | The 3-line judges-page snippet and where it goes. |
| `preview.html` / `preview.png` | Dev-only preview page and its captured render. Not a judge route. |
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

Re-running any of these is safe: the schema is `IF NOT EXISTS`, ingest
upserts on `(run_id, seq)`, and the snapshot is regenerated whole. After a
real ingest + snapshot, the chart's label flips to "Served from TigerData
queries" by itself — do not flip anything by hand.

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
- **No rates from n=5.** Five clips, one run each: per-clip values only,
  with the caveats rendered beside them.
- **Decision framing.** These are turn decisions and cancelled replies, not
  observed audible interruptions; first audio is scheduled-play time
  including Gemini + ElevenLabs latency, not measured speaker output.
- **Offline fallback is always labeled**, on every figure.

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
