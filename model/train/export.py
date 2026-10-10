"""Export a checkpoint to ONNX + CONTRACT section 5 metadata (training-v1.md section 5).

  python model/train/export.py --haan H --work W --ckpt W/runs/R1/ckpt-e1.0.pt --name stutterturn-v1-rR1-c1.0
  python model/train/export.py --haan H --work W --zero-step --name zero-step-stock-fp32   # check 3

Output: W/exports/<name>.onnx and <name>.json. Refuses to overwrite. Parity: ORT vs
PyTorch < 1e-5 at B = 1 and 2 on real cuts from --check-items (default: dev stuttered
unfinished items, cut at silence start + 0.2 s).
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402


def check_features(items_path, n=2):
    feats = []
    for line in open(items_path):
        it = json.loads(line)
        if it.get("kind") != "unfinished":
            continue
        path = os.path.join(C.BENCH, it["audio"])
        if not os.path.exists(path):
            continue
        x = C.read_audio(path)
        cut = min(int(round((it["silence_start_s"] + 0.2) * C.SR)), len(x))
        feats.append(C.features(x[:cut]))
        if len(feats) == n:
            break
    if len(feats) < n:
        sys.exit(f"need {n} items with local audio in {items_path}")
    import numpy as np
    return np.stack(feats)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--haan", required=True)
    ap.add_argument("--work", required=True)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--ckpt")
    g.add_argument("--zero-step", action="store_true", help="export the untrained recovered stock FP32")
    ap.add_argument("--name", required=True)
    ap.add_argument("--check-items", default=os.path.join(C.BENCH, "items", "v1", "dev.jsonl"))
    ap.add_argument("--status", default="dev-candidate")
    a = ap.parse_args()

    import torch
    load_from_onnx, SmartTurnModel = C.import_haan(a.haan)
    out_dir = os.path.join(a.work, "exports")
    os.makedirs(out_dir, exist_ok=True)
    onnx_path = os.path.join(out_dir, a.name + ".onnx")
    meta_path = os.path.join(out_dir, a.name + ".json")
    for p in (onnx_path, meta_path):
        if os.path.exists(p):
            sys.exit(f"REFUSING: {p} exists")

    meta_src = {}
    if a.zero_step:
        model = load_from_onnx(C.stock_fp32_path(a.work))
        meta_src = {"source": "zero-step recovered stock-fp32", "run_id": None, "checkpoint": None}
    else:
        ck = torch.load(a.ckpt, map_location="cpu", weights_only=False)
        model = SmartTurnModel()
        model.load_state_dict(ck["state_dict"])
        meta_src = {"source": "checkpoint", "run_id": ck.get("run_id"), "checkpoint": os.path.basename(a.ckpt),
                    "checkpoint_sha256": C.sha256_file(a.ckpt), "step": ck.get("step"),
                    "epoch": ck.get("epoch"), "training_config": ck.get("config_sha256"),
                    "train_manifest_sha256": ck.get("train_manifest_sha256")}
    model.eval()

    feats = check_features(a.check_items)
    rep = C.export_onnx(model, onnx_path, feats)
    meta = {"model_id": a.name, "sha256": rep["sha256"], "base_model": "stock-fp32", "threshold": 0.5,
            "precision": "fp32", "train_manifest_sha256": meta_src.get("train_manifest_sha256"),
            "dev_manifest_sha256": C.sha256_file(a.check_items) if os.path.exists(a.check_items) else None,
            "training_config": meta_src.get("training_config"), "code_commit": C.git_commit(),
            "export": {"opset": 18, "sigmoid_wrapper": True, "eval_mode": True, "dynamo": False},
            "parity_max_abs_error": max(p["max_abs_prob_error"] for p in rep["parity"]),
            "parity": rep["parity"], "status": a.status, "provenance": meta_src,
            "license": "non-commercial research use (training data includes SEP-28k, CC BY-NC 4.0)"}
    C.write_json(meta_path, meta)
    print(json.dumps({"onnx": onnx_path, "sha256": rep["sha256"], "parity": rep["parity"]}))


if __name__ == "__main__":
    main()
