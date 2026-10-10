# Proposed v3: one 80/20 experiment, with separate validation

**October 10, 2026. Recommendation for Vinh, Guttuu, and Niko; not execution approval.** Vinh clarified that 80/20 means original training replay versus stutter-focused adaptation, then paused training. He requested this recommendation/report and its Git push. Those requests do not resume training or open the reserved test.

## Recommendation and why

Run **only W3**, if Vinh explicitly resumes the experiment in time: 80% original Smart Turn training replay, 10% SEP unfinished-gap examples, and 10% SEP completed-window examples. Start from stock FP32 Smart Turn v3.2, not the rejected v2 checkpoint.

v2's nearest miss reduced stutter-gap premature decisions from 47.4% to 18.5%, but worsened general-speech incomplete specificity by about 0.6 percentage point. More original replay directly tests whether we can protect that general behavior while retaining some adaptation. It may also weaken the stutter-gap improvement. Keep the outcome either way; do not promise that 80/20 will work.

This is narrower than [Niko's reviewed v3 spec](https://github.com/vinhbin/stutterturn/blob/f7201981e2af591d14321ee2047b39a8e3371449/model/specs/training-v3.md), which requires W1/W2 at 70% replay and W3 at 80%, with optional W4. **Before execution, record the W3-only amendment and its checks in the team protocol.** Do not silently claim that the current required run grid was completed.

## Proposed frozen recipe

| Item | Recommendation |
|---|---|
| Initialization | Existing recovered stock FP32 v3.2 weights, same verified export path |
| Per-sample mixture | 0.80 original replay / 0.10 SEP incomplete / 0.10 SEP complete proxy |
| Data | Reuse `data-v2` and original labels; no new downloads or synthetic additions to this run |
| Optimization | Learning rate `1e-5`; seed 0; existing AdamW, schedule, fixed mixture-derived loss weighting and batch policy |
| Length | Two existing weighted epochs; approximately 18,820 sampled draws, not two full dataset passes |
| Checkpoints | Existing half-epoch schedule and deterministic prescreen ranking; at most two qualifying exports |
| Candidate thresholds | Existing grid `{0.4, 0.5, 0.6}`; no expansion after viewing outcomes |
| Final selection | Existing selector constraints, including M5 no regression and beating the qualifying stock comparator |
| Output | Fresh `prescreen-v3.json` and `sel-v3`; preserve all candidate results and failures |
| Final test | Sealed under D-009 regardless of the development result |

The 20% adaptation source is **not exclusively stuttering audio**. Its positive half intentionally includes both disfluent and fluent podcast clips, and endpoint labels are automatic proxies. This balance addresses v1's one-sided podcast labels. Newly generated ElevenLabs audio is not part of this recipe; the original replay dataset already includes some upstream synthetic speech.

W3 keeps approximately the same SEP exposure as the typical v2 run (about 1,882 draws from each SEP source), while increasing replay to about 15,056 draws. That is roughly 2.7 times the v2 replay volume. Record actual draws and steps; batch rounding and early stopping can change the counts.

## Checks before and after a run

1. **Verify inputs and caches before starting.** Assert actual reference-file hashes against the v2 manifest, train-only membership, replay/guard disjointness, audio identities, and base-model identity. Check recorded duplicate exclusions; identical source audio must not appear across training and validation under different IDs. Show separation does not prove speaker separation. The inspected harness does not enforce every provenance check; use a fresh feature cache or verify a content/preprocessing-aware cache identity. No reserved-test contents need to be opened for this handoff.
2. **Verify the mixture and baseline.** Check sampled fractions against 80/10/10, the three-source loss-weight formula, and unchanged step-zero development metrics before interpreting any gain.
3. **Keep the original selector decision intact.** M1 is stutter-gap premature decisions; M2 is fluent-pause premature decisions; M3 is completed-window decisions; M4/M4b are general completed-speech checks; M5 is general unfinished-speech specificity. Candidate limits versus stock: M2 at most +1 point, M3 at least -2 points, M4/M4b at least -1 point, M5 no decrease. A candidate must also improve M1 over the qualifying stock-threshold comparator. Do not waive a failed condition because the miss is small.
4. **Register additional promotion checks before the run.** At the actual selected threshold, repeat stuttered-completion M3s and cropped-context M3-crop against stock at 0.5, retaining their existing -2-point tolerances. Report these separately from the unchanged selector. Also check matched agent `turn_onset` inputs and complete a reviewed audio acceptance run before integrating a candidate. A selector pass alone is only development eligibility; incomplete or failed additional checks mean no promotion.
5. **Disclose repeated development use.** v3 is designed after v1/v2 on the same development items and guard. Preserve all three outcomes and any amendments; this is not independent final evidence.

**Promotion acceptance:** these checks supplement, and do not replace, [PLAN's measured-improvement gate](../PLAN.md): human-reviewed endpoints; under 10% premature completions; median endpointing delay within +50 ms of stock separately for stuttered/fluent completed turns; no worse timeout/nonresponse rate or fluent unfinished-turn premature rate; and a matched patient baseline. Report tail and audible delay separately. Niko must verify the matched `turn_onset` comparison and label/metric evidence; Guttuu must verify source/reply audibility, explicit Stop/restart, and cancellation when speech resumes during already audible playback, with saved timing evidence. Vinh records the integration decision. Missing labels, unresolved reviewer disagreements, inadequate timing resolution, or incomplete audio checks block promotion, even if the proxy selector passes. No current result establishes this gate.

## Human review and synthetic testing are separate work

Prepare a **20–40-example development review**, approximately 5–10 per category: unfinished stuttered, unfinished fluent, completed stuttered, completed fluent. Use source context to confirm the speaker and actual turn boundary; two reviewers should independently label before resolving disagreements. Select by documented rules without consulting model performance, record exclusions/uncertain cases, and freeze labels before the new comparison. This small set diagnoses proxy failures; it cannot establish population performance. If it guides changes, it is development data.

Keep **synthetic/team QA** in a separate manifest: source type, script, speaker/voice identifier where permitted, audio hash, known pause timing, expected behavior, and observed events. Saved ElevenLabs output with explicitly timed inserted silence and team recordings of scripted pauses can check early replies, natural resumption while reply audio is playing, cancellation, explicit Stop, and clean restart. They must not be presented as authentic stuttering examples or folded into the headline score. The public demo's no-imitated-stuttering rule remains; label recordings and synthetic sources clearly.

For later confirmation, obtain different authentic recordings with reviewed endpoints and appropriate permission, preferably from speakers absent from training. Freeze the selected model, thresholds, timing and analysis before scoring. Do not use results to retune and then reuse the same examples as a final test. Neither this recommendation nor a v3 pass authorizes unsealing the existing reserved set.

## Timing, ownership and fallback

[Niko's 18:45 EDT update](https://github.com/vinhbin/stutterturn/issues/2#issuecomment-6102988921) requests go/no-go by about **19:00 EDT**, estimates roughly 45 minutes end to end, and retains the **20:00 hard stop** on October 10. The reviewed proposal also targets prescreen by 19:15 and selection by 19:40. If approval or checks cannot fit, do not compress verification or extend the deadline implicitly. No v4 or extra sweep follows a failed result.

- **Vinh:** decide whether to resume; the pause currently stands.
- **Niko:** reconcile the W3-only amendment and additional promotion checks with the team spec; own selection and disclosure.
- **Guttuu:** execute only after approval, record the environment/artifacts and exact outcome, and verify audible behavior before any candidate integration.

If no candidate qualifies, retain the stock/patient demonstration and report the failed adaptation honestly. Its human-label, audio and hosting acceptance work still has to be completed. The [judge-facing training report](training-report-2026-10-10.md) explains the current evidence and limitations.
