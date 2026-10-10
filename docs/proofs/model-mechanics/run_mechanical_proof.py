"""Local synthetic mechanics proof; no stutter adaptation or real-audio acceptance."""
import argparse
import hashlib
import importlib.metadata
import json
import pathlib
import platform
import sys
import subprocess
import time
from datetime import datetime, timezone

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--source", type=pathlib.Path, required=True, help="Reviewed pinned haan checkout")
parser.add_argument("--model", type=pathlib.Path, required=True, help="Pinned official FP32 ONNX")
parser.add_argument("--output", type=pathlib.Path, required=True, help="Directory for local proof artifacts")
args = parser.parse_args()
SOURCE = args.source.resolve()
ROOT = args.output.resolve()
ROOT.mkdir(parents=True, exist_ok=True)
SCRIPT = pathlib.Path(__file__).resolve()
source_commit = subprocess.check_output(["git", "-C", str(SOURCE), "rev-parse", "HEAD"], text=True).strip()
assert source_commit == "540f97de03f8eb938b871196752206f6d0698791", source_commit
assert not subprocess.check_output(["git", "-C", str(SOURCE), "diff", "HEAD", "--", "haan/model.py", "haan/convert.py", "tests/test_convert.py"], text=True).strip(), "Pinned proof source has modifications"
sys.path.insert(0, str(SOURCE))
import numpy as np
import onnx
import onnxruntime as ort
import torch
from haan.convert import load_from_onnx
from haan.model import SmartTurnModel

