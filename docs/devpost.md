# StutterTurn — Devpost draft

Draft based on main `adb8892` and agent preparation at `12b9845`, October 10, 2026. The fields below describe the current prototype. Refresh them from the [claims ledger](claims-ledger.md) when new results arrive. The [original intended pitch](pitch-and-qa.md) remains intact.

## Project name

StutterTurn

## Elevator pitch

Let people finish. Building voice AI that gives people who stutter room to speak, using open turn-taking models.

## Inspiration

A pause is not always the end of a thought.

For someone who stutters, a block can happen while they are still trying to finish a word. A voice agent has to decide whether to wait or answer. Responding too early can take the turn away from the person it is supposed to help; waiting too long after every sentence creates a different problem.

We chose to work on that handoff. StutterTurn is for developers building voice agents and the people who have to speak to them. Our goal is straightforward: let people finish, then respond promptly, with an inspectable model and evidence others can check.

## What it does

We are building StutterTurn around model adaptation, speech evaluation and a comparison interface. The intended interaction is simple: replay the same recording through stock and adapted models, see when each decides the speaker is finished, and hear when the agent responds. A longer-wait stock configuration is an essential comparison too.

The current prototype contains exploratory experiments, a tested path for updating the stock weights, a reviewed UI and a proposed agent interface. The agent branch also includes a pinned asset-fetch script, dependency requirements and implementation steps. Live audio comparison and adaptation to reviewed stuttered speech remain in progress. The UI preview contains labeled synthetic events, with no real audio or model output.

## How we built it

We started with Pipecat's Smart Turn v3.2 and real podcast clips from SEP-28k. Python scripts save predictions around pauses. Clip-level stuttering labels and automatically detected gaps do not establish a true conversational turn boundary, so human review with surrounding context is our next data requirement.

The official trained release provides ONNX artifacts, while the upstream training script initializes from Whisper Tiny. Using the source-pinned community **haan** converter, we recovered the trained FP32 weights and checked their outputs against the official model. In an isolated CPU environment, we then ran a synthetic training update, saved and reloaded the weights, exported ONNX, and checked its outputs again.

Our browser interface separates completion decisions from response-audio events, attributes events to a run and configuration, and resets between runs. Its controls, failure handling and mobile layout have been checked.

The proposed live pipeline connects voice activity detection and Smart Turn to Gemini responses and ElevenLabs speech. That pipeline is an integration target; the separate saved ElevenLabs experiment is not proof that this full interaction works.

## Challenges we ran into

**Defining an interruption.** A completion prediction does not prove that an agent spoke over someone: the system might wait or cancel. We need both the decision and actual response playback, aligned with human-reviewed speaker continuation.

**Recovering the right starting point.** A fresh classifier initialized from Whisper is not stock Smart Turn. Recovering the released weights with numerical parity gave us a verifiable starting point.

**Making the comparison fair.** A longer wait is a legitimate baseline. An adapted model needs fewer premature responses and acceptable delays for both stuttered and fluent speech. That requires separate training, development and final-test recordings, with unresolved labels and nonresponses reported.

## Accomplishments that we're proud of

