# StutterTurn

**Let people finish.** StutterTurn's goal is an open turn-taking model that waits through stuttered speech and answers promptly when the speaker finishes.

We are building a matched stock-versus-adapted comparison using real recorded speech, a voice agent and evidence covering both premature responses and response delay. The intended contribution is a reusable open model and benchmark. A trained improvement, drop-in compatibility and novelty remain claims to earn with the artifacts below.

| Hacklanta '26 | |
|---|---|
| Main track | AI/ML |
| Team | Vinh · Guttuu · Niko · Kareem |
| Demo / Devpost | Pending; no working public demo is claimed here |
| Intended core integrations | Gemini agent responses and ElevenLabs voice, subject to the working-agent proof |
| Optional after core proof | Phone transport, Vultr hosting/training and Tiger Data; actual use determines sponsor entries |

## Build status

**[PLAN.md](PLAN.md#current-status) is the current task-status authority.** Read its deliverable table for owners, acceptance checks and blockers. Issues #1–6 group the phase gates; a merged implementation does not automatically pass a gate.

Main includes the reviewed passive demo UI and corrected claims/pitch documents from merged [PR #7](https://github.com/vinhbin/stutterturn/pull/7) and [PR #8](https://github.com/vinhbin/stutterturn/pull/8). The UI preview contains synthetic events. Follow PLAN for live-agent, model and annotation acceptance; these merges do not establish efficacy.

## What the first complete demonstration must show

Replay the **same real, labeled source recording** through stock and the selected patient/adapted configuration. Observe whether the speaker resumes before the agent's first audible response; distinguish this from the model's internal completion decision. Measure true completed-turn delay and nonresponses for both stuttered and fluent speech.

The candidate arm becomes available only after a real exported model is integrated. If the adaptation gate fails, the deliverable becomes a corrected benchmark and interactive baseline comparison. That fallback still needs validated labels and reproducible runs. A UI fixture or a model prediction alone does not prove either outcome.

Nobody imitates stuttering. A recorded backup must be labeled as a recording; sample audio and its use require appropriate rights. The [intended strong pitch](docs/pitch-and-qa.md) is a draft, not a capability report. Use only evidence-reviewed wording in the delivered pitch.

## Evidence and reproducibility

- [Historical benchmark report](benchmark/RESULTS.md) and [scripts](benchmark/scripts/) preserve the exploratory work. The 116/200 first-check outputs are model completion predictions under the original harness, **not a validated percentage of callers interrupted**.
- [D-006 and D-007](docs/decision-log.md) record the methodological corrections. One-second observation/censoring does not establish a three-second fallback; energy-derived cut points do not establish semantic turn ends; repeated harness checks do not prove live-agent behavior.
- [Required evaluation work](PLAN.md#evaluation-work-required-before-a-comparison-can-pass) includes reviewed endpoints, frozen development/final-test splits, matched model/data/configuration records, both caller groups, audible outcomes, and explicit nonresponse/censoring.
- The [claims ledger](docs/claims-ledger.md) is the single claim-status source. Headline numbers must link to applicable run evidence; do not promote targets or historical interpretations to measured outcomes.

The existing benchmark setup is incomplete: `benchmark/requirements.txt` is not committed, and no clean reproduction or candidate run is claimed. Niko's handoff includes exact dependencies, checkpoint provenance and a verified command. See [benchmark context](benchmark/README.md).

For the **UI scaffold only**, from current main:

```bash
python -m http.server 8010 --directory web/demo-ui
```

Open `http://localhost:8010/`. The preview is synthetic UI data without audio or model output. It is not the live product or benchmark evidence. Real-agent run instructions belong to Guttuu's pending `agent/CONTRACT.md`.

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
| Niko | Trainable checkpoint/export, corrected evaluation and immutable evidence |
| Guttuu | Runnable stock/patient web agent, control/event contract and real audio timings |
| Vinh | A-batch human labels, integration decisions, demo UI, pitch/video/submission |
| Kareem | B-batch human labels, judges page, README and evidence links |

[PLAN.md](PLAN.md) contains the executable deliverables; [agent handoff](docs/agent-handoff.md) defines parallel write scopes; [decision log](docs/decision-log.md) preserves scope decisions. `benchmark/` contains current exploratory work. `model/` and `agent/` are pending producer handoffs; `web/demo-ui/` is on main.

Artifact licensing, publication, accessible demo links and final submission confirmation remain release checks in PLAN. Do not infer a commercial deployment license from research access.
