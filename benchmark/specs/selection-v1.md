# Spec: candidate selection script v1 (`select_candidate.py`)

**Status:** reviewed (Opus, 2026-10-10), revised · **Owner:** Niko · **Implements:** `model/specs/training-v1.md` §6 (pre-registered selection on dev) · **Depends on:** `benchmark/specs/checks-only-grid-v1.md` (`grid_scope`, `--rescore --threshold`; must land first), `model/train/guard_eval.py` (`--out` JSON with `per_row`), `model/train/prescreen.py` (`prescreen.json`), `model/train/export.py` (metadata JSON), all on `guttuu/train-harness`.

## Why

At about 20:45 tonight, §6 needs these arms on dev:

- A, B and D as inference runs;
- C as a 50-threshold sweep by rescoring;
- E as rescores;
- F and G as report-only arms;
- metrics M1–M5 plus M4b;
- the constraints against B, then the pre-registered rule.

Doing that by hand under time pressure invites mistakes. One script runs the whole chain, writes a decision file, and leaves no step to judgment. **The script reports a development decision; Vinh records it in the decision log. The efficacy claim comes only from the single test run in training-v1 §7.2.**

## Where it runs

All official arms run on **one machine**: the one holding the candidates and the guard data (Guttuu's). INT8 and Silero numerics differ across platforms, and comparisons are only valid within one platform. That machine needs:

- `benchmark/scripts/fetch_split_audio.py --splits dev`, which skips present files; its defaults, `block` and `fluent`, suffice;
- the stock models with verified hashes.

The script refuses to proceed if the `env.platform` of its runs differ. Guard JSONs don't record a platform, so `decision.json` records the operator-stated platform (`--platform-note`, required).

Stock arms A, B, C and F don't depend on candidates. They **may be pre-run earlier on the official machine** via `--stock-only` and are reused by the later full run. Runs on other machines, such as Niko's, are **previews, never evidence**.

Runtime estimate: about 22k model calls in total, so 10–15 min of CPU inference plus about 112 rescore subprocesses (2–5 min).

## Interface

```
python benchmark/scripts/select_candidate.py \
  --out-id <name> --platform-note "<os/cpu>" \
  --stock-int8 PATH --stock-fp32 PATH \
  --prescreen W/prescreen.json --train-manifest W/data/manifest.json \
  --candidate PATH [--candidate PATH] \
  --guard stock-fp32=G0.json --guard <candidate model_id>=G1.json [...] \
  [--vad-model PATH --vad-sha256 HEX]        # enables report-only arm G
  [--stock-only]                             # run A, B, C, F only, for reuse by a later full run with the same --out-id
  [--scratch --items-main PATH --items-eow PATH]   # subset override, only with --scratch
```

### Input checks (all before any inference)

- **Stock models** must match the pinned hashes `2bb02631…` (INT8) and `ab8dc64b…` (FP32).
- **Candidates:**
  - Read the metadata JSON beside each candidate (`<file stem>.json`, as `agent/engine.py` reads it).
  - Require `sha256(file) == meta["sha256"]`, `meta["status"] == "dev-candidate"` and `meta["threshold"] == 0.5`.
  - Identify each candidate as `meta["provenance"]["run_id"] + "/" + meta["provenance"]["checkpoint"]`. Never parse the file name.
  - The set of candidate IDs must equal `prescreen.json` `top2`, and the count must match. If `top2` is empty, write a decision with outcome `dev_nothing_passes` and run only the stock arms. If it has 1 entry, exactly 1 `--candidate` is required.
- **Items:** by default `benchmark/items/v1/dev.jsonl` and `dev_end_of_window.jsonl`, each checked against `items/v1/manifest.json` `output_sha256["dev.jsonl"]` and `output_sha256["dev_end_of_window.jsonl"]`.
  - **Refuse any item path that has a path component or basename starting with `test`**, compared case-insensitively via `os.path.normcase`.
  - Apply this to item paths only, so fixture paths like `benchmark/tests/...` aren't refused.
- **Guard JSONs:**
  - Exactly one for stock FP32 and one per candidate, each keyed by the candidate's `meta["model_id"]`.
  - Each `model_sha256` must equal its model's hash, and stock's must equal the pinned FP32 hash.
  - Each needs `per_row` (`id`, `label`, `p_full`, `p_cut`), with `n` equal to the guard count in `--train-manifest`. This rejects `--limit` runs.
  - Every file must have the same id set, the same labels, and the **same set of null-`p_cut` rows**. Those depend only on the audio.
  - Recomputing M4 and M5 at 0.5 from `per_row` must equal the file's `M4_recall_full` and `M5_specificity_full`.
- **Output:** `benchmark/selection/<out-id>/`, refused if it exists, unless it contains a completed `--stock-only` stage and this is the full run. With `--scratch`, the out-id is prefixed `scratch-` and every runner call uses `--scratch`. Add `benchmark/selection/.gitignore` containing `scratch-*`.

## Arms

All runner calls use `configs/agent-v0.1-single-checks.json` unless stated otherwise, and each runs on both the main and the end-of-window items. Invoke the runner as a subprocess (`sys.executable`, list arguments, no shell), passing `--run-id <out-id>-<arm>-<main|eow>[-thX.XX]`; don't parse stdout. Official C and E rescores are **non-scratch evidence**, which overrides the scratch suggestion in checks-only-grid-v1.

| Arm | How |
|---|---|
| A | stock INT8, inference. No guard metrics. |
| B | stock FP32, inference |
| C | B rescored with `--threshold` 0.50, 0.51, …, 0.99 (50 values, 0 model calls) |
| D | each candidate, inference at 0.5 |
| E | each D rescored at 0.40, 0.50 and 0.60 |
| F (report only) | stock FP32 inference with new configs `agent-v0.1-patient-{04,06,08}-checks.json` (`vad_stop_s` 0.4/0.6/0.8; otherwise identical to single-checks; their `config_id`s differ, so comparisons use `--allow-config-diff`) |
| G (report only) | B and the selected candidate under `agent-v0.1-turn-checks.json`, only with `--vad-model`. Run it for B only if no candidate is selected. |

## Metrics (per arm × threshold), always from `results.jsonl` and `per_row`, never `summary.json`

- **M1:** the mean of `premature` over main rows with `group == stuttered` and `kind == unfinished`.
- **M2:** the same over `group == fluent` and `kind == unfinished`.
- **M3:** over **all** end-of-window rows with `group == fluent` and `kind == completed`, the fraction with `trigger == "model"`. Censored rows stay in the denominator.
- **M4:** over guard rows with `label == 1`, the fraction with `p_full > th`.
- **M4b:** over guard rows with `label == 1` and a non-null `p_cut`, the fraction with `p_cut > th`. Record `M4b_n`; negatives always have a null `p_cut`.
- **M5:** over guard rows with `label == 0`, the fraction with `p_full ≤ th`.

Arm C uses stock FP32's guard file, and arms D and E use their candidate's. Guard probabilities are rounded to 6 decimals in the file, which is acceptable; the M4/M5 input check above confirms consistency at 0.5.

**Per-show M1:** join `clip_key` to the `show` column of `benchmark/splits/v1/dev.csv` (items have no show field).

For each metric, report `n` and a Wilson 95% CI. Against B, also report:

- discordant counts `(b, c)`, where `b` = rows true under B and false under the arm, and `c` the reverse, for the metric's event;
- an exact two-sided McNemar p;
- a **Wald 95% CI for the paired difference**, `Δ ± 1.96·sqrt(b + c − (b − c)²/n) / n`, labelled "Wald (paired)".

CIs and p-values are reported and never bind.

## Constraints and rule (training-v1 §6; point estimates bind)

Every candidate operating point (a D or E row) and every C row is checked against **B** (stock FP32 at 0.5):

- ΔM2 ≤ +1.0 point;
- ΔM3 ≥ −2.0 points;
- ΔM4 ≥ −1.0 point;
- ΔM4b ≥ −1.0 point;
- ΔM5 ≥ 0.

Compare with a 1e-9 tolerance, so a value exactly at a bound passes. `decision.md` notes that on about 1.5k guard negatives, one flipped row decides ΔM5.

1. **Selected candidate:** among D/E rows meeting every constraint, the lowest M1. Ties go to the **earlier checkpoint** (lower `meta["provenance"]["epoch"]`, then `top2` order), then the threshold closest to 0.5, then the lower threshold. If none qualify, the outcome is **`dev_nothing_passes`**.
2. **Comparator:** always computed, even when no candidate is selected. It is the C row with the lowest M1 among those meeting every constraint; ties go to the threshold closest to 0.5. *C includes 0.50, which is B itself with every Δ = 0, so a comparator always exists and §6's matched-M3/M4 fallback can never trigger.* Put that sentence in a code comment.
3. **Outcome:**
   - **`dev_candidate_passes`** if the selected M1 < the comparator's M1 **and** the paired discordant counts favour the candidate (`b > c`, with `b` = items premature under the comparator but not the candidate).
     - On identical items, `M1_comp − M1_cand = (b − c)/n` exactly, so this clause is implied by the first and adds no significance test. Assert the identity, and refuse if the two item sets differ. `decision.md` says plainly that the clause is not a significance test and shows McNemar p beside it.
   - Otherwise **`dev_threshold_suffices`**, if the comparator's M1 < B's M1.
   - Otherwise **`dev_stock_suffices`**.
   - Under `dev_nothing_passes`, also record `comparator_M1_below_B`, because §6's "a threshold change suffices" still applies.
4. **Test plan:** write a `test_plan` block for training-v1 §7.2:
   - the selected candidate's file, sha256 and threshold;
   - the comparator's threshold, so stock FP32 can be rescored on test;
   - the arms to run.

   **If the selected threshold isn't 0.5, `decision.json` must state that §7.1 has to set the selected export's metadata `threshold` to that value**: the agent reads it, and `export.py` writes 0.5.

## Outputs

- **`decision.json`:**
  - inputs: paths, hashes, items sha256, prescreen sha256, guard file sha256s, `--train-manifest` sha256, `code_commit`, runner platform and `--platform-note`;
  - every run ID;
  - the full metric table, with one row per arm × threshold × candidate;
  - the constraint flags;
  - the selected row, the comparator row, the outcome, `comparator_M1_below_B` and `test_plan`;
  - the limits text.
- **`decision.md`:** it **opens with** PLAN's wording: *"Development decision, not a publishable efficacy result. The candidate was ranked and selected on these dev items (pre-screen on M1, then up to 6 operating points); the claim comes only from the single test run in training-v1 §7.2."* Then:
  - a short table of B, the comparator, the selected candidate and A;
  - the constraint deltas with Wald CIs and McNemar p;
  - the outcome on one line;
  - the per-show M1;
  - the report-only F/G arms;
  - the `test_plan`;
  - the limits text verbatim: energy-derived labels; end-of-window proxies; guard set not perfectly independent of upstream checkpoint choice; no stuttered completed turns; the training-v1 §10 shortcut-learning risk; and the ΔM5 one-row note.

  The wording reports data and never states a verdict about the gate.

## Files the implementer writes

- `benchmark/scripts/select_candidate.py`
- `benchmark/configs/agent-v0.1-patient-{04,06,08}-checks.json`
- `benchmark/selection/.gitignore`
- `benchmark/tests/fixtures/selection/`, for synthetic inputs

Don't modify `eval_runner.py`, `compare_runs.py`, `model/`, `agent/`, items, splits or data. Don't commit or push. Must also run on Windows: use `os.path`, `sys.executable`, `subprocess` with list arguments, and no shell features.

## Acceptance checks (paste commands and output)

No real candidates exist yet, so the checks use stand-ins:

- **Candidate files:** copies of stock INT8 and FP32 with hand-written metadata in export.py's format (`sha256`, `status`, `threshold`, `model_id`, `provenance.{run_id, checkpoint, epoch}`).
- **Pre-screen:** a hand-written `prescreen.json` and `train-manifest`.
- **Guard files:** synthetic guard JSONs with matching hashes (about 200 rows with fixed probabilities).

1. **Guards.** Each of these must exit non-zero before any inference:
   - a test item path such as `.../items/v1/test.jsonl`;
   - a candidate whose hash differs from its metadata;
   - `status` not `dev-candidate`;
   - a metadata threshold of 0.6;
   - candidate IDs not equal to `top2`;
   - a candidate count mismatched with `top2`;
   - a guard JSON with a different id set;
   - a guard JSON with different null-`p_cut` rows;
   - a guard `n` not equal to the manifest;
   - a guard `model_sha256` mismatch;
   - stock guard not equal to the pinned FP32 hash;
   - an existing out-id;
   - `--items-main` without `--scratch`.

   A fixtures path under `benchmark/tests/` is **not** refused.
2. **Rule logic, unit-tested on synthetic metric tables** (no inference). Cases that must yield:
   - `dev_candidate_passes`;
   - `dev_threshold_suffices`, where a C threshold beats the candidate;
   - `dev_nothing_passes`, where every candidate fails ΔM3, with `comparator_M1_below_B` true in one variant and false in another;
   - `dev_stock_suffices`;
   - a constraint exactly at its bound (+1.0 point) passing;
   - each tie-break, including an "earlier checkpoint" case where `top2` order and epoch order disagree;
   - `test_plan` noting a non-0.5 selected threshold;
   - an empty `top2`.

   Also assert `b − c = n·ΔM1` on the comparisons.
3. **Guard metrics:** on a synthetic `per_row`, M4/M4b/M5 at 3 thresholds equal hand-computed values, and a null `p_cut` is excluded from M4b and counted.
4. **End-to-end dry run on this Mac** with `--scratch`:
   - **Subset:** a stratified dev subset, 150 stuttered and 150 fluent main items, plus 100 end-of-window items. **Each set includes both dev shows.** Write it to the scratchpad.
   - **Stand-ins and arm G:** the stand-in candidates, with Silero for arm G.
   - **Pass criteria:**
     - it completes, and `decision.md` is pasted;
     - B's M1 and M2 equal a direct `eval_runner` FP32 run on the same subset;
     - C at 0.50 equals B on every metric;
     - the per-show M1 lists both shows;
     - the script's discordant counts for B vs A on M1 equal `compare_runs.py`'s output for the same pair.

   Report wall time and total model calls. Also run `--stock-only` and then the full run with the same out-id, and show that the stock runs are reused (0 new stock inference).
5. **No test leakage:** `grep` shows the only reference to test items is the refusal.

Report any check you couldn't run as **NOT RUN** with the reason, never as passed.
