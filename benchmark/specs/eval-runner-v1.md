# Spec: matched evaluation runner v1

**Owner:** Niko · **Implementer:** Sonnet subagent · **Status:** spec ready for implementation · **PLAN:** E1 and the "Evaluation work required" checklist · **Depends on:** `model/CONTRACT.md` v0.1; `specs/splits-v1.md` (under review)

## Why

`scripts/run_model_arm.py` produced the exploratory numbers, but it can't support a matched stock-vs-candidate decision:

| Defect | Where | Consequence |
|---|---|---|
| Model path hard-coded; ONNX session created at import | `run_model_arm.py:22,29` | A candidate can't be evaluated without editing code. `threshold_sweep.py` imports it and silently loads stock. |
| Outputs overwrite `data/*.csv`; no run ID | `:96,121,144` | Runs can't be told apart and history is lost |
| Cache keyed by nothing but its path | `threshold_sweep.py:26-28` | A candidate sweep would reuse stock fluent probabilities (the plan's "never mix" rule) |
| Fluent loop `break`s at the first complete | `:107-111` | Probabilities after the first decision are missing, so other thresholds can't be re-scored |
| 100 ms checkpoint grid | `:53-54` | Can't resolve the +50 ms target |
| 1 s observation with censored items silently uncounted | `:112-113`, `FLUENT_CHECKPOINTS` | Not reaching a decision within the clip is mixed up with the 3 s fallback |
| No model, data or config hashes; no `requirements.txt` | — | Results can't be reproduced or audited |

## Scope

- **In scope:** a new runner, a comparison tool, a run-record schema, a model-hash-keyed cache, `benchmark/requirements.txt`, and a legacy item converter used only for a regression check.
- **Out of scope:** building new eval items from splits (the next spec), training, agent and live-audio runs, and changing existing scripts or `data/` files. The old scripts stay as the historical record.

## Inputs

### 1. Model (per `model/CONTRACT.md` §1–3)

`--model PATH --model-id ID --expected-sha256 HEX`. Hash the file before loading and exit non-zero on a mismatch. Use the contract's preprocessing exactly (16 kHz, last 8 s, left zero-pad, `WhisperFeatureExtractor(chunk_length=8)`, `do_normalize=True`), and give it a constant `PREPROC_VERSION = "smartturn-v3-upstream-1"`. ORT CPU, sequential, `inter_op_num_threads=1`, as in the current script. The output is already a probability, so no sigmoid.

### 2. Eval items (`--items PATH.jsonl`)

One JSON object per line. The runner is agnostic about how items were built:

```json
{"item_id": "dev-blk-000123", "clip_key": "HeStutters_1_133", "audio": "audio/HeStutters_1_133.wav",
 "split": "dev", "group": "stuttered", "kind": "unfinished",
 "silence_start_s": 0.88, "resume_s": 1.35, "turn_end_s": null,
 "observe_until_s": 3.0, "label_source": "energy_vad"}
```

- `group`: `stuttered` or `fluent` (the caller group). `kind`: `unfinished` (the speaker resumes; any completion before `resume_s` is premature) or `completed` (the turn really ended at `turn_end_s`; measure delay).
- `observe_until_s`: the end of real audio available. **The runner never pads past it with synthetic silence.** Anything beyond is right-censored.
- `label_source`: one of `human`, `sep28k_annotator`, `energy_vad`. It is copied into every result and summary group, so a reader always sees how the ground truth was established (PLAN: energy-derived cut points ≠ semantic turn ends).
- Validate every line and exit non-zero listing all bad lines (missing fields, `resume_s ≤ silence_start_s`, `kind`/field mismatch, missing audio file).

### 3. Schedule config (`--config PATH.json`)

```json
{"config_id": "agent-v0.1-single", "threshold": 0.5,
 "vad_stop_s": 0.2, "schedule": "single", "recheck_interval_s": null,
 "fallback_timeout_s": 3.0, "grid_step_s": 0.01}
```

- `schedule: "single"` mirrors agent contract v0.1. The model is called once at `silence_start_s + vad_stop_s`. If p ≤ threshold, the decision falls to `fallback_timeout_s` after silence start, unless speech resumes first.
- `schedule: "interval"` calls the model at `vad_stop_s` and then every `recheck_interval_s` (e.g. 0.05) until a complete decision, resume, fallback or the end of observation.
- `schedule: "legacy"` takes an explicit `checkpoints_s` list. It exists only for the regression check below.
- **Probabilities are always computed on the full `grid_step_s` grid** from `vad_stop_s` up to `min(resume_s or turn_end bound, observe_until_s, fallback)`. The decision is then derived from the grid according to the schedule. Every grid probability is stored, so thresholds and schedules can be re-scored offline from one inference pass. A 10 ms grid resolves the +50 ms target. Cut sample index = `round((silence_start_s + t) * 16000)`.

## Outcomes per item

- **unfinished:** `premature = true` if the schedule yields a complete decision (model or fallback) at a time `< resume_s`. Record `decision_t`, `trigger` (`model` or `fallback`), and `margin_s = resume_s - decision_t`.
- **completed:** `delay_s` = decision time minus `turn_end_s`, with `trigger` `model` or `fallback`. If neither the model fired nor the fallback fell within `observe_until_s`, the outcome is `censored` and `delay_s = null`, with `censored_at_s` recorded. **A fallback is only counted if `turn_end_s + fallback_timeout_s ≤ observe_until_s`;** otherwise the item is censored. Never assume the fallback fired.
- Inference time per call goes in `infer_ms`. It is reported separately and **not** added to `delay_s`.

## Outputs: immutable run directory

`benchmark/runs/<run_id>/`, where `run_id = YYYYMMDDTHHMMSSZ-<model_id>-<config_id>-<first 8 of items sha256>`. Refuse to run if the directory exists.

- `run.json`: `run_id, created_utc, code_commit, code_dirty (bool), runner_sha256, model_id, model_sha256, preproc_version, items_path, items_sha256, config (resolved), config_sha256, env` (python, platform, onnxruntime, transformers, numpy, soundfile versions), `cache_hits, cache_misses, wall_s`.
- `results.jsonl`: one line per item, with all input fields plus `grid` (`{t: p}` with 3-decimal keys) and the outcome fields above.
- `summary.json`: grouped by `split × group × kind × label_source`:
  - for unfinished: `n`, `premature_n`, `premature_rate`, Wilson 95% CI;
  - for completed: `n`, `decided_by_model_n`, `decided_by_fallback_n`, `censored_n`, plus median/p90/max `delay_s` over decided items **reported alongside `censored_n`, never in place of it**;
  - `infer_ms` mean/p95.

`benchmark/runs/` is committed only for runs cited as evidence. Add a `benchmark/runs/.gitignore` containing `scratch-*`, and accept `--scratch` to prefix the run ID with `scratch-` for throwaway runs.

## Cache

`benchmark/cache/probs.sqlite`, gitignored, with key `(model_sha256, preproc_version, audio_sha256, cut_sample_index)` → `prob`. Audio is keyed by **content hash, never filename**. It's enabled by default; `--no-cache` disables it. A cache can never serve a different model or modified audio, so the "mixed stock/candidate cache" failure is impossible by construction.

## Comparison tool

`python benchmark/scripts/compare_runs.py RUN_A RUN_B` must:

- **Refuse** (exit 2 with the reason) unless `items_sha256` matches, and the configs are identical except `threshold`. Any other config difference requires `--allow-config-diff` and is printed in the header.
- Per group and kind, print both rates with CIs. For paired unfinished items, print the discordant counts (A premature / B not, and the reverse). For completed items, print the delay median difference, a p90 comparison, and censored and fallback counts for both runs.
- Print the PLAN 3 PM checks as data, not verdicts: premature rate for B, median delay difference per group against +50 ms, and whether censored/fallback counts got worse. The gate decision belongs to Vinh and the team.

## Legacy converter (regression proof only)

`python benchmark/scripts/legacy_items.py` writes `benchmark/runs/legacy-items/block.jsonl`. The legacy converter's output stays under `runs/`, not `data/`. It converts `data/block_eval.csv` (stuttered, unfinished, `silence_start_s = gap_start`, `resume_s = gap_start + gap_dur`, `observe_until_s = 3.0`, `label_source = energy_vad`, `split = "exploratory"`). Pair it with `configs/legacy-block.json` (`schedule: legacy`, `checkpoints_s` = the old `BLOCK_CHECKPOINTS`, applying the old rule of stopping at `t ≥ gap_dur - 0.01` and falling back to 0.2 when no checkpoint fits).

## Files the implementer writes

- `benchmark/scripts/eval_runner.py`, `benchmark/scripts/compare_runs.py`, `benchmark/scripts/legacy_items.py`
- `benchmark/configs/agent-v0.1-single.json`, `benchmark/configs/interval-50ms.json`, `benchmark/configs/legacy-block.json`
- `benchmark/requirements.txt`: pinned `numpy==2.2.6`, `soundfile`, `onnxruntime==1.29.0`, `transformers==5.19.0`, `huggingface_hub` (for `download_clips.py`). Pin `soundfile` and `huggingface_hub` to the versions actually installed and tested.
- `benchmark/runs/.gitignore`; append `benchmark/cache/` to the existing **`benchmark/.gitignore` only, creating it if needed**. Don't edit the root `.gitignore`, which Vinh coordinates.

Don't modify existing scripts, `data/`, or anything outside `benchmark/`. Don't commit or push.

## Acceptance checks (paste the commands and output)

Setup: a fresh venv, `pip install -r benchmark/requirements.txt`, the stock INT8 model downloaded from `pipecat-ai/smart-turn-v3` @ `f766f81` with its hash verified (`2bb026316b14a660486a75b1733cd3fbab8c2fd0314dc9af7be49f8cca967e4f`), and audio fetched with `python benchmark/scripts/download_clips.py`. Note the macOS commands used.

1. **Legacy regression:** run the legacy items and config with stock INT8. Total **first-check premature = 116/200** and **any-check = 136/200**, matching `data/model_block_results.csv`. Per-item probabilities at the shared checkpoints match that CSV within 1e-3 (it stored 4 decimals). If they don't match, stop and report; don't tune.
2. **Hash guard:** a wrong `--expected-sha256` exits non-zero before inference.
3. **Immutability:** re-running with the same run ID refuses. `--scratch` runs land under `scratch-*`.
4. **Cache safety:** run twice and the second has 100% cache hits with an identical `results.jsonl` except timings. Then run with the FP32 stock model (hash `ab8dc64b88713f90b571c15b714bd1330e6c883cad8763dacf65c9376dc539be`): **0 cache hits**.
5. **Censoring:** a hand-made 3-item JSONL (completed, `turn_end_s = 2.5`, `observe_until_s = 3.0`) under the `single` config with a 3.0 s fallback reports **censored, not fallback**, for any item where the model didn't fire.
6. **Re-scoring without inference:** `eval_runner.py --rescore RUN_DIR --config other.json` writes a new run directory from the stored grids, with 0 model calls, when only `threshold` or `schedule` differ. It refuses if `grid_step_s` or `vad_stop_s` differ.
7. **Compare guard:** `compare_runs.py` on two runs with different `items_sha256` exits 2.
8. **INT8 vs FP32 stock** on the legacy items: report both premature totals. This measures the quantization effect that `model/CONTRACT.md` §5.4 needs.

Report any acceptance check you couldn't run (for example, audio download failed) as **not run** with the reason. Never report it as passed.
