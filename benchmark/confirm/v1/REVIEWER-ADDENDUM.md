# Reviewer addendum to `README.md` (v1.1, 2026-10-10)

`README.md` is frozen: its sha256 is recorded in `manifest.json`, so it isn't edited. This addendum adds the label rules that `benchmark/scripts/build_confirm_items.py` (spec: `benchmark/specs/confirm-items-v1.md`) enforces. **It changes nothing in the worksheet or its selection.**

- **Unfinished fluent pause:** put the **pause onset in `block_onset_s`** and the speech resumption in `resumption_s`. A blank onset is rejected as `missing_time`.
- **Unfinished rows of either kind** need both `block_onset_s` and `resumption_s`, with `resumption_s − block_onset_s > 0.2` s. If not, the row is rejected as `gap_not_checkable`.
- **Completed rows** need `turn_end_s ≤ clip length − 0.2` s. If not, the row is rejected as `post_end_too_short`.
- **Keep the proposed category.** If listening shows the row belongs to a different category, record `accepted=false` with the reason. An accepted row whose category differs from the worksheet's is dropped as `category_mismatch`.
- **No skipping:** label rows in worksheet order within each category. The builder refuses a gap in the labelled prefix.
- **Deliver one adjudicated file,** `benchmark/annotations/confirm-v1/adjudicated.csv`, plus `crosscheck-note.md` covering reviewer identities, the cross-checked rows and disagreements.
