"""Pre-registered checkpoint pre-screen (training-v1.md section 4, rev 265ab02).

  python model/train/prescreen.py --work W --runs R1 R2 [R3 R4] [--out NAME.json]

Ranks every checkpoint of the given runs by in-loop dev stutter premature (lower is
better) among those meeting the in-loop constraints against step 0 (= stock FP32):
  M2  dev fluent premature            <= step 0 + 0.010
  M3  dev end-of-window first-check decide >= step 0 - 0.020   (added in rev 265ab02)
  M4  guard recall                    >= step 0 - 0.010
Ties go to the earlier checkpoint. Reads metrics_reval.jsonl when present (revalidate.py),
otherwise metrics.jsonl (which must then contain in-loop M3). Prints the full ranking and
the top 2; writes W/<out> and refuses to overwrite. Only the top 2 go to export and section 6.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

M3 = "dev_eow_first_check_decide"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--runs", nargs="+", required=True)
    ap.add_argument("--out", default="prescreen.json")
    a = ap.parse_args()
    out_path = os.path.join(a.work, a.out)
    if os.path.exists(out_path):
        sys.exit(f"REFUSING: {out_path} exists")
    rows = []
    for run in a.runs:
        run_dir = os.path.join(a.work, "runs", run)
        src = "metrics_reval.jsonl" if os.path.exists(os.path.join(run_dir, "metrics_reval.jsonl")) \
            else "metrics.jsonl"
        recs = [json.loads(l) for l in open(os.path.join(run_dir, src))]
        if M3 not in recs[0]:
            sys.exit(f"{run}/{src} lacks in-loop M3; run revalidate.py first")
        base = next(r for r in recs if r["step"] == 0)
        for r in recs:
            if r["kind"] != "checkpoint":
                continue
            d_flu = r["dev_fluent_premature"] - base["dev_fluent_premature"]
            d_m3 = r[M3] - base[M3]
            d_rec = r["guard_recall"] - base["guard_recall"]
            ok = d_flu <= 0.010 + 1e-9 and d_m3 >= -0.020 - 1e-9 and d_rec >= -0.010 - 1e-9
            rows.append({"run": run, "ckpt": r["ckpt"], "epoch": r["epoch"], "step": r["step"],
                         "metrics_source": src,
                         "dev_stutter_premature": r["dev_stutter_premature"],
                         "base_dev_stutter_premature": base["dev_stutter_premature"],
                         "d_dev_fluent_premature": round(d_flu, 4),
                         M3: r[M3], "base_" + M3: base[M3], "d_" + M3: round(d_m3, 4),
                         "d_guard_recall": round(d_rec, 4), "guard_specificity": r["guard_specificity"],
                         "meets_constraints": ok})
    eligible = sorted([r for r in rows if r["meets_constraints"]],
                      key=lambda r: (r["dev_stutter_premature"], r["epoch"], r["run"]))
    top2 = eligible[:2]
    out = {"rule": "lowest in-loop dev stutter premature among checkpoints with d_dev_fluent_premature "
                   "<= +0.010, d_dev_eow_first_check_decide >= -0.020 and d_guard_recall >= -0.010 vs "
                   "step 0; ties -> earlier (training-v1.md rev 265ab02)",
           "ranking": rows, "eligible_order": [f"{r['run']}/{r['ckpt']}" for r in eligible],
           "top2": [f"{r['run']}/{r['ckpt']}" for r in top2], "code_commit": C.git_commit()}
    C.write_json(out_path, out)
    for r in sorted(rows, key=lambda r: (not r["meets_constraints"], r["dev_stutter_premature"], r["epoch"])):
        print(f"{'OK ' if r['meets_constraints'] else 'no '} {r['run']}/{r['ckpt']:16s} "
              f"stu={r['dev_stutter_premature']:.4f} (base {r['base_dev_stutter_premature']:.4f}) "
              f"dflu={r['d_dev_fluent_premature']:+.4f} m3={r[M3]:.4f} (base {r['base_' + M3]:.4f}, "
              f"d {r['d_' + M3]:+.4f}) drec={r['d_guard_recall']:+.4f}")
    print("TOP 2:", out["top2"] or "none eligible")


if __name__ == "__main__":
    main()
