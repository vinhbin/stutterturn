# Spec: StutterTurn candidate training v1

**Owner:** Niko (spec, benchmark, selection rule) · **Executor:** Guttuu (harness + training runs, on his machine) · **Status:** reviewed (Opus, 2026-10-10), revised · **PLAN:** F1 (agent-ready export), E1 (dev selection), 3 PM gate criteria · **Depends on:** `model/CONTRACT.md` v0.1, `benchmark/splits/v1`, `benchmark/items/v1` (in progress), `benchmark/scripts/eval_runner.py`

**Division of work:** Guttuu implements the §8 harness and runs training on his machine; Niko's M2 (8 GB RAM, 7 GB free) can't fit the data or the runs. Niko delivers the benchmark pieces in §6 (a checks-only runner option) and reviews each harness check. **The run grid and the selection rule are pre-registered here; nobody picks runs or checkpoints outside them.** Nothing here is evidence of improvement until §6's dev comparison runs.

**First thing to report on issue #2:** the device (GPU model and VRAM, or CPU), free disk, and the §8 check-5 throughput. §4 and §9 scale from that.

## 1. Goal and the claim it must earn

Fine-tune stock Smart Turn v3.2 so that, **at the agent's single-check schedule**, it predicts "incomplete" during stutter blocks more often than stock, while keeping its behaviour on completed turns and on fluent pauses.

The claim must beat both of these on dev, not just stock INT8:

1. **Stock FP32** (exploratory: 43.5% first-check premature vs 58% for INT8).
2. **Stock FP32 with a raised threshold.** Raising the threshold also cuts premature decisions, but sends more completed turns to the 3 s fallback (RESULTS.md §5). **The candidate only earns credit if, at equal or better completed-turn behaviour, it makes fewer premature decisions than stock at any threshold.** This operating-point comparison is the central test.

## 2. Training data

### 2a. Stutter negatives (label 0 = incomplete) from **train shows only**

- **Source:** `benchmark/splits/v1/train.csv`, `category == block` (1,723 clips; about 60% survive the gap/resume rule, so roughly 1,000 clips).
- **Audio fetch:** `fetch_split_audio.py` only allows dev and test. Add `model/train/fetch_train_audio.py`, using the same mirror, idiom, atomic `.part` write and empty-on-mirror log. Fetch train `block` clips into `benchmark/audio/`. Only 314 of the 1,723 are on disk today.
- **Construction:**
  - Use the same audio gate and `find_first_gap(analyze(...))` as `eval-items-v1`, keeping `reason == "ok"`.
  - For each offset `t ∈ {0.20, 0.25, …, 0.60}` with `t < gap_dur − 0.05`, add the sample `audio[0 : round((gap_start + t)·16000)]` with label 0. Offsets stop at 0.60: on the block_eval proxy, 24% of uncapped samples fell within 0.15 s of the resume, where a wrong resume label does the most harm.
  - Weighting within each clip (total 1): **`t = 0.20` gets 0.5**, and the other offsets share 0.5 equally. If `t = 0.20` is the only offset, it gets 1. Uncapped, `t = 0.20` got only 21% of each clip's weight, yet it is the deployed check.
  - Later offsets make the model robust to `interval` schedules and longer silences.
- **Label quality, stated plainly:** "contains a block" comes from SEP-28k annotator votes (Block ≥ 2). The gap and resume times are energy-derived, and the resume may be another speaker. If it is, **every** offset in that clip is wrong, not just the late ones. Among train blocks, NaturalPause ≥ 2 is 5.7%, and Interjection ≥ 2 is 306/1,723. **This is noisy training data, which is acceptable for training.** The evaluation labels and human review stay separate (eval-items-v1). This is the training-label decision flagged in planning; record it in the decision log.
- **Leakage asserts:**
  - every clip_key is in `train.csv`;
  - none is in dev or test;
  - none is in `items/v1/manifest.json` `annotated_dev_test_keys`;
  - the manifest records the sha256 of `train.csv`.

### 2b. Original Smart Turn data replay (both labels), to keep stock behaviour

