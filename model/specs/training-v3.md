# Spec: StutterTurn candidate training v3 (replay-protected)

**Owner:** Niko (spec, selection) · **Executor:** Guttuu · **Status:** pre-registered draft, written 18:20 EDT **before any v3 run**. **Runs only if Vinh records approval of a v3 timebox** (the "no v3 tonight" rule in training-v2 §9 otherwise stands). **Proposal:** [issue #2, Guttuu, 21:53Z](https://github.com/vinhbin/stutterturn/issues/2#issuecomment-6102568699). **This is a delta on `model/specs/training-v2.md`: every section not changed here applies unchanged.**

## 0. Why v3, and what it must disclose

`sel-v2` gave `dev_nothing_passes`. Every candidate operating point failed the **M5 guard** (specificity on Smart Turn's own held-out negatives). The nearest miss was `V2/ckpt-e2.00` at threshold 0.6: M1 47.4% → 18.5%, every other constraint met, M5 −0.6 pt (about 9 of 1,516 guard negatives).

**The hypothesis:** adding SEP-28k positives made the model slightly more willing to say "complete" on Smart Turn *incomplete* audio. Giving Smart Turn's own data (2b replay) a larger share of each batch should protect it.

**v3 changes one thing: the mixture shares.** No data, rule, metric, constraint or threshold changes.

**Disclosure, required in every v3 description:** dev has now served **three** pre-registered attempts (v1 and v2 both `dev_nothing_passes`; v3 was designed after seeing v2's dev and guard results). The test set stays sealed under **D-009**. No efficacy claim is possible from dev, and a v3 candidate does **not** authorize a test run. Only a later, explicit unseal decision by Vinh could do that.

## 2d. Mixture (replaces v2 §2d shares only)

The formula, length matching, `pos_weight` (three-source) and the per-sample draw are as in v2. Only the shares change:

| Run | lr | `p_neg = p_pos` | replay `p_r` | Notes |
|---|---|---|---|---|
| W1 (required) | 1e-5 | 0.15 | 0.70 | |
| W2 (required) | 3e-5 | 0.15 | 0.70 | |
| W3 (required) | 1e-5 | 0.10 | 0.80 | |
| W4 (optional) | W1 settings, encoder frozen except the last 2 layers and the classifier | | | |

These use 2 epochs, seed 0, and checkpoints every half epoch plus the end. The epoch definition is as in v2 (941 / `p_neg`), so each epoch is longer in samples at lower `p_neg`. Run IDs are `W1`–`W4`, so they can't be confused with `R*` (v1) or `V*` (v2).

## Data

**Unchanged.** Reuse the v2 data build (`data-v2`) as is, and **assert that its manifest hashes equal the ones recorded for v2**. No rebuild and no new clips.

## 4. In-loop validation and pre-screen

**Unchanged from v2:** metrics M1, M2, M3, M3s, M3-crop and guard recall, plus the v2 pre-screen rule. Write the output to **`prescreen-v3.json`**, with a rule string citing training-v3.

## 6. Selection

**Unchanged rule, unchanged thresholds.** Use `select_candidate.py` with the §6 constraints, **including "M5 not worse" on point estimates**. The arm E thresholds stay **{0.4, 0.5, 0.6}**; extending to 0.7 was considered and rejected, to avoid another choice made after seeing v2.
- **Out-id:** `sel-v3` (fresh). Run the stock-only stage first; it can run while W1–W3 train.
- **Limits text:** `--training-spec v3`, which writes the three-attempt disclosure.
- **Outcome:** reported exactly as the script gives it.

## 8. Harness acceptance checks (delta)

1. The data-v2 manifest hashes are unchanged.
2. **Mixture:** over 10k draws, the source fractions are within ±0.02 of each run's `p_neg`/`p_pos`/`p_r`. The logged `pos_weight` equals the three-source formula for that run.
3. **Step 0** reproduces v2's step-0 in-loop metrics exactly.

## 9. Timebox and stop rule

| By | What |
|---|---|
| on approval | the stock-only `sel-v3` stage starts; W1–W3 train |
| 19:15 | pre-screen done (`prescreen-v3.json`); exports and full guard evals |
| 19:40 | full `sel-v3` stage done; `decision.md` posted on issue #2 |
| **20:00** | **hard stop, unchanged.** If no v3 candidate passes, the fallback scope stands. **There is no v4.** |

## 10. Risks (in addition to v2 §10)

- **Trade-off, not a fix:** more replay may restore M5 by weakening the SEP-28k signal, so M1 gains may shrink. That would be an honest result.
- **Selection on dev three times:** the more attempts on one dev set, the more an apparent pass may reflect chance. That's another reason a v3 pass is a development decision only.
