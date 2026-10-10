"""Convert data/block_eval.csv to eval-runner items (regression proof only).

Writes benchmark/runs/legacy-items/block.jsonl. Pair with configs/legacy-block.json.
`legacy_gap_dur_s` keeps the CSV's gap_dur verbatim so the legacy rule
(stop at t >= gap_dur - 0.01) is evaluated on the identical float.
"""
import csv, json, os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
out_dir = os.path.join(BASE, "runs", "legacy-items")
os.makedirs(out_dir, exist_ok=True)
out = os.path.join(out_dir, "block.jsonl")
with open(os.path.join(BASE, "data", "block_eval.csv")) as f, open(out, "w") as o:
    for i, r in enumerate(csv.DictReader(f)):
        gs, gd = float(r["gap_start"]), float(r["gap_dur"])
        item = {"item_id": f"legacy-blk-{i:03d}", "clip_key": os.path.splitext(r["file"])[0],
                "audio": "audio/" + r["file"], "split": "exploratory", "group": "stuttered",
                "kind": "unfinished", "silence_start_s": gs, "resume_s": gs + gd,
                "turn_end_s": None, "observe_until_s": 3.0, "label_source": "energy_vad",
                "legacy_gap_dur_s": gd}
        o.write(json.dumps(item) + "\n")
print("wrote", out)