- **Source:** `pipecat-ai/smart-turn-data-v3.2-train` (CC-BY-4.0; 270,946 examples in 83 parquet shards, ~41 GB, fields `audio, id, language, endpoint_bool, midfiller, endfiller, synthetic, spoken_text, dataset`). **Download only a bounded subset:** pinned to revision `f8c95d28…` (record the full SHA in the manifest). **Stream one shard at a time** (~500 MB each), keep only the selected rows' FLAC bytes plus metadata in `<work>/data/`, then delete the shard. Shards 00000–00002 hold only 2,361 English rows (804, 753, 804), so continue in order until the cap is met.
- **Filter:** `language == "eng"` (the dataset uses ISO 639-3; `"en"` matches 0 rows), since SEP-28k is English. Keep `endpoint_bool` **unchanged** (PLAN: preserve original labels). Record the counts by label, `synthetic`, `midfiller` and `endfiller`.
- **Cap:** 6,000 English examples, about 8 shards, stratified by `endpoint_bool` to match the natural ratio and chosen deterministically by the lowest `sha256(id)` within each shard read. If disk or time forces fewer shards, stop at a whole shard and record the count actually reached; the cap is a ceiling, not a requirement.
- The `audio` column is `struct{bytes, path}` holding FLAC PCM_16 mono at 16 kHz. Decode `audio.bytes` with `soundfile` (verified 789/789, with no `torchcodec`). Assert 16 kHz, and resample nothing.
- **Dedupe:** hash each decoded waveform (sha256 of the int16 bytes), and drop any replay row whose hash also occurs in the guard set (2c). Record the count.

### 2c. Guard set: original **test** data (never trained on, by us or upstream)

- **Source:** `pipecat-ai/smart-turn-data-v3.2-test` at revision `dfc17924…`; its files are named `train-0000X-of-00010`. Stream shards 00000–00003 (about 789 English rows each, 49% positive, 32% synthetic) up to a stratified cap of 3,000 English rows, deleting each shard after extraction.
- **Disjointness:** upstream `train.py` uses this set only in its eval callback (`:410-415`, `:736-739`), never as training data. The released checkpoint may still have been chosen by watching those curves, and the same sources (`liva_1`, `chirp3_*`) appear in train and test. "Unseen" therefore means not trained on, not perfectly independent; say so wherever it is cited.
- **Purpose:** this is **the only completed-turn evaluation with trustworthy labels available today.** It tracks recall on `endpoint_bool = 1`, meaning completed turns still get decided complete, and accuracy on `endpoint_bool = 0`.
- **Limit:** this is mostly fluent and partly synthetic speech, not people who stutter, so it guards against general regression and is no substitute for human-confirmed stuttered turn ends.

### 2d. Mixture

**Mix per sample:** each sample is drawn from 2a with probability `p_stutter` (weighted by its §2a weight), otherwise from 2b. An **epoch** is one weighted pass's worth of 2a draws, about 1,000 clip-weights, divided by `p_stutter`. The loss is BCE-with-logits, with a **fixed** `pos_weight` computed once on the full mixture (upstream recomputes it per batch, `train.py:123-125`, which is noisy at small batch sizes). That `pos_weight` is about 1.7–2.3 and partly cancels the stutter negatives' push toward "incomplete"; log its value.

**Not in v1 (named so nobody adds it quietly):**
- SEP-28k end-of-window proxies as positives;
- `other_disfluent` clips;
- synthetic or imitated stutters;
- any dev or test audio.

## 3. Model and initialization

- Start from the stock FP32 ONNX (sha256 `ab8dc64b…c539be`), converted with **haan @ `540f97d`** (`haan.convert.load_from_onnx`, `haan.model.SmartTurnModel`), exactly as in `docs/proofs/model-mechanics/`.
- **Before training, assert reconstruction parity < 5e-5** in CPU torch on 3 real dev-item feature arrays, not just random input. The review measured a max of 1.13e-5 on CPU (0.5% above 1e-5) and 4.4e-6 on MPS against stock ORT, so 1e-5 fails spuriously.
- haan returns **raw logits**. Training uses logits; exports apply `sigmoid(...).reshape(-1,1)` (CONTRACT §2).
- Environment: Python 3.12, `torch==2.8.0`, `transformers==5.19.0`, `onnx==1.19.1`, `onnxruntime==1.29.0` (from `docs/proofs/model-mechanics/requirements-lock.txt`), plus `pyarrow`, `soundfile` and `huggingface_hub`. Install in a venv outside the repo (`uv` works; use plain `torch==2.8.0` with no `+cpu` suffix on macOS, and the matching CUDA wheel on a GPU machine). Device: CUDA, then MPS, then CPU; record it.

