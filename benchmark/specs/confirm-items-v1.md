# Spec: confirmation items builder v1 (`build_confirm_items.py`)

**Status:** reviewed (Opus, 2026-10-10; prototype: `apply_annotations` works with empty state and split `confirm`, all four categories, items pass `load_items`), revised · **Owner:** Niko (evaluation) · **Completes:** `benchmark/specs/confirm-set-v1.md` §"Turning labels into items" (that step was NOT RUN because `build_items.py --annotations` re-runs the energy pass on **test** and rewrites `test.jsonl`, which is against D-009's intent). **It turns the reviewed confirmation labels into runner items without touching test or the v1 items.** This script **supersedes** the `--confirm-only` mode that `confirm-set-v1.md` mentions; there's no change to `build_items.py`.

## Why a separate script, not a mode of `build_items.py`

`build_items.py` owns the frozen `items/v1` (dev + test, energy pass, review queue). Adding a mode there risks its v1 invariants. The new script **imports** `build_items.py`'s `apply_annotations`, `Gate`, `ANN_HEADER`, `CATEGORIES`, `mk_item` and `prov_row` and doesn't copy them. It **never calls** `energy_pass`, `build_queue`, `main` or anything that reads test.

## Inputs (and nothing else)

- `benchmark/confirm/v1/worksheet.csv` and `manifest.json`: worksheet sha256 must equal `manifest.json`'s recorded value (`037190de…939c`).
- `benchmark/annotations/confirm-v1/adjudicated.csv`: **the single adjudicated file**, with the exact `ANN_HEADER`. Any other `.csv` in that directory → refuse.
- `benchmark/annotations/confirm-v1/crosscheck-note.md`: must exist. It's hashed, not parsed.
- `benchmark/splits/v1/dev.csv`, for the `start` offset used by `time_origin=episode_start`. Only worksheet keys are loaded from it.
- Audio for worksheet keys under `benchmark/audio/`, through `Gate`.

A guarded `open()` refuses any path under `benchmark/runs/`, `benchmark/selection/`, `model/evidence/`, `benchmark/items/v1/`, or any file whose basename starts with `test`. It's installed process-wide before imports, as in `build_confirm_set.py`.

## Processing

1. **Worksheet join.** Every annotation row's `(sample_id, source_id)` must match a worksheet row exactly. Otherwise refuse, naming the row.
2. **No skipping (anti-cherry-picking).** Within each worksheet bucket (the proposed `category`), the annotated `sample_id`s must form a **contiguous prefix** of that bucket's worksheet order. Every row up to the last annotated one is present, accepted or rejected. If there's a gap, refuse, listing the missing `sample_id`s.
3. **No silent category switch, filtered *before* `apply_annotations`.** `apply_annotations` builds items from the annotated category, so the check has to come first:
   - **Filter:** rows with `accepted=true` and `category` ≠ the worksheet's proposed category are dropped and recorded as `category_mismatch`. That's tallied, not fatal; the reviewer should have recorded `accepted=false` with the reason.
   - **Stage:** only the filtered rows are written to a staging directory inside the out dir's temp area, which is passed as `ann_dir`.
   - **Record:** the manifest records both the original `adjudicated.csv` sha256 and the staged file's sha256 (`ann_files`).
   - **Prefix check:** rows with a blank or non-boolean `accepted` count as **present** for the prefix check, but `apply_annotations` rejects them (`accepted_not_boolean`).
4. **Label → item.** Call `apply_annotations` on a fresh state for split label **`confirm`**: `state = {"confirm": {"main": {}, "eow": {}, "prov": {}, "fts": {}}}`, with `rowmap = {key: ("confirm", dev_row)}` for worksheet keys only.
   - `T = defaultdict(Counter)`, and `Gate` is built from `benchmark/audio/empty_on_mirror.txt` (the empty set if that's absent).
   - With no energy items, unfinished rows need `block_onset_s` **and** `resumption_s`, with a gap over 0.2 s. For `unfinished_fluent_pause`, the pause onset goes in `block_onset_s`; a blank onset gives `missing_time`. Put this in the reviewer README.
   - Completed rows need `turn_end_s ≤ clip length − 0.2 s`.
   - Rejections, uncertainty and duplicates are tallied exactly as `apply_annotations` does.
   - Item IDs come out as `confirm-<g>-<k>-<clip_key>`. `label_source` is `"human"`.
5. **Quota report.** Build it from `outcomes` (by `sample_id`) **joined to the worksheet bucket**, not from `T`, which is keyed by the SEP-28k category. For each bucket, report the accepted count, rows reviewed, and rejections by reason (including `category_mismatch`). A bucket under 20 is a reported shortfall, never refilled.

## Outputs (`benchmark/items/confirm-v1/`, refused if it exists; `--out` for scratch)

- `confirm.jsonl`: runner items, all categories in one file, sorted by `item_id`. They must pass `eval_runner.load_items()`.
- `provenance.jsonl`, and `outcomes.csv` (`sample_id`, `source_id`, `category`, outcome).
- `manifest.json`, containing:
  - script sha256, and the `build_items.py` sha256;
  - the worksheet sha256 and confirm-set manifest sha256;
  - the `adjudicated.csv` and `crosscheck-note.md` sha256;
  - per-category counts and the quota report;
  - `"blind": true`, `"test_read": false`, `"items_v1_read": false`;
  - the D-009 note.
- The script prints `RECORD IN DECISION LOG: adjudicated.csv sha256 = …, confirm.jsonl sha256 = …`. **The freeze point is that decision-log entry. No model may run on `confirm.jsonl` before it exists.**

`--check DIR` re-verifies every hash in an existing output's manifest.

## Use afterwards (not part of this build)

`eval_runner.py` on `confirm.jsonl`, under `agent-v0.1-single-checks` (and `-turn-checks`), for the frozen arms only:
- the X1 candidate at 0.6;
- stock FP32 at 0.5;
- the comparator at 0.55;
- the patient waits.

Run once, on one platform, after the freeze, and report PLAN's per-group gate with Wilson CIs as feasibility evidence, with the limits from `confirm-set-v1.md`. **No threshold or candidate is chosen on these results.**

## Acceptance checks (synthetic labels only; no real labels exist yet)

Build a scratch `adjudicated.csv` and `crosscheck-note.md` under the scratchpad, with reviewer `SYNTHETIC-TEST`, using real worksheet rows. Output goes only under `--out` in the scratchpad. **Never write `benchmark/annotations/` or `benchmark/items/confirm-v1/`.**

1. **Happy path:**
   - an accepted `unfinished_stutter_block` (onset 1.0, resumption 1.6) gives a valid `human` item;
   - an accepted `completed_fluent_turn` (`turn_end` 2.0) gives an item;
   - an accepted `unfinished_fluent_pause` row gives an item;
   - `confirm.jsonl` passes `eval_runner.load_items()`;
   - the IDs start with `confirm-`.
2. **Rejections are tallied, not fatal:**
   - `accepted=false` with reviewer;
   - `uncertainty` non-empty;
   - resumption − onset = 0.15 → `gap_not_checkable`;
   - `turn_end` = clip length − 0.1 → `post_end_too_short`;
   - `accepted` blank → `accepted_not_boolean`, counted as present for the prefix check;
   - **`category_mismatch`** (e.g. C0114, proposed `completed_stuttered_turn` but annotated `completed_fluent_turn`): **no item is produced**, and the staged file excludes it.
3. **Refusals** (non-zero exit, nothing written):
   - a row whose `sample_id`/`source_id` isn't in the worksheet;
   - a gap in a bucket prefix (C0001 and C0003 annotated, C0002 missing);
   - a second CSV in the annotations dir;
   - a header mismatch;
   - a missing `crosscheck-note.md`;
   - a worksheet hash mismatch;
   - an existing out dir.
4. **Never reads test or v1 items:** the guarded open is installed. A test hook (`--probe-forbidden`) proves an attempted read of `benchmark/items/v1/test.jsonl` and `benchmark/runs/x` aborts. `grep` shows no `energy_pass(`, `build_queue(` or `main(` call into `build_items`.
5. **Determinism:** two builds from the same inputs have identical output hashes (no timestamps in `manifest.json`).
6. **`--check`** passes on a fresh build, and fails after one byte of `confirm.jsonl` is changed.

Report any check you couldn't run as **NOT RUN** with the reason.
