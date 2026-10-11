#!/usr/bin/env python
"""X1 preflight: integrity gates for the pre-registered blend check (model/specs/x1-blend-check-v1.md).

Verifies hashes, environment, and input completeness on the EXECUTING machine.
Performs no scoring, no export, no model load. Exit 0 = all gates pass.

Usage:
  python model/train/preflight_x1.py --work <work-dir> [--repo <repo-root>]

<work-dir> is the training work directory (e.g. C:/Users/Guttu/st-train/work
on Guttuu's machine, or the transferred copy per spec Appendix A).
"""
import argparse, hashlib, importlib, json, os, sys

CANDIDATE_SHA = "612df85bd3fd0570d4515ed45a37acf299473842ce5017a3b2c00b1c989c74b3"
W3_SOURCE_SHA = "1a60eb6789244e2422fb6724601ce7d3e0d1e0c7dfaa2989cb393b7f6e3507f3"
STOCK_FP32_SHA = "ab8dc64b88713f90b571c15b714bd1330e6c883cad8763dacf65c9376dc539be"

results = []

def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
    return ok

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()

def file_gate(name, path, expected=None):
    if not os.path.isfile(path):
        return check(name, False, f"missing: {path}")
    digest = sha256(path)
    if expected is None:
        return check(name, True, f"present, sha256={digest[:16]}… (recorded)")
    return check(name, digest == expected,
                 f"sha256={digest[:16]}… expected={expected[:16]}…")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--repo", default=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    a = ap.parse_args()
    w, r = a.work, a.repo

    print("== X1 preflight (spec: model/specs/x1-blend-check-v1.md) ==")

    # 1. Frozen weights
    file_gate("candidate blend-a0.75-W3ee1.00.pt", os.path.join(w, "runs", "X4", "blend-a0.75-W3ee1.00.pt"), CANDIDATE_SHA)
    file_gate("blend source W3/ckpt-e1.00.pt", os.path.join(w, "runs", "W3", "ckpt-e1.00.pt"), W3_SOURCE_SHA)
    stock_candidates = [
        os.path.join(r, "agent", "models", "smart-turn-v3.2-gpu.onnx"),
        os.path.join(w, "models", "smart-turn-v3.2-gpu.onnx"),
    ]
    stock = next((p for p in stock_candidates if os.path.isfile(p)), stock_candidates[0])
    file_gate("stock FP32 comparator", stock, STOCK_FP32_SHA)

    # 2. v4 run metadata and reference files (presence + recorded hash)
    for name, rel in [
        ("X4 metrics.jsonl", os.path.join(w, "runs", "X4", "metrics.jsonl")),
        ("data-v2 manifest", os.path.join(w, "data", "manifest.json")),
        ("m3s refs", os.path.join(w, "data", "m3s_refs.json")),
        ("guard items", os.path.join(w, "data", "guard.jsonl")),
    ]:
        file_gate(name, rel)

    # 3. Repo-side item sets used by in-loop metrics
    for name, rel in [
        ("items/v1 dev.jsonl", os.path.join(r, "benchmark", "items", "v1", "dev.jsonl")),
        ("items/v1 dev_end_of_window.jsonl", os.path.join(r, "benchmark", "items", "v1", "dev_end_of_window.jsonl")),
        ("items/v1 manifest", os.path.join(r, "benchmark", "items", "v1", "manifest.json")),
    ]:
        file_gate(name, rel)

    # 4. Reserved-test seal: refuse to run if test items are anywhere under --work
    leaked = []
    for root, _dirs, files in os.walk(w):
        for f in files:
            if f in ("test.jsonl", "test_end_of_window.jsonl"):
                leaked.append(os.path.join(root, f))
    check("D-009 seal (no reserved-test items under --work)", not leaked,
          "; ".join(leaked) if leaked else "none found")

    # 5. Environment
    for mod in ("torch", "onnxruntime", "transformers", "numpy", "soundfile"):
        try:
            m = importlib.import_module(mod)
            check(f"import {mod}", True, getattr(m, "__version__", "?"))
        except Exception as e:
            check(f"import {mod}", False, repr(e))

    failed = [n for n, ok, _ in results if not ok]
    print(json.dumps({"preflight": "x1", "pass": not failed, "failed_gates": failed}))
    sys.exit(1 if failed else 0)

if __name__ == "__main__":
    main()