## 4. Optimization (pre-registered: 2 runs, plus up to 2 if time allows)

| Setting | Value |
|---|---|
| Optimizer | AdamW, weight decay 0.01, grad-clip 1.0 |
| Required runs | **R1:** lr 3e-5, `p_stutter` 0.40. **R2:** lr 1e-5, `p_stutter` 0.40. |
| Optional, in this order and only if §9 allows | **R3:** lr 3e-5, `p_stutter` 0.25. **R4:** R1's settings with the encoder frozen except the last 2 layers and the classifier. |
| Schedule | 10% linear warmup, then linear decay (upstream full training used 5e-5; fine-tuning goes lower) |
| Batch | 32, or the largest that fits; record it |
| Length | 2 epochs (§2d definition), with a hard cap of 60 minutes wall time per run |
| Checkpoints | every half epoch, plus at the end. Each one is kept and hashed. |
| Seed | 0. Record it, along with torch determinism flags. MPS and CUDA aren't bit-deterministic; say so. |

For scale: on Niko's M2 the review measured about 56 samples/s on MPS and 21–27/s on CPU, plus 8 ms of feature extraction per sample. That is about 35–50 min per run. Precompute features once per sample to remove the 8 ms.

**In-loop fast validation** runs in PyTorch, with no ONNX, at every checkpoint:
- **dev stutter premature:** premature rate at `t = 0.20` on dev `stuttered/unfinished` items;
- **dev fluent premature:** the same at `t = 0.20` on dev `fluent/unfinished` items;
- **guard recall:** at threshold 0.5 on 2c positives;
- **guard specificity:** on 2c negatives.

Log these to `metrics.jsonl`. In-loop PyTorch probabilities match ORT within about 1e-5, so these metrics are good enough to **pre-screen**. Rank checkpoints by in-loop dev stutter premature among those meeting the in-loop M2/M4 constraints (§6), and send only the **top 2** through §5 export and §6. Record the full ranking. This step is pre-registered, so it isn't a free choice.

## 5. Export (every checkpoint that §6 will evaluate)

- `model.eval()`, then wrap the model as `sigmoid(model(x)).reshape(-1,1)`.
- Export with opset 18, input `input_features` and output `logits`, a dynamic batch axis, and the legacy exporter (`dynamo=False`), as the proof did.
- The ONNX checker must pass. A fresh ORT session must match PyTorch probabilities within 1e-5 at B = 1 and 2 on real dev features.
- File name: `stutterturn-v1-r{run}-c{ckpt}.onnx`, kept in the scratch area outside the repo (weights are never committed). Write the CONTRACT §5 metadata JSON beside it, with `status: "dev-candidate"`.

## 6. Selection on dev (pre-registered; test is never used here)

**Runner cost:** `eval_runner.grid_times` (`:167-189`) computes the full 10 ms grid even under `single`. On dev that is about 139k calls, or about 73 min per FP32 model on the M2, while the single schedule uses only about 2,550. **Niko adds a checks-only grid option to the runner** (a separate benchmark spec, reviewed as usual) and a config `agent-v0.1-single-checks.json`. All arms use it. Re-scoring across thresholds stays free.

**Arms**, all run through `eval_runner.py` on `items/v1/dev.jsonl` (plus `dev_end_of_window.jsonl`) under that config:

| Arm | What it is |
|---|---|
| A | stock INT8 |
| B | stock FP32 |
| C | stock FP32 rescored at every threshold 0.50, 0.51, …, 0.99, using `--rescore` (no extra inference), so stock gets as many operating points as the candidate |
| D | the 2 pre-screened candidate checkpoints, at threshold 0.5 |
| E | each D checkpoint rescored at thresholds {0.4, 0.5, 0.6} |
| F (report only) | stock FP32 "patient" waits: `vad_stop_s` 0.4, 0.6 and 0.8, compared with `--allow-config-diff` |

