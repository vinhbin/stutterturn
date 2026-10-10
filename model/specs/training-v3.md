# Spec: StutterTurn candidate training v3 (replay-protected)

**Owner:** Niko (spec, selection) · **Executor:** Guttuu · **Status:** pre-registered 18:20 EDT, reviewed and amended 18:3x, then **amended at 18:5x to W3 only per D-010** (Vinh: 80% original replay / 20% adaptation; [recommendation](../../docs/v3-recommendation-2026-10-10.md)). All of this happened **before any v3 run**. **Training is paused (D-010): nothing runs until Vinh explicitly resumes.**

## 0. Why v3, and what it must disclose

`sel-v2` gave `dev_nothing_passes`. Every candidate operating point failed the **M5 guard** (specificity on Smart Turn's own held-out negatives). The nearest miss was `V2/ckpt-e2.00` at threshold 0.6: M1 47.4% → 18.5%, every other constraint met, M5 −0.6 pt (about 9 of 1,516 guard negatives).

**The hypothesis:** adding SEP-28k positives made the model slightly more willing to say "complete" on Smart Turn *incomplete* audio. Giving Smart Turn's own data (2b replay) a larger share of each batch should protect it.

**v3 changes one thing: the mixture shares.** No data, rule, metric, constraint or threshold changes.

**Disclosure, required in every v3 description:** dev has now served **three** pre-registered attempts (v1 and v2 both `dev_nothing_passes`; v3 was designed after seeing v2's dev and guard results). The test set stays sealed under **D-009**. No efficacy claim is possible from dev, and a v3 candidate does **not** authorize a test run. Only a later, explicit unseal decision by Vinh could do that.

## 2d. Mixture and runs (replaces the v2 §2d shares and the v2 §4 run grid)

The formula, length matching, `pos_weight` (three-source) and the per-sample draw are as in v2. Only the shares change:

| Run | lr | `p_neg = p_pos` | replay `p_r` | Notes |
|---|---|---|---|---|
| **W3 (the only run)** | 1e-5 | 0.10 | 0.80 | 80% original replay / 10% SEP unfinished / 10% SEP completed proxies, per D-010 |

**Amended at 18:5x (D-010):** W1, W2 and the optional W4 are **dropped** and won't be run, so no claim may say the original grid was completed. W3 starts from the recovered stock FP32 weights, not from any v2 checkpoint.

W3 uses 2 epochs, seed 0, and checkpoints every half epoch plus the end. The epoch definition is as in v2 (941 / `p_neg`), so each epoch is longer in samples at lower `p_neg`. The run ID is `W3`, so it can't be confused with `R*` (v1) or `V*` (v2). Record the actual draws and steps (about 18.8k draws expected).

## Data

**Unchanged.** Reuse the v2 data build (`data-v2`) as is, and **assert that its manifest hashes equal the ones recorded for v2**. No rebuild and no new clips.

## 4. In-loop validation and pre-screen

**Unchanged from v2:** metrics M1, M2, M3, M3s, M3-crop and guard recall, plus the v2 pre-screen rule. Write the output to **`prescreen-v3.json`**, with a rule string citing training-v3.

## 6. Selection

**Unchanged rule, unchanged thresholds.** Use `select_candidate.py` with the §6 constraints, **including "M5 not worse" on point estimates**. The arm E thresholds stay **{0.4, 0.5, 0.6}**; extending to 0.7 was considered and rejected, to avoid another choice made after seeing v2.
- **Out-id:** `sel-v3` (fresh). Run the stock-only stage first; it can run while W3 trains.
- **Limits text:** `--training-spec v3`, which writes the three-attempt disclosure.
- **Outcome:** reported exactly as the script gives it.

**Additional promotion checks (D-010; registered before any run, reported separately from the unchanged selector):** a selector pass is **development eligibility only**. A candidate is promoted only if all of these hold:
1. At the selected threshold, in-loop **M3s** and **M3-crop** are each ≥ stock FP32 at 0.5 − 2.0 pt.
2. **Matched `turn_onset` comparison (Niko):** the selected candidate vs stock FP32 under `agent-v0.1-turn-checks` on dev (selection arm G). M1 doesn't worsen relative to the `clip_start` result by more than stock's own shift.
3. **Audio acceptance (Guttuu):** source and reply audibility, explicit Stop/restart, and cancellation when speech resumes during audible playback, with saved timing evidence.
4. **PLAN's measured-improvement gate:** human-reviewed endpoints, under 10% premature, +50 ms delay per group, and the rest. **No current result meets it**, so promotion to the demo also needs those labels.

Missing or failed checks mean no promotion, even if the selector passes.

**§7 (test run) is suspended under D-009. No v3 outcome triggers §7.2**, despite the "applies unchanged" inheritance through v2 and v1.

## 8. Harness acceptance checks (delta)

1. **Inputs before starting:**
   - the data-v2 manifest hashes are unchanged;
   - train-only membership and replay/guard waveform disjointness are re-asserted;
   - the base-model sha256 equals stock FP32;
   - a **fresh feature cache**, or a cache keyed by content and preprocessing.
2. **Mixture:** over 10k draws, the source fractions are within ±0.02 of 0.10/0.10/0.80. The logged `pos_weight` equals the three-source formula for that run.
3. **Step 0** reproduces v2's step-0 in-loop metrics exactly.

## 9. Timebox and stop rule

| By | What |
|---|---|
| on Vinh's explicit resume | the stock-only `sel-v3` stage starts; W3 trains (one run) |
| resume + 20 min | pre-screen done (`prescreen-v3.json`); exports and full guard evals |
| resume + 40 min | full `sel-v3` stage done; `decision.md` posted on issue #2 |

**If the resume comes after about 19:15, there isn't time:** don't compress checks or move the stop.
| **20:00** | **hard stop, unchanged.** If no v3 candidate passes, the fallback scope stands. **There is no v4.** |

## 10. Risks (in addition to v2 §10)

- **Trade-off, not a fix:** more replay may restore M5 by weakening the SEP-28k signal, so M1 gains may shrink. That would be an honest result.
- **More replay steps:** an epoch is weight_total / `p_neg`, about 9.4k samples at 0.10 against 4.7k in v2. 2a and SEP-28k draws stay about constant (about 1.9k each over 2 epochs); only the replay volume grows, about 2.7×. Epochs stay as defined, because fixing steps would cut the SEP-28k exposure and change the hypothesis.
- **Selection on dev three times:** the more attempts on one dev set, the more an apparent pass may reflect chance. That's another reason a v3 pass is a development decision only.
