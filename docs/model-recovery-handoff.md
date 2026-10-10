# Niko: recover the trained Smart Turn model before adapting it

October 10 execution check. This is a shortcut for **PLAN F1**, not a new model choice or a passed training gate. Niko owns the model implementation. Keep the existing 45-minute recovery cap and 2 PM/3 PM decisions.

## What was checked

- The [official model inventory at `f766f81`](https://huggingface.co/pipecat-ai/smart-turn-v3/tree/f766f81d3cfdf7737ac64aad813d91bbfd56bf93) contains ONNX releases, not a trained PyTorch/safetensors checkpoint. The repository is `pipecat-ai/smart-turn-v3`; v3.2 is an artifact version within it.
- [Official `train.py` at `4786657`](https://github.com/pipecat-ai/smart-turn/blob/4786657e242dfe77dd138699ac564ee074a2a543/train.py) initializes from `openai/whisper-tiny`. Running it unchanged does not restore the trained stock Smart Turn head. Its full-data training defaults are unsuitable for the one-batch proof.
- The existing local CPU INT8 model matched the official SHA-256 `2bb026316b14a660486a75b1733cd3fbab8c2fd0314dc9af7be49f8cca967e4f`. Loading, Whisper feature extraction and inference on eight seconds of synthetic silence passed: float input `[1,80,800]`, finite probability output `[1,1]`. Environment: ONNX Runtime 1.29.0, Transformers 5.19.0. This proves only operational inference, **not human-speech performance, trainability, parity or an agent run**.
- That default local Python environment has no PyTorch. Use an isolated, prepared environment; do not replace a teammate's installed stack. Upstream and the converter below have different Transformers requirements.

## Existing conversion implementation to evaluate first

[Smart Turn issue #42](https://github.com/pipecat-ai/smart-turn/issues/42) links the community project **haan**. Its [converter](https://github.com/Charansripadi/haan/blob/540f97de03f8eb938b871196752206f6d0698791/haan/convert.py) and [parity test](https://github.com/Charansripadi/haan/blob/540f97de03f8eb938b871196752206f6d0698791/tests/test_convert.py) were inspected at **`540f97de03f8eb938b871196752206f6d0698791`**. They map trained FP32 ONNX tensors into the matching PyTorch architecture and compare probabilities numerically. The maintainer's acknowledgement is not certification of this implementation.

The source uses a BSD-2-Clause license with upstream notices; retain those notices if code is incorporated. We have **not run this conversion, its parity test, training or export**. The author's reported numerical error is not our result.

In a reviewed checkout of that pinned source, with its dependencies installed in Niko's environment, the proposed commands are:

```powershell
python -c "from huggingface_hub import hf_hub_download; print(hf_hub_download('pipecat-ai/smart-turn-v3', 'smart-turn-v3.2-gpu.onnx', revision='f766f81d3cfdf7737ac64aad813d91bbfd56bf93', local_dir='models'))"
Get-FileHash -Algorithm SHA256 -LiteralPath 'models/smart-turn-v3.2-gpu.onnx'
python -m pytest tests/test_convert.py -q -rs
python -m haan.convert models/smart-turn-v3.2-gpu.onnx models/smart-turn-v3.2.pt
```

Expected FP32 artifact SHA-256: `ab8dc64b88713f90b571c15b714bd1330e6c883cad8763dacf65c9376dc539be`. The [32.4 MB artifact](https://huggingface.co/pipecat-ai/smart-turn-v3/blob/f766f81d3cfdf7737ac64aad813d91bbfd56bf93/smart-turn-v3.2-gpu.onnx) can be tested on CPU despite its GPU filename.

**Read the test result:** it must pass, not skip because dependencies or the file are absent. Its seeded `(3,80,800)` test requires maximum probability error below `1e-5`. This tests reconstruction against **stock FP32**; comparison to the quantized CPU model is separate. Save the actual error, source/model hashes, versions and command output.

## One-batch and export checks

After reconstruction passes, use one local batch to check gradients, an actual parameter update and save/reload. A synthetic batch is acceptable for this mechanical smoke test while humans label, but cannot count as stutter adaptation. Avoid convenience training commands that download whole datasets before honoring their step limit.

**Output convention matters:** haan returns raw logits; the official ONNX output named `logits` contains sigmoid probabilities. An export wrapper for haan must apply `torch.sigmoid(...).reshape(-1, 1)`. Export input `input_features` and output `logits`, shapes `[B,80,800]` and `[B,1]`, with the appropriate supported opset (the inspected upstream exporter uses 18).

Call `model.eval()` before export/parity checks so dropout is disabled. Reload the export in ONNX Runtime and compare probabilities to the post-batch PyTorch model on batch sizes 1 and 2. Shape agreement alone is insufficient. Before calling it a drop-in CPU replacement, also verify preprocessing, threshold semantics, runtime loading and any quantization effects in Guttuu's actual agent.

## Handoff at the existing gate

Return **artifact/hash + exact command + parity result + one-batch/update log + export/reload result + runtime + blocker** to PLAN F1 and `model/CONTRACT.md`. Proposed time allocation: 10 minutes environment/artifact, 10 reconstruction/parity, 15 one-batch/export and 10 evidence/handoff. These are timeboxes, not measured runtime promises.

If recovery or parity fails inside the cap, record the exact failure and use the agreed corrected-comparison scope. Newly initialized Whisper Tiny must not be labeled recovered stock Smart Turn. Human labels and the real audio path remain independent unfinished gates.
