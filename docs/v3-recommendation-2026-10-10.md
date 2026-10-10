# Approved v3 scope: one 80/20 experiment, with separate validation

**October 10, 2026. Execution approved at approximately 19:00 EDT under D-011.** Vinh explicitly resumed W3 only with “ok do it” after the bounded recommendation. [The approval is recorded on issue #2](https://github.com/vinhbin/stutterturn/issues/2#issuecomment-6103109431). It supersedes his earlier training pause, but keeps the reserved test sealed, all validation/promotion checks, and the 20:00 EDT hard stop. Approval does not establish that Guttuu has started or completed the run.

## Recommendation and why

Run **only W3**, following preflight and within the approved timebox: 80% original Smart Turn training replay, 10% SEP unfinished-gap examples, and 10% SEP completed-window examples. Start from stock FP32 Smart Turn v3.2, not the rejected v2 checkpoint.

v2's nearest miss reduced stutter-gap premature decisions from 47.4% to 18.5%, but worsened general-speech incomplete specificity by about 0.6 percentage point. More original replay directly tests whether we can protect that general behavior while retaining some adaptation. It may also weaken the stutter-gap improvement. Keep the outcome either way; do not promise that 80/20 will work.

This narrows [Niko's original reviewed v3 spec](https://github.com/vinhbin/stutterturn/blob/f7201981e2af591d14321ee2047b39a8e3371449/model/specs/training-v3.md), which required W1/W2 at 70% replay and W3 at 80%, with optional W4. Niko recorded the [W3-only amendment](https://github.com/vinhbin/stutterturn/issues/2#issuecomment-6103046179), now merged in PR #28. Use the [reconciled team protocol](../model/specs/training-v3.md). Record W1/W2/W4 as not run; do not claim the original grid was completed.

## Approved frozen recipe

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

[Niko's reconciled protocol](../model/specs/training-v3.md) targets prescreen at **resume +20 minutes** and selection at **resume +40 minutes**, with the unchanged **20:00 EDT hard stop** on October 10. Vinh approved at approximately 19:00. If execution or checks cannot fit in the remaining time, do not compress verification or extend the deadline. No v4 or extra sweep follows a failed result.

- **Vinh:** approved W3 only under D-011; later integration still requires evidence and a recorded decision.
- **Niko:** the amendment is recorded; own selection, matched input checks, and disclosure.
- **Guttuu:** execute the approved run after preflight, record start/environment/artifacts/outcome, and verify audible behavior before any candidate integration.

If no candidate qualifies, retain the stock/patient demonstration and report the failed adaptation honestly. Its human-label, audio and hosting acceptance work still has to be completed. The [judge-facing training report](training-report-2026-10-10.md) explains the current evidence and limitations.

## Follow-on: more authentic training data

Vinh also asked about data beyond the current sources. These are researched options, not downloaded inputs or amendments to the frozen v3 recipe:

| Source | Why it is useful | What must happen first |
|---|---|---|
| [AImpower English Stuttered Speech, Mozilla Data Collective](https://mozilladatacollective.com/datasets/cms4tcqvl01lyo207p6j1ykng) | 44 participant folders; adult English speakers who stutter; spontaneous conversations and read commands, with timestamped semantic/verbatim transcripts and stutter-event annotations. Best prospective match for conversational turn-taking. | Verify practical access: the listing provides CC BY-SA 4.0 information but also describes sharing with approved partners under data-use agreements. Access has not been tested. Respect withheld participants and withdrawals. |
| [UCLASS, University College London](https://www.uclass.psychol.ucl.ac.uk/) | Downloadable real stuttered speech, including conversational material; longer context can support endpoint review. Transcripts are available for some files. | Follow its stated research/teaching and attribution conditions; assess age/task coverage for our intended users. No audio has been downloaded. |

Prioritize reviewed conversational endpoints over simply increasing clip count. Stutter annotations and timestamped transcripts still do not directly supply the complete/incomplete turn labels our task needs. Group all sessions/crops from the same speaker into one partition before creating examples, check duplicate and near-duplicate audio against existing sources, and document unresolved speaker identities. A source that looks new is not automatically an independent test.

For a later version, build a small reviewed real-speech pilot first, then freeze a new training manifest and separate development/confirmation speakers. Keep original replay in the mixture and retain both incomplete and completed adaptation examples. Do not insert these sources into W3 at the last minute: changing data and mixture together would change the approved experiment. The W3 approval does not cover these additional datasets, another training variant, or any final-test run.
