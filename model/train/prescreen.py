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
    ap.add_argument("--v2", action="store_true",
                    help="training-v2 rule: also M3s >= step0 - 0.020 and M3-crop >= step0 - 0.020")
    ap.add_argument("--v3", action="store_true", help="training-v3: the v2 rule unchanged, cited as training-v3")
    ap.add_argument("--v4", action="store_true", help="proposed v4 (interpolation): the v2 rule unchanged")
    a = ap.parse_args()
    a.v2 = a.v2 or a.v3 or a.v4
    extra = [("dev_stu_completed_decide", "M3s"), ("dev_eow_crop_decide", "M3-crop")] if a.v2 else []
    out_path = os.path.join(a.work, a.out)
    if os.path.exists(out_path):
        sys.exit(f"REFUSING: {out_path} exists")
    rows = []
    for run in a.runs:
        run_dir = os.path.join(a.work, "runs", run)
        src = "metrics_reval.jsonl" if os.path.exists(os.path.join(run_dir, "metrics_reval.jsonl")) \
            else "metrics.jsonl"
        recs = [json.loads(l) for l in open(os.path.join(run_dir, src))]
        for key in [M3] + [k for k, _ in extra]:
            if key not in recs[0]:
                sys.exit(f"{run}/{src} lacks in-loop {key}; run revalidate.py first")
        base = next(r for r in recs if r["step"] == 0)
        for r in recs:
            if r["kind"] != "checkpoint":
                continue
            d_flu = r["dev_fluent_premature"] - base["dev_fluent_premature"]
            d_m3 = r[M3] - base[M3]
            d_rec = r["guard_recall"] - base["guard_recall"]
            ok = d_flu <= 0.010 + 1e-9 and d_m3 >= -0.020 - 1e-9 and d_rec >= -0.010 - 1e-9
            ext = {}
            for key, _ in extra:
                d = r[key] - base[key]
                ext[key], ext["base_" + key], ext["d_" + key] = r[key], base[key], round(d, 4)
                ok = ok and d >= -0.020 - 1e-9
            rows.append({"run": run, "ckpt": r["ckpt"], "epoch": r["epoch"], "step": r["step"],
                         "metrics_source": src,
                         "dev_stutter_premature": r["dev_stutter_premature"],
                         "base_dev_stutter_premature": base["dev_stutter_premature"],
                         "d_dev_fluent_premature": round(d_flu, 4),
                         M3: r[M3], "base_" + M3: base[M3], "d_" + M3: round(d_m3, 4),
                         "d_guard_recall": round(d_rec, 4), "guard_specificity": r["guard_specificity"],
                         **ext, "meets_constraints": ok})
    eligible = sorted([r for r in rows if r["meets_constraints"]],
                      key=lambda r: (r["dev_stutter_premature"], r["epoch"], r["run"]))
    top2 = eligible[:2]
    rule = ("lowest in-loop dev stutter premature among checkpoints with d_dev_fluent_premature "
            "<= +0.010, d_dev_eow_first_check_decide >= -0.020 and d_guard_recall >= -0.010 vs "
            "step 0; ties -> earlier (training-v1.md rev 265ab02)")
    if a.v2:
        rule = ("lowest in-loop dev stutter premature among checkpoints with d_dev_fluent_premature "
                "<= +0.010, d_dev_eow_first_check_decide >= -0.020, d_dev_stu_completed_decide (M3s) "
                ">= -0.020, d_dev_eow_crop_decide (M3-crop) >= -0.020 and d_guard_recall >= -0.010 vs "
                "step 0; ties -> earlier (training-v2.md section 4)")
    if a.v3:
        rule = rule.replace("(training-v2.md section 4)",
                            "(training-v3.md section 4: training-v2.md section 4 unchanged)")
    if a.v4:
        rule = rule.replace("(training-v2.md section 4)",
                            "(proposed v4, issue #2 comment 6103360382: training-v2.md section 4 unchanged)")
    out = {"rule": rule,
           "ranking": rows, "eligible_order": [f"{r['run']}/{r['ckpt']}" for r in eligible],
           "top2": [f"{r['run']}/{r['ckpt']}" for r in top2], "code_commit": C.git_commit()}
    C.write_json(out_path, out)
    for r in sorted(rows, key=lambda r: (not r["meets_constraints"], r["dev_stutter_premature"], r["epoch"])):
        print(f"{'OK ' if r['meets_constraints'] else 'no '} {r['run']}/{r['ckpt']:16s} "
              f"stu={r['dev_stutter_premature']:.4f} (base {r['base_dev_stutter_premature']:.4f}) "
              f"dflu={r['d_dev_fluent_premature']:+.4f} m3={r[M3]:.4f} (base {r['base_' + M3]:.4f}, "
              f"d {r['d_' + M3]:+.4f}) drec={r['d_guard_recall']:+.4f}"
              + "".join(f" {lab}={r[k]:.4f}(d {r['d_' + k]:+.4f})" for k, lab in extra))
    print("TOP 2:", out["top2"] or "none eligible")


if __name__ == "__main__":
    main()
