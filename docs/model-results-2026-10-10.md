# Model results: Saturday, October 10 (draft for Vinh)

**Status:** filled from the official selection `sel-v2` (Guttuu's machine, Windows 11, `select_candidate.py` @ `f007c06`, code `a78f21b`; [`decision.md` on issue #2](https://github.com/vinhbin/stutterturn/issues/2#issuecomment-6102500044)), about 18:00 EDT. **Outcome: `dev_nothing_passes`.** Numbers marked *preview* come from Niko's Mac. Stock FP32 values are identical across both machines (B: 167/352, 767/1518, 317/680 on each). Every number here is a **development** result on energy-labelled proxies. **No efficacy claim exists until the single sealed test run (training-v1 §7.2).**

## What we can say tonight, whatever the outcome

1. **Stock Smart Turn decides "complete" too early on pauses in general, not only on stutters.** On dev (two held-out shows), stock FP32 at its default threshold decides "complete" during **47.4%** of stutter blocks (167/352, CI 42.3–52.7) and **50.5%** of fluent mid-turn pauses (767/1518) at the agent's 0.2 s check (official arm B). Don't frame this as "the model discriminates against stuttering". The measured problem is premature endpointing on pauses, which stutter blocks produce often and for longer.
2. **The shipped INT8 file is worse than its own FP32 weights.** On the 200 exploratory block clips, INT8 makes first-check premature decisions on **116/200 (58%)** against **87/200 (43.5%)** for FP32. On dev it's 57.4% (202/352) vs 47.4% (official arms A and B). Quantization alone costs about 10–15 points, and switching the agent to FP32 is a free improvement.
3. **Raising the threshold trades one error for another.** Stock FP32 on dev (*preview*; the official arm-C sweep in `decision.json` uses identical FP32 probabilities). The best threshold meeting every guard is **0.55**, which is only −1.7 pt on M1:

   | Threshold | Stutter-block premature (M1) | Fluent-pause premature (M2) | Completed proxies decided at 1st check (M3) |
   |---|---|---|---|
   | 0.50 (default) | 47.4% | 50.5% | 46.6% |
   | 0.80 | 36.4% | 41.4% | 39.1% |
   | 0.90 | 28.4% | 33.7% | 34.0% |
   | 0.95 | 22.2% | 27.4% | 27.9% |
   | 0.99 | 0.9% | 1.8% | 4.0% |

   To get stutter-block cut-ins down, stock has to stop answering finished turns at the first check too.
3b. **Waiting longer before the check works, but every reply gets slower.** Stock FP32 checked after longer silences (official report-only arm F):

   | Wait before the check | M1 | M2 | M3 | Added delay on **every** turn |
   |---|---|---|---|---|
   | 0.2 s (stock agent) | 47.4% | 50.5% | 46.6% | – |
   | 0.4 s | 37.5% | 45.1% | 52.8% | +0.2 s |
   | 0.6 s | 26.7% | 33.5% | 54.7% | +0.4 s |
   | 0.8 s | 12.8% | 15.3% | 48.2% | +0.6 s |

   M3 counts *whether* the first check decides, not *when*, so it hides the added latency. This is the simplest baseline any model change has to beat, at equal latency.
4. **A naive fine-tune learns a shortcut, and our pre-registered checks caught it.** Training v1 used stutter-block cuts as "incomplete" examples and nothing else from the podcasts. All 16 checkpoints learned "podcast audio ⇒ incomplete": stutter-block premature fell to 1–6%, but first-check decisions on completed proxies fell from 46.6% to 8–22%. The pre-screen rejected all of them (`dev_nothing_passes`). We kept the evidence rather than tuning around it.
5. **In the agent, early decisions haven't become audible interruptions yet.** Replay v2 (fixed pre-roll): stock decided "complete" before the labelled resume in **4 of 5** clips, and **0** became audible, because the speaker resumed before Gemini/ElevenLabs replied (about 1.5–2.5 s). A faster reply path would make them audible. No rates from n = 5.
6. **The agent and the benchmark feed the model identical audio.** This is verified to 1e-4 (agent replay) and 5e-7 (benchmark `turn_onset` vs agent onset on 155 clips). A pre-roll bug that we found in review was fixed (PR #14).

## Outcome: `dev_nothing_passes`

**Decision-log entry (Vinh to record):** at 17:45 EDT, the training-v2 selection `sel-v2` (Guttuu's machine; run IDs and hashes in `benchmark/selection/sel-v2/decision.json`, not committed) gave **`dev_nothing_passes`** with `comparator_M1_below_B = true`. Comparator: stock FP32 at threshold 0.55 (M1 45.7%, every constraint met). Training v1 had earlier given `dev_nothing_passes` (domain shortcut). **Scope: fallback, the corrected benchmark.** There is no fine-tuned model in the demo. Test stays sealed and unused; the 20:00 stop was respected. Limits: energy-derived dev labels, end-of-window proxies, two pre-registered attempts on the same dev items.

**Why v2 didn't pass, stated plainly:** v2 balanced the podcast audio (adding completed proxies as "complete" examples) and removed the shortcut. 4 of 16 checkpoints passed the pre-screen. The top two, run through the benchmark on dev (official arms D, at 0.5):

| Dev, check at 0.2 s | Stock FP32 | v2 candidate `V3/ckpt-e0.51` | v2 candidate `V2/ckpt-e2.00` |
|---|---|---|---|
| Stutter-block premature (M1) | 47.4% | **23.0%** | **31.0%** |
| Fluent-pause premature (M2) | 50.5% | 40.7% (−9.8) | 51.2% (+0.7) |
| Completed proxies decided at 1st check (M3) | 46.6% | **62.3%** (+15.7) | **64.1%** (+17.5) |
| Stuttered completed proxies decided (M3s, in-loop) | 24.2% | 35.7% | 45.0% |
| Guard specificity (M5) | 93.5% | 91.8% (**−1.7**) | 92.0% (**−1.5**) |

**Every operating point failed one pre-registered guard.** On Smart Turn's own held-out test audio, specificity (calling unfinished turns unfinished) dropped at all six candidate operating points, so the candidates call some unfinished non-podcast turns complete more often. The nearest miss is V2 at threshold 0.6: M1 18.5% with every other constraint met, but M5 −0.6 pt (about 9 of 1,516 guard negatives). The rule was fixed before the runs. Relaxing it after seeing results would invalidate any claim.

**Allowed claim (exploratory, dev only):** "At the agent's 0.2 s check, a domain-balanced fine-tune halved stutter-block cut-ins on held-out shows (47% → 23%) while answering more completed turns at the first check (47% → 62%). Raising the stock threshold can't do that: at about 22% cut-ins, stock answers only 28% (*preview*). It slightly reduced specificity on general speech, failed our pre-registered guard, and is not released."

**State alongside it:** waiting 0.8 s instead of 0.2 s gets stock to 13% cut-ins with M3 unchanged, at the cost of 0.6 s added to every response. The fine-tune's only advantage is at the fast check.

**Must accompany it:**
- dev-only;
- selected on these dev items (two pre-registered attempts; v2 designed after v1 failed);
- energy-derived labels and end-of-window proxies, not human-confirmed turn ends;
- training positives and M3 share one proxy definition;
- no stuttered completed turns confirmed by humans;
- test sealed and unused.

## Never say (any outcome)

- "Fixes stuttering interruptions", "inclusive model ready", or any test-set or human-validated claim before those exist.
- Rates from the 5 replay clips, or "the agent interrupts people who stutter" (0 audible so far).
- Completed-turn **delay** improvements: the +50 ms gate criterion can't be measured with clip items under the single-check schedule.

## Sources

- Issue #2 thread: v1 result 20:34Z, v2 result 21:28Z.
- `model/specs/training-v{1,2}.md`, `benchmark/specs/selection-v1.md`, `benchmark/specs/eval-runner-v1.md` (INT8/FP32 acceptance results), `benchmark/specs/checks-only-grid-v1.md` (dev preview), `agent/evidence/2026-10-10-replay-v2/`.
- Official numbers: `sel-v2` `decision.md` (issue #2 comment 6102500044). `decision.json` and run dirs are on Guttuu's machine.
