# StutterTurn model contract

**Contract version:** 0.1 (draft) · **Owner:** Niko · **Consumers:** Guttuu (`agent/`), Vinh (`web/demo-ui/`), E1 evaluation

This file defines what a StutterTurn model artifact is and how the agent calls it. Each clause is marked **Verified** (with linked evidence) or **Proposed** (agreed interface, not yet tested). Proposed clauses can be built against, but they are not evidence of a working candidate. Breaking changes bump the major version, and Niko tells Guttuu and Vinh before merging them.

## 1. Artifacts

| ID | File | SHA-256 | Status | Use |
|---|---|---|---|---|
| `stock-int8` | `smart-turn-v3.2-cpu.onnx` (pipecat-ai/smart-turn-v3 @ `f766f81`) | `2bb026316b14a660486a75b1733cd3fbab8c2fd0314dc9af7be49f8cca967e4f` | **Verified** hash and inference ([handoff](../docs/model-recovery-handoff.md)) | Stock arm, and the exploratory benchmark's model |
| `stock-fp32` | `smart-turn-v3.2-gpu.onnx` (same revision; runs on CPU) | `ab8dc64b88713f90b571c15b714bd1330e6c883cad8763dacf65c9376dc539be` | **Verified** hash and reconstruction parity ([evidence](../docs/proofs/model-mechanics/evidence.json)) | Starting point for training; a stock arm when compared against an FP32 candidate |
| `stutterturn-v{N}` | `stutterturn-v{N}.onnx` | Recorded per release in §6 | **Proposed**; no candidate exists yet | Candidate arm |

- `synthetic-one-batch.onnx` (`9a00002e…7d3c`) is a mechanical proof output. **It must never be loaded as a candidate or shown in the demo.**
- Never overwrite a published `v{N}`. Any retraining, even with the same data, produces `v{N+1}`.
- Weights are not committed to Git. Artifacts are fetched by URL plus SHA-256, and the agent **must refuse to load a file whose hash doesn't match**.

## 2. Inference interface

| Item | Value | Status |
|---|---|---|
| Runtime | ONNX Runtime, `CPUExecutionProvider` | **Verified** (ORT 1.29.0) |
| Input name / dtype / shape | `input_features`, `float32`, `[B, 80, 800]`, with a dynamic batch axis | **Verified** for stock and exported artifacts; B = 1 and 2 were tested on the export |
| Output name / dtype / shape | `logits`, `float32`, `[B, 1]` | **Verified** |
| Output meaning | **Probability in [0, 1] that the turn is complete.** The tensor is named `logits` but holds post-sigmoid probabilities, matching the official convention. **Don't apply another sigmoid.** | **Verified** for stock and exports produced by the proof's export wrapper |
| Decision rule | `complete = p > threshold`, with default `threshold = 0.5` | **Verified** as upstream's rule; a candidate may ship a different threshold in its metadata (§5) |

## 3. Preprocessing (must be identical for every arm)

The agent must produce features exactly as `benchmark/scripts/run_model_arm.py` does, which follows upstream Smart Turn:

1. Mono PCM at **16 kHz**, float32 in [-1, 1]. Resample upstream if the source isn't 16 kHz. *8 kHz phone audio is out of scope until tested.*
2. Keep the **last 8 s** (128 000 samples) of the current user turn. If it's shorter, **left-pad with zeros**.
3. `WhisperFeatureExtractor(chunk_length=8)(audio, sampling_rate=16000, padding="max_length", max_length=128000, truncation=True, do_normalize=True, return_tensors="np")`
4. Cast to float32 and shape it as `[1, 80, 800]`.

**Status:** this is the **Verified** procedure behind the exploratory stock results. It **hasn't been verified inside the agent**: Guttuu's acceptance check is that the agent's features for a saved clip match this script's features (max abs diff < 1e-5) and produce the same probability.

Open item: which audio counts as "the current user turn" (reset point, whether any agent audio is included). Guttuu proposes this in `agent/CONTRACT.md`; it must be the same for stock and candidate.

