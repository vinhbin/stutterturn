#!/usr/bin/env python3
"""Ingest StutterTurn run-log JSONLs into TigerData (TimescaleDB).

Loads every committed evidence log (agent/evidence/**/*.jsonl, schema in
agent/CONTRACT.md v0.1) into the tables defined by web/tiger/schema.sql:
one `runs` row per log, one `events` hypertable row per event line, with
ts = run t0_wall + t.

Honesty:
  * Logs under agent/evidence/2026-10-10-first-replay are ingested with
    superseded = true: that recording session used a faulty model input and
    is superseded by 2026-10-10-replay-v2 (see both READMEs). The rows stay
    queryable; analysis views exclude them.
  * Nothing is synthesized. Only committed log lines become rows.

Connection (never hardcoded, never committed):
  1. env TIGER_SERVICE_URL                 e.g. postgres://user:pass@host:port/db?sslmode=require
  2. file ~/.tiger_conn                    (C:/Users/<you>/.tiger_conn on Windows)
                                           containing that same URL on one line

Usage:
  python web/tiger/ingest.py --dry-run     # parse + validate + counts, no DB, no deps
  python web/tiger/ingest.py               # apply schema.sql, then upsert everything

Idempotent: re-running upserts in place, keyed on (run_id, seq) — the
hypertable key also carries ts, which is deterministic from (t0_wall, t).
Requires psycopg (web/tiger/requirements.txt) only for a live ingest.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_ROOT = REPO_ROOT / "agent" / "evidence"
SCHEMA_SQL = Path(__file__).resolve().parent / "schema.sql"

# Per agent/evidence/2026-10-10-replay-v2/README.md ("Supersedes
# 2026-10-10-first-replay, whose model input was faulty").
SUPERSEDED_DIRS = {"2026-10-10-first-replay"}

CONN_FILE = Path.home() / ".tiger_conn"

EVENT_FIELDS = (
    "ts run_id config source_id seq t kind name state prob threshold trigger "
    "model silence_s infer_ms input_s before_audible detail superseded raw"
).split()

RUN_FIELDS = (
    "run_id config model model_sha256 commit_sha contract_v source_id "
    "source_duration_s t0_wall services reason params summary evidence_dir "
    "log_file superseded"
).split()


def connection_url() -> str | None:
    url = os.environ.get("TIGER_SERVICE_URL", "").strip()
    if url:
        return url
    if CONN_FILE.is_file():
        text = CONN_FILE.read_text(encoding="utf-8").strip()
        if text:
            return text.splitlines()[0].strip()
    return None


def parse_t0(t0_wall: str) -> datetime:
    return datetime.fromisoformat(t0_wall.replace("Z", "+00:00"))


def parse_log(path: Path) -> dict:
    """Parse one run-log JSONL into {'run': {...}, 'events': [...]}; raises on a malformed log."""
    lines = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines:
        raise ValueError(f"{path.name}: empty log")
    started, ended = lines[0], lines[-1]
    if started.get("type") != "run_started":
        raise ValueError(f"{path.name}: first line is {started.get('type')!r}, not run_started")
    if ended.get("type") != "run_ended":
        raise ValueError(f"{path.name}: last line is {ended.get('type')!r}, not run_ended")
    run_id = started["run_id"]
    superseded = path.parent.name in SUPERSEDED_DIRS
    t0 = parse_t0(started["t0_wall"])
    last_seq = -1
    for line in lines:
        if line.get("run_id") != run_id:
            raise ValueError(f"{path.name}: run_id mismatch on seq {line.get('seq')}")
        if line["seq"] != last_seq + 1:
            raise ValueError(f"{path.name}: seq jumps {last_seq} -> {line['seq']}")
        last_seq = line["seq"]

    source = started.get("source", {})
    run = {
        "run_id": run_id,
        "config": started["config"],
        "model": started.get("model"),
        "model_sha256": started.get("model_sha256"),
        "commit_sha": started.get("commit"),
        "contract_v": started.get("v"),
        "source_id": source.get("source_id"),
        "source_duration_s": source.get("duration_s"),
        "t0_wall": t0,
        "services": started.get("services"),
        "reason": ended.get("reason"),
        "params": json.dumps(started.get("params", {})),
        "summary": json.dumps(ended.get("summary", {})),
        "evidence_dir": path.parent.relative_to(REPO_ROOT).as_posix(),
        "log_file": path.name,
        "superseded": superseded,
    }

    events = []
    for line in lines[1:-1]:
        if line.get("type") != "event":
            raise ValueError(f"{path.name}: unexpected line type {line.get('type')!r} at seq {line['seq']}")
        t = float(line["t"])
        events.append({
            "ts": t0 + timedelta(seconds=t),
            "run_id": run_id,
            "config": run["config"],
            "source_id": run["source_id"],
            "seq": line["seq"],
            "t": t,
            "kind": line["kind"],
            "name": line.get("name"),
            "state": line.get("state"),
            "prob": line.get("prob"),
            "threshold": line.get("threshold"),
            "trigger": line.get("trigger"),
            "model": line.get("model"),
            "silence_s": line.get("silence_s"),
            "infer_ms": line.get("infer_ms"),
            "input_s": line.get("input_s"),
            "before_audible": line.get("before_audible"),
            "detail": line.get("detail"),
            "superseded": superseded,
            "raw": json.dumps(line),
        })
    return {"run": run, "events": events}


def collect() -> list[dict]:
    paths = sorted(EVIDENCE_ROOT.glob("*/*.jsonl"))
    if not paths:
        sys.exit(f"No JSONL logs found under {EVIDENCE_ROOT}")
    return [parse_log(p) for p in paths]


def report(parsed: list[dict]) -> None:
    by_dir: dict[str, list[dict]] = {}
    for item in parsed:
        by_dir.setdefault(item["run"]["evidence_dir"], []).append(item)
    total_e = 0
    for d, items in sorted(by_dir.items()):
        n_events = sum(len(i["events"]) for i in items)
        total_e += n_events
        flag = "superseded=true" if items[0]["run"]["superseded"] else "current"
        print(f"  {d}: {len(items)} logs -> {len(items)} runs rows, {n_events} events rows ({flag})")
    print(f"  total: {len(parsed)} runs rows, {total_e} events rows")


def ingest(parsed: list[dict], url: str) -> None:
    import psycopg  # lazy: --dry-run must not need it

    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            cur.execute(SCHEMA_SQL.read_text(encoding="utf-8"))
            run_cols = ", ".join(RUN_FIELDS)
            run_ph = ", ".join(f"%({f})s" for f in RUN_FIELDS)
            run_upd = ", ".join(f"{f} = EXCLUDED.{f}" for f in RUN_FIELDS if f != "run_id")
            ev_cols = ", ".join(EVENT_FIELDS)
            ev_ph = ", ".join(f"%({f})s" for f in EVENT_FIELDS)
            ev_upd = ", ".join(f"{f} = EXCLUDED.{f}" for f in EVENT_FIELDS if f not in ("run_id", "seq", "ts"))
            for item in parsed:
                cur.execute(
                    f"INSERT INTO runs ({run_cols}) VALUES ({run_ph}) "
                    f"ON CONFLICT (run_id) DO UPDATE SET {run_upd}",
                    item["run"],
                )
                cur.executemany(
                    f"INSERT INTO events ({ev_cols}) VALUES ({ev_ph}) "
                    f"ON CONFLICT (run_id, seq, ts) DO UPDATE SET {ev_upd}",
                    item["events"],
                )
        conn.commit()
        with conn.cursor() as cur:
            cur.execute("SELECT count(*), count(*) FILTER (WHERE superseded) FROM runs")
            runs_n, runs_sup = cur.fetchone()
            cur.execute("SELECT count(*), count(*) FILTER (WHERE superseded) FROM events")
            ev_n, ev_sup = cur.fetchone()
    print(f"Ingested. DB now holds {runs_n} runs ({runs_sup} superseded), {ev_n} events ({ev_sup} superseded).")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true",
                    help="parse and validate every log and print row counts; no database, no psycopg needed")
    args = ap.parse_args()

    parsed = collect()
    print(f"Parsed {len(parsed)} run logs under {EVIDENCE_ROOT.relative_to(REPO_ROOT).as_posix()}:")
    report(parsed)

    if args.dry_run:
        print("Dry run: no database touched.")
        return

    url = connection_url()
    if not url:
        sys.exit(
            "No TigerData connection configured.\n"
            "Set TIGER_SERVICE_URL or put the service URL in "
            f"{CONN_FILE} (one line). Sign up: mlh.link/tigerdata - see web/tiger/README.md.\n"
            "To validate the logs without a database, run with --dry-run."
        )
    ingest(parsed, url)


if __name__ == "__main__":
    main()
