# Model results: Saturday, October 10 (draft for Vinh)

**Status:** v1 failed its amended prescreen; v2 and W3 returned **`dev_nothing_passes`**. The v2 numbers below come from Guttuu's Windows 11 selection `sel-v2` (`select_candidate.py` @ `f007c06`, code `a78f21b`; [issue report](https://github.com/vinhbin/stutterturn/issues/2#issuecomment-6102500044)). [W3's result](https://github.com/vinhbin/stutterturn/issues/2#issuecomment-6103321119) and [published v2/v3 records at `bd095f9`](https://github.com/vinhbin/stutterturn/tree/bd095f9/benchmark/selection) are summarized below. Numbers marked *preview* come from Niko's Mac. Stock FP32 values are identical across both machines (B: 167/352, 767/1518, 317/680 on each). These are **development/validation** results using SEP endpoint proxies and upstream guard labels, not an independent reproduction. The reserved final evaluation remains sealed under D-009. An efficacy claim additionally requires reviewed endpoints and relevant audio outcomes; a proxy test run alone would not establish it.

## What we can say tonight, whatever the outcome

1. **Stock Smart Turn decides "complete" too early on pauses in general, not only on stutters.** On dev (two held-out shows), stock FP32 at its default threshold decides "complete" during **47.4%** of stutter blocks (167/352, CI 42.3–52.7) and **50.5%** of fluent mid-turn pauses (767/1518) at the agent's 0.2 s check (official arm B). Don't frame this as "the model discriminates against stuttering". The measured problem is premature endpointing on pauses, which stutter blocks produce often and for longer.
2. **Stock FP32 makes fewer premature predictions than the shipped INT8 file on these items.** On the 200 exploratory block clips, INT8 makes first-check premature decisions on **116/200 (58%)** against **87/200 (43.5%)** for FP32. On dev it's 57.4% (202/352) vs 47.4% (official arms A and B). This roughly 10–15 point difference concerns internal decisions on proxy-labelled items; runtime, response latency and audible-outcome acceptance remain separate.
3. **Raising the threshold trades one error for another.** Stock FP32 on dev (*preview*; the official arm-C sweep in `decision.json` uses identical FP32 probabilities). The best threshold meeting every guard is **0.55**, which is only −1.7 pt on M1:

   | Threshold | Stutter-block premature (M1) | Fluent-pause premature (M2) | Completed proxies decided at 1st check (M3) |
   |---|---|---|---|
   | 0.50 (default) | 47.4% | 50.5% | 46.6% |
   | 0.80 | 36.4% | 41.4% | 39.1% |
   | 0.90 | 28.4% | 33.7% | 34.0% |
   | 0.95 | 22.2% | 27.4% | 27.9% |
   | 0.99 | 0.9% | 1.8% | 4.0% |

   In this sweep, higher thresholds reduce completion predictions in energy-labelled stutter gaps and also reduce first-check decisions on end-of-window proxies. These proxies do not establish whether a person has finished speaking or when an answer is heard.
3b. **Waiting longer changes the decision outcomes and delays the configured first check.** Stock FP32 checked after longer silences (official report-only arm F):

   | Wait before the check | M1 | M2 | M3 | Added configured wait before first check |
   |---|---|---|---|---|
   | 0.2 s (stock agent) | 47.4% | 50.5% | 46.6% | – |
   | 0.4 s | 37.5% | 45.1% | 52.8% | +0.2 s |
   | 0.6 s | 26.7% | 33.5% | 54.7% | +0.4 s |
   | 0.8 s | 12.8% | 15.3% | 48.2% | +0.6 s |

   M3 counts *whether* the first check decides, not *when*. These wait differences are configuration values, not measured per-turn audible response delays: changed decisions, fallbacks and provider latency also affect response time. This baseline must accompany any candidate comparison.
4. **The v1 result is consistent with a podcast-domain shortcut.** Training v1 used stutter-block cuts as "incomplete" examples and nothing else from the podcasts. Across 16 checkpoints, stutter-block premature fell to 0.85–6.25%, but first-check decisions on completed proxies fell from 46.62% to 8.24–22.06%. The M3 check was added after training and an initial prescreen; all saved checkpoints were rescored and rejected under the amended rule (`dev_nothing_passes`). The earlier selection was retained as superseded. This is not a direct measurement of the model's internal mechanism or a fully preregistered v1 evaluation. See [Guttuu's chronology](https://github.com/vinhbin/stutterturn/issues/2#issuecomment-6101907402).
5. **The saved replay distinguishes early decisions from reported audio overlap.** Replay v2 (fixed pre-roll): stock decided "complete" before the energy-labelled resume in **4 of 5** clips (one decision preceded the labelled gap), versus 0 of 5 for patient. Three replies were cancelled before reported audio; no response-audio overlap was reported in those ten runs. Physical playback was not verified for that packet. A faster reply path could produce overlap, but that is a hypothesis, not an observed result. No interruption rates from n = 5. Separately, [Guttuu's human listening check](https://github.com/vinhbin/stutterturn/issues/3#issuecomment-6102558836) verifies source/reply audibility and explicit Stop/restart; audible cancellation on natural resumption remains untested.
6. **Parity was verified for the matched replay/onset paths.** Reported probability agreement is within 1e-4 for agent replay and 5e-7 for benchmark `turn_onset` versus agent onset on 155 clips. The main selection instead uses `clip_start`; `turn_onset` is a report-only comparison. This does not establish that every selected benchmark input equals the agent's input. A pre-roll bug was fixed in PR #14.

## Outcome: `dev_nothing_passes`

**Observed selection outcomes:** training v1 failed under its amended prescreen. The training-v2 selection `sel-v2` gave **`dev_nothing_passes`** with `comparator_M1_below_B = true`; its [decision and hashes are now published](https://github.com/vinhbin/stutterturn/blob/bd095f9/benchmark/selection/sel-v2/decision.json). Comparator: stock FP32 at threshold 0.55 (M1 45.7%, every constraint met). Vinh then approved W3 only under D-011: 80% original replay / 10% SEP unfinished / 10% SEP completed proxies, unchanged checks and a 20:00 hard stop. [W3 also returned `dev_nothing_passes`](https://github.com/vinhbin/stutterturn/issues/2#issuecomment-6103321119), with `selected = null`; all six candidate operating points failed M5. The nearest miss, W3 epoch 1 at threshold 0.6, achieved **M1 20.2%** but **M5 −0.33 percentage points** (five net additional errors among 1,516 guard negatives). No promotion checks followed that failed selection. Its [decision](https://github.com/vinhbin/stutterturn/blob/bd095f9/benchmark/selection/sel-v3/decision.json), [training/export/guard records](https://github.com/vinhbin/stutterturn/tree/bd095f9/model/evidence/2026-10-10) and harness commit `95c651e` are published; the latter includes previously local `d9b6ae6`.

**Current scope:** no fine-tuned model is selected for the demo. Vinh is continuing the original improvement goal; stock/patient remains a backup, not an accepted final-scope fallback. Vinh [conditionally approved the six fixed v4 interpolation blends](https://github.com/vinhbin/stutterturn/issues/2#issuecomment-6103422097) under [D-012](decision-log.md), requiring Niko's corrected code/protocol sign-off before execution. Stop after 45 minutes from the approved execution start or at 20:45 EDT, whichever comes first. This supersedes D-011's 20:00 stop/no-v4 restriction for one attempt only; all numeric gates remain unchanged and no automatic v5 is approved. No start/result is reported; `c17e4bc` remains proposal code. The reserved test remains sealed under [D-009](decision-log.md), including after any future development pass. Limits: automatic endpoint proxies, three adaptive attempts on the same development data, and historical exploratory exposure of some later reserved source clips. See the [judge-facing report](training-report-2026-10-10.md) for the full chronology and qualifications.

**Why v2 didn't pass, stated plainly:** v2 balanced the podcast audio by adding completed proxies as "complete" examples and addressed the v1 shortcut in the measured checks. 4 of 16 checkpoints passed the pre-screen. The top two, run through the benchmark on dev (official arms D, at 0.5):

| Dev, check at 0.2 s | Stock FP32 | v2 candidate `V3/ckpt-e0.51` | v2 candidate `V2/ckpt-e2.00` |
|---|---|---|---|
| Stutter-block premature (M1) | 47.4% | **23.0%** | **31.0%** |
| Fluent-pause premature (M2) | 50.5% | 40.7% (−9.8) | 51.2% (+0.7) |
| Completed proxies decided at 1st check (M3) | 46.6% | **62.3%** (+15.7) | **64.1%** (+17.5) |
| Stuttered completed proxies decided (M3s, in-loop) | 24.2% | 35.7% | 45.0% |
| Guard specificity (M5) | 93.5% | 91.8% (**−1.7**) | 92.0% (**−1.5**) |

**Every v2 operating point failed one pre-registered guard.** On the general-speech guard drawn from Smart Turn's upstream test audio, specificity (calling unfinished turns unfinished) dropped at all six candidate operating points, so the candidates call some unfinished non-podcast turns complete more often. This guard has been reused for development selection; it is separate from our sealed final test. The nearest v2 miss is V2 at threshold 0.6: M1 18.5% with every other constraint met, but M5 −0.6 pt (about 9 of 1,516 guard negatives). The rule was fixed before the runs. Relaxing it after seeing results would invalidate a claim of passing that rule.

**Exploratory development description (not an efficacy claim):** "On development shows at the 0.2 s check, a domain-balanced fine-tune reduced completion predictions in energy-labelled stutter gaps from 47% to 23%, while deciding 'complete' on more end-of-window proxies (47% → 62%). In the stock threshold sweep, a setting with about 22% premature predictions decided on 28% of those proxies (*preview*). The fine-tune reduced specificity on the general-speech guard, failed selection, and is not released." These are internal decisions on proxies, not observed cut-ins or answers to human-confirmed completed turns.

**State alongside it:** checking stock after 0.8 s instead of 0.2 s yields 12.8% premature predictions on the same development proxy items and 48.2% end-of-window decisions, versus 47.4% and 46.6% at 0.2 s. The first-check wait is configured 0.6 s later; this is not a measured 0.6 s increase in every audible response. The candidate comparison above concerns the faster check.

**Must accompany it:**
- dev-only;
- the v2 description follows two adaptive attempts on these dev items; W3 subsequently reused them a third time (v1's M3 check was added after initial results, and later attempts were designed after earlier failures);
- energy-derived labels and end-of-window proxies, not human-confirmed turn ends;
- training positives and M3 share one proxy definition;
- no stuttered completed turns confirmed by humans;
- rebuilt final evaluation sealed and unrun; 58 original exploratory block clips fall in the later reserved partition.

## Later attempts: v3 and v4 (both `dev_nothing_passes`)

After `sel-v2`, Vinh approved two more bounded, pre-registered attempts (D-011, then his v4 go-ahead). Both ran inside their stops, with test sealed (D-009) throughout. Each was a further adaptive attempt on the same dev items and guard, so dev has now served **four** attempts. **No candidate was selected; model work stopped, with no v5.**

| Attempt | What changed | Best operating point (nearest miss) | M1 (stock 47.4%) | ΔM5 (must be ≥ 0) |
|---|---|---|---|---|
| v2 (`sel-v2`) | added SEP completed proxies | V2/e2.00 @0.6 | 18.5% | −0.6 pt (~9 of 1,516) |
| v3 (`sel-v3`, [spec](../model/specs/training-v3.md)) | replay share 80% (W3 only) | W3/e1.00 @0.6 | 20.2% | −0.33 pt (~5) |
| v4 (`sel-v4`, [spec](../model/specs/training-v4.md)) | weight interpolation stock↔W3, 6 blends | 0.75×W3/e2.00 @0.6 | 24.4% | −0.33 pt (~5) |

Every other constraint was met at each nearest miss. The guard rule is a point estimate decided by a handful of rows; it was fixed before the runs and was **not** changed after seeing them. In v4, blends at α ≤ 0.5 were *more* premature than stock on fluent pauses, so interpolation didn't trade off smoothly.

**Failure analysis** (Guttuu; descriptive, dev/guard only; numbers independently reproduced by Niko from the committed guard files). The M5 losses concentrate on **short** Smart Turn unfinished turns. For guard negatives under 3 s, the candidates raise p(complete) by +0.09 to +0.24 on average; for clips of 8 s or longer, by +0.01 or less. Mean change on guard positives is about 0. Vinh's recount adds that all net extra errors in v4 fall below 8 s, in both human and synthetic audio.

**Mechanism, as corrected by Guttuu** ([issue #2](https://github.com/vinhbin/stutterturn/issues/2#issuecomment-6103688105)): weighted by the actual W3 mixture (model input capped at 8 s), training labels are **balanced at every length**, about 50% complete for 0–2 s, 2–4 s and 4–8 s draws. A simple "short ⇒ complete" base-rate cue is therefore **not** supported. What *is* lopsided is the source: about 91% of 0–2 s draws are SEP-28k podcast cuts whose "complete" labels are energy-end proxies. The better-supported hypothesis is a **domain × length confound**: what the model learns about very short inputs comes almost entirely from proxy-labelled podcast audio, and it transfers badly to short Smart Turn unfinished turns. This is still a **hypothesis, not proof**: length, source, content and label quality remain confounded, one checkpoint also lost 12 long negatives, and the bins are small.

**For any future attempt (team decision, nothing scheduled):**
1. Add left-cropped Smart Turn replay at 1–4 s, with a crop-validity audit before use: a human sample per label and a validity gate, as proposed on issue #2.
2. Anchor to stock on Smart Turn data.
3. Use human-confirmed turn ends instead of energy proxies.
4. Evaluate on data that hasn't guided v1–v4: a fresh Smart Turn guard, and human-labelled items. A/B are reused dev recordings, so they improve label validity but not independence. Any change to the M5 rule would apply only to future candidates.

Records (on `main` via [PR #35](https://github.com/vinhbin/stutterturn/pull/35)): [`benchmark/selection/`](../benchmark/selection/) (`sel-v2`, `sel-v3`, `sel-v4`) and [`model/evidence/2026-10-10/`](../model/evidence/2026-10-10/).

## Never say (any outcome)

- "Fixes stuttering interruptions", "inclusive model ready", or any test-set or human-validated claim before those exist.
- Interruption rates from the 5 replay clips, or "the agent interrupts people who stutter" (no response-audio overlap reported in replay v2; physical playback unverified for that packet).
- Completed-turn **delay** improvements: the +50 ms gate criterion can't be measured with clip items under the single-check schedule.

## Sources

- Issue #2 thread: v1 result 20:34Z, v2 result 21:28Z.
- `model/specs/training-v{1,2,3}.md`, `benchmark/specs/selection-v1.md`, `benchmark/specs/eval-runner-v1.md` (INT8/FP32 acceptance results), `benchmark/specs/checks-only-grid-v1.md` (dev preview), `agent/evidence/2026-10-10-replay-v2/`.
- Official numbers: [v2 report](https://github.com/vinhbin/stutterturn/issues/2#issuecomment-6102500044), [v3 report](https://github.com/vinhbin/stutterturn/issues/2#issuecomment-6103321119), and [published `sel-v2`/`sel-v3` decision records at `bd095f9`](https://github.com/vinhbin/stutterturn/tree/bd095f9/benchmark/selection). Training, export and guard records are [published alongside them](https://github.com/vinhbin/stutterturn/tree/bd095f9/model/evidence/2026-10-10); they have not been independently rerun here.