## 4. When the model is called (Proposed; owned jointly with Guttuu)

- The model is called when the VAD reports speech stopped, after `vad_stop_secs = 0.2`, matching the pipecat default and the exploratory harness's "first check". This agrees with `agent/CONTRACT.md` v0.1 (`guttuu/web-agent`).
- If `p ≤ threshold`, the agent waits for more speech or the **3.0 s silence fallback**, following Pipecat `LocalSmartTurnAnalyzerV3` defaults and agent contract v0.1. The timeout must be stated in every run record.
- **Open question for Guttuu:** should the agent also re-check during continued silence, for example every 50 ms? The exploratory "any check" result (68%) assumed repeated checks, which this single-check default doesn't do. Whichever schedule is chosen, the benchmark harness must replicate it exactly so offline and live numbers are comparable.
- Stock and candidate use **the same VAD, check schedule, timeout and audio source**. Only the model file and threshold differ between arms.
- Every model call is logged (§7). Model completion decisions are kept separate from the agent's first audible response.

## 5. Candidate release requirements (Proposed)

Each `stutterturn-v{N}` release publishes a JSON metadata file beside the ONNX file:

```json
{
  "model_id": "stutterturn-v1",
  "sha256": "<onnx sha256>",
  "base_model": "stock-fp32",
  "threshold": 0.5,
  "precision": "fp32",
  "train_manifest_sha256": "<frozen training split>",
  "dev_manifest_sha256": "<frozen dev split>",
  "training_config": "<path or hash>",
  "code_commit": "<git sha>",
  "export": {"opset": 18, "sigmoid_wrapper": true, "eval_mode": true},
  "parity_max_abs_error": 0.0,
  "status": "dev-candidate | selected | rejected"
}
```

A candidate is **agent-ready** only when all of the following hold:

1. ONNX checker passes. A fresh ORT session matches the post-training PyTorch probabilities within 1e-5 at B = 1 and 2.
2. The same saved real clip goes through §3 in both the benchmark script and the agent, with matching probabilities.
3. Load time and per-call latency on the demo machine are recorded. Stock INT8 measured about 25 ms mean / 28 ms p95 on a different machine, which is a reference, not a requirement.
4. If the candidate is FP32 and stock is INT8, the precision difference is reported. Alternatively, stock FP32 is used as the comparator. A candidate may be quantized only after it has been evaluated, and the quantized artifact gets its own ID.

Being agent-ready doesn't mean improved. Improvement is decided only by the PLAN 3 PM development gate and the separate final test.

## 6. Release log

| model_id | sha256 | status | evidence |
|---|---|---|---|
| — | — | No candidate yet | — |

## 7. Per-call log record (Proposed; consumed by E1 and the UI)

Each model call must produce at least these fields. In agent contract v0.1 they map onto `decision` events (`turn_complete` / `turn_incomplete`) and `run_started` (`model`, `model_sha256`, `params`). The only addition requested of the agent is `silence_s` and `infer_ms`. `t` uses the agent's time origin: the first source sample.

```json
{"run_id": "...", "t": 1.234, "time_origin": "source_audio_start",
 "model_id": "stock-int8", "model_sha256": "...", "threshold": 0.5,
 "silence_s": 0.20, "prob": 0.71, "complete": true, "infer_ms": 26.1}
```

`t` and `silence_s` are seconds, measured from the run's stated `time_origin`. Audible-response and cancellation timings belong to the agent contract, not this one.

## 8. Known limits

- Only synthetic inputs have been used for training/export so far. No stutter adaptation, real-audio accuracy or drop-in agent behaviour has been demonstrated.
- Mechanical evidence was produced on Windows with Python 3.12.10, torch 2.8.0+cpu and transformers 5.19.0. Reproduction on other platforms hasn't been checked.
- Training uses the community **haan** converter pinned at `540f97d` (BSD-2-Clause; keep its notices). Upstream Smart Turn ships no PyTorch checkpoint.
- English, wideband podcast audio only. Long blocks (> 1.6 s) and 8 kHz telephony are untested.
