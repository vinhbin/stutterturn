"""Fetch pinned model weights and a few SEP-28k source clips for the agent.

usage: python agent/fetch_assets.py [N_CLIPS_PER_SET]

Weights go to agent/models/ (gitignored) and are checked against pinned SHA-256.
Clips go to benchmark/audio/ (gitignored), the same place as the benchmark scripts.
"""
import csv
import hashlib
import os
import shutil
import sys
import urllib.request

from huggingface_hub import hf_hub_download

AGENT = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(AGENT)
MODELS = os.path.join(AGENT, "models")
AUDIO = os.path.join(ROOT, "benchmark", "audio")
DATA = os.path.join(ROOT, "benchmark", "data")

SMART_TURN_REPO = "pipecat-ai/smart-turn-v3"
SMART_TURN_REV = "f766f81d3cfdf7737ac64aad813d91bbfd56bf93"
# INT8 (stock) and FP32 (stock_fp32, comparator for candidates); hashes from model/CONTRACT.md
SMART_TURN_FILES = {
    "smart-turn-v3.2-cpu.onnx": "2bb026316b14a660486a75b1733cd3fbab8c2fd0314dc9af7be49f8cca967e4f",
    "smart-turn-v3.2-gpu.onnx": "ab8dc64b88713f90b571c15b714bd1330e6c883cad8763dacf65c9376dc539be",
}

SILERO_URL = "https://github.com/snakers4/silero-vad/raw/v5.1.2/src/silero_vad/data/silero_vad.onnx"
SILERO_FILE = "silero_vad.onnx"
SILERO_SHA256 = "2623a2953f6ff3d2c1e61740c6cdb7168133479b267dfef114a4a3cc5bdd788f"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def fetch_models():
    os.makedirs(MODELS, exist_ok=True)
    for name, pinned in SMART_TURN_FILES.items():
        dest = os.path.join(MODELS, name)
        if not os.path.exists(dest):
            src = hf_hub_download(SMART_TURN_REPO, name, revision=SMART_TURN_REV)
            shutil.copyfile(src, dest)
        got = sha256(dest)
        if got != pinned:
            sys.exit(f"{name}: SHA-256 {got} does not match pinned {pinned}")
        print(f"{name} ok {got}")

    dest = os.path.join(MODELS, SILERO_FILE)
    if not os.path.exists(dest):
        urllib.request.urlretrieve(SILERO_URL, dest)
    got = sha256(dest)
    if got != SILERO_SHA256:
        sys.exit(f"{SILERO_FILE}: SHA-256 {got} does not match pinned {SILERO_SHA256}")
    print(f"{SILERO_FILE} ok {got}")


def fetch_clips(n):
    os.makedirs(AUDIO, exist_ok=True)
    for name in ("block_eval.csv", "fluent_eval.csv"):
        with open(os.path.join(DATA, name), newline="") as f:
            rows = list(csv.DictReader(f))[:n]
        for row in rows:
            dest = os.path.join(AUDIO, row["file"])
            if os.path.exists(dest):
                continue
            src = hf_hub_download("miosipof/sep28k_full",
                                  f"data/{row['Show']}/{row['file']}", repo_type="dataset")
            shutil.copyfile(src, dest)
        print(f"{name}: {len(rows)} clips in benchmark/audio/")


if __name__ == "__main__":
    fetch_models()
    fetch_clips(int(sys.argv[1]) if len(sys.argv) > 1 else 5)