Arms B, C and D are also scored on guard set 2c by `guard_eval.py`, **not** through the runner. Each guard example is scored on its full audio, with ORT and the same preprocessing. **Caveat:** the clips don't end at the turn boundary. Trailing low-energy audio has a median of about 0.99 s for human clips and 0.2–0.3 s for synthetic ones, so full-audio scoring is a check at about 1 s of silence, not at the deployed 0.2 s. Also score **M4b**: positives cut at their energy end + 0.2 s, using the same energy rule as eval-items. Report guard recall and specificity separately from the runner metrics.

**Metrics** (paired by item; Wilson CIs and discordant counts from `compare_runs.py`):
- **M1 (primary):** premature rate, dev stuttered/unfinished.
- **M2:** premature rate, dev fluent/unfinished. This must not worsen.
- **M3:** first-check decision rate on dev fluent end-of-window proxies. This is a weak proxy for "still answers promptly". There are no stuttered end-of-window items in `items/v1`, so the stuttered counterpart can't be measured (§10).
- **M4:** guard recall (completed turns decided complete), on 2c, full audio; **M4b** at energy end + 0.2 s.
- **M5:** guard specificity, on 2c.

**Constraints, against arm B** (stock FP32 at 0.5):
- M2 no more than +1.0 point (the 95% CI upper bound of the paired difference is reported);
- M3 no more than −2.0 points;
- M4 and M4b no more than −1.0 point each;
- M5 not worse.

Constraints apply to the **point estimates**; paired 95% CIs are reported beside them. A candidate that leans toward "incomplete" improves M1, M2 and M5 automatically, so **M3 and M4/M4b are the binding constraints**; read results with that in mind.

**Rule:**
- Among the candidate checkpoints and thresholds (D and E) that meet every constraint, pick the lowest M1. Ties go to the earlier checkpoint.
- Then compare it with **the best arm-C threshold that also meets the constraints**. If no arm-C threshold meets them, compare at **matched M3 and M4**: the arm-C threshold whose M3 and M4 are closest to the candidate's, without being worse.
- **The candidate passes only if its M1 is lower than that arm's M1 and the paired discordant counts favour the candidate.**
- If arm C wins or ties, report it honestly: a threshold change achieves the same.

**Outcome recording:** Vinh records the result in the decision log, with run IDs, sample counts and limits. Possible outcomes:
- the candidate passes;
- a threshold change or FP32 suffices (credit the existing setting);
- nothing passes, in which case take the PLAN fallback scope.

## 7. After selection

1. Rename the selected export to **`stutterturn-v1.onnx`**, set its metadata `status: "selected"`, and record its sha256 in `model/CONTRACT.md` §6. Previous names are never reused.
2. **A single final-test run:** stock FP32, stock INT8 and `stutterturn-v1` on `items/v1/test.jsonl`, once, plus stock FP32 rescored at the arm-C threshold chosen on dev. Record the run IDs. Don't iterate after seeing test.
3. **Agent check (CONTRACT §5.2–5.3):**
   - Set `CANDIDATE_MODEL` in Guttuu's agent and replay 3 dev clips.
   - Probabilities must match `eval_runner` on the same audio cut within 1e-5, after accounting for the agent's `turn_audio` input.
   - Record load time and per-call latency on the demo machine.
4. **Quantization is out of scope for v1.** The demo compares stock FP32 and `stutterturn-v1` FP32 (and stock INT8 for context). An INT8 candidate would be a separate artifact ID with its own evaluation.
5. **License note for release:** the training data includes SEP-28k (CC BY-NC 4.0). The `stutterturn-v1` weights are therefore **non-commercial research use**. Attribute:
   - SEP-28k (Lea et al. 2021); the podcast audio rights stay with the podcast owners;
   - the Smart Turn data (CC-BY-4.0);
   - the Smart Turn v3 weights (BSD-2-Clause);
   - haan (BSD-2-Clause, notices kept).

## 8. Harness to implement (Sonnet) and its acceptance checks

