# Confirmation review set v1 - labelling protocol

Spec: `benchmark/specs/confirm-set-v1.md`. This directory holds a **worksheet only**
(`worksheet.csv`, exact PLAN header, every human field blank). It contains no model
outputs, energy times or proxy labels. Categories are *proposed*; humans decide.

Rule: no model is run on these keys until the reviewed labels are committed and their
sha256 is recorded in the decision log. Never used for training or for selecting among
candidates; used only to judge an already-selected candidate against stock FP32 @0.5, the
comparator @0.55 and patient.

## Blind
No model predictions are shown or available. Nobody runs a model on `benchmark/confirm/v1`
keys until labels are frozen.

## Working down the lists
Each category's rows are a ranked list (sample_id order = bucket order, then rank). Work
down each list in order and never skip ahead. Stop at 20 accepted per category, or at the
end of the time you have, and report the shortfall; it is not refilled. Yields are expected
to be low (near zero for `unfinished_fluent_pause`): every clip here was rejected by the
earlier energy pass. Record rejections as `accepted=false` with reviewer and reason, as in
the PLAN worksheet rules (see `docs/labeling/README.md`).

## Reviewers
Two people. The second cross-checks every row the first marks `uncertainty`, plus a random
10% chosen by `sha256("confirm-v1-xcheck|" + sample_id)`. Record reviewer identities, the
sampled rows and any disagreements.

## One adjudicated CSV (the freeze point)
The reviewed file is a single adjudicated CSV with the exact PLAN header:
`benchmark/annotations/confirm-v1/adjudicated.csv`. Cross-check identities, sampled rows
and disagreements go in a separate `crosscheck-note.md` (following the `docs/labeling`
convention); two reviewer CSVs in one directory would break the builder. Its sha256 then
goes in the decision log. That is the freeze point.

## Timing rules (the builder enforces them; confirm keys have no energy item to fall back on)
- All times are clip-relative, within 0-3.0 s (`time_origin=clip_start`).
- Unfinished rows need `block_onset_s` (or the pause onset) and `resumption_s`, with
  `resumption_s - block_onset_s > 0.2`.
- Completed rows need `turn_end_s <= clip length - 0.2 s`.
- Rows that cannot meet these are `accepted=false` with the reason.
- An accepted row with nonempty `uncertainty` is rejected by the builder.

## Out of scope for v1
Turning labels into items. A follow-up spec adds a `--confirm-only` mode to `build_items.py`
(dev rows restricted to the worksheet keys, no held-out pass, output only
`benchmark/items/confirm-v1/`). Until it exists and is reviewed, that step is NOT RUN.

## Limits (state wherever results from this set are reported)
- Same two dev shows as the exposed items, so possibly the same speakers. These are
  untouched *recordings*, not new speakers or a held-out show.
- The pool is skewed in every bucket: every clean clip is one the energy rules rejected, so
  its distribution differs from the exposed items. Low yields are expected and reported.
- 3-second windows: events must fall inside the clip to be scoreable. Context links allow
  judging the speaker and the turn.
- Small n (up to 20 accepted per category): feasibility evidence with Wilson CIs, not
  population rates.
