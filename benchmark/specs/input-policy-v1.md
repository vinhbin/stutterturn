# Spec: runner input policy v1 (`turn_onset`)

**Status:** reviewed (Opus, 2026-10-10), revised · **Owner:** Niko · **Extends:** `benchmark/specs/eval-runner-v1.md`

## Why

The runner feeds the model everything from the clip start up to the cut (last 8 s). Guttuu's agent (`agent/engine.py`) feeds only the current turn: audio from its Silero speech onset, minus a pre-roll. On PR #11 we proposed that both sides use one policy: **"current turn from the Silero onset − 0.2 s, up to 8 s"**. This spec adds that policy to the runner as a config option, so a candidate is evaluated on exactly the audio the agent will give it.

Evidence so far ([PR #11 comment](https://github.com/vinhbin/stutterturn/pull/11#issuecomment-6101469046)): on the 200 legacy block clips, the input start changed the agent's premature count 98 (engine as-is, pre-roll bug) / 93 (intended pre-roll) / 93 (clip start). These differences are not significant (McNemar p ≈ 0.4). The option is for **parity**, not because it is expected to move results.

## Config

Two new optional config keys:

- `input_policy`: `"clip_start"` (default when absent: today's behaviour) or `"turn_onset"`.
- `pre_roll_s`: required when `input_policy` is `"turn_onset"`, and must be absent otherwise. v1 configs use `0.2`.

Existing configs don't change, so their `config_sha256` and run IDs stay the same. **Do not `setdefault` these keys in `load_config`**: the resolved config is hashed into `run.json`. Read them with `cfg.get("input_policy", "clip_start")` everywhere, including the rescore guard, so that old runs without the keys don't raise `KeyError`. Add **`benchmark/configs/agent-v0.1-turn.json`**: identical to `agent-v0.1-single.json`, except `config_id: "agent-v0.1-turn"`, `input_policy: "turn_onset"` and `pre_roll_s: 0.2`.

`schedule: "legacy"` with `turn_onset` is refused at config load. Legacy exists only to reproduce the old results.

## Onset definition (must match the agent exactly)

Per clip, computed once from the clip's audio (16 kHz mono float32, as the runner already loads it):

1. Run **Silero VAD v5.1.2** (`silero_vad.onnx`, sha256 `2623a2953f6ff3d2c1e61740c6cdb7168133479b267dfef114a4a3cc5bdd788f`) over consecutive 512-sample frames **aligned to sample 0**, ignoring a trailing partial frame. Use CPU, 1 intra- and 1 inter-op thread. Per frame:
   - `input` = concat(context, frame), shape (1, 576) float32. `context` is the last 64 samples of the previous `input`, all zeros for the first frame.
   - `state` starts as zeros (2, 1, 128) float32 and is carried over from each call's second output.
   - `sr` = `np.array(16000, dtype=np.int64)`.
   - The speech probability is `out[0][0]`.

   This is `SileroVAD` in `agent/engine.py`, but it must be implementable from this text alone.
2. A frame is speech if `p ≥ 0.5`. Speech is declared after `start_n = ceil(vad_start_s / 0.032 − 1e-9) = 7` consecutive speech frames (`vad_start_s = 0.2`). The **onset frame** is the first frame of that run.
3. `pre_roll_frames = round(pre_roll_s / 0.032)`, which is 6 for 0.2. `input_start_sample = max(0, (onset_frame − pre_roll_frames) × 512)`.
4. Use the **first** declared onset in the clip. The benchmark scores each item as if no earlier decision had reset the turn. The agent resets its turn only after a decision, so this matches the agent whenever the item's check is the first decision. Document this in a code comment.
5. **Fallback:** if no onset is declared, or the first onset frame starts at or after the item's `silence_start_s`, use `input_start_sample = 0` and set `input_start_fallback: true` on that item. **Fallback items are not at parity with the agent.** These are mostly items with short pre-speech, where Silero needs 7 frames (0.224 s) to declare speech, so the agent would have no open turn and would never check. They stay in the item set so that runs stay comparable, but every claim about agent parity uses the non-fallback subset only.
6. Parity is with the agent's **intended** pre-roll. The engine at `49716d0` (`agent/engine.py` turn buffer) currently starts the turn one frame *after* the onset. That bug was reported on PR #11.

An onset may be declared up to 6 frames (≤ 0.192 s) after its onset frame, so it can occur after `silence_start_s`. On the fixture, 15 of 155 onsets are declared after `ss`, but none after `ss + 0.2`. Using the onset frame is still correct, because the agent's check comes at `ss + 0.2` or later.

For each grid point, the model input becomes `x[input_start_sample:cut]`. The existing `predict()` then keeps the last 8 s and left-pads. Nothing else in preprocessing changes.

The Silero model is passed by `--vad-model PATH --vad-sha256 HEX`. These are required when the config uses `turn_onset` (exit non-zero otherwise), and the hash is verified before any inference, like the Smart Turn hash guard. Don't vendor the ONNX file into the repo.

## Recorded outputs

- In `results.jsonl`, every item gets `input_policy` and `input_start_s` (= `input_start_sample / 16000`, 6 decimals). Under `turn_onset` it also gets `onset_s` (null if there is none) and `input_start_fallback`.
- In `run.json`, add `vad_model_sha256` (null under `clip_start`).
- In `summary.json`, under `turn_onset` add per group: `input_start_fallback_n`, plus `premature_n_nonfallback`, `n_nonfallback` and their rate with a Wilson CI for unfinished items.
- Add the new per-item fields to `OUTCOME_KEYS` (`eval_runner.py:30`) so that `--rescore` recomputes or carries them consistently instead of copying them as item fields.

## Cache

Keep the table schema. The cache key's `preproc_version` component becomes `PREPROC_VERSION` under `clip_start`, which is unchanged so existing entries still hit, and `f"{PREPROC_VERSION}|start={input_start_sample}|vad={vad_sha256[:16]}"` under `turn_onset`. A `turn_onset` probability can never be served to a `clip_start` run, or the other way round. `turn_onset` items with start 0 deliberately don't reuse `clip_start` entries, even though the input is identical. That keeps check 4 clean.

## Re-scoring and comparison

- `--rescore` refuses if `input_policy` or `pre_roll_s` differ between the stored run and the new config, since the stored grids are for a different input.
- `compare_runs.py` treats `input_policy` and `pre_roll_s` like any other config key: a difference is refused unless `--allow-config-diff` is given. Confirm this holds with the existing code; change it only if it doesn't. Compare via `.get`, so an absent key and an explicit `"clip_start"` count as a difference. That's conservative and should be documented.

## Fixture

`benchmark/fixtures/agent-onset-v1/onsets.csv` (sha256 `d3307a54e0c8610515ec26bb3d633647f8ef0134ef842e5dcb731563310c1c03`) was produced by `generate.py` in the same folder. That script replays all 200 `data/block_eval.csv` clips through Guttuu's engine (turn logic as on `main` `49716d0`). It records:

- the first `speech_start`;
- the intended pre-roll start;
- `cut = round((gap_start + 0.2) × 16000)`;
- `p` = stock INT8 `SmartTurn.predict(x[start:cut])` on macOS arm64.

155 clips have an onset before the gap. 45 fall back: 41 have their first onset at or after `gap_start`, and 4 have no onset. Fallback rows have an empty `onset_frame` and an empty `p_turn_onset_int8_macos`. 129 rows have `input_start_sample = 0`, made up of 84 genuine onsets near the clip start and the 45 fallbacks. (On the new items, a 100-item sample showed 7% fallbacks in dev, 23% in test and 0% in dev end-of-window.)

## Files the implementer writes

- Edits `benchmark/scripts/eval_runner.py` (and `compare_runs.py` only if needed).
- Adds `benchmark/configs/agent-v0.1-turn.json`.
- Appends a short "Input policy" note to `benchmark/specs/eval-runner-v1.md` that points to this spec.

Don't modify the fixture, the items, the splits, `data/`, or anything outside `benchmark/`. Don't commit or push.

## Acceptance checks (paste commands and output)

Setup: the venv from `benchmark/requirements.txt`, stock INT8 and FP32 models with verified hashes, and Silero v5.1.2 from `https://github.com/snakers4/silero-vad/raw/v5.1.2/src/silero_vad/data/silero_vad.onnx` with its hash verified. Make **all runs `--scratch`**.

0. **Baseline before editing:** with the unmodified runner, make `--no-cache` runs of stock INT8 on the legacy items with `legacy-block.json` and with `agent-v0.1-single.json`. Keep these run dirs.
1. **No change under `clip_start`:** after the edit, repeat both runs with `--no-cache`. Each `results.jsonl` must be identical to its baseline once the new `input_policy`/`input_start_s` fields and the timing fields (`infer_ms`) are dropped: every grid probability is bit-identical, and so is every outcome. The legacy run still reports 116/200 first-check and 136/200 any-check. `config_sha256` is unchanged for both configs.
2. **Onset parity with the agent:** run stock INT8 on the legacy items with `agent-v0.1-turn.json`. For all 200 items, `round(input_start_s × 16000)` equals the fixture's `input_start_sample` exactly, and `onset_s` equals the fixture's `onset_s` within 1e-6 (null where the fixture's is empty). Exactly the 45 fixture rows with an empty `onset_frame` have `input_start_fallback: true`. Silero `p ≥ 0.5` can flip across platforms, so this check is binding on macOS arm64 only.
3. **Probability parity:** in the same run, the grid probability at `t = 0.200` matches the fixture's `p_turn_onset_int8_macos` within 1e-5 for all 155 non-fallback items. This applies on macOS arm64 only; elsewhere report it as NOT RUN, because INT8 drifts across platforms. Report the max absolute difference.
4. **Cache isolation:** a second `agent-v0.1-turn` run with the cache on gets 100% hits and identical results. An `agent-v0.1-single` run with the cache on after it gets 0 hits from `turn_onset` entries, meaning its probabilities equal the baseline from check 0.
5. **Guards:**
   - `turn_onset` without `--vad-model` exits non-zero.
   - A wrong `--vad-sha256` exits non-zero before inference.
   - `legacy` + `turn_onset` is refused at config load.
   - `pre_roll_s` under `clip_start` is refused.
   - `--rescore` of a `clip_start` run with `agent-v0.1-turn.json` is refused.
   - `compare_runs.py` refuses a policy-only difference without `--allow-config-diff`. Test it with a scratch copy of the turn config whose `config_id` is `agent-v0.1-single`, because differing `config_id`s are refused anyway and would make the test vacuous.
6. **Report, not a criterion:** first-check premature totals on the legacy items for `agent-v0.1-single` vs `agent-v0.1-turn`, stock INT8 and stock FP32, with the paired discordant counts, both for all 200 items and for the 155 non-fallback items. This states the policy effect in the benchmark's own timing.

If the data contradicts the spec (for example, onsets don't match the fixture), stop and report the first mismatches. Don't adapt. Report any check you couldn't run as **NOT RUN** with the reason, never as passed.
