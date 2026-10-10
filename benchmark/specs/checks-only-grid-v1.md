# Spec: runner checks-only grid v1 (`grid_scope`)

**Status:** reviewed (Opus, 2026-10-10; no blockers; core claim proven, 0 differences in 42k real + 2.4M synthetic comparisons), revised · **Owner:** Niko · **Extends:** `benchmark/specs/eval-runner-v1.md`, and is implemented **on top of** `benchmark/specs/input-policy-v1.md` (that change must land first; both edit `load_config` and `do_rescore`) · **Needed by:** `model/specs/training-v1.md` §6

## Why

`grid_times` (`eval_runner.py:167-189`) computes a probability every `grid_step_s` (10 ms) from `vad_stop_s` to the resume, end of observation or fallback, whatever the schedule. Under `single`, `decide` reads only **one** of those points. On `items/v1` dev (1,870 main + 680 end-of-window items), that comes to about 139k model calls, roughly 73 min per FP32 model on Niko's M2, when the schedule needs only about 2,550. Training selection (training-v1 §6) needs stock INT8, stock FP32, 2 candidates and 3 patient arms on dev tonight. That doesn't fit at full-grid cost.

The full grid stays the default. It is what makes offline re-scoring across **schedules** possible. Checks-only gives up schedule re-scoring and keeps threshold re-scoring, which is all §6 needs.

## Config

One new optional key:

