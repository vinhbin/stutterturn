#!/usr/bin/env python
"""X1 preflight: integrity gates for the pre-registered blend check (model/specs/x1-blend-check-v1.md v1.1).

Asserts identity (exact SHA-256), a clean tree at the signed commit, absent outputs and the D-009
seal on the EXECUTING machine. Performs no scoring, no export and no model load. Exit 0 = all pass.

Usage:
  python model/train/preflight_x1.py --work <work-dir> --expect-head <signed commit sha>
"""
import argparse, hashlib, importlib, json, os, subprocess, sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EXPORT_NAME = "stutterturn-x1-rX4-blend-a0.75-W3ee1.00"

# (label, path relative to --work ("W") or the repo ("R"), exact sha256) — spec §2
PINS = [
    ("candidate blend-a0.75-W3ee1.00.pt", "W", "runs/X4/blend-a0.75-W3ee1.00.pt",
     "612df85bd3fd0570d4515ed45a37acf299473842ce5017a3b2c00b1c989c74b3"),
    ("blend source W3/ckpt-e1.00.pt", "W", "runs/W3/ckpt-e1.00.pt",
     "1a60eb6789244e2422fb6724601ce7d3e0d1e0c7dfaa2989cb393b7f6e3507f3"),
    ("X4 config.json", "W", "runs/X4/config.json",
     "810e262ab2e82e83b4c788fafc9e96e108ee86ed32d791226d6fabfd16e8ae64"),
    ("X4 metrics.jsonl", "W", "runs/X4/metrics.jsonl",
     "59cc83fff0351e7af0de41356ad4064bf8d102daa0b29a7af1b37567addaab29"),
    ("data-v2 manifest.json", "W", "data-v2/manifest.json",
     "92c11eb3da502162f4321e221c18142098d3c8dc312d917d8478cfb01a8ebcee"),
    ("stock guard stock-fp32.json", "W", "guard/stock-fp32.json",
     "5be10cddd69aef2be90896d2601d19cab7c5c3e7aec16bbd2f824a24737e7883"),
    ("stock FP32", "R", "agent/models/smart-turn-v3.2-gpu.onnx",
     "ab8dc64b88713f90b571c15b714bd1330e6c883cad8763dacf65c9376dc539be"),
    ("stock INT8", "R", "agent/models/smart-turn-v3.2-cpu.onnx",
     "2bb026316b14a660486a75b1733cd3fbab8c2fd0314dc9af7be49f8cca967e4f"),
    ("Silero VAD", "R", "agent/models/silero_vad.onnx",
     "2623a2953f6ff3d2c1e61740c6cdb7168133479b267dfef114a4a3cc5bdd788f"),
    ("items/v1 dev.jsonl", "R", "benchmark/items/v1/dev.jsonl",
     "742b645ba7213fecc0753d6c10376e330673b70c0d21d59881f0ca442e962ee3"),
    ("items/v1 dev_end_of_window.jsonl", "R", "benchmark/items/v1/dev_end_of_window.jsonl",
     "e30a456895cd61dd203fee319c864a9014097f720581a1fe87611cf6d7f52905"),
]

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


def git(*args):
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, check=True).stdout.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--expect-head", required=True, help="the commit Niko signed off (full or short sha)")
    a = ap.parse_args()
    w = a.work
    print("== X1 preflight (spec: model/specs/x1-blend-check-v1.md v1.1) ==")

    # 1. Clean tree at the signed commit
    head = git("rev-parse", "HEAD")
    check("HEAD is the signed commit", head.startswith(a.expect_head.lower()), f"HEAD={head}")
    dirty = git("status", "--porcelain", "--", "model/", "benchmark/scripts/")
    check("clean tree under model/ and benchmark/scripts/", not dirty, dirty.replace("\n", "; ") or "clean")

    # 2. Identity of every frozen input
    for label, base, rel, expected in PINS:
        path = os.path.join(w if base == "W" else REPO, rel)
        if not os.path.isfile(path):
            check(label, False, f"missing: {path}")
            continue
        got = sha256(path)
        check(label, got == expected, f"sha256={got[:16]}… expected={expected[:16]}…")
    pre = os.path.join(REPO, "model", "specs", "x1", "prescreen-x1.json")
    try:
        top2 = json.load(open(pre)).get("top2")
        check("frozen prescreen-x1.json top2", top2 == ["X4/blend-a0.75-W3ee1.00.pt"],
              f"top2={top2}, sha256={sha256(pre)} (recorded)")
    except Exception as e:  # noqa: BLE001
        check("frozen prescreen-x1.json top2", False, repr(e))

    # 3. One execution ever: outputs must not exist yet
    outs = [os.path.join(w, "exports", EXPORT_NAME + ext) for ext in (".onnx", ".json")] + \
           [os.path.join(w, "guard", EXPORT_NAME + ".json"), os.path.join(REPO, "benchmark", "selection", "sel-x1")]
    present = [p for p in outs if os.path.exists(p)]
    check("X1 outputs absent (first and only execution)", not present, "; ".join(present) or "none present")

    # 4. Reserved-test seal: no reserved-test item files under --work
    leaked = [os.path.join(root, f) for root, _d, files in os.walk(w) for f in files
              if f in ("test.jsonl", "test_end_of_window.jsonl")]
    check("D-009 seal (no reserved-test items under --work)", not leaked, "; ".join(leaked) or "none found")

    # 5. Environment
    for mod in ("torch", "onnxruntime", "transformers", "numpy", "soundfile"):
        try:
            m = importlib.import_module(mod)
            check(f"import {mod}", True, getattr(m, "__version__", "?"))
        except Exception as e:  # noqa: BLE001
            check(f"import {mod}", False, repr(e))

    failed = [n for n, ok, _ in results if not ok]
    print(json.dumps({"preflight": "x1", "spec": "v1.1", "head": head, "pass": not failed, "failed_gates": failed}))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
