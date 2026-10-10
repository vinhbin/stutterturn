"""Pre-registered checkpoint pre-screen (training-v1.md section 4, last paragraph).

  python model/train/prescreen.py --work W --runs R1 R2 [R3 R4]

Ranks every checkpoint of the given runs by in-loop dev stutter premature (lower is
better) among those meeting the in-loop constraints against the run's own step-0
validation (= stock FP32): dev fluent premature <= +1.0 point and guard recall >= -1.0
point (M2/M4). Ties go to the earlier checkpoint. Prints the full ranking and the top 2;
writes W/prescreen.json. Not a free choice: only the top 2 go to export and section 6.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--runs", nargs="+", required=True)
    a = ap.parse_args()
    rows = []
    for run in a.runs:
        recs = [json.loads(l) for l in open(os.path.join(a.work, "runs", run, "metrics.jsonl"))]
        base = next(r for r in recs if r["step"] == 0)
        for r in recs:
            if r["kind"] != "checkpoint":
                continue
            d_flu = r["dev_fluent_premature"] - base["dev_fluent_premature"]
            d_rec = r["guard_recall"] - base["guard_recall"]
            ok = d_flu <= 0.010 + 1e-9 and d_rec >= -0.010 - 1e-9
            rows.append({"run": run, "ckpt": r["ckpt"], "epoch": r["epoch"], "step": r["step"],
                         "dev_stutter_premature": r["dev_stutter_premature"],
                         "base_dev_stutter_premature": base["dev_stutter_premature"],
                         "d_dev_fluent_premature": round(d_flu, 4), "d_guard_recall": round(d_rec, 4),
                         "guard_specificity": r["guard_specificity"], "meets_constraints": ok})
    eligible = sorted([r for r in rows if r["meets_constraints"]],
                      key=lambda r: (r["dev_stutter_premature"], r["epoch"], r["run"]))
    top2 = eligible[:2]
    out = {"rule": "lowest in-loop dev stutter premature among checkpoints with "
                   "d_dev_fluent_premature <= +0.010 and d_guard_recall >= -0.010 vs step 0; ties -> earlier",
           "ranking": rows, "eligible_order": [f"{r['run']}/{r['ckpt']}" for r in eligible],
           "top2": [f"{r['run']}/{r['ckpt']}" for r in top2], "code_commit": C.git_commit()}
    C.write_json(os.path.join(a.work, "prescreen.json"), out)
    for r in sorted(rows, key=lambda r: (not r["meets_constraints"], r["dev_stutter_premature"], r["epoch"])):
        print(f"{'OK ' if r['meets_constraints'] else 'no '} {r['run']}/{r['ckpt']:16s} stu={r['dev_stutter_premature']:.4f} "
              f"(base {r['base_dev_stutter_premature']:.4f}) dflu={r['d_dev_fluent_premature']:+.4f} "
              f"drec={r['d_guard_recall']:+.4f} spec={r['guard_specificity']:.4f}")
    print("TOP 2:", out["top2"] or "none eligible")


if __name__ == "__main__":
    main()