started = time.perf_counter()
torch.set_num_threads(4)
torch.manual_seed(0)
onnx_path = args.model.resolve()
expected_hash = "ab8dc64b88713f90b571c15b714bd1330e6c883cad8763dacf65c9376dc539be"
sha256 = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha256(onnx_path) == expected_hash
assert torch.version.cuda is None
evidence = {
    "scope": "synthetic mechanical recovery, backward/update, save/reload, and ONNX export proof only",
    "excluded_claims": ["stutter adaptation", "real audio accuracy", "demo acceptance", "drop-in runtime acceptance"],
    "utc_started": datetime.now(timezone.utc).isoformat(),
    "python": sys.version,
    "platform": platform.platform(),
    "source_commit": source_commit,
    "model_revision": "f766f81d3cfdf7737ac64aad813d91bbfd56bf93",
    "model_sha256": expected_hash,
    "versions": {p: importlib.metadata.version(p) for p in ["torch", "transformers", "onnx", "onnxruntime", "numpy", "pytest", "onnxscript"]},
    "cuda": torch.version.cuda,
}
def record(key, value):
    evidence[key] = value
    (ROOT / "evidence.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(key, json.dumps(value), flush=True)

opts = ort.SessionOptions()
opts.intra_op_num_threads = 4
opts.inter_op_num_threads = 1
model = load_from_onnx(str(onnx_path)).eval()
x = np.random.default_rng(0).standard_normal((3, 80, 800)).astype(np.float32)
session = ort.InferenceSession(str(onnx_path), sess_options=opts, providers=["CPUExecutionProvider"])
expected = session.run(None, {"input_features": x})[0].reshape(-1)
with torch.no_grad():
    recovered = torch.sigmoid(model(torch.from_numpy(x))).numpy()
error = float(np.max(np.abs(expected - recovered)))
assert error < 1e-5, error
record("reconstruction_parity", {"shape": list(x.shape), "seed": 0, "max_abs_probability_error": error, "required_lt": 1e-5, "passed": True, "ort": expected.tolist(), "torch": recovered.tolist()})
torch.save(model.state_dict(), ROOT / "recovered-stock.pt")

features = torch.from_numpy(x[:2].copy())
targets = torch.tensor([0., 1.])
before = {name: param.detach().clone() for name, param in model.named_parameters() if param.requires_grad}
optimizer = torch.optim.SGD(model.parameters(), lr=1e-4)
model.train()
optimizer.zero_grad(set_to_none=True)
loss = torch.nn.functional.binary_cross_entropy_with_logits(model(features), targets)
assert torch.isfinite(loss)
loss.backward()
gradients = {name: p.grad for name, p in model.named_parameters() if p.requires_grad}
assert gradients and all(g is not None and torch.isfinite(g).all() for g in gradients.values())
nonzero_gradients = [name for name, g in gradients.items() if torch.count_nonzero(g).item() > 0]
assert nonzero_gradients
gradient_norm = float(torch.sqrt(sum((g.detach().double() ** 2).sum() for g in gradients.values())))
optimizer.step()
updates = {name: float((p.detach() - before[name]).abs().max()) for name, p in model.named_parameters() if name in before}
changed = {name: value for name, value in updates.items() if value > 0}
assert changed and any(name.startswith("encoder.") for name in changed) and any(name.startswith("classifier.") for name in changed)
assert all(torch.isfinite(p).all() for p in model.parameters())
record("synthetic_batch", {"shape": list(features.shape), "targets": targets.tolist(), "loss": float(loss.detach()), "optimizer": "SGD", "learning_rate": 1e-4, "steps": 1, "all_trainable_gradients_finite": True, "trainable_parameter_tensors": len(gradients), "nonzero_gradient_tensors": len(nonzero_gradients), "gradient_l2_norm": gradient_norm, "updated_parameter_tensors": len(changed), "max_abs_update": max(changed.values()), "encoder_updated": True, "classifier_updated": True})

model.eval()
checkpoint = ROOT / "synthetic-one-batch.pt"
torch.save(model.state_dict(), checkpoint)
reloaded = SmartTurnModel()
reloaded.load_state_dict(torch.load(checkpoint, map_location="cpu", weights_only=True), strict=True)
reloaded.eval()
with torch.no_grad():
    reload_error = float((model(features) - reloaded(features)).abs().max())
assert reload_error == 0
record("save_reload", {"max_abs_logit_error": reload_error, "strict": True, "weights_only": True, "sha256": sha256(checkpoint), "passed": True})

class ProbabilityWrapper(torch.nn.Module):
    def __init__(self, inner):
        super().__init__()
        self.inner = inner
    def forward(self, input_features):
        return torch.sigmoid(self.inner(input_features)).reshape(-1, 1)

wrapper = ProbabilityWrapper(reloaded).eval()
export_path = ROOT / "synthetic-one-batch.onnx"
torch.onnx.export(wrapper, (features[:1],), str(export_path), input_names=["input_features"], output_names=["logits"], dynamic_axes={"input_features": {0: "batch"}, "logits": {0: "batch"}}, opset_version=18, dynamo=False)
exported = onnx.load(str(export_path))
onnx.checker.check_model(exported)
assert exported.graph.input[0].type.tensor_type.shape.dim[0].dim_param == "batch"
assert exported.graph.output[0].type.tensor_type.shape.dim[0].dim_param == "batch"
reloaded_ort = ort.InferenceSession(str(export_path), sess_options=opts, providers=["CPUExecutionProvider"])
export_results = []
for batch_size in (1, 2):
    sample = x[:batch_size].copy()
    with torch.no_grad():
        expected = wrapper(torch.from_numpy(sample)).numpy()
    got = reloaded_ort.run(["logits"], {"input_features": sample})[0]
    assert got.shape == (batch_size, 1), got.shape
    assert np.isfinite(got).all() and np.all((got >= 0) & (got <= 1))
    error = float(np.max(np.abs(got - expected)))
    assert error < 1e-5, error
    export_results.append({"batch_size": batch_size, "shape": list(got.shape), "max_abs_probability_error": error, "required_lt": 1e-5, "passed": True})
record("export", {"opset": 18, "eval_mode": True, "dynamic_batch": True, "sigmoid_wrapper": True, "input": "input_features", "output": "logits", "sha256": sha256(export_path), "onnx_checker_passed": True, "provider": reloaded_ort.get_providers(), "parity": export_results})
record("artifacts", {name: {"sha256": sha256(ROOT / name), "bytes": (ROOT / name).stat().st_size} for name in ["recovered-stock.pt", "synthetic-one-batch.pt", "synthetic-one-batch.onnx"]})
record("script", {"filename": SCRIPT.name, "sha256": sha256(SCRIPT)})
record("result", {"passed": True, "runtime_seconds": time.perf_counter() - started, "utc_finished": datetime.now(timezone.utc).isoformat()})
