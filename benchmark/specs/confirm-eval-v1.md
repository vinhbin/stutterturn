# Spec: confirmation evaluation v1 (promotion check (d))

**Status:** reviewed (Opus, 2026-10-10), revised · **Owner:** Niko (evaluation) · **Pre-registered before any confirmation label exists.** **Applies to:** the X1 candidate (`model/specs/x1-blend-check-v1.md`; `x1_pass_dev_exploratory`) and its promotion check (d) under `training-v4.md` §4 and X1 §5. **Inputs:** `benchmark/items/confirm-v1/confirm.jsonl`, built by `build_confirm_items.py` from the adjudicated labels. **D-009 is unchanged: test sealed.**

## 0. Preconditions (checked by the scoring script)

1. The decision log has the freeze entry: the sha256 of `adjudicated.csv` and of `confirm.jsonl`, as printed by `build_confirm_items.py`.
2. `build_confirm_items.py --check benchmark/items/confirm-v1` passes, and `confirm.jsonl`'s sha256 equals the logged value.
3. **The set of `benchmark/runs/conf-*` directories equals the §1 run-ID list exactly**: no extras, no suffixes, nothing missing. Each one's `items_sha256` equals the logged `confirm.jsonl` hash. Any extra `conf-*` directory means an unregistered look, and the scoring script refuses.

## 1. What runs (exactly once, one platform, one machine for inference *and* rescoring)

- **Platform:** Guttuu's machine (Windows 11, ORT CPU), which holds the X1 export. The confirmation keys' dev audio is fetched there first. **All rescores run on the same machine,** because `env.platform` comes from the rescoring host.
- **Primary configuration family: `turn_onset`** (`agent-v0.1-turn-checks` and `agent-v0.1-patient-0{4,6,8}-turn-checks`). That's the agent's actual input. **Secondary (report only): `clip_start`** (`agent-v0.1-single-checks`), for arms X and S only.
- **Exact commands.** `P` = the venv python, and the common flags are `--items benchmark/items/confirm-v1/confirm.jsonl --vad-model agent/models/silero_vad.onnx --vad-sha256 2623a2953f6ff3d2c1e61740c6cdb7168133479b267dfef114a4a3cc5bdd788f`.

  | Run ID | Command (beyond the common flags) | Role |
  |---|---|---|
  | `conf-X-turn` | `--model <X1 export> --model-id x1 --expected-sha256 d1a503fee1eca1e6d6ffe78e918d8ed312922eddb5f3dd19cc5315c1b824c025 --config benchmark/configs/agent-v0.1-turn-checks.json` | X inference at 0.5 (not a criterion) |
  | `conf-X-turn-th0.60` | `--rescore benchmark/runs/conf-X-turn --config benchmark/configs/agent-v0.1-turn-checks.json --threshold 0.6` | **candidate X** |
  | `conf-S-turn` | `--model <stock FP32> --model-id stock-fp32 --expected-sha256 ab8dc64b88713f90b571c15b714bd1330e6c883cad8763dacf65c9376dc539be --config benchmark/configs/agent-v0.1-turn-checks.json` | **stock baseline S** |
  | `conf-C-turn-th0.55` | `--rescore benchmark/runs/conf-S-turn --config benchmark/configs/agent-v0.1-turn-checks.json --threshold 0.55` | comparator, report only |
  | `conf-F04-turn`, `conf-F06-turn`, `conf-F08-turn` | stock FP32 with `agent-v0.1-patient-0{4,6,8}-turn-checks.json` | patient baselines on the same inputs (PLAN) |
  | `conf-X-clip`, `conf-X-clip-th0.60`, `conf-S-clip` | as X and S, with `agent-v0.1-single-checks.json` (no VAD flags) | secondary, report only |

  Every command passes **`--run-id <the ID in the table>`**, so with `--run-id` no automatic `-th` suffix is added. These 10 IDs are the only `conf-*` runs allowed.

## 2. Groups and metrics (per group: stuttered, fluent)

Use the item kinds from `confirm.jsonl`: stuttered/fluent × unfinished/completed, all `label_source=human`.

