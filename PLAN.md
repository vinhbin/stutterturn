# StutterTurn plan and coordination

**Team:** Vinh · Guttuu · Niko · Kareem (departed Sat afternoon — [D-008](docs/decision-log.md)) · **Repo:** https://github.com/vinhbin/stutterturn

**Times:** America/New_York (EDT), Saturday October 10 unless marked Sunday. **Deadlines:** feature freeze Sun 1:00 AM; video + Devpost 1:00–8:00 AM; submit by 8:30 AM (official 9:00 AM). Judging: 3 minutes, about two judges at the table.

**User outcome:** let a caller who stutters finish speaking, then answer promptly once their turn is complete. The intended demo compares stock and StutterTurn using the same real recording and live agent. Audible improvement and unchanged response delays are goals until measured.

**Task-status authority:** this PLAN. Issues #1–6 group acceptance gates and hold evidence links; PRs carry implementation/review evidence. Do not maintain a second independent task-status table. **Integration owner:** Vinh coordinates one reviewed merge at a time; Guttuu verifies the combined audio path and Niko verifies model/evaluation artifacts.

**Technical execution roadmap (October 10):** [Six implementation packages](docs/superpowers/plans/2026-10-10-technical-execution.md) cover validated inputs and candidate comparisons, actual playback/cancellation, reproducible failure tests and evidence, then post-demo evaluation and integration. Start label/evaluation integrity and playback independently; preserve the existing freeze. The roadmap proposes work and interfaces; accepted assignments, gate outcomes and completion status stay in this PLAN.

## Current status