**Files** (under `model/train/`; weights, data caches and exports go outside the repo in a `--work DIR`):
- `fetch_train_audio.py`: §2a audio fetch.
- `build_train_set.py`: §2a/2b/2c. Writes `<work>/data/{stutter_neg,orig_replay,guard}.jsonl` (sample references, labels and weights; no audio) and `manifest.json` with every hash and count.
- `train.py`: §3–4. Writes `<work>/runs/<run_id>/{config.json, metrics.jsonl, ckpt-*.pt, run.json}`. Refuses to overwrite.
- `export.py`: §5, for a checkpoint path.
- `guard_eval.py`: M4/M5 for an ONNX file on the guard set.
- `requirements.txt` (`model/train/`), pinned.

**Checks:**
1. **Data build:** counts printed, including English rows per shard read, the achieved replay and guard sizes, and the dedupe count. The leakage asserts pass, and so does guard-vs-replay waveform dedupe. A rebuild gives identical jsonl hashes. The `language == "eng"` filter keeps more than 0 rows.
2. **Parity before training:** in CPU torch, the recovered model matches the FP32 ONNX within 5e-5 on 3 real dev feature arrays.
3. **Zero-step pipeline identity:** export the *untrained* recovered model through `export.py`, then run `eval_runner` on `benchmark/runs/legacy-items/block.jsonl` with `configs/legacy-block.json`. It must reproduce **stock FP32 87/200 first-check and 109/200 any-check** exactly. This ties the training and export path to arm B. The review showed this is achievable: max diff 3.4e-6 vs stock ORT on 40 real cuts, where the closest legacy probability sits 6e-4 from the threshold.
4. **Learning sanity:** 200 steps on a fixed 64-sample subset drive the training loss below 20% of its starting value.
5. **Throughput:** measured samples/s for forward+backward on the chosen device, and the projected epoch time for the §4 mixture. **Post this on issue #2 before any full run.** If 2 epochs don't fit the 60-minute cap, reduce to the epochs that fit (minimum 1) and say so; don't change anything else.
6. **Checkpoint chain:** for one checkpoint, run `export.py` (parity passes), the metadata JSON, an `eval_runner --scratch` run on 5 dev items, and `guard_eval.py` on 50 guard examples, end to end.
7. **Refusal guards:** `train.py` refuses an existing run directory, `export.py` refuses an existing output name, and `build_train_set.py` refuses any dev or test key, shown with a planted bad key in `--out` scratch mode.

## 9. Timebox (EDT, today)

| By | What |
|---|---|
Rebased at 16:00 after the review and the handoff to Guttuu.

| By | What |
|---|---|
| 18:00 | Harness checks 1–7 pass; data built; throughput posted |
| 18:15 | R1 starts |
| 20:15 | R1 and R2 done (R3/R4 only if both finished by 19:45) |
| 20:45 | Pre-screen + §6 dev comparison done |
| 21:00 | Selection decision recorded by Vinh |
| 21:30 | Single final-test run + agent check |
| 22:00 | Handoff to demo engineering (PLAN 7–10 PM block) |

**Stop rules:** if the harness isn't passing by **18:15**, if R1 hasn't started by 18:30, or if no candidate meets §6 by 21:00, stop model work and record the fallback. Don't extend into the 1 AM freeze.

## 10. Known risks

- **Shortcut learning:** the model may learn "stutter-like voice ⇒ incomplete" and wait too long on *completed* stuttered turns. No completed stuttered labels exist to measure this (eval-items-v1). M4 measures general completed-turn regression only. **State this risk in every claim** until human completed stuttered turns are evaluated.
- **Noisy negatives:** some gaps end in another speaker's speech, which would teach "incomplete" on genuinely finished turns. The 40-item dev review estimates how often this happens; it can't fix training.
- **Show confounds:** train contains the WomenWhoStutter/HeStutters host pair, and WomenWhoStutter is 67% of train blocks, which skews gender. Dev and test have two shows each, so per-show results must be reported.
- **Possible speaker overlap:** a guest named "Geoff" appears in both HeStutters (train) and StrongVoices (test). It's unconfirmed whether it's the same person; note it as a test-leakage caveat.
- **PLAN 3 PM gate wording:** "completed-turn delay within +50 ms per group, including stuttered" can't be measured with `items/v1` (eval-items-v1). §6 uses M3/M4 instead; the gate wording is Vinh's call (issue #2).
- **3 s context:** training negatives carry at most about 2.8 s of audio before the cut, while the model sees 8 s windows (left zero-padded) on both sides of training and inference. Longer real-call context is untested.
