"""Guard-set evaluation of an ONNX model (training-v1.md sections 2c and 6: M4, M4b, M5).

  python model/train/guard_eval.py --work W --model W/exports/X.onnx --expected-sha256 HEX [--limit 50]

ORT + eval_runner preprocessing. M4 = recall on endpoint_bool=1 (full audio), M4b = recall
with positives cut at their energy speech end + 0.2 s (eval-items energy rule), M5 =
specificity on endpoint_bool=0 (full audio). Full-audio clips end ~1 s (human) or
0.2-0.3 s (synthetic) after speech, so M4 is not a check at the deployed 0.2 s; M4b is
closer. The guard set is not trained on, but may have informed upstream checkpoint choice.
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

sys.path.insert(0, os.path.join(C.BENCH, "scripts"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--expected-sha256", required=True)
    ap.add_argument("--threshold", type=float, default=0.5)
    ap.add_argument("--limit", type=int, help="first N guard rows only (check 6)")
    ap.add_argument("--out", help="write results JSON here")
    a = ap.parse_args()
    import build_eval_sets as bes

    got = C.sha256_file(a.model)
    if got != a.expected_sha256.lower():
        sys.exit(f"model hash mismatch: {got} != {a.expected_sha256}")
    rows = [json.loads(l) for l in open(os.path.join(a.work, "data", "guard.jsonl")) if l.strip()]
    if a.limit:
        rows = rows[:a.limit]
    sess = C.ort_session(a.model)
    p_full, p_cut, cut_skipped = [], [], 0
    for r in rows:
        path = os.path.join(a.work, r["audio"])
        x = C.read_audio(path)
        p_full.append(float(C.ort_probs(sess, C.features(x)[None])[0]))
        if r["label"] == 1:
            ft = bes.fluent_features(bes.analyze(path))
            if ft is None:
                cut_skipped += 1
                p_cut.append(None)
                continue
            cut = min(int(round((ft["speech_end"] + 0.2) * C.SR)), len(x))
            p_cut.append(float(C.ort_probs(sess, C.features(x[:cut])[None])[0]))
        else:
            p_cut.append(None)
    y = np.array([r["label"] for r in rows])
    pf = np.array(p_full)
    pc = np.array([p for p, l in zip(p_cut, y) if l == 1 and p is not None])
    th = a.threshold
    res = {"model": os.path.basename(a.model), "model_sha256": got, "threshold": th, "n": len(rows),
           "n_pos": int((y == 1).sum()), "n_neg": int((y == 0).sum()),
           "M4_recall_full": round(float((pf[y == 1] > th).mean()), 4),
           "M4b_recall_end_plus_0.2": round(float((pc > th).mean()), 4) if len(pc) else None,
           "M4b_n": int(len(pc)), "M4b_skipped_no_speech": cut_skipped,
           "M5_specificity_full": round(float((pf[y == 0] <= th).mean()), 4),
           "synthetic_n": int(sum(bool(r["synthetic"]) for r in rows))}
    if a.out:
        C.write_json(a.out, {**res, "per_row": [{"id": r["id"], "label": int(r["label"]), "p_full": round(p, 6),
                                                 "p_cut": None if q is None else round(q, 6)}
                                                for r, p, q in zip(rows, p_full, p_cut)]})
    print(json.dumps(res))


if __name__ == "__main__":
    main()
