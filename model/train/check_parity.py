"""Section 8 check 2: the haan-recovered model (CPU torch) matches stock FP32 ONNX
within 5e-5 on real dev-item cuts (silence start + 0.2 s).

  python model/train/check_parity.py --haan H --work W [--n 3]
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402
from export import check_features  # noqa: E402

TOL = 5e-5


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--haan", required=True)
    ap.add_argument("--work", required=True)
    ap.add_argument("--n", type=int, default=3)
    ap.add_argument("--items", default=os.path.join(C.BENCH, "items", "v1", "dev.jsonl"))
    a = ap.parse_args()
    load_from_onnx, _ = C.import_haan(a.haan)
    onnx_path = C.stock_fp32_path(a.work)
    model = load_from_onnx(onnx_path).eval()
    feats = check_features(a.items, a.n)
    p_torch = C.torch_probs(model, feats)
    p_ort = C.ort_probs(C.ort_session(onnx_path), feats)
    err = float(np.max(np.abs(p_torch - p_ort)))
    ok = err < TOL
    print(json.dumps({"check": 2, "n": len(feats), "torch": p_torch.round(6).tolist(),
                      "ort": p_ort.round(6).tolist(), "max_abs_error": err, "tol": TOL,
                      "passed": ok}))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
