# StutterTurn

**Let people finish.** StutterTurn's goal is an open turn-taking model that waits through stuttered speech and answers promptly when the speaker finishes.

In our exploratory measurement on real recordings, the standard open model's INT8 CPU build (Smart Turn v3.2) declared the turn over during 58% of tested stutter blocks at its first check — 116 of 200 energy-detected gaps; model completion decisions, not observed talk-overs ([method and numbers](benchmark/RESULTS.md)). We are building a matched stock-versus-adapted comparison using real recorded speech, a working web replay agent and evidence covering both premature decisions and response delay. The intended contribution is a reusable open model and benchmark. A trained improvement, drop-in compatibility and novelty remain claims to earn with the artifacts below.

| Hacklanta '26 | |
|---|---|
| Main track | AI/ML |
| Team | Vinh · Guttuu · Niko · Kareem |
| Demo / Devpost | Pending; no working public demo is claimed here |
| Intended core integrations | Gemini agent responses and ElevenLabs voice — both ran in the [saved replay v2](agent/evidence/2026-10-10-replay-v2/) |
| Other integrations | Vultr hosts an earlier site build. Niko ingested the saved logs into Tiger Data and generated the [judge chart snapshot](web/tiger/snapshot.json), merged in [PR #26](https://github.com/vinhbin/stutterturn/pull/26); this is a saved database export, not live connection status. Phone transport and Vultr training remain optional. See [PLAN](PLAN.md#current-status). |

## Build status

**[PLAN.md](PLAN.md#current-status) is the current task-status authority.** Read its deliverable table for owners, acceptance checks and blockers. Issues #1–6 group the phase gates; a merged implementation does not automatically pass a gate.

Legend: ✅ on main with saved evidence · ⬜ no repo evidence yet

| Capability | Status | Evidence |
|---|---|---|
| Exploratory stock baseline on real recordings (INT8 CPU build; energy-derived labels, listen-through pending) | ✅ | [benchmark/RESULTS.md](benchmark/RESULTS.md) |
| Agent contract and runnable stock/patient **web replay** agent (Gemini reply, ElevenLabs voice) | ✅ | [agent/CONTRACT.md](agent/CONTRACT.md) v0.1 · [replay v2](agent/evidence/2026-10-10-replay-v2/) (supersedes the [first replay](agent/evidence/2026-10-10-first-replay/)) · [PR #11](https://github.com/vinhbin/stutterturn/pull/11), [PR #14](https://github.com/vinhbin/stutterturn/pull/14) |
| Landing page, judge view and run console wired to the real backend | ✅ | [web/](web/README.md) · [saved model-only runs](web/evidence/2026-10-10-ui-integration/) · [PR #12](https://github.com/vinhbin/stutterturn/pull/12) |
| Stock-weight recovery, synthetic update and ONNX export/reload parity (mechanics only, not adaptation) | ✅ | [docs/proofs/model-mechanics/](docs/proofs/model-mechanics/README.md) |
| Frozen show-separated split manifests v1 and matched eval-runner spec | ✅ | [benchmark/splits/v1/](benchmark/splits/v1/) · [benchmark/specs/](benchmark/specs/) · [PR #9](https://github.com/vinhbin/stutterturn/pull/9) |
| Human label listen-through (A/B feasibility batches) | ⬜ | |
| Training v1/v2 development evaluation; no candidate passed selection | ✅ | [Model results and limits](docs/model-results-2026-10-10.md); no accepted model or final-test efficacy result |
| Long-block (3+ s) evaluation | ⬜ | |
| Gemini end-of-speech rival arm | ⬜ | Separate from Gemini's working reply-generation role |
| Phone transport (8 kHz) — the current agent replays web audio; no phone path | ⬜ | |

In the saved replay v2 — which supersedes the first replay after a model-input fix restored the missing pre-roll — stock decided "complete" before the energy-labelled speech resumption in 4 of 5 clips (one decision preceded the labelled gap), versus 0 of 5 for patient. Three replies were cancelled before reported audio; no response-audio overlap was reported in the ten runs. Physical playback was not verified for that packet, and five clips support no interruption rate. Separately, [Guttuu's human listening check](https://github.com/vinhbin/stutterturn/issues/3#issuecomment-6102558836) heard a source and generated reply, verified explicit Stop and restart, and heard only the later reply after an earlier reply was cancelled before playback. Natural resumption during an already audible reply and acoustic timing remain untested. Follow PLAN for remaining acceptance; a merged PR does not pass a gate.

## What the first complete demonstration must show

Replay the **same real, labeled source recording** through stock and the selected patient/adapted configuration. Observe whether the speaker resumes before the agent's first audible response; distinguish this from the model's internal completion decision. Measure true completed-turn delay and nonresponses for both stuttered and fluent speech. The [saved replay v2](agent/evidence/2026-10-10-replay-v2/) separates completion decisions, reported audio events and cancellations for five clips under exploratory labels; it does not establish true completed-turn delay or acoustic outcomes. Human-validated labels and more sources are still required before any rate is quoted.

The candidate arm becomes available only after a real exported model is integrated. If the adaptation gate fails, the deliverable becomes a corrected benchmark and interactive baseline comparison. That fallback still needs validated labels and reproducible runs. A UI fixture or a model prediction alone does not prove either outcome.

Nobody imitates stuttering. A recorded backup must be labeled as a recording; sample audio and its use require appropriate rights. The [intended strong pitch](docs/pitch-and-qa.md) is a draft, not a capability report. Use only evidence-reviewed wording in the delivered pitch.

## Evidence and reproducibility

- [Historical benchmark report](benchmark/RESULTS.md) and [scripts](benchmark/scripts/) preserve the exploratory work. The 116/200 first-check outputs are the INT8 CPU build's completion predictions under the original harness, **not a validated percentage of callers interrupted**. The [current model results](docs/model-results-2026-10-10.md) report matched stock INT8/FP32 development comparisons and the failed v1/v2 candidate selections, with proxy-label limits.
- Exploratory comparisons are saved for the configurations we tested — including silence timeouts of 0.8 s and 1.5 s and a 0.99 confidence threshold. They do not yet establish which configurations meet both our interruption and response-delay targets; no universal "no setting fixes it" claim is made.
- [D-006 and D-007](docs/decision-log.md) record the methodological corrections. One-second observation/censoring does not establish a three-second fallback; energy-derived cut points do not establish semantic turn ends; repeated harness checks do not prove live-agent behavior.
- [Required evaluation work](PLAN.md#evaluation-work-required-before-a-comparison-can-pass) includes reviewed endpoints, frozen development/final-test splits, matched model/data/configuration records, both caller groups, audible outcomes, and explicit nonresponse/censoring.
- The [claims ledger](docs/claims-ledger.md) is the single claim-status source. Headline numbers must link to applicable run evidence; do not promote targets or historical interpretations to measured outcomes.

`benchmark/requirements.txt` is committed, and the [eval-runner spec](benchmark/specs/eval-runner-v1.md) records a verified rerun reproducing the historical 116/200 and 136/200 decisions on the same items. Candidates were evaluated on development data, but none passed every selection constraint. Vinh has kept the reserved test sealed for later testing; the additional-training proposal remains undecided. See [benchmark context](benchmark/README.md).

For the presentation site and run console, from current main:

```bash
python -m http.server 8041 --bind 127.0.0.1 --directory web
```

`/` is the landing page, `/judge/` the guided judge view and `/live/` the run console; `/judges/` and `/demo-ui/` remain legacy routes. Vultr still serves the earlier build, so the new routes await deployment. Without a backend, the preview is synthetic UI data and labeled as such. With Guttuu's local backend running (`python agent/server.py`, setup in [agent/README.md](agent/README.md)), the console runs real local model decisions against the same recordings — see [web/README.md](web/README.md) and the [saved model-only runs](web/evidence/2026-10-10-ui-integration/). The run-control/event schema is [agent/CONTRACT.md](agent/CONTRACT.md) v0.1.

## Scope and limits

- The target is turn-taking, not improved speech recognition or a medical/therapeutic outcome.
- The original exploratory clips are short; longer stutter blocks and 8 kHz phone transfer remain unvalidated here.
- No measured custom-model improvement, unchanged response delay, universal “no setting fixes it,” or “first” claim is currently accepted. Ambitious intended wording is preserved separately until supported.
- No person who stutters is on the team; human endpoint review is not a substitute for user research. Do not imply community endorsement or invented testimony.

## Foundations and disclosure

- **SEP-28k:** [Apple's stuttering-event dataset](https://github.com/apple/ml-stuttering-events-dataset), with CC BY-NC 4.0 annotations. Audio is fetched through the `miosipof/sep28k_full` mirror, not redistributed here; underlying podcast audio rights remain with the owners. Confirm permissions for the intended demo/release.
- **Smart Turn v3.2:** [pipecat-ai's open turn-taking model](https://github.com/pipecat-ai/smart-turn), the intended adaptation baseline. Preserve the upstream model/code license and disclose modifications.
- **Existing accessibility work:** [Apple's atypical-speech research](https://arxiv.org/abs/2302.09044) and [AImpower's speech-recognition work](https://aimpower.org/fair-speech-ai/) are relevant prior art. Neither this list nor an unsuccessful search establishes that our contribution is first.
- **Before the event:** concept research and planning; the team changed direction to StutterTurn on Saturday morning. **During the event:** AI-assisted benchmark development and subsequent implementation, with provenance in Git history. Accounts, external models, datasets and services are not original team work.

## Team and repository

| Owner | Current handoff |
|---|---|
| Niko | Trainable checkpoint/export, corrected evaluation and immutable evidence — splits v1 and the eval-runner spec are on main |
| Guttuu | Runnable stock/patient web agent, control/event contract and real audio timings — contract v0.1 and replay v2 (superseding the first replay) are on main |
| Vinh | A/B human labels, integration decisions, demo UI, site/README upkeep, pitch/video/submission |
| Kareem | Judges page, README and evidence links; pages and evidence index delivered via [PR #12](https://github.com/vinhbin/stutterturn/pull/12). Current maintenance and task ownership are tracked in [PLAN](PLAN.md#current-status). |

[PLAN.md](PLAN.md) contains the executable deliverables; [agent handoff](docs/agent-handoff.md) defines parallel write scopes; [decision log](docs/decision-log.md) preserves scope decisions. `benchmark/` contains current exploratory work plus frozen split manifests and run specs. `agent/` (contract v0.1 and the replay agent) and the `web/` site are on main; `model/` holds its contract and training specs. No fine-tuned model is selected for the demo.

Artifact licensing, publication, accessible demo links and final submission confirmation remain release checks in PLAN. Do not infer a commercial deployment license from research access.
