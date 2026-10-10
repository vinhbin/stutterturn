# Spec: StutterTurn candidate training v2 (domain-balanced)

**Owner:** Niko (spec, benchmark, selection) · **Executor:** Guttuu (harness changes and runs) · **Status:** reviewed (Opus, 2026-10-10), revised · **Supersedes:** nothing. v1 stays on record with outcome `dev_nothing_passes`. **This is a delta on `model/specs/training-v1.md`: every section not changed here applies unchanged.**

## 0. Why v2, and what it must disclose

v1 failed the pre-registered pre-screen (issue #2, `guttuu/train-harness` @ `c30dddb`):

- All 16 checkpoints cut first-check decisions on dev completed proxies (in-loop M3) from 46.6% to 8–22%.
- Every SEP-28k sample in training was labelled 0, so podcast audio itself predicted "incomplete": a **domain shortcut**.

v2's single change of substance is to **make SEP-28k audio label-balanced**, by adding train-show completed proxies as positives. Everything else that could be tuned stays fixed, so v2 tests one idea.

**Disclosure, required in every v2 claim:** v2 was designed after v1 failed on the same dev items. Dev has therefore been used for two pre-registered attempts, while test stays sealed, and the §7.2 test run is the only efficacy evidence.

## 2e. New data: SEP-28k completed proxies (label 1 = complete), **train shows only**

- **Source:** `benchmark/splits/v1/train.csv`, categories `fluent` (4,890), `block` (1,723) and `other_disfluent` (6,669).
- **Fetch:** extend `fetch_train_audio.py` to these categories (same mirror, idiom, atomic write and empty-on-mirror log). That's about 11.5k more clips at ~96 KB each, about 1.1 GB.
- **Rule: exactly the eval-items end-of-window rule** (`benchmark/scripts/build_items.py`, `energy_pass`), so that training positives and the dev M3 items are built identically:
  - same audio gate; `ft = fluent_features(analyze(path))`; `MIN_TRAILING_S = 0.50`; `te = speech_end`; require `duration − te ≥ 0.2`;
  - **fluent:** additionally `ft["total_speech"] ≥ 0.5` (`MIN_FLUENT_SPEECH_S`), the same as eval-items;
  - **block, other_disfluent:** `ft is not None` and trailing ≥ 0.5 (the eval-items `cand_stu_cmp` rule).
  - **Implementation:** import `build_items.py`'s constants and `build_eval_sets`' functions. Don't copy thresholds.
- **Samples:** for each offset `t ∈ {0.20, 0.25, …, 0.60}` with `te + t ≤ duration − 0.01`, the cut is `c = round((te + t)·16000)`, with label 1. The within-clip weights are as in §2a: `t = 0.20` gets 0.5 and the rest share 0.5.
- **Length matching (removes a context-length cue):**
  - **The cue:** on dev, stutter-gap cuts sit at a median of 1.45 s from the clip start (p10–p90 0.47–2.24 s), while end-of-window cuts sit at 2.03–2.53 s. Inputs are left zero-padded, so "≥ about 1.9 s of audio ⇒ complete" would nearly separate the labels.
  - **The fix:** each 2e sample keeps only its last `L` samples, `audio[max(0, c − L) : c]`. `L` is drawn deterministically from the **empirical distribution of 2a cut lengths** (the `round((gap_start + t)·16000)` values of all 2a samples, weighted by their §2a weights).
  - **The draw:** `u = int(sha256(f"{clip_key}|{t:.2f}"), 16) / 2**256`, and `L` = the weighted `u`-quantile, so it is reproducible.
  - **Scope:** 2a negatives and replay are unchanged. Record the 2e length distribution beside 2a's (p10/p50/p90).
- **Group balance inside 2e:**
  - stuttered positives (block and other_disfluent) get **total weight 0.5 of 2e**, and fluent positives the other 0.5;
  - weights are spread equally across clips within each group.

  This directly targets the §10 risk ("stutter-like voice ⇒ incomplete"): stuttered speech must also end turns.
- **Label quality, stated plainly:** trailing silence at the end of a 3 s window is **not** a confirmed turn end. The episode continues, and a pause may be mid-turn. These are noisy positives. **Dev M3 uses the same proxy on other shows, so improving M3 means "agrees with the proxy", not "answers real turn ends".** Every claim must say so.
- **Leakage asserts:** the same as 2a (train-only keys, none in dev/test/annotated, `train.csv` sha recorded). A block clip can have a mid-clip gap (negative) and trailing silence (positive). Both are kept, since negative cuts are `< rs − 0.05 ≤ te` and positive cuts are `≥ te + 0.2`. Assert that no negative/positive cut pair from the same clip is within 0.05 s, and record how many clips feed both sources.

## 2d. Mixture (replaces v1 §2d)

Each sample is drawn per sample from:

- **2a** (stutter negatives) with probability `p_neg`;
- **2e** (SEP-28k positives) with probability `p_pos`;
- **2b** (replay) with probability `1 − p_neg − p_pos`.

Each draw is weighted by its source weights. **v2 fixes `p_neg = p_pos`**, so within SEP-28k audio the label is balanced. An **epoch** is one weighted pass's worth of 2a draws: 941 / `p_neg`, about 4.7k samples at 0.20.

**`pos_weight` (three sources; v1's two-source formula in `train.py`'s `Mixture` is wrong here):** `pos_weight = (p_neg + p_r·(1 − fp)) / (p_pos + p_r·fp)`, with `p_r = 1 − p_neg − p_pos` and `fp` the replay positive fraction. At 0.20/0.20 with `fp ≈ 0.498` this is about 1.005; the old formula would give about 1.51. Log it.

**Harness:** add a `--p-pos` flag and a third source in `batch()` (label 1), and log `p_neg`, `p_pos` and `pos_weight` in `config.json`.

## 4. Runs (replaces v1 §4 grid; all other §4 settings unchanged)

| Run | lr | p_neg = p_pos | Notes |
|---|---|---|---|
| V1 (required) | 3e-5 | 0.20 | |
| V2 (required) | 1e-5 | 0.20 | |
| V3 (optional) | 3e-5 | 0.30 | |
| V4 (optional) | V1 settings, encoder frozen except the last 2 layers and the classifier | | |

These all use 2 epochs and seed 0, with checkpoints every half epoch plus the end. Run IDs are `V1`–`V4`, so they can't be confused with v1's `R1`–`R4`.

**In-loop validation:** the v1 metrics, including M3 (`dev_eow_first_check_decide`), plus one new metric:

- **dev stuttered completed decide (in-loop M3s):** the rate of `p > 0.5` at `te + 0.20` (full audio from the clip start) on dev `block`/`other_disfluent` clips meeting the stuttered rule above. These are eval-items' `cand_stu_cmp`: 538 dev clips, 98 block and 440 other_disfluent; 46 of the block ones are also dev main stuttered items. No file lists these keys, so recompute them with the 2e code path. Guttuu's machine needs the dev `other_disfluent` audio: `fetch_split_audio.py --splits dev --categories other_disfluent` (2,277 clips).
- **M3-crop (context-length diagnostic):** M3 recomputed with only the last 1.25 s before each cut kept and everything earlier zeroed. If a checkpoint's M3 holds only with long context, it learned the length cue.

**Pre-screen (pre-registered):** this is v1's rule with M3 as amended in `265ab02`, plus **M3s ≥ step 0 − 0.020** and **M3-crop ≥ step 0 − 0.020**. Rank by in-loop dev stutter premature among checkpoints meeting every constraint, and take the top 2.
- Use **a new work directory, or `--out prescreen-v2.json`**, because v1's `prescreen.json` exists and the script refuses to overwrite.
- The rule string cites training-v2.
- The format is otherwise unchanged, so `select_candidate.py` consumes it as is.

## 6. Selection

**Unchanged.** It runs the v1 §6 arms, metrics, constraints and rule via `benchmark/scripts/select_candidate.py` (`benchmark/specs/selection-v1.md`). Arms A, B, C and F are stock-only, so they're shared with the fallback-scope comparison and run once. M3s isn't a §6 metric (no runner items exist for it); report it beside the decision from the in-loop metrics.

## 8. Harness acceptance checks (delta)

1. **Data build:** report:
   - 2e counts by category and gate reason, and the stuttered/fluent split;
   - the overlap assert and the both-sources clip count;
   - the 2a vs 2e length distributions (p10/p50/p90): after matching they must agree within 0.1 s at each quantile;
   - that the leakage asserts pass.

   A rebuild gives identical hashes.
2. **Rule identity:** re-run the 2e rule on **dev** clips with the same code path. It must yield exactly the `dev_end_of_window.jsonl` item set (680 keys, the same `silence_start_s`) for fluent, and the 538 `cand_stu_cmp` keys for stuttered. Compare against eval-items provenance or a recomputation. This proves training positives and M3 items share one definition.
3. **Mixture:** over 10k draws, the empirical source fractions are within ±0.02 of `p_neg`/`p_pos`/replay, and the stuttered share within 2e draws is within ±0.03 of 0.5.
4. **Step 0** reproduces v1's step-0 in-loop metrics exactly (same model, same dev refs). M3s and M3-crop at step 0 are reported.
5. **`pos_weight`:** the logged value equals the three-source formula, about 1.005 at 0.20/0.20.

v1 checks 2–7 still hold. Re-run 3 (zero-step identity) only if `export.py` changed.

## 9. Timebox and stop rule

| By | What |
|---|---|
| 17:30 | spec reviewed and revised; posted to Guttuu |
| 18:30 | harness delta checks 1–4 pass; V1/V2 run; pre-screen done |
| 19:15 | `select_candidate.py` ready (Niko) and §6 run on Guttuu's machine |
| **20:00** | **hard stop.** If no v2 candidate passes §6 by then, the fallback scope stands. No v3 tonight. |

## 10. Risks (in addition to v1 §10)

- **Proxy circularity:** 2e and dev M3 share a definition. A v2 that passes may have learned "trailing window silence ⇒ complete". That would look good on M3 without answering real turn ends. Only human-confirmed turn ends (the 90-row review queue) can separate the two.
- **Context-length shortcut:** addressed by length matching (2e) and checked by M3-crop. Other cues that differ between gaps and window ends, such as speaker turn patterns, can't be fully controlled in v2.
- **Selection (`decision.md` limits text):** for v2, cite this spec's §0 disclosure, and replace "no stuttered completed turns" with "stuttered completed turns are energy proxies only (M3s), not human-confirmed".