October 10, evening EDT repository check, through merged [PR #26](https://github.com/vinhbin/stutterturn/pull/26) (`7865b1d`), including the runtime evidence and handoff in PRs #24–25.

- **Team change — Kareem departed** this afternoon (confirmed by Vinh); recorded as [D-008](docs/decision-log.md). His web-lane deliverables — landing page, judge view and evidence index — landed via [PR #12](https://github.com/vinhbin/stutterturn/pull/12) and are now maintained by Vinh's side, which also absorbs root `README.md` upkeep and disclosures. Gate criteria and evidence standards are unchanged.
- **OPEN — needs a new human:** the B-batch label cross-check (F4's independence check, previously Kareem's) is unassigned. Flagged for reassignment to **Guttuu or Niko**; the team has not decided. Until someone cross-checks Vinh's `uncertainty`-flagged rows plus 5 random rows, F4's independence caveat is unmet.
- **Tiger Data executed:** Niko reports live ingestion of 20 runs / 302 events in [PR #26](https://github.com/vinhbin/stutterturn/pull/26). Its merged [snapshot](web/tiger/snapshot.json), generated at `2026-10-10T21:43:03Z`, carries database provenance and the same values as the earlier offline export: ten current runs over five clips, ten superseded runs excluded. `/judge/` renders this saved database export; it does not query the database or report current connection health. Credentials remain private; no additional Vinh-side connection is needed to serve the snapshot.
- **On main:** Guttuu's `agent/CONTRACT.md` v0.1 and runnable stock/patient web replay agent with the [replay v2 evidence](agent/evidence/2026-10-10-replay-v2/) ([PR #11](https://github.com/vinhbin/stutterturn/pull/11), fixes in [PR #13](https://github.com/vinhbin/stutterturn/pull/13), pre-roll fix and v2 evidence in [PR #14](https://github.com/vinhbin/stutterturn/pull/14); v2 supersedes the [first replay](agent/evidence/2026-10-10-first-replay/), whose model input lacked pre-roll): five block clips × stock/patient; stock decided "complete" before the energy-labeled speech resumption in 4 of 5 clips (one decision preceded the labeled gap), versus 0 of 5 for patient; three replies cancelled before reported audio. No response-audio overlap was reported in those ten runs; actual playback was not verified, and these five clips do not establish an interruption rate. The run console, landing and judge pages with real backend integration and [saved model-only runs](web/evidence/2026-10-10-ui-integration/) ([PR #10](https://github.com/vinhbin/stutterturn/pull/10), [PR #12](https://github.com/vinhbin/stutterturn/pull/12)). Niko's frozen show-separated splits v1 and matched eval-runner spec landed in PR #9; PR #26 merged eval items v1, selection tooling, training specs, precision-baseline findings and the v2 selection write-up. The [model-mechanics proof](docs/proofs/model-mechanics/README.md) stands; it is not adaptation.
- **Not yet in the repository:** human-reviewed A/B annotations (F3/F4), a selected candidate model, final-test results, long-block tests, phone transport, and a recorded final scope choice. Development selection results are published; elapsed time or a merged PR does not pass the remaining gates.
- **Playback code landed:** PR #20 adds optional laptop-speaker output through `--play`; the browser remains a controller/observer. Scheduled timeline positions and reported device latency are not acoustic verification. The [execution roadmap](docs/superpowers/plans/2026-10-10-technical-execution.md) identifies cancellation, buffering and measurement acceptance still required.
- **Candidate selection finished:** v1 and v2 both returned `dev_nothing_passes`. [Guttuu's `sel-v2` result](https://github.com/vinhbin/stutterturn/issues/2#issuecomment-6102500044) rejects every candidate operating point on the M5 guard; no fine-tuned model is selected. The stock FP32 comparator is threshold 0.55. [Niko's merged write-up](docs/model-results-2026-10-10.md) contains the development results and proxy-label limits; raw `sel-v2` run directories and `decision.json` remain on Guttuu's machine. Niko recommends the corrected-benchmark fallback. [Guttuu's v3 proposal](https://github.com/vinhbin/stutterturn/issues/2#issuecomment-6102568699) is undecided by Vinh; the existing no-v3 rule and 20:00 hard stop remain unchanged.
- **Reserved test stays sealed:** Vinh explicitly asked to keep it untouched for later testing; [D-009](docs/decision-log.md) records that decision. [Niko's stock-only test proposal](https://github.com/vinhbin/stutterturn/issues/2#issuecomment-6102597230) is not authorized. `test.jsonl` remains sealed and unused, with manifest SHA-256 `6bddc5b6b59ad2b929b0542828199d13c0130cd450b57394f7ac2488b6c26d32`; preserve the end-of-window test alongside it. This does not approve v3 or declare the final project scope.
- **Human listening on-ramp:** [proposed A/B worksheets](docs/labeling/README.md) now map 30 disjoint development candidates to exact source/context links. They are not annotations: all human timing, reviewer and acceptance fields are blank. Vinh still needs to listen and publish A, then B; the independent B cross-check remains unassigned.
- **Current-code runtime and listening:** the [three-run packet](docs/proofs/playback-runtime/README.md) records real-device source stop/restart and one Gemini/ElevenLabs reply at `42b86d0`. [Guttuu's subsequent human check](https://github.com/vinhbin/stutterturn/issues/3#issuecomment-6102558836) at `03fc9b1` (same playback code) passed source/reply audibility, explicit Stop during source and reply, clean restart, and cancellation before audio followed by a later audible reply. He reports 26 deterministic tests and ten-clip × two-precision parity passing. Natural source resumption during an already audible reply, the provider-cap path and acoustic timing remain untested; one subsequent run hit a Gemini timeout. Both heard replies commented on the caller's speech. The reply-policy follow-up (`75307b1`) supplies a stricter system instruction and a [bounded smoke check](docs/proofs/reply-policy/README.md): four of four audio replies used the neutral fallback, two text-only probes received relevant answers, and 27 offline tests passed. Guttuu's audible acceptance of the revised replies remains pending. These checks do not establish model improvement.
- **UI integrated on main:** PR #21 preserves the approved charcoal/cyan studio design and separates `/judge/` from `/live/`. Vultr still serves the earlier build at the 17:19 EDT check: `/judges/` and `/demo-ui/` work, while `/judge/` and `/live/` return 404. Windows HTTPS validation succeeds; Python's local expired-root selection caused a separate client validation error. The older backend on port 8765 was preserved; the current-code test server closed after acceptance checks. No merge or deployment was performed.

Replace this current summary as evidence arrives. Preserve meaningful previous decisions in [the decision log](docs/decision-log.md), rather than appending competing current snapshots.

## Current decision — 12:30–2 PM proof, then explicit gates

Vinh approved this bounded proof and task update on October 10. Keep StutterTurn conditional while proving the central interaction; this is not a claim that the whole team has confirmed the pick or that any gate has passed. This section supersedes the earlier telephony-first schedule and 10 PM model-abandon decision. Tasks and evidence remain unchecked until completed.

### Finishable deliverables and handoffs

The status below describes published evidence, not guesses about local work. Use Ready → Building → Awaiting acceptance → Verified; mark Blocked/Cut explicitly and leave unreported work **Unreported**. A code PR may finish while its parent interaction gate remains open.

| ID / owner | Concrete artifact → consumer | Observable acceptance | Current status / evidence | Checkpoint |
|---|---|---|---|---|
| **F1 / Niko** · [#2](https://github.com/vinhbin/stutterturn/issues/2) | `model/CONTRACT.md`, checkpoint provenance, one-batch log and reloaded export → Guttuu | Match initial outputs to the corresponding stock precision, train one batch, export/reload/infer; record runtime and command. **45-minute recovery cap.** | [Mechanical proof passed](docs/proofs/model-mechanics/README.md); contract, training/evaluation specs and development write-up are on main via PR #26. Both candidate selections failed; no selected artifact. | Preserve failed-selection evidence; no candidate integration authorized |
| **F2 / Guttuu** · [#2](https://github.com/vinhbin/stutterturn/issues/2) | `agent/CONTRACT.md`, runnable stock/patient replay and saved run log → Vinh UI + evidence page | Same real source/settings; save model decision, speech resumption, first audible response, cancellation, timeout and no response. A model prediction alone does not pass. | Replay v2 and runtime packet saved; [human listening partially accepted](https://github.com/vinhbin/stutterturn/issues/3#issuecomment-6102558836). Prompt response and audible natural-resumption cancellation remain. | Finish reply acceptance; retain acoustic timing as unmeasured |
| **F3 / Vinh** · [#1](https://github.com/vinhbin/stutterturn/issues/1) | `benchmark/annotations/feasibility/vinh.csv`, A01–A15 → Niko | Human listening with context; five examples per category, documented true end/resumption and uncertainty; no ambiguous labels accepted | Unreported; file is an assigned output, not an existing artifact | 2 PM; missing context/category becomes a blocker |
| **F4 / Vinh (reassigned ~2:15 PM; was Kareem)** · [#1](https://github.com/vinhbin/stutterturn/issues/1) | `benchmark/annotations/feasibility/kareem.csv`, B01–B15 → Niko | Same check as F3, different source samples. **Independence caveat:** a second human must cross-check every row Vinh flags `uncertainty` plus 5 random rows before Niko consumes the file | Labels unreported; replacement cross-check reviewer unassigned | After F3; assign reviewer and report missing categories |
| **I1 / Vinh UI builder** · [#4](https://github.com/vinhbin/stutterturn/issues/4) | `web/demo-ui/` → Guttuu adapter + judge page | Review scaffold/reset/keyboard/error behavior; separately accept a real replay attributed to the right run/configuration | UI, live adapter and saved runs are on main; Guttuu used `/live/` for listening acceptance. No selected candidate; hosted browser audio remains unimplemented. | Rehearse chosen rig and verify reset under 60 seconds |
| **P1 / Vinh evidence builder** · [#5](https://github.com/vinhbin/stutterturn/issues/5) | `docs/claims-ledger.md`, pitch/submission wording → README + Vinh delivery | Every delivered claim has applicable evidence, scope and limits; preserve intended pitch separately. Historical-report agreement alone is insufficient. | Corrected draft merged via PR #8; newer runtime/listening evidence and development-selection results now exist. Final submission wording remains to be reconciled against their limits. | Recheck claims against actual artifacts before any rehearsal/public use |
| **I2 / Vinh (delivered by Kareem)** · [#3](https://github.com/vinhbin/stutterturn/issues/3) | Judges-page shell outside `web/demo-ui/` → judge entry point | Link/embed I1; real run/evidence links; missing services and fixtures labeled; no duplicated figures | PR #12 delivered the page/evidence index; PRs #21/23 integrated the judge guide and chart; PR #26 supplies the Tiger database snapshot | Check deployed build and final evidence wording |
| **E1 / Niko; Guttuu supplies audio outcomes** · [#2](https://github.com/vinhbin/stutterturn/issues/2), [#5](https://github.com/vinhbin/stutterturn/issues/5) | Frozen split manifests and immutable matched run records → claims ledger + page | Apply all evaluation repairs below; protect both caller groups, report censored/nonresponses; DEV selects, separate final test supports release | Splits/items, evaluation tools and failed development-selection write-up on main. Raw selection records remain with Guttuu; labels are proxies, completed-turn +50 ms criterion unmeasurable, test kept sealed by Vinh | Preserve evidence; no final-test run or efficacy claim authorized |

F3/F4 together supply **30 feasibility examples**: 10 unfinished stutter blocks, 10 completed stuttered turns and 10 completed fluent turns. Annotation CSVs use the same header: `sample_id,source_id,context_ref,speaker_id,category,time_origin,block_onset_s,resumption_s,turn_end_s,reviewer,reviewed_at,uncertainty,accepted`. Times refer to the explicitly named source/context; leave inapplicable fields empty. Unknown speaker identity stays unknown. Niko validates schema, disjoint source samples and usable counts before consuming the files. No audio is committed.

**F1 execution shortcut:** [model recovery handoff](docs/model-recovery-handoff.md) records the verified official artifact/source and a now-executed community FP32-to-PyTorch recovery path. The [tested mechanical proof](docs/proofs/model-mechanics/README.md) verifies reconstruction, a synthetic update and reloaded export with numerical parity. Niko can reproduce this route and proceed to reviewed real data and integration. A skipped parity test or fresh Whisper initialization does not pass F1; the synthetic checkpoint is not a candidate for the demo.

These 30 examples are a **feasibility set**, not the final benchmark. If context or examples are unavailable, record the missing category as a blocker rather than substituting energy-derived labels. A loading/one-batch smoke test can run in parallel with listening; adaptation on newly selected stutter labels waits for their validation.

### Original kickoff assignments — historical

The table below preserves the original sprint handoffs and credits; it does not assign new work to Kareem. Current ownership and acceptance are in **Finishable deliverables and handoffs** above: Vinh maintains the web/README lane, and the independent B-batch reviewer remains unassigned. Acceptance requirements remain in force; any reserved-test execution requires a later explicit unseal decision under D-009.

| Lane | Work that starts immediately | Early handoff; only dependent work waits |
|---|---|---|
| **Niko** | Checkpoint recovery/smoke test; repair model/run cache handling and evaluation runner. | In the first 15 minutes of the sprint, document the intended artifact/input/output interface in `model/CONTRACT.md`; distinguish proposed from verified compatibility. Full stutter training waits for reviewed labels and frozen splits, not UI or telephony. |
| **Guttuu** | Complete stock web agent, replay/logging and a patient/wait configuration. | In the first 15 minutes, publish the proposed run-control/event schema and local connection instructions in `agent/CONTRACT.md`. Use a versioned contract; notify consumers before breaking it. Start with stock; candidate integration waits only for Niko's export. |
| **Vinh** | Label **A01–A15**, push the file, then take **B01–B15** (reassigned from Kareem); record the 2 PM gate; draft Devpost fields + fallback-video storyboard early (no dependencies). | UI builds a passive display/adapter against the proposed contract while backend work proceeds. Human listening takes priority over UI polish. Pass reviewed labels to Niko as available; reserve final-test examples separately. |
| **Kareem** | B-batch labeling reassigned to Vinh (cross-check duty stays with Kareem); full focus on the results-page shell, run-evidence index and README/run instructions — his lane's unreported items. | Build the page against the proposed schema, with clearly labeled development fixtures until real runs arrive. Exclude `web/demo-ui/` from edits; embed/link Vinh's surface after its handoff. |

The A/B sample lists must be disjoint; reviewers can cross-check ambiguous cases without duplicating the whole batch. Contract drafts and scaffolds are allowed during the proof; **polish and optional integrations wait**, not all frontend work. Humans may delegate their independent scaffold tasks while listening. Gate decisions and integration synchronize the lanes; they do not require everyone to work serially.

Each lane owns its branch/worktree and subdirectory. The only annotation write exceptions inside Niko's `benchmark/` lane are F3's `vinh.csv` and F4's `kareem.csv`; Niko owns merged manifests and generated outputs. Keep dependencies/configuration inside the owned package where practical; Vinh coordinates any shared root manifest/lockfile change with the other owners before it is made. Merge completed, reviewed increments into `main` one at a time. Publish draft contracts early and accept their implementation separately. See [agent handoff](docs/agent-handoff.md).

### 2 PM — feasibility and scope decision (Vinh records, team reviews)

- [ ] Training/export path works, the complete stock agent runs, and human-checked examples expose a meaningful failure worth fixing: continue model adaptation to the 3 PM gate.
- [ ] Training path is blocked: stop promising a trained fix; switch to a **corrected benchmark and interactive baseline comparison**. That fallback still requires validated labels, reproducible runs and an honest interpretation.
- [ ] An existing configuration already solves the tested problem acceptably: credit it. Continue custom-model work only for a specific remaining advantage that can be tested immediately; otherwise use the comparison-tool scope.
- [ ] Full-pipeline failure or insufficient trustworthy examples: no audible-improvement claim. Repair the benchmark/comparison path and state the unresolved limitation.

### 3 PM — measured improvement decision

- [ ] On the **development set**, candidate reduces premature completion decisions versus matched stock; separately measure audible interruptions through the same agent pipeline. Keep both metrics distinct.
- [ ] Development target: **under 10% premature completions**, with completed-turn median endpointing delay within **+50 ms of stock for each group** (stuttered and fluent), and no worse timeout/no-response rate. Report tail delay and audible response delay too; do not hide nonresponses by averaging only successful turns.
- [ ] Check human-validated unfinished fluent turns too: their premature-completion rate must not worsen versus matched stock. Completed-turn speed alone does not protect fluent callers from new interruptions.
- [ ] Check the simplest patient/wait baseline on the same inputs and pipeline. If it meets the same targets, document the remaining advantage before extending custom-model work.
- [ ] Vinh records continue/fallback with run IDs, sample counts and limitations. If improvement is not demonstrated, commit to the corrected benchmark/comparison scope now; **do not defer this decision to 10 PM**.

This is a development decision, not a publishable efficacy result. Freeze a larger, separate final test before checkpoint selection; run stock and the chosen candidate on that same test once selection is complete. Small feasibility-set percentages must not become headline claims.

### Record the decision and first complete run

At each gate Vinh records **time / actual pass or miss / artifact and input IDs / limits / continue or fallback / recovery owner / next checkpoint** in the decision log and refreshes this current summary. An elapsed deadline is not a passed gate. Niko owns checkpoint/evaluation recovery, Guttuu owns audio-path recovery, and Vinh/Kareem own missing listening context. Independent work continues while the relevant failure is repaired.

Capture the first successful stock replay with real input and audible output as a labeled backup; add the matched patient/candidate run when available. Save the run command, commit/configuration, source ID and timing log with it. A fixture animation, model-only inference or recording of an unconnected UI does not satisfy this gate.

## Evaluation work required before a comparison can pass

**Owner: Niko; Vinh coordinates annotation/evidence handoffs without independently changing benchmark interfaces.** The reserved test remains untouched under D-009; these criteria do not authorize its execution.

- [ ] Freeze show-separated training, development and final-test manifests, checking speaker overlap where identities are known. The current 200+200 evaluation spans all eight SEP-28k shows; rebuild the partition and rerun stock. Treat existing measurements as exploratory, not the comparator for a new final test.
- [ ] Use development data for every checkpoint/threshold decision; reserve final test for the selected configuration. Include unfinished blocks **and genuine completed turns from both caller groups**.
- [ ] Add human-validated unfinished fluent continuations/pauses to development and final-test regression coverage. The 30-example feasibility set can remain unchanged.
- [ ] Preserve original Smart Turn `endpoint_bool` labels; original data contains both complete and incomplete turns. Save actual usable training counts after exclusions and filtering; select a bounded original-data subset.
- [ ] Use matching causal check schedules for stock/candidate and caller groups. Observe through the deployed timeout, or report right censoring explicitly. A model not firing within one second is not proof of a three-second fallback.
- [ ] Use timing resolution fine enough to assess the +50 ms target; the existing 100 ms checkpoints alone cannot establish that bound.
- [ ] Add model-path/output arguments and model/dataset/config hashes to run records. Invalidate fluent caches when any input changes; never mix tuned block results with cached stock fluent results.
- [ ] Document dependencies, checkpoint retrieval and a reproducible command. Select truly active-speech controls and human-verified turn ends; energy-only controls cannot validate semantic labels.

## Original roles and worktree boundaries — historical

These were the kickoff allocations. Kareem's delivered page/evidence work remains credited; his active maintenance responsibilities transferred to Vinh under D-008. Use the current deliverable owners above for new work, including Vinh's ownership of `web/` and root `README.md`; retain the rule that concurrent writers must own disjoint files.

| Owner | Responsibility | Owned paths | Handoff |
|---|---|---|---|
| **Niko** | Training, annotation validation/splits, evaluation and long-block testing | `model/`, `benchmark/` except the two human annotation files assigned above | Versioned model + immutable run records + limits |
| **Guttuu** | Complete web agent first; optional phone transport after proof | `agent/` | Runnable agent, documented control/event interface and observed timings |
| **Kareem** | Human B-batch labels, judges page, claims/evidence links; optional Tiger Data | `web/` **except `web/demo-ui/`**, `README.md`, assigned `kareem.csv` | Results page whose claims match saved evidence |
| **Vinh** | Human A-batch labels, gate decisions, integration, demo UI, pitch, rehearsals, video, Devpost | `PLAN.md`, `docs/decision-log.md`, `docs/agent-handoff.md`, `web/demo-ui/`, the three pitch/evidence docs, assigned `vinh.csv` | Three-minute demo and submission with verified claims |

Vinh can run **two builders in separate worktrees plus a read-only reviewer** using [the agent handoff](docs/agent-handoff.md). One builder owns the minimal demo UI; one owns pitch/evidence preparation. Minimal UI needed to exercise the live agent can proceed in parallel without delaying human listening. Polish follows the proof. No two writers own the same file; Kareem's page work excludes Vinh's UI directory. Shared model/event contract changes coordinate with their owners first.

Nobody imitates stuttering. Use real recordings, clearly identified on screen; confirm the applicable audio/demo rights. Automated waveform inspection does not count as human listening.

## Original phase schedule and acceptance requirements

The schedule below preserves the original phase gates, not current task assignments or completion claims. Vinh now owns Kareem's page, release-documentation and submission-check responsibilities; Niko checks metrics and Guttuu checks the rig. The current status above governs completed integrations. D-009 keeps final-test execution on hold; no phase deadline overrides that decision.

| Phase (EDT) | Owners | Exit condition | Task |
|---|---|---|---|
| **12:30–2 PM: proof** | All, assignments above | Trustworthy examples, model feasibility, live baseline; record 2 PM decision | [#1](https://github.com/vinhbin/stutterturn/issues/1), [#2](https://github.com/vinhbin/stutterturn/issues/2) |
| **2–3 PM: candidate or fallback** | Niko + Guttuu; Vinh records gate | Development improvement with both groups protected, or explicit corrected-benchmark scope | [#2](https://github.com/vinhbin/stutterturn/issues/2) |
| **3–7 PM: integration** | Guttuu + Niko; Kareem page | Working web comparison for selected scope; attempt long-block evaluation if real context is available; optional phone/sponsor additions after core works | [#3](https://github.com/vinhbin/stutterturn/issues/3) |
| **7–10 PM: demo engineering** | Vinh leads; all | Live comparison or clearly labeled recorded fallback; reset under 60 seconds; three rehearsals including an unscripted participant | [#4](https://github.com/vinhbin/stutterturn/issues/4) |
| **10 PM–Sun 1 AM: freeze** | Kareem + all | Claims/evidence audit, reproducible instructions, final test report; no new features after 1 AM | [#5](https://github.com/vinhbin/stutterturn/issues/5) |
| **Sun 1–8:30 AM: video + submit** | Vinh; Kareem checks | Protect 3–4 hours for video/Devpost; check links logged out; received confirmation by 8:30 | [#6](https://github.com/vinhbin/stutterturn/issues/6) |

**Deferred, not removed:** telephone provisioning, duplicate cloud training and additional rival API arms remain optional after the core proof. Tiger Data ingestion and the saved SQL snapshot have landed; the approved UI is integrated on main. Use already working core services; do not add a new dependency merely for a sponsor entry. Record later additions against remaining time and the chosen scope.

**Rest and meals:** schedule one protected 90-minute rest block per person between 3 and 10 PM at the 3 PM gate, around actual handoffs. Keep Vinh's early afternoon rest and protect submission time. Do not plan late-night recovery work as a substitute for the early gates.

## Shared contracts and evidence

| Boundary | Owner | Definition |
|---|---|---|
| Model | Niko | Intended stock Smart Turn input/output; prove compatibility. Name exports `stutterturn-v{N}.onnx`; do not overwrite previous runs. |
| Evaluation | Niko | Run ID, model hash, data-manifest hash, configuration, group/category, counts, premature decisions, audible interruptions where measured, median/tail delay, timeout/nonresponse and censoring. Version schema changes. |
| Agent/UI | Guttuu + Vinh | Document command and event contract before wiring controls. Existing proposed event fields `{t, state: speaking\|silence\|holding\|agent, prob, model}` are not evidence of an implemented service. Add run identity, time origin and cancellation/response timings by agreement. |
| Public claims | Vinh + Kareem | Keep the ambitious pitch draft. Mark each statement ready, target or unsupported in the claims ledger; use only ready claims in the delivered pitch. |

The merged [claims ledger](docs/claims-ledger.md) is the **single claim-status authority**; link exact model/run/data/configuration artifacts rather than copying numbers independently into multiple pages. A ledger row must distinguish a model output, synthetic/energy-derived control, human-validated endpoint and full-agent audible outcome. “Ready” requires a valid method for the stated conclusion, not merely a matching number in `benchmark/RESULTS.md`.

## Strong pitch, earned claims

The strong pitch remains the intended destination; it is not being replaced with a tentative research-question script. Vinh + Kareem own the release checklist in [#5](https://github.com/vinhbin/stutterturn/issues/5):

- [ ] Restore a numerical interruption claim only with validated labels, the exact denominator/population and measured outcome. **58% of tested blocks is not 58% of callers.** Internal completion predictions are not call hang-ups or necessarily audible interruptions.
- [ ] Use “none of the settings we tested met our target” only after matched baseline comparisons establish it; do not claim every possible setting or system was ruled out.
- [ ] Use “first” only for a narrowly scoped contribution supported by a documented prior-art review and appropriate uncertainty; a search finding no result is not proof of universal absence.
- [ ] Say “fine-tuned,” “drop-in,” “unchanged latency” or show a result arrow only after the corresponding artifact/test exists. If evaluation is rebuilt, rerun stock rather than reusing the old 58%.
- [ ] Keep English/blocks-only and dataset/audio limitations visible. Proposed research/noncommercial release is not an established commercial adoption path; resolve rights and licensing before publication.

## Open questions and submission checklist

- [ ] Vinh: confirm the team's choice and fetch the actual main-track judging rubric; MLH side prizes are not the main rubric.
- [ ] Vinh: verify Kareem's repo access and required API access without sharing credentials in issues.
- [ ] Team: any community outreach requires a separate team decision; do not invent consent or first-person testimony.
- [ ] Guttuu: if phone transport is added, test narrowband behavior before claiming phone-path support.
- [ ] Vinh + Kareem: choose artifact licenses and confirm audio/demo permissions; disclose SEP-28k, Smart Turn, AI assistance and pre-event work accurately.
- [ ] Kareem: repo visibility, zero-key evidence access where feasible, accurate run instructions and logged-out link checks before submission.
- [ ] Vinh: label real recordings and recorded fallback video; confirm the submitted video meets event requirements; enter only sponsor prizes backed by actual use.
- [ ] Team: Vultr credit code `MAJORLEAGUEHACKING` and post-event DEV writing challenge remain optional resources, not proof-gate dependencies.

Historical interpretations and their corrections are preserved in [D-006 and D-007](docs/decision-log.md). Original numerical artifacts remain unchanged; their existence is not final benchmark acceptance.
