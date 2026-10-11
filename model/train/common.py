"""Shared pieces of the training harness (model/specs/training-v1.md).

Preprocessing is byte-for-byte the benchmark's (benchmark/scripts/eval_runner.py
Model.predict): last 8 s, left zero-pad, WhisperFeatureExtractor(chunk_length=8),
do_normalize=True. haan is imported from a pinned checkout passed with --haan.
"""
import hashlib
import json
import os
import subprocess
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BENCH = os.path.join(ROOT, "benchmark")
SR = 16000
N_SAMPLES = 8 * SR

HAAN_COMMIT = "540f97de03f8eb938b871196752206f6d0698791"
SMART_TURN_REPO = "pipecat-ai/smart-turn-v3"
SMART_TURN_REV = "f766f81d3cfdf7737ac64aad813d91bbfd56bf93"
STOCK_FP32_FILE = "smart-turn-v3.2-gpu.onnx"
STOCK_FP32_SHA256 = "ab8dc64b88713f90b571c15b714bd1330e6c883cad8763dacf65c9376dc539be"
STOCK_INT8_SHA256 = "2bb026316b14a660486a75b1733cd3fbab8c2fd0314dc9af7be49f8cca967e4f"


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def git_commit():
    try:
        sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
                             text=True, check=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain", "--", "model/train/"], cwd=ROOT,
                               capture_output=True, text=True, check=True).stdout.strip()
        return sha + ("-dirty" if dirty else "")
    except Exception:
        return "unknown"


def import_haan(haan_dir):
    """Put the pinned haan checkout on sys.path after verifying its commit."""
    head = subprocess.run(["git", "-C", haan_dir, "rev-parse", "HEAD"], capture_output=True,
                          text=True).stdout.strip()
    if head != HAAN_COMMIT:
        sys.exit(f"haan checkout at {head or '?'}, expected {HAAN_COMMIT}")
    diff = subprocess.run(["git", "-C", haan_dir, "diff", "HEAD", "--", "haan/model.py",
                           "haan/convert.py"], capture_output=True, text=True).stdout.strip()
    if diff:
        sys.exit("haan checkout has local modifications to model.py/convert.py")
    if haan_dir not in sys.path:
        sys.path.insert(0, haan_dir)
    from haan.convert import load_from_onnx
    from haan.model import SmartTurnModel
    return load_from_onnx, SmartTurnModel


def stock_fp32_path(work):
    """Download (once) and verify the stock FP32 ONNX into <work>/models/."""
    d = os.path.join(work, "models")
    os.makedirs(d, exist_ok=True)
    dest = os.path.join(d, STOCK_FP32_FILE)
    if not os.path.exists(dest):
        import shutil
        from huggingface_hub import hf_hub_download
        src = hf_hub_download(SMART_TURN_REPO, STOCK_FP32_FILE, revision=SMART_TURN_REV)
        shutil.copyfile(src, dest + ".part")
        os.replace(dest + ".part", dest)
    got = sha256_file(dest)
    if got != STOCK_FP32_SHA256:
        sys.exit(f"{dest}: SHA-256 {got} != pinned {STOCK_FP32_SHA256}")
    return dest


_FE = None


def feature_extractor():
    global _FE
    if _FE is None:
        from transformers import WhisperFeatureExtractor
        _FE = WhisperFeatureExtractor(chunk_length=8)
    return _FE


def features(audio):
    """float32 [80, 800] for one mono 16 kHz cut, exactly as eval_runner.Model.predict."""
    audio = np.asarray(audio, dtype=np.float32)
    if len(audio) > N_SAMPLES:
        audio = audio[-N_SAMPLES:]
    elif len(audio) < N_SAMPLES:
        audio = np.pad(audio, (N_SAMPLES - len(audio), 0), mode="constant")
    inp = feature_extractor()(audio, sampling_rate=SR, return_tensors="np", padding="max_length",
                              max_length=N_SAMPLES, truncation=True, do_normalize=True)
    return inp.input_features.squeeze(0).astype(np.float32)


def read_audio(path):
    import soundfile as sf
    x, sr = sf.read(path, dtype="float32")
    if x.ndim > 1:
        x = x.mean(axis=1).astype(np.float32)
    if sr != SR:
        raise ValueError(f"{path}: {sr} Hz, expected {SR}")
    return x


def ort_session(path):
    import onnxruntime as ort
    so = ort.SessionOptions()
    so.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
    so.inter_op_num_threads = 1
    so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    return ort.InferenceSession(path, sess_options=so, providers=["CPUExecutionProvider"])


def ort_probs(sess, feats):
    """feats [B, 80, 800] -> probabilities [B]."""
    return sess.run(None, {"input_features": np.asarray(feats, dtype=np.float32)})[0].reshape(-1)


def torch_probs(model, feats, device="cpu"):
    import torch
    with torch.no_grad():
        x = torch.from_numpy(np.asarray(feats, dtype=np.float32)).to(device)
        return torch.sigmoid(model(x)).reshape(-1).cpu().numpy()


def export_onnx(model, out_path, check_feats):
    """Section 5: eval-mode sigmoid wrapper, opset 18, legacy exporter, checker, and ORT
    parity < 1e-5 against PyTorch (CPU) at B = 1 and 2 on real features. Returns a report."""
    import onnx
    import torch

    class Wrapper(torch.nn.Module):
        def __init__(self, inner):
            super().__init__()
            self.inner = inner

        def forward(self, input_features):
            return torch.sigmoid(self.inner(input_features)).reshape(-1, 1)

    if os.path.exists(out_path):
        sys.exit(f"REFUSING: export target exists: {out_path}")
    model = model.to("cpu").eval()
    wrapper = Wrapper(model).eval()
    feats = np.asarray(check_feats, dtype=np.float32)
    example = torch.from_numpy(feats[:1])
    tmp = out_path + ".part"
    torch.onnx.export(wrapper, (example,), tmp, input_names=["input_features"],
                      output_names=["logits"],
                      dynamic_axes={"input_features": {0: "batch"}, "logits": {0: "batch"}},
                      opset_version=18, dynamo=False)
    onnx.checker.check_model(onnx.load(tmp))
    sess = ort_session(tmp)
    parity = []
    for b in (1, 2):
        x = feats[:b]
        err = float(np.max(np.abs(ort_probs(sess, x) - torch_probs(model, x))))
        parity.append({"batch_size": b, "max_abs_prob_error": err})
        if not err < 1e-5:
            os.remove(tmp)
            sys.exit(f"export parity failed at B={b}: {err:.3e} >= 1e-5")
    os.replace(tmp, out_path)
    return {"path": out_path, "sha256": sha256_file(out_path), "opset": 18,
            "onnx_checker_passed": True, "parity": parity}


def write_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1)
