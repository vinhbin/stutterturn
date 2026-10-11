"""Failure analysis (descriptive, dev/guard only): where do fine-tuned candidates lose M5?

Reproduces the numbers in the issue #2 failure-analysis comment from files on this branch:
  python model/evidence/2026-10-10/analysis/guard_flip_by_length.py
Optional training-length summary (needs the local work dir with data-v2/*.jsonl):
  python model/evidence/2026-10-10/analysis/guard_flip_by_length.py --work <st-train/work>

Inputs: guard/*.json (guard_eval per_row probabilities at full audio) and guard_meta.csv
(id, label, n_samples, dataset, synthetic, endfiller, midfiller from data-v2/guard.jsonl; no audio).
"lost" = stock p <= 0.5 and candidate p > T (a guard negative newly called complete).
No model is run; nothing touches the test set.
"""
import argparse
import csv
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
EV = os.path.dirname(HERE)
CANDS = {"v2 V2/e2.00": "stutterturn-v2-rV2-c2.00", "v3 W3/e1.00": "stutterturn-v3-rW3-c1.00",
         "v3 W3/e2.00": "stutterturn-v3-rW3-c2.00", "v4 blend 0.75xe2.00": "stutterturn-v4-rX4-blend-a0.75-W3ee2.00"}
BINS = [(0, 3), (3, 5), (5, 8), (8, 1e9)]


def probs(name):
    return {r["id"]: r["p_full"] for r in json.load(open(os.path.join(EV, "guard", name + ".json")))["per_row"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", help="optional: st-train work dir for training clip lengths")
    ap.add_argument("--threshold", type=float, default=0.6, help="candidate threshold for 'lost' (default 0.6)")
    a = ap.parse_args()
    meta = {r["id"]: r for r in csv.DictReader(open(os.path.join(HERE, "guard_meta.csv"), newline=""))}
    S = probs("stock-fp32")
    C = {k: probs(v) for k, v in CANDS.items()}
    negs = [i for i, m in meta.items() if m["label"] == "0"]
    poss = [i for i, m in meta.items() if m["label"] == "1"]
    dur = {i: int(meta[i]["n_samples"]) / 16000 for i in meta}
    T = a.threshold
    print(f"guard negatives {len(negs)}, positives {len(poss)}; lost = stock<=0.5 and candidate>{T}\n")
    print("Mean change in p(complete) vs stock FP32, and lost negatives, by clip length (guard negatives):")
    print(f"{'length':8s} {'n':>5s}  " + "  ".join(f"{k:>24s}" for k in CANDS))
    for lo, hi in BINS:
        ids = [i for i in negs if lo <= dur[i] < hi]
        cells = []
        for k in CANDS:
            dp = np.mean([C[k][i] - S[i] for i in ids])
            lost = sum(S[i] <= 0.5 and C[k][i] > T for i in ids)
            cells.append(f"dp {dp:+.3f}, lost {lost:2d}")
        lab = f"{lo}-{hi}s" if hi < 1e9 else f">={lo}s"
        print(f"{lab:8s} {len(ids):5d}  " + "  ".join(f"{c:>24s}" for c in cells))
    print("\nMean change on guard positives (all lengths):",
          {k: round(float(np.mean([C[k][i] - S[i] for i in poss])), 4) for k in CANDS})
    common = [i for i in negs if S[i] <= 0.5 and all(C[k][i] > T for k in CANDS)]
    print(f"\nNegatives lost by all {len(CANDS)} candidates at {T}: {len(common)}")
    for i in sorted(common, key=lambda i: dur[i]):
        m = meta[i]
        print(f"  {m['dataset']:22s} synthetic={m['synthetic']:5s} {dur[i]:5.2f}s  stock {S[i]:.3f} -> "
              + ", ".join(f"{C[k][i]:.2f}" for k in CANDS))
    if a.work:
        print("\nTraining clip lengths (model input seconds):")
        for fn in ("sep_pos.jsonl", "stutter_neg.jsonl", "orig_replay.jsonl"):
            L = []
            for line in open(os.path.join(a.work, "data-v2", fn)):
                r = json.loads(line)
                if r.get("keep_samples"):
                    L.append(min(r["keep_samples"], r["cut_samples"]) / 16000)
                elif "cut_samples" in r:
                    L.append(r["cut_samples"] / 16000)
                else:
                    L.append(r["n_samples"] / 16000)
            L = np.array(L)
            print(f"  {fn:18s} n={len(L):6d} median {np.median(L):.2f}s, share < 4 s {np.mean(L < 4):.2f}")
        rep = [json.loads(l) for l in open(os.path.join(a.work, "data-v2", "orig_replay.jsonl"))]
        rn = np.array([r["n_samples"] / 16000 for r in rep if r["label"] == 0])
        print(f"  replay negatives   n={len(rn):6d} median {np.median(rn):.2f}s, share < 4 s {np.mean(rn < 4):.2f}")


if __name__ == "__main__":
    main()
