# StutterTurn plan and coordination

**Team:** Vinh · Guttuu · Niko · Kareem · **Repo:** https://github.com/vinhbin/stutterturn

**Times:** America/New_York (EDT), Saturday October 10 unless marked Sunday. **Deadlines:** feature freeze Sun 1:00 AM; video + Devpost 1:00–8:00 AM; submit by 8:30 AM (official 9:00 AM). Judging: 3 minutes, about two judges at the table.

**User outcome:** let a caller who stutters finish speaking, then answer promptly once their turn is complete. The intended demo compares stock and StutterTurn using the same real recording and live agent. Audible improvement and unchanged response delays are goals until measured.

## Current decision — 12:30–2 PM proof, then explicit gates

Vinh approved this bounded proof and task update on October 10. Keep StutterTurn conditional while proving the central interaction; this is not a claim that the whole team has confirmed the pick or that any gate has passed. This section supersedes the earlier telephony-first schedule and 10 PM model-abandon decision. Tasks and evidence remain unchecked until completed.

| Owner | Next task | Evidence required by 2 PM | Task |
|---|---|---|---|
| **Niko** | Recover/load trainable Smart Turn weights; compare initial outputs with stock, run one training batch, export and reload. Cap checkpoint recovery at **45 minutes**. | Checkpoint provenance, parity comparison against corresponding stock precision, one-batch log, exported-model inference. Measure actual runtime before budgeting iterations. | [#2](https://github.com/vinhbin/stutterturn/issues/2) |
| **Guttuu** | Run the complete **web voice agent**; replay real recordings through stock and a patient/wait configuration in the same pipeline. | Input IDs/settings and timestamps for model decision, speech resumption, first audible response, cancellation and timeout/no response. Show whether a premature decision becomes an audible interruption. | [#2](https://github.com/vinhbin/stutterturn/issues/2) |
| **Vinh + Kareem** | Human-check **30 examples**: 10 unfinished stutter blocks, 10 completed stuttered turns, 10 completed fluent turns. | Annotation sheet with source/context, speaker, onset/resumption or true turn end, category, reviewer and uncertainty. Use surrounding audio; a three-second clip boundary is not proof of a turn end. Exclude ambiguous samples. | [#1](https://github.com/vinhbin/stutterturn/issues/1) |

These 30 examples are a **feasibility set**, not the final benchmark. If context or examples are unavailable, record the missing category as a blocker rather than substituting energy-derived labels. A loading/one-batch smoke test can run in parallel with listening; adaptation on newly selected stutter labels waits for their validation.

### Four parallel lanes — start together

| Lane | Work that starts immediately | Early handoff; only dependent work waits |
|---|---|---|
| **Niko** | Checkpoint recovery/smoke test; repair model/run cache handling and evaluation runner. | In the first 15 minutes of the sprint, document the intended artifact/input/output interface in `model/CONTRACT.md`; distinguish proposed from verified compatibility. Full stutter training waits for reviewed labels and frozen splits, not UI or telephony. |
| **Guttuu** | Complete stock web agent, replay/logging and a patient/wait configuration. | In the first 15 minutes, publish the proposed run-control/event schema and local connection instructions in `agent/CONTRACT.md`. Use a versioned contract; notify consumers before breaking it. Start with stock; candidate integration waits only for Niko's export. |
| **Vinh** | Label **A01–A15** (five samples per category); delegate demo UI and pitch/evidence tasks to separate worktrees. | UI builds a passive display/adapter against the proposed contract while backend work proceeds. Human listening takes priority over UI polish. Pass reviewed labels to Niko as available; reserve final-test examples separately. |
| **Kareem** | Label **B01–B15** (five different samples per category); prepare results-page shell, run-evidence index and README/run instructions. | Build the page against the proposed schema, with clearly labeled development fixtures until real runs arrive. Exclude `web/demo-ui/` from edits; embed/link Vinh's surface after its handoff. |

The A/B sample lists must be disjoint; reviewers can cross-check ambiguous cases without duplicating the whole batch. Contract drafts and scaffolds are allowed during the proof; **polish and optional integrations wait**, not all frontend work. Humans may delegate their independent scaffold tasks while listening. Gate decisions and integration synchronize the lanes; they do not require everyone to work serially.

Each lane owns its branch/worktree and subdirectory. Keep dependencies/configuration inside the owned package where practical; Vinh coordinates any shared root manifest/lockfile change with the other owners before it is made. Merge completed, reviewed increments into `main` one at a time so nobody builds on an unpublished interface. See [agent handoff](docs/agent-handoff.md).

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
| **Niko** | Training, annotations/splits, evaluation and long-block testing | `model/`, `benchmark/` | Versioned model + immutable run records + limits |
| **Guttuu** | Complete web agent first; optional phone transport after proof | `agent/` | Runnable agent, documented control/event interface and observed timings |
| **Kareem** | Annotation coordination, judges page, claims/evidence links; optional Tiger Data | `web/` **except `web/demo-ui/`**, `README.md` | Results page whose claims match saved evidence |
| **Vinh** | Human annotation review, gate decisions, demo UI, pitch, rehearsals, video, Devpost | `web/demo-ui/`, `docs/pitch-and-qa.md`, `docs/submission.md`, `docs/claims-ledger.md` | Three-minute demo and submission with verified claims |

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

## Historical status — superseded interpretation, preserved for context

**~11 AM:** initial scripts and saved results were committed; 116/200 completion predictions gave the exploratory 58% figure. Later review found unresolved gap labels, latency censoring, comparator and training-path problems. The earlier “baseline banked,” “novelty verified,” and “no knob fixes it” conclusions are not current gate evidence. See [decision D-006](docs/decision-log.md) and the original saved results; numerical artifacts have not been rewritten by this planning update.
