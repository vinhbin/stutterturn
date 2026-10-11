# Spec: confirmation review set v1 (`benchmark/confirm/v1/`)

**Status:** reviewed (Opus, 2026-10-10; preview numbers reproduced exactly), revised · **Owner:** Niko (evaluation) · **Purpose:** the "fresh frozen confirmation set" that X1 §5.3, training-v4 §4(d) and the revised evaluation view ([issue #2, 6103719447](https://github.com/vinhbin/stutterturn/issues/2#issuecomment-6103719447)) require before any candidate can be promoted. **Builds a worksheet only. No model is run on these clips until the human labels are frozen.**

## Why

v1–v4 selection used every dev clip that was itemized (`items/v1/dev.jsonl`, `dev_end_of_window.jsonl`), every clip in the in-loop M3s pool (538 dev stuttered completed proxies, `model/train/proxies.py`), and the 59 dev clips in the exploratory `data/block_eval.csv`. The A/B worksheets and the 90-row review queue are subsets of those. Human labels on exposed clips add label validity, but they **can't confirm** a candidate that was selected on them. This set is drawn only from dev recordings that **no** v1–v4 step touched.

## Exposure set (all excluded)

- **E1:** clip keys in `benchmark/items/v1/dev.jsonl` (1,870 items).
- **E2:** clip keys in `benchmark/items/v1/dev_end_of_window.jsonl` (680).
- **E3:** the 538 dev keys from `model/train/proxies.py` `completed_proxies(split_rows("dev"))` with group `stuttered`. **Recompute them; don't hard-code**, and assert the count is 538.
- **E4:** dev keys in `benchmark/data/block_eval.csv` (59; filename minus `.wav`).
- **E5 (conservative):** dev keys in `benchmark/data/block_candidates.csv`. They were energy-screened in the pre-split exploration and no model ran on them, but they're excluded to be safe. The review found 12 untouched dev block keys there.
- **Time-overlap exclusion:** a dev clip is also excluded if its `[start, stop)` interval (from `splits/v1/dev.csv`) overlaps any exposed clip's interval **in the same `(show, ep_id)`**.

Preview numbers (Niko, 20:4x; reproduced exactly by review): dev has 5,882 clips. Before E5, 2,831 are exposed and 3,051 aren't; 644 of those overlap an exposed clip under a half-open `[start, stop)` test in samples. That leaves a **clean pool of 2,407**: 122 block, 872 fluent, 1,413 other_disfluent, across both dev shows. E5 removes about 12 more block keys. The build must recompute these and report them; any difference from the preview must be explained, not adjusted.

## Proposal buckets (categories are *proposed*; humans decide)

The draw is from the clean pool, stratified by show in proportion to pool size within each bucket. Order is deterministic: ascending `sha256("confirm-v1|" + clip_key)`.

| Bucket (PLAN category token) | Drawn from | Order | Target accepted |
|---|---|---|---|
| `unfinished_stutter_block` | all clean `block` | hash | 20 |
| `completed_stuttered_turn` | all clean `other_disfluent` | hash | 20 |
| `unfinished_fluent_pause` | **half** the clean `fluent` keys (see below) | SEP `natural_pause` ≥ 1 first, then hash | 20 |
| `completed_fluent_turn` | the **other half** of the clean `fluent` keys | hash | 20 |

- **Ranked lists are the whole bucket**, not 40. Every clean clip is one the earlier energy pass rejected (no clean gap or resume; no mid-pause; trailing silence under 0.5 s), so **yields will be low, near zero for `unfinished_fluent_pause`**. Reviewers stop at 20 accepted or at the end of the time they have, and report the shortfall.
- **The fluent split** is deterministic and decided before any ordering: a key goes to `unfinished_fluent_pause` if `int(sha256("confirm-v1-split|"+key),16) % 2 == 0`, otherwise to `completed_fluent_turn`.
- **The `natural_pause` ordering** uses the SEP-28k crowd annotation (about 265 of 872 clean fluent clips have ≥ 1 vote). It's a human label from the dataset, not energy, VAD or model output, so it leaks no selection signal.
- **The show split** applies within each bucket: interleave the shows by largest-remainder apportionment to pool size, so the first rows aren't all from one show.

- **No energy, VAD or model features are used to select or order clips.** The only inputs are the SEP-28k category and `natural_pause` vote (from the split) and the hash order. Every rejection is recorded.
- **Reviewers work down each ranked list in order** and never skip ahead. Rejections are recorded as in the PLAN worksheet rules (`accepted=false`, reviewer, reason). A shortfall is reported, not refilled.

## Outputs (`benchmark/confirm/v1/`)

- **`worksheet.csv`:** the exact PLAN annotation header (the same as `review_queue_dev.csv`), with:
  - `sample_id` = `C0001`…, in bucket order, then rank;
  - `source_id` = `clip_key`;
  - `context_ref` = episode URL `#t=<clip start seconds>`, built with the same function as `build_items.py`;
  - `category` = the proposed bucket token;
  - `time_origin=clip_start`;
  - every human field blank.

  **It contains no model outputs, energy times or proxy labels.**
- **`manifest.json`:**
  - script sha256, `splits/v1` sha check, and the sha256 of `dev.jsonl`, `dev_end_of_window.jsonl`, `block_eval.csv`, `block_candidates.csv`, `review_queue_dev.csv` and the sorted E3 key list;
  - the git rev of HEAD at build time;
  - pool counts, overlap-exclusion count and per-bucket list sizes;
  - the worksheet sha256;
  - `"frozen": true`;
  - the rule text: "no model is run on these keys until the reviewed labels are committed and their sha256 is recorded in the decision log".
- **`exposure_keys.json`:** the sorted union E1–E4, plus the overlap-excluded keys, so disjointness can be re-checked by anyone.

## Script: `benchmark/scripts/build_confirm_set.py`

- **Refusals:**
  - refuses if `benchmark/confirm/v1/` exists (`--out DIR` for scratch);
  - never opens `benchmark/runs/`, `benchmark/selection/`, `model/evidence/`, or any `test*` file;
  - asserts disjointness, both by key and by time overlap, before writing anything.
- **E3 computation:** imports `model/train/proxies.py`. That needs dev audio for `block`/`other_disfluent` under `benchmark/audio/`, fetched with `fetch_split_audio.py --splits dev --categories block other_disfluent`. If audio is missing, it stops and reports.
- **Determinism:** a rebuild gives identical output hashes.

## Labelling protocol (for the reviewers; recorded in the worksheet's README)

- **Blind:** no model predictions are shown or available, and nobody runs a model on `benchmark/confirm/v1` keys until labels are frozen.
- **Reviewers:** two people. The second cross-checks every row the first marks `uncertainty`, plus a random 10% chosen by `sha256("confirm-v1-xcheck|" + sample_id)`. Reviewer identities and disagreements are recorded.
- **One adjudicated CSV:** the reviewed file is a **single adjudicated CSV**, `benchmark/annotations/confirm-v1/adjudicated.csv`. Cross-check identities, the sampled rows and any disagreements go in a separate `crosscheck-note.md`, following the `docs/labeling` convention; two reviewer CSVs in one directory would break the builder. Its sha256 then goes in the decision log. **That is the freeze point.**
- **Timing rules the reviewers must follow** (the builder enforces them; confirm keys have no energy item to fall back on):
  - all times are clip-relative, within 0–3.0 s;
  - unfinished rows need `block_onset_s` (or the pause onset) and `resumption_s`, with `resumption_s − block_onset_s > 0.2`;
  - completed rows need `turn_end_s ≤ clip length − 0.2 s`;
  - rows that can't meet these are `accepted=false` with the reason.
- **Turning labels into items is out of scope for v1.** `build_items.py --annotations` re-runs the energy pass on **test** and rewrites `test.jsonl`, which is against D-009's intent, and it merges labels into the full dev item set. The follow-up `benchmark/specs/confirm-items-v1.md` (a separate `build_confirm_items.py`, superseding the earlier idea of a `--confirm-only` mode) handles this: dev rows restricted to the worksheet keys, **no test pass**, output only `benchmark/items/confirm-v1/`. Until that exists and is reviewed, this step is **NOT RUN**.
- **Never used for training or for selecting among candidates.** It's used only to judge an already-selected candidate against stock FP32 @0.5, the comparator @0.55 and patient.

## Limits (stated wherever results from this set are reported)

- **Same two dev shows as the exposed items, so possibly the same speakers.** These are untouched *recordings*, not new speakers or a held-out show.
- **The pool is skewed in every bucket.** Every clean clip is one the energy rules rejected (block: no gap, no resume or no pre-gap speech; fluent: no mid-pause and short trailing silence), so the pool's distribution differs from the exposed items. Low yields are expected and will be reported.
- **3-second windows:** events must fall inside the clip to be scoreable. Context links allow judging the speaker and the turn.
- **Small n (up to 20 accepted per category):** results are feasibility evidence with Wilson CIs, not population rates.

## Acceptance checks (paste commands and output)

1. **Build:** counts printed (pool, E5 and overlap exclusions, per-bucket list sizes, the fluent split, and `natural_pause` ≥ 1 counts). E3 recomputed = 538, and the counts before E5 match the preview (2,831 / 3,051 / 644 / 2,407).
2. **Disjointness:** independent re-check from `exposure_keys.json` and `dev.csv`: 0 worksheet keys in E1–E4, and 0 time overlaps with any exposed clip in the same episode.
3. **Determinism:** a second `--out` build has identical `worksheet.csv` and `manifest.json` hashes, apart from timestamps if any; better to have none.
4. **Blindness:** `worksheet.csv` columns equal the PLAN header exactly, and every human field is empty.
5. **Refusals:**
   - the build refuses an existing out dir;
   - a planted exposed key (scratch `--plant KEY` test hook) aborts it;
   - `grep` shows no reference to `runs/`, `selection/`, `evidence/` or `test` except the refusal code.
6. **The script never reads test:** the only items files opened are `dev.jsonl` and `dev_end_of_window.jsonl`, and this is asserted in code.

Report any check you couldn't run as **NOT RUN** with the reason.
