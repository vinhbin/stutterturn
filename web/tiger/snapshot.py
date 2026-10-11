#!/usr/bin/env python3
"""Write web/tiger/snapshot.json for the judges-page chart block.

Default mode runs the named views from web/tiger/schema.sql against the
TigerData (TimescaleDB) service — clip_first_completion,
decision_to_audio_gap, cancelled_before_audio, run_outcomes — so every
number on the page traces to a database query over the committed run logs.
Until credentials exist it exits with instructions instead of inventing data.

--offline computes the same JSON directly from the committed JSONL files
(same definitions, no database) and marks the output "offline_fallback":
true. The chart renders a visible LOCAL SNAPSHOT label for that case; the
page never shows fabricated data.

Usage:
  python web/tiger/snapshot.py             # needs TIGER_SERVICE_URL or ~/.tiger_conn
  python web/tiger/snapshot.py --offline   # no database, stdlib only

Current evidence is 5 clips x 2 configurations, one run each (replay v2).
The snapshot carries per-clip values and caveats only — no rates.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ingest  # noqa: E402  (shared parsing, connection resolution, superseded flag)

OUT_PATH = Path(__file__).resolve().parent / "snapshot.json"
HISTORICAL_DIRS = {
    "agent/evidence/2026-10-10-first-replay",
    "agent/evidence/2026-10-10-replay-v2",
}

CAVEATS = [
    "5 clips, one run per configuration for each clip, one show (HeStutters). Per-clip values only; no rates or aggregates.",
    "gap_start/resume labels in the evidence README are energy-derived and not human-reviewed.",
    "Each run appends 5 s of synthetic silence; fallback decisions on these 3 s clips happen during that padding.",
    "First agent audio is the reported agent_audio_start event; Gemini + ElevenLabs latency included. Speaker playback remains unverified, and this chart plays no audio.",
    "The clips are 3 s excerpts, usually ending mid-turn; these runs cannot establish completed-turn response delay.",
    "These are turn decisions and cancelled replies, not observed audible interruptions.",
]


def r3(x):
    return None if x is None else round(float(x), 3)


def per_run_from_log(item: dict) -> dict:
    """Mirror the schema.sql view definitions over one parsed log."""
    events = item["events"]
    run = item["run"]
    summary = json.loads(run["summary"])
    completes = sorted((e for e in events if e["name"] == "turn_complete"), key=lambda e: (e["t"], e["seq"]))
    audio = sorted((e for e in events if e["name"] == "agent_audio_start"), key=lambda e: (e["t"], e["seq"]))
    cancels = [e for e in events if e["name"] == "cancelled" and e.get("before_audible")]

    first = completes[0] if completes else None
    first_audio_t = audio[0]["t"] if audio else None
    answered = None
    if first_audio_t is not None and completes:
        answered = max((e["t"] for e in completes if e["t"] <= first_audio_t), default=None)
    cancel = cancels[0] if cancels else None
    cancelled_decision_t = None
    if cancel is not None and completes:
        cancelled_decision_t = max((e["t"] for e in completes if e["t"] <= cancel["t"]), default=None)

    return {
        "run_id": run["run_id"],
        "source_id": run["source_id"],
        "config": run["config"],
        "source_duration_s": r3(run["source_duration_s"]),
        "first_complete_t": r3(first["t"]) if first else None,
        "trigger": first["trigger"] if first else None,
        "prob": r3(first["prob"]) if first else None,
        "speaker_resumed_after_decision": summary.get("speaker_resumed_after_decision"),
        "cancelled_before_audio": cancel is not None,
        "cancelled_t": r3(cancel["t"]) if cancel else None,
        "cancelled_decision_t": r3(cancelled_decision_t),
        "answered_decision_t": r3(answered),
        "first_audio_t": r3(first_audio_t),
        "gap_s": r3(first_audio_t - answered) if first_audio_t is not None and answered is not None else None,
        "llm_latency_s": r3(summary.get("llm_latency_s")),
        "tts_first_audio_s": r3(summary.get("tts_first_audio_s")),
    }


def rows_offline() -> tuple[list[dict], dict]:
    parsed = [i for i in ingest.collect() if i['run']['evidence_dir'] in HISTORICAL_DIRS]
    current = [i for i in parsed if not i["run"]["superseded"]]
    rows = [per_run_from_log(i) for i in current]
    meta = evidence_meta(
        current_rows=[i["run"] for i in current],
        superseded_n=len(parsed) - len(current),
        dirs=sorted({i["run"]["evidence_dir"] for i in parsed}),
    )
    return rows, meta


def rows_live(url: str) -> tuple[list[dict], dict]:
    import psycopg
    from psycopg.rows import dict_row

    with psycopg.connect(url, row_factory=dict_row) as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM clip_first_completion")
        first = {r["run_id"]: r for r in cur.fetchall()}
        cur.execute("SELECT * FROM decision_to_audio_gap")
        gaps = {r["run_id"]: r for r in cur.fetchall()}
        cur.execute("SELECT * FROM cancelled_before_audio")
        cancels = {r["run_id"]: r for r in cur.fetchall()}
        cur.execute("SELECT * FROM run_outcomes WHERE NOT superseded")
        outcomes = {r["run_id"]: r for r in cur.fetchall()}
        cur.execute("SELECT run_id, config, source_id, source_duration_s, commit_sha, evidence_dir, superseded FROM runs")
        runs = [r for r in cur.fetchall() if r['evidence_dir'] in HISTORICAL_DIRS]

    rows = []
    for run in (r for r in runs if not r["superseded"]):
        rid = run["run_id"]
        f, g, c, o = first.get(rid), gaps.get(rid), cancels.get(rid), outcomes.get(rid, {})
        rows.append({
            "run_id": rid,
            "source_id": run["source_id"],
            "config": run["config"],
            "source_duration_s": r3(run["source_duration_s"]),
            "first_complete_t": r3(f and f["first_complete_t"]),
            "trigger": f["trigger"] if f else None,
            "prob": r3(f and f["prob"]),
            "speaker_resumed_after_decision": o.get("speaker_resumed_after_decision"),
            "cancelled_before_audio": c is not None,
            "cancelled_t": r3(c and c["cancelled_t"]),
            "cancelled_decision_t": r3(c and c["cancelled_decision_t"]),
            "answered_decision_t": r3(g and g["answered_decision_t"]),
            "first_audio_t": r3(g and g["first_audio_t"]),
            "gap_s": r3(g and g["gap_s"]),
            "llm_latency_s": r3(g and g["llm_latency_s"]),
            "tts_first_audio_s": r3(g and g["tts_first_audio_s"]),
        })
    meta = evidence_meta(
        current_rows=[r for r in runs if not r["superseded"]],
        superseded_n=sum(1 for r in runs if r["superseded"]),
        dirs=sorted({r["evidence_dir"] for r in runs}),
    )
    return rows, meta


def evidence_meta(current_rows: list[dict], superseded_n: int, dirs: list[str]) -> dict:
    return {
        "dirs": dirs,
        "commit": sorted({r["commit_sha"] for r in current_rows})[0] if current_rows else None,
        "contract": "0.1",
        "runs_current": len(current_rows),
        "runs_superseded_excluded": superseded_n,
        "clips": len({r["source_id"] for r in current_rows}),
        "configs": sorted({r["config"] for r in current_rows}),
    }


def assemble(rows: list[dict], meta: dict, offline: bool) -> dict:
    clips = []
    for source_id in sorted({r["source_id"] for r in rows}):
        configs = {}
        for row in (r for r in rows if r["source_id"] == source_id):
            configs[row["config"]] = {k: v for k, v in row.items() if k not in ("source_id", "config")}
        clips.append({"source_id": source_id, "configs": configs})
    snapshot = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "offline_fallback": offline,
        "source_note": (
            "Computed directly from committed run logs by snapshot.py --offline; "
            "this snapshot did not query Tiger Data."
            if offline else
            "Saved snapshot generated from Tiger Data queries over committed run logs; not live database status."
        ),
        "evidence": meta,
        "clips": clips,
        "caveats": CAVEATS,
    }
    return snapshot


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--offline", action="store_true",
                    help="compute the snapshot from the committed JSONL files; marks offline_fallback: true")
    args = ap.parse_args()

    if args.offline:
        rows, meta = rows_offline()
    else:
        url = ingest.connection_url()
        if not url:
            sys.exit(
                "No TigerData connection configured, so no snapshot was generated from the database.\n"
                "Set TIGER_SERVICE_URL or put the service URL in "
                f"{ingest.CONN_FILE} (one line), run web/tiger/ingest.py, then rerun this.\n"
                "For development without credentials use --offline (output is labeled as a local fallback)."
            )
        rows, meta = rows_live(url)

    snapshot = assemble(rows, meta, offline=args.offline)
    OUT_PATH.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")
    mode = "offline fallback (local, labeled)" if args.offline else "TigerData queries"
    print(f"Wrote {OUT_PATH.relative_to(ingest.REPO_ROOT).as_posix()} from {mode}: "
          f"{meta['clips']} clips, {meta['runs_current']} current runs, "
          f"{meta['runs_superseded_excluded']} superseded runs excluded.")


if __name__ == "__main__":
    main()