- **P (premature), unfinished items:** the share where the arm decides "complete" before `resume_s`. This is the runner's `premature`.
- **D (agent delay model), completed items:** 3-second windows end before the 3.0 s fallback, so the runner gives `trigger=model` or censored. **Pre-registered model:** D = the arm's configured **`vad_stop_s`** (0.2 for X/S/C, 0.4/0.6/0.8 for F) if `trigger == "model"`, otherwise **3.0 s**, the agent's fallback; censored items are assumed to hit the fallback, which is stated. Report the mean and median D.
- **R (fallback rate, first check missed):** the share of completed items not decided at the first check. The agent still answers, at 3.0 s, so this is **not** PLAN's "no response". Real non-responses (timeouts, provider failures) aren't measured here.

## 3. Pre-registered promotion criteria (all must hold; candidate X vs stock S, primary family)

1. **Premature:** P(X) **< 10%** in **each** group, the PLAN target.
2. **Fluent unfinished not worse:** P_fluent(X) ≤ P_fluent(S), on point estimates.
3. **Completed-turn delay:** **mean** D(X) − mean D(S) ≤ **+0.050 s** in each group.
   - **This is stricter than PLAN's median test, on purpose.** Under this delay model the median can only be 0.2 or 3.0 s, so a median test says almost nothing.
   - **Mean D = 0.2 + 2.8·R,** so this equals ΔR ≤ 1.79 points. At about 20 items per cell, one item is about 5 points, so **criterion 3 is effectively R(X) ≤ R(S)**, the same as criterion 4.
4. **Fallback rate not worse:** R(X) ≤ R(S) in each group.
5. **Minimum evidence:** at least **10** human-accepted items in each of the four group × kind cells. If any cell has fewer, the outcome is **`confirm_insufficient`**, with no promotion. **This outcome is likely:** confirm-set yields are expected to be low, especially for `unfinished_fluent_pause`. Saying so up front is part of the pre-registration.

**Outcomes:** `confirm_pass_feasibility` (all of 1–4, with 5 met), `confirm_fail`, or `confirm_insufficient`. Every number is reported with its Wilson 95% CI and n.

**Patient baseline (PLAN):** F04, F06 and F08 run on the same `turn_onset` inputs, and the report states whether each meets criteria 1–4 against S. That shows whether simply waiting achieves the same thing. It's a report, not a criterion on X.

**Wording, whatever the outcome:** "X1 was a post-hoc exploratory candidate (fifth adaptive look at dev/guard). The confirmation set is untouched recordings from the same two dev shows (possibly the same speakers), human-labelled and blind." A pass permits promotion **to the demo as an experimental configuration, alongside stock and patient**, once (c) audio acceptance has also passed. **It doesn't permit any efficacy claim; D-009's test stays sealed.**

## 4. Limits (stated in the report)

- **Timing:** the agent checks 7 frames × 32 ms = 0.224 s after its VAD speech-stop; the runner checks 0.2 s after the labelled silence start. The offset is the same for every arm, so the X − S comparison stays fair, but absolute delays aren't the agent's.
- **Mid-turn pauses:** the runner checks only at the labelled pause or turn end. The agent also checks at any VAD pause earlier in the clip, which isn't evaluated here.
- **Not measured:** tail delay and audible response delay, which PLAN asks for. They belong to (c) audio acceptance, not here.
- **Small n:** about 20 items or fewer per cell, the same two shows as dev, and proxy-free human labels. These are feasibility results.

## 5. Scoring script: `benchmark/scripts/score_confirm.py` (implemented later, after review)

- **Checks:** §0. It also checks that every run shares one `env.platform`, and that the model and VAD hashes match §1.
- **Output:** `benchmark/selection/confirm-x1/decision.{json,md}`, containing:
  - §2 metrics per arm and group, with CIs;
  - the §3 criteria for X vs S, and the F arms against criteria 1–4;
  - the outcome, the paired discordant counts X vs S, the report-only arms, and the §4 limits and wording verbatim.

  It refuses if the output exists. It changes no threshold and selects nothing.
- **Acceptance (later):** synthetic runs from synthetic labels, built in the scratchpad with scratch run IDs and an override of the `conf-*` prefix check for testing only. It covers hand-computed metrics on a 10-item fixture, each refusal (including an extra `conf-*` directory), and each outcome, including a cell with 9 items.

## 6. What this spec deliberately does not allow

- Choosing a different threshold, configuration or candidate after seeing confirmation results.
- Re-running any arm, unless a run crashes; then re-run unchanged and report the crash.
- Pooling the confirmation set with dev items, or using it for training or selection.
- Treating report-only arms (C, F, `clip_start`) as criteria on X.