- `grid_scope`: `"full"` (default when absent: today's behaviour) or `"checks"`.

**Refuse any other value at config load** (a typo such as `"check"` would otherwise run silently as a full-grid run). Read it with `cfg.get("grid_scope", "full")` and **don't `setdefault` it**, the same rule input-policy-v1 sets for its keys, so existing configs keep their `config_sha256` and run IDs.

`schedule: "legacy"` with `grid_scope: "checks"` is refused at config load. Legacy already evaluates only its checkpoints, and allowing both would add a second way to spell the same run.

New configs:

- `benchmark/configs/agent-v0.1-single-checks.json`: `agent-v0.1-single.json` plus `"grid_scope": "checks"`, with `config_id: "agent-v0.1-single-checks"`.
- `benchmark/configs/agent-v0.1-turn-checks.json`: `agent-v0.1-turn.json` plus `"grid_scope": "checks"`, with `config_id: "agent-v0.1-turn-checks"`.

## Behaviour

Under `"checks"`, the inference loop evaluates only `check_times(grid_times(it, cfg), cfg)`:

- `single`: just the `vad_stop_s` point, if it is on the item's grid;
- `interval`: every point on `vad_stop_s + k·recheck_interval_s`.

Everything downstream is unchanged:

- The stored `grid` holds only those points.
- `decide()` already derives its checks from the grid's keys via `check_times`. On a check-points-only grid it must return **exactly** the same outcome as on the full grid; acceptance check 1 proves this.
- The fallback and censoring logic doesn't read the grid.
- Items whose grid is empty, because the gap is shorter than `vad_stop_s`, behave as today.

**Cache:** unchanged. Keys are per cut sample, so checks-only calls reuse full-grid entries and the reverse. A checks run after a full run of the same model, items and input policy gets 100% hits.

## Re-scoring

`do_rescore` today requires every point of `grid_times(it, cfg)` (`eval_runner.py:452-460`). Change only how `need` is computed:

- **Target config `"checks"`:** `need` = the check points `check_times(grid_times(it, cfg), cfg)`, and the output grid keeps only those.
- **Target config `"full"`:** unchanged, so re-scoring a checks run into a full config fails with the existing "lacks N required points" refusal. That is the intended refusal; don't special-case it.

Threshold-only re-scoring of a checks run (training-v1 arm C: 0.50…0.99) therefore needs 0 model calls.

**Threshold sweeps (arm C):**
- Each threshold config **keeps `config_id: "agent-v0.1-single-checks"`** and changes only `threshold`. That makes D (checks run) vs C (checks rescore) a threshold-only difference, which `compare_runs` already accepts. A per-threshold `config_id` would be refused.
- Run IDs have one-second resolution (`make_run_id`), so a fast loop can collide. Add `--threshold X` to `--rescore` (it overrides the config's threshold and appends `-th{X:.2f}` to the run ID), and run sweeps with `--scratch`.
- The sweep's runs are evidence only once the selected comparison is re-run without `--scratch`. Changing `vad_stop_s` is still refused by the existing guard. The patient arms are separate inference runs, which is cheap under checks.

## Comparison

`compare_runs.py` today refuses any config difference except `threshold` (`compare_runs.py:44-48`), and that includes `config_id`. A difference whose keys are all within {`threshold`, `grid_scope`, `config_id`} **and** includes `grid_scope` is allowed without `--allow-config-diff`, because outcomes are proven identical. `config_id` is exempt only in that case. Every other `config_id` difference is still refused. Normalise `grid_scope` with `.get(…, "full")` on both configs **before** computing `diff`; today `diff` uses a raw `.get` (`compare_runs.py:44`). Two different schedules can't slip through, because `schedule` or `recheck_interval_s` would show up in `diff`. The header must still print it (`grid_scope: full vs checks`). Every other refusal is unchanged. Compare via `.get(…, "full")`, so absent and explicit `"full"` are equal here. This is the opposite of the conservative rule for `input_policy`, because here equivalence is proven.

## Recorded outputs

- `run.json`: the resolved config already carries `grid_scope` when the file has it. Add top-level `model_calls` = cache misses (actual inferences, the meaning rescore already uses with `model_calls: 0`) and `grid_points` = hits + misses, so cost is visible.
- `summary.json`: no change. Per-group `infer_ms.n` differs between full and checks runs; that is expected.
- Patient configs (`vad_stop_s` 0.4–0.8) have items with no check point, so their call counts fall below the item count; that is expected too.

## Files the implementer writes

- Edits `benchmark/scripts/eval_runner.py` and `benchmark/scripts/compare_runs.py`. Line references in this spec are to the pre-input-policy runner; they will have moved.
- Adds the two configs above.
- Appends a short "Grid scope" note to `benchmark/specs/eval-runner-v1.md` that points here.

Don't modify items, splits, fixtures, `data/`, or anything outside `benchmark/`. Don't commit or push.

## Acceptance checks (paste commands and output)

Setup: the existing venv and models (INT8, FP32 and Silero, with verified hashes). Make **all runs `--scratch`**. Subset files go in the scratchpad:

- `sub_main.jsonl` = the first 300 lines of `items/v1/dev.jsonl`;
- `sub_eow.jsonl` = the first 100 lines of `items/v1/dev_end_of_window.jsonl`.

Never use `test.jsonl`; it is sealed.

1. **Equivalence, single schedule:**
   - Run stock INT8 with `agent-v0.1-single.json` (full) and with `agent-v0.1-single-checks.json`, both `--no-cache`, on `sub_main`, `sub_eow` and `runs/legacy-items/block.jsonl`.
   - For every item, every outcome field (`outcome`, `premature`, `decision_t`, `trigger`, `margin_s`, `delay_s`, `censored_at_s`) is identical, and the checks run's grid probabilities are bit-identical to the same keys in the full run.
   - Report the call count of each run.
2. **Equivalence, interval schedule:** same as check 1 on `sub_main` with a scratch copy of `interval-50ms.json`, with and without `grid_scope: "checks"`.
3. **Equivalence, input policy:** same as check 1 on `sub_main` with `agent-v0.1-turn.json` vs `agent-v0.1-turn-checks.json`.
4. **Cost on full dev:**
   - Run stock INT8 and stock FP32 with `agent-v0.1-single-checks.json` on the full `dev.jsonl` and `dev_end_of_window.jsonl`, with the cache on.
   - Report `model_calls` (cache misses), `grid_points`, `wall_s` and premature or decided counts. The expected call count is about 2,550 per model, and lower if some items have no check.
   - Don't run the full-grid version on full dev; checks 1–3 establish equivalence.
5. **Re-scoring:**
   - From the check 1 checks-run on `sub_main`, rescore at thresholds 0.50, 0.75 and 0.99 with **0 model calls**. Outcomes must equal rescoring the check 1 full run at the same thresholds into the checks config.
   - Rescoring the checks run into `agent-v0.1-single.json` (full) is refused with "lacks … required points".
   - `--rescore … --threshold 0.73` writes a run ID ending `-th0.73`, and two such rescores issued in the same second don't collide.
6. **Guards and hashes:**
   - `legacy` + `grid_scope: "checks"` is refused at config load, and so is `grid_scope: "check"` (an invalid value).
   - `config_sha256` of `agent-v0.1-single.json`, `agent-v0.1-turn.json`, `interval-50ms.json` and `legacy-block.json` is unchanged from before the edit; record the before values first.
   - `compare_runs.py` accepts full vs checks of the same model and items, printing the `grid_scope` difference.
   - It accepts a checks run vs a checks rescore of it at another threshold with the same `config_id` (the training-v1 D vs C case).
   - It refuses full vs checks when `vad_stop_s` also differs.
   - It still refuses a run pair differing in `vad_stop_s` without `--allow-config-diff`. Test this with a scratch config that keeps `config_id`, because differing `config_id`s are refused anyway.
7. **Regression:** the legacy run (`legacy-block.json`, stock INT8) still reports 116/200 first-check and 136/200 any-check.

If any equivalence check finds a difference, stop and report the first differing items. Don't adapt `decide()` to hide it. Report any check you couldn't run as **NOT RUN** with the reason, never as passed.
