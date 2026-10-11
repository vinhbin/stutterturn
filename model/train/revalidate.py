"""Re-run the current in-loop validation on saved checkpoints (no training).

  python model/train/revalidate.py --haan H --work W --runs R1 R2 R3 R4

Used when the in-loop metric set changes after runs finished (spec rev 265ab02 added
in-loop M3). For each run it scores step 0 (stock FP32, the same initial state) and every
saved checkpoint with train.validate(), writing W/runs/<run>/metrics_reval.jsonl. The
original metrics.jsonl is never modified.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402
import train as T  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--haan", required=True)
    ap.add_argument("--work", required=True)
    ap.add_argument("--runs", nargs="+", required=True)
    a = ap.parse_args()
    import torch
    load_from_onnx, SmartTurnModel = C.import_haan(a.haan)
    device = T.pick_device()
    D = T.load_data(a.work)
    stock = load_from_onnx(C.stock_fp32_path(a.work)).to(device)
    base = T.validate(stock, D, device)
    for run in a.runs:
        rd = os.path.join(a.work, "runs", run)
        out = os.path.join(rd, "metrics_reval.jsonl")
        if os.path.exists(out):
            sys.exit(f"REFUSING: {out} exists")
        orig = [json.loads(l) for l in open(os.path.join(rd, "metrics.jsonl"))]
        recs = [{"step": 0, "epoch": 0.0, "kind": "validation", "source": "revalidate", **base}]
        for r in orig:
            if r["kind"] != "checkpoint":
                continue
            path = os.path.join(rd, r["ckpt"])
            if C.sha256_file(path) != r["ckpt_sha256"]:
                sys.exit(f"{path}: hash differs from metrics.jsonl")
            m = SmartTurnModel()
            m.load_state_dict(torch.load(path, map_location="cpu", weights_only=False)["state_dict"])
            m = m.to(device)
            recs.append({"step": r["step"], "epoch": r["epoch"], "kind": "checkpoint", "ckpt": r["ckpt"],
                         "ckpt_sha256": r["ckpt_sha256"], "source": "revalidate", **T.validate(m, D, device)})
        with open(out, "w") as f:
            for rec in recs:
                f.write(json.dumps(rec) + "\n")
        print(f"{run}: {len(recs) - 1} checkpoints revalidated -> {out}")


if __name__ == "__main__":
    main()
