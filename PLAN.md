# StutterTurn plan and coordination

**Team:** Vinh · Guttuu · Niko · Kareem · **Repo:** https://github.com/vinhbin/stutterturn

**Times:** America/New_York (EDT), Saturday October 10 unless marked Sunday. **Deadlines:** feature freeze Sun 1:00 AM; video + Devpost 1:00–8:00 AM; submit by 8:30 AM (official 9:00 AM). Judging: 3 minutes, about two judges at the table.

**User outcome:** let a caller who stutters finish speaking, then answer promptly once their turn is complete. The intended demo compares stock and StutterTurn using the same real recording and live agent. Audible improvement and unchanged response delays are goals until measured.

**Task-status authority:** this PLAN. Issues #1–6 group acceptance gates and hold evidence links; PRs carry implementation/review evidence. Do not maintain a second independent task-status table. **Integration owner:** Vinh coordinates one reviewed merge at a time; Guttuu verifies the combined audio path and Niko verifies model/evaluation artifacts.

## Current status

October 10, 2 PM EDT repository check.

- **On main:** exploratory benchmark scripts and historical results at `8161223`; their labels, comparator and latency interpretation still need the corrections below. No validated efficacy result is available.
- **Merged implementation:** [PR #7](https://github.com/vinhbin/stutterturn/pull/7) merged at `9c2cbca`; its UI fixes at `ee06776` passed 30/30 original checks and 14/14 focused regressions, with an independent rerun of the latter. [PR #8](https://github.com/vinhbin/stutterturn/pull/8) merged at `8828693`, bringing reviewed evidence corrections and the preserved intended pitch onto main. Live acceptance remains blocked; neither merge proves a working voice interaction.
- **Model mechanics verified independently:** [recovery handoff](docs/model-recovery-handoff.md) and [reproduction artifacts](docs/proofs/model-mechanics/README.md) record recovered stock FP32 weights, a synthetic training update and ONNX export/reload parity. This does not establish stutter adaptation, real-audio preprocessing or agent compatibility; Niko's complete F1 integration handoff is still pending.
- **Not yet reported in the repository:** human-reviewed A/B annotations, the stock/patient web-agent run, model/agent contracts, an adapted speech model and a corrected matched evaluation. This does not rule out teammates' unpushed work; owners attach their artifact at the next checkpoint.
- **Gate status:** the 2 PM feasibility decision has no published result yet; the 3 PM development gate remains next. Vinh records the actual result and evidence. Time elapsed or a merged PR does not pass a gate.
- **Immediate dependency:** Guttuu's agent contract and first complete stock replay unblock live UI integration. Niko's checkpoint proof and the two human listening batches continue independently. Additional UI/pitch expansion waits for these handoffs.

Replace this current summary as evidence arrives. Preserve meaningful previous decisions in [the decision log](docs/decision-log.md), rather than appending competing current snapshots.

## Current decision — 12:30–2 PM proof, then explicit gates

Vinh approved this bounded proof and task update on October 10. Keep StutterTurn conditional while proving the central interaction; this is not a claim that the whole team has confirmed the pick or that any gate has passed. This section supersedes the earlier telephony-first schedule and 10 PM model-abandon decision. Tasks and evidence remain unchecked until completed.

### Finishable deliverables and handoffs

The status below describes published evidence, not guesses about local work. Use Ready → Building → Awaiting acceptance → Verified; mark Blocked/Cut explicitly and leave unreported work **Unreported**. A code PR may finish while its parent interaction gate remains open.

| ID / owner | Concrete artifact → consumer | Observable acceptance | Current status / evidence | Checkpoint |
|---|---|---|---|---|
| **F1 / Niko** · [#2](https://github.com/vinhbin/stutterturn/issues/2) | `model/CONTRACT.md`, checkpoint provenance, one-batch log and reloaded export → Guttuu | Match initial outputs to the corresponding stock precision, train one batch, export/reload/infer; record runtime and command. **45-minute recovery cap.** | [Mechanical proof passed](docs/proofs/model-mechanics/README.md) in isolation; Niko's model contract and agent-ready artifact handoff pending. Synthetic update is not adaptation. | Consume tested recovery route; report actual remaining integration at gate |
| **F2 / Guttuu** · [#2](https://github.com/vinhbin/stutterturn/issues/2) | `agent/CONTRACT.md`, runnable stock/patient replay and saved run log → Vinh UI + Kareem evidence | Same real source/settings; save model decision, speech resumption, first audible response, cancellation, timeout and no response. A model prediction alone does not pass. | Unreported; UI live integration blocked | Contract first; complete run by 2 PM; repair core audio path before extras |
| **F3 / Vinh** · [#1](https://github.com/vinhbin/stutterturn/issues/1) | `benchmark/annotations/feasibility/vinh.csv`, A01–A15 → Niko | Human listening with context; five examples per category, documented true end/resumption and uncertainty; no ambiguous labels accepted | Unreported; file is an assigned output, not an existing artifact | 2 PM; missing context/category becomes a blocker |
| **F4 / Vinh (reassigned ~2:15 PM; was Kareem)** · [#1](https://github.com/vinhbin/stutterturn/issues/1) | `benchmark/annotations/feasibility/kareem.csv`, B01–B15 → Niko | Same check as F3, different source samples. **Independence caveat:** one reviewer now labels both batches, so Kareem must cross-check every row Vinh flags `uncertainty` plus 5 random rows before Niko consumes the file | Unreported; handoff effective only after Vinh's own F3 file is pushed | ASAP after F3; report missing categories |
| **I1 / Vinh UI builder** · [#4](https://github.com/vinhbin/stutterturn/issues/4) | `web/demo-ui/` → Guttuu adapter + Kareem page | Review scaffold/reset/keyboard/error behavior; separately accept a real replay attributed to the right run/configuration | Scaffold review passed at `ee06776`, merged via [PR #7](https://github.com/vinhbin/stutterturn/pull/7); **live acceptance blocked on F2**, candidate arm also F1 | Scaffold on main; real integration in 3–7 PM block |
| **P1 / Vinh evidence builder** · [#5](https://github.com/vinhbin/stutterturn/issues/5) | `docs/claims-ledger.md`, pitch/submission wording → Kareem README + Vinh delivery | Every delivered claim has applicable evidence, scope and limits; preserve intended pitch separately. Historical-report agreement alone is insufficient. | Corrected draft reviewed at `bc8fc70`, merged via [PR #8](https://github.com/vinhbin/stutterturn/pull/8); new live/model evidence remains pending | Recheck claims against actual artifacts before any rehearsal/public use |
| **I2 / Kareem** · [#3](https://github.com/vinhbin/stutterturn/issues/3) | Judges-page shell outside `web/demo-ui/` → judge entry point | Link/embed I1; real run/evidence links; missing services and fixtures labeled; no duplicated figures | Unreported; shell may proceed, real results wait for F2/E1 | Integrated path by 7 PM |
| **E1 / Niko; Guttuu supplies audio outcomes** · [#2](https://github.com/vinhbin/stutterturn/issues/2), [#5](https://github.com/vinhbin/stutterturn/issues/5) | Frozen split manifests and immutable matched run records → claims ledger + page | Apply all evaluation repairs below; protect both caller groups, report censored/nonresponses; DEV selects, separate final test supports release | Unreported; old results are exploratory | DEV decision 3 PM; final report before 1 AM freeze |

F3/F4 together supply **30 feasibility examples**: 10 unfinished stutter blocks, 10 completed stuttered turns and 10 completed fluent turns. Annotation CSVs use the same header: `sample_id,source_id,context_ref,speaker_id,category,time_origin,block_onset_s,resumption_s,turn_end_s,reviewer,reviewed_at,uncertainty,accepted`. Times refer to the explicitly named source/context; leave inapplicable fields empty. Unknown speaker identity stays unknown. Niko validates schema, disjoint source samples and usable counts before consuming the files. No audio is committed.

**F1 execution shortcut:** [model recovery handoff](docs/model-recovery-handoff.md) records the verified official artifact/source and a now-executed community FP32-to-PyTorch recovery path. The [tested mechanical proof](docs/proofs/model-mechanics/README.md) verifies reconstruction, a synthetic update and reloaded export with numerical parity. Niko can reproduce this route and proceed to reviewed real data and integration. A skipped parity test or fresh Whisper initialization does not pass F1; the synthetic checkpoint is not a candidate for the demo.

These 30 examples are a **feasibility set**, not the final benchmark. If context or examples are unavailable, record the missing category as a blocker rather than substituting energy-derived labels. A loading/one-batch smoke test can run in parallel with listening; adaptation on newly selected stutter labels waits for their validation.

### Four parallel lanes — start together

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

**Owner: Niko; Kareem helps organize annotations and evidence without independently changing benchmark interfaces.**

- [ ] Freeze show-separated training, development and final-test manifests, checking speaker overlap where identities are known. The current 200+200 evaluation spans all eight SEP-28k shows; rebuild the partition and rerun stock. Treat existing measurements as exploratory, not the comparator for a new final test.
- [ ] Use development data for every checkpoint/threshold decision; reserve final test for the selected configuration. Include unfinished blocks **and genuine completed turns from both caller groups**.
- [ ] Add human-validated unfinished fluent continuations/pauses to development and final-test regression coverage. The 30-example feasibility set can remain unchanged.
- [ ] Preserve original Smart Turn `endpoint_bool` labels; original data contains both complete and incomplete turns. Save actual usable training counts after exclusions and filtering; select a bounded original-data subset.
- [ ] Use matching causal check schedules for stock/candidate and caller groups. Observe through the deployed timeout, or report right censoring explicitly. A model not firing within one second is not proof of a three-second fallback.
- [ ] Use timing resolution fine enough to assess the +50 ms target; the existing 100 ms checkpoints alone cannot establish that bound.
- [ ] Add model-path/output arguments and model/dataset/config hashes to run records. Invalidate fluent caches when any input changes; never mix tuned block results with cached stock fluent results.
- [ ] Document dependencies, checkpoint retrieval and a reproducible command. Select truly active-speech controls and human-verified turn ends; energy-only controls cannot validate semantic labels.

## Roles, boundaries and worktree agents

| Owner | Responsibility | Owned paths | Handoff |
|---|---|---|---|
| **Niko** | Training, annotation validation/splits, evaluation and long-block testing | `model/`, `benchmark/` except the two human annotation files assigned above | Versioned model + immutable run records + limits |
| **Guttuu** | Complete web agent first; optional phone transport after proof | `agent/` | Runnable agent, documented control/event interface and observed timings |
| **Kareem** | Human B-batch labels, judges page, claims/evidence links; optional Tiger Data | `web/` **except `web/demo-ui/`**, `README.md`, assigned `kareem.csv` | Results page whose claims match saved evidence |
| **Vinh** | Human A-batch labels, gate decisions, integration, demo UI, pitch, rehearsals, video, Devpost | `PLAN.md`, `docs/decision-log.md`, `docs/agent-handoff.md`, `web/demo-ui/`, the three pitch/evidence docs, assigned `vinh.csv` | Three-minute demo and submission with verified claims |

Vinh can run **two builders in separate worktrees plus a read-only reviewer** using [the agent handoff](docs/agent-handoff.md). One builder owns the minimal demo UI; one owns pitch/evidence preparation. Minimal UI needed to exercise the live agent can proceed in parallel without delaying human listening. Polish follows the proof. No two writers own the same file; Kareem's page work excludes Vinh's UI directory. Shared model/event contract changes coordinate with their owners first.

Nobody imitates stuttering. Use real recordings, clearly identified on screen; confirm the applicable audio/demo rights. Automated waveform inspection does not count as human listening.

## Remaining phases — follow the selected scope

| Phase (EDT) | Owners | Exit condition | Task |
|---|---|---|---|
| **12:30–2 PM: proof** | All, assignments above | Trustworthy examples, model feasibility, live baseline; record 2 PM decision | [#1](https://github.com/vinhbin/stutterturn/issues/1), [#2](https://github.com/vinhbin/stutterturn/issues/2) |
| **2–3 PM: candidate or fallback** | Niko + Guttuu; Vinh records gate | Development improvement with both groups protected, or explicit corrected-benchmark scope | [#2](https://github.com/vinhbin/stutterturn/issues/2) |
| **3–7 PM: integration** | Guttuu + Niko; Kareem page | Working web comparison for selected scope; attempt long-block evaluation if real context is available; optional phone/sponsor additions after core works | [#3](https://github.com/vinhbin/stutterturn/issues/3) |
| **7–10 PM: demo engineering** | Vinh leads; all | Live comparison or clearly labeled recorded fallback; reset under 60 seconds; three rehearsals including an unscripted participant | [#4](https://github.com/vinhbin/stutterturn/issues/4) |
| **10 PM–Sun 1 AM: freeze** | Kareem + all | Claims/evidence audit, reproducible instructions, final test report; no new features after 1 AM | [#5](https://github.com/vinhbin/stutterturn/issues/5) |
| **Sun 1–8:30 AM: video + submit** | Vinh; Kareem checks | Protect 3–4 hours for video/Devpost; check links logged out; received confirmation by 8:30 | [#6](https://github.com/vinhbin/stutterturn/issues/6) |

**Deferred, not removed:** telephone provisioning, duplicate cloud training, additional rival API arms, Tiger Data integration and UI polish wait until the core proof passes. Use already working core services; do not add a new dependency merely for a sponsor entry. Record later additions against remaining time and the chosen scope.

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
