# Mechanical Smart Turn recovery proof, October 10, 2026

This is an executed local proof of stock FP32 recovery, one synthetic gradient/update step, checkpoint save/reload, and ONNX probability export. It does not establish stutter adaptation, real-audio quality, interruption reduction, demo acceptance, or compatibility with the live agent.

The probe ran outside the project repository in a separate environment; only its harness and evidence are committed here. The source checkout retains its original BSD-2-Clause notices. This package contains our proof harness, not copied haan implementation code.

## Files to hand off

- `run_mechanical_proof.py`: tested portable harness; accepts explicit source, model, and output directories.
- `requirements-lock.txt`: full resolved environment; CPU PyTorch required.
- `evidence.json`: measured results and artifact hashes from this harness.
- `upstream-test.json`: summary of the local upstream JUnit result, 1 test, 0 skipped, 0 failed, 0 errors.
- `portable-wall-time.json`: harness process wall time, including Python imports.
Raw logs and the original JUnit output remain local; they contain local paths or machine metadata.

Keep `.venv/`, `haan/`, and downloaded/generated weights local. `recovered-stock.pt` is the recovered stock model; `synthetic-one-batch.pt` and `synthetic-one-batch.onnx` contain a synthetic optimizer update and must not be presented as trained stutter models or deployed as production models.

## Reproduce in a new scratch directory

Copy `run_mechanical_proof.py` and `requirements-lock.txt` into that directory. These are PowerShell commands. Every step must exit successfully before proceeding.

```powershell
git clone https://github.com/Charansripadi/haan.git haan
git -C haan checkout 540f97de03f8eb938b871196752206f6d0698791
# Review haan/model.py, haan/convert.py, tests/test_convert.py, and LICENSE before execution.
uv venv --python 3.12 .venv
uv pip install --python .venv/Scripts/python.exe --torch-backend cpu -r requirements-lock.txt
New-Item -ItemType Directory -Path haan/models -Force
Invoke-WebRequest -Uri 'https://huggingface.co/pipecat-ai/smart-turn-v3/resolve/f766f81d3cfdf7737ac64aad813d91bbfd56bf93/smart-turn-v3.2-gpu.onnx' -OutFile 'haan/models/smart-turn-v3.2-gpu.onnx'
Get-FileHash -Algorithm SHA256 -LiteralPath haan/models/smart-turn-v3.2-gpu.onnx
$env:OMP_NUM_THREADS = '4'
$env:MKL_NUM_THREADS = '4'
Push-Location haan
../.venv/Scripts/python.exe -m pytest tests/test_convert.py -q -rs --junitxml=../parity-junit.xml
Pop-Location
.venv/Scripts/python.exe run_mechanical_proof.py --source haan --model haan/models/smart-turn-v3.2-gpu.onnx --output proof-output
```

The expected official model SHA-256 is `ab8dc64b88713f90b571c15b714bd1330e6c883cad8763dacf65c9376dc539be`; the harness asserts it and verifies the pinned source commit plus unmodified source files used for this proof. The upstream test must pass, not skip. Run the harness normally, without Python's `-O`, because its proof conditions use assertions.

## What actually ran

Environment creation used Python 3.12.10 and uv 0.12.10. Initial dependency installation ran:

```powershell
uv pip install --python .venv/Scripts/python.exe 'torch==2.8.0+cpu' --index https://download.pytorch.org/whl/cpu
uv pip install --python .venv/Scripts/python.exe 'transformers==5.19.0' 'onnxruntime==1.29.0' 'onnx==1.19.1' 'numpy==2.2.6' pytest onnxscript
```

The final lockfile command shown above was then executed and audited the existing 45-package environment. CPU PyTorch reports `torch.version.cuda == None`. No CUDA stack, dataset, whole-model pretraining, paid service, or real audio was used. The CPU torch wheel was approximately 590.7 MiB on Windows and installed in approximately 27 seconds here; these are observations, not runtime promises.

The pinned upstream pytest command passed in 10.58 seconds. The portable harness completed with exit code 0, with approximately 7 seconds process wall time and 1.81 seconds measured after imports. Its exact wall time is in `portable-wall-time.json`. The original fixed-layout harness also passed before the portable variant was introduced; both produced identical model artifact hashes.

Measured stock reconstruction error: `1.1920928955078125e-07`, with the seeded `(3,80,800)` test input. The required bound is `<1e-5`. One SGD step at `1e-4` on two synthetic feature arrays with targets `[0,1]` produced finite gradients for all 78 trainable parameter tensors and actual updates to all 78; both encoder and classifier changed. Strict weights-only save/reload gave zero maximum logit difference.

The exporter ran with the model in evaluation mode, opset 18, explicit dynamic batch axes, and `sigmoid(...).reshape(-1,1)`. ONNX checker passed. Fresh CPU ONNX Runtime sessions produced finite `(1,1)` and `(2,1)` probabilities, each within `5.960464477539063e-08` of the post-update PyTorch model. The legacy exporter emitted deprecation and shape-branch tracing warnings; dynamic batch 1 and 2 were tested successfully. Other input lengths and batch sizes were not acceptance-tested.

The output named `logits` intentionally contains probabilities, matching the official artifact convention. Preprocessing, threshold semantics, quantization effects, real recordings, human labels, held-out comparisons, and the actual agent integration still require separate verification.