- **A working route from released weights to a trainable model and back to ONNX.** Reconstruction and post-update export matched their reference probabilities within `1.2e-7` in our synthetic checks. This proves training/export mechanics; improvement on stuttered speech remains unproved. [Tested script and exact results](https://github.com/vinhbin/stutterturn/tree/main/docs/proofs/model-mechanics).
- **A reviewed comparison interface.** The scaffold passed 30 original browser checks and 14 focused regressions covering run isolation, failures, keyboard controls and mobile layout. Live-agent acceptance remains separate. [UI and run instructions](https://github.com/vinhbin/stutterturn/tree/main/web/demo-ui).
- **Inspectable evidence.** We saved the exploratory results and their limitations. Our claims ledger keeps measured observations, goals and unsupported interpretations distinct. [Claims and evidence](https://github.com/vinhbin/stutterturn/blob/main/docs/claims-ledger.md).

## What we learned

Turn-taking is a system behavior. Model accuracy, audio playback and the meaning of a pause all matter, and each needs its own evidence.

Recovering weights and exporting a model removes an engineering uncertainty. Whether that model helps people who stutter still depends on reviewed speech, a fair comparison and the complete interaction.

## What's next for StutterTurn

1. Complete the human listening and annotation pass, retaining surrounding context and excluding unresolved examples.
2. Run the same real recording through stock and a patient/wait configuration, with audible responses and saved logs for decisions, speaker resumption, cancellation, response playback and nonresponse.
3. Adapt the recovered model using reviewed training data, select on development data, and evaluate the chosen model on a separate frozen final test.
4. Report premature responses and response delay together, for both stuttered and fluent speech. Keep model decisions separate from audible outcomes.
5. Connect the UI to the verified agent, capture a reproducible comparison, and publish the artifacts whose release terms we have confirmed.

## Built with

Python · PyTorch · ONNX · ONNX Runtime · Hugging Face Transformers · NumPy · JavaScript · HTML · CSS · Smart Turn v3.2 · haan · SEP-28k

ElevenLabs was used in a separate exploratory agent experiment. The combined Gemini/ElevenLabs web-agent pipeline remains proposed. Add sponsor integrations to the submitted technology tags only when their actual use is verified.

## Try it out

- [Source repository](https://github.com/vinhbin/stutterturn)
- [Model mechanics: tested script, environment and results](https://github.com/vinhbin/stutterturn/tree/main/docs/proofs/model-mechanics)
- [Comparison UI: local scaffold instructions](https://github.com/vinhbin/stutterturn/tree/main/web/demo-ui)
- [Claims ledger](https://github.com/vinhbin/stutterturn/blob/main/docs/claims-ledger.md)

A public live demo and demo video are not available in this draft. The local scaffold preview has no real audio or model outputs.

## Credits and disclosures

**Team:** Vinh, Guttuu, Niko and Kareem. **Track:** AI/ML.

Smart Turn, Whisper, the haan converter and SEP-28k are upstream work, not models or datasets we created. We credit Pipecat, the haan contributors, and the SEP-28k authors (Lea et al.). SEP-28k annotations are CC BY-NC 4.0; underlying podcast audio rights remain with their owners. Audio is not redistributed in this repository. Audio/demo permissions and adapted-weight release terms remain separate release checks.

Before the event, we researched concepts and prepared plans. The team changed direction to StutterTurn on Saturday morning. Our benchmark development and subsequent implementation took place during the event. Claude Code and Codex assisted with code, documentation and review; the repository records the work and its verification. The synthetic training batch is a mechanical check, not stutter adaptation. We do not imitate stuttering or claim community validation we have not performed.

---

## Team-only publish checklist — do not paste into the project story

- [ ] Update this snapshot against the latest published code, saved runs and [claims ledger](claims-ledger.md). Replace pending statements only when their corresponding result exists.
- [ ] Require actual response playback for the audible demo. The current agent implementation plan schedules audio events from received TTS chunks and makes speaker playback optional; those events alone cannot establish an audible interruption.
- [ ] Add the actual live-demo and video URLs after checking them logged out. Keep prerecorded input and fallback footage labeled.
- [ ] Verify repository visibility and every evidence link before putting them on a public submission; pushing this file does not publish a Devpost entry or change repository visibility.
- [ ] Have all four teammates confirm their names, Devpost accounts and required disclosures. Enter sponsor prizes only for verified actual use.
- [ ] Keep the original strong pitch intact. Do not add unsupported novelty, caller-level interruption rates or unchanged-delay claims to this story.
- [ ] Confirm submission receipt before the team's 8:30 AM Sunday deadline. Follow [the submission plan](submission.md) for video, rehearsal and final checks.

**Evidence snapshot:** model mechanics are on main at `8bbd721`; the reviewed UI and pitch were merged through PRs #7 and #8. Guttuu's [agent contract at `538dacf`](https://github.com/vinhbin/stutterturn/blob/538dacfed3266946e6080442524d595755fd63a8/agent/CONTRACT.md) explicitly describes a proposed interface; [preparation at `12b9845`](https://github.com/vinhbin/stutterturn/tree/12b9845b4df8726805d529947eee58bd242e7aec/agent) adds setup code and implementation steps. Its example events and commands are not run evidence. Preserve these distinctions when updating the public story.
