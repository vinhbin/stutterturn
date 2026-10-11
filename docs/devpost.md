# StutterTurn — Devpost submission

Updated October 11, 2026 against the Vultr backend at `667460f45fdd`, auto-connecting console at `bccef4bf7bb6`, saved model results, and verified hosted browser playback. Copy the public fields below; omit the team-only notes.

## Project name

StutterTurn

## Elevator pitch

Let people finish. StutterTurn combines an adapted turn-taking model, a cloud-hosted voice agent, and inspectable evidence to explore more patient voice AI.

## Inspiration

A pause is not always the end of a thought.

Imagine asking a voice assistant for help and getting an answer before you can finish your question. For someone who stutters, a speech block can leave them still trying to finish a word while the system decides it is already time to respond.

More than three million Americans stutter, according to the [National Institute on Deafness and Other Communication Disorders](https://www.nidcd.nih.gov/health/statistics/quick-statistics-voice-speech-language). We wanted to examine a small but consequential part of their interaction with voice AI: who gets to decide when their turn is over?

Our first exploratory experiment gave us a reason to investigate. Smart Turn v3.2's INT8 model predicted completion at its first check in **116 of 200 automatically detected gaps in stutter-labelled recordings — 58%**. These were internal model decisions under an exploratory evaluation, not a measured rate of people being audibly interrupted.

That distinction became central to StutterTurn. We wanted to build the complete interaction, inspect what happens after a premature decision, and explore whether model adaptation can improve turn-taking without simply making every response slower.

## What it does

StutterTurn is a working research prototype for developers building voice agents.

Our comparison interface replays the same real recording through stock Smart Turn, a longer-wait stock configuration, and an exploratory adapted candidate. A shared timeline exposes speech activity, completion decisions, cancelled replies, and reported response-audio events.

The backend now runs on **Vultr**, including turn-model inference, **Gemini** response requests, **ElevenLabs** speech generation, and the HTTP/WebSocket API that feeds the console. The authenticated hosted console plays the source recording and generated reply in the browser while displaying live run events. Start enables sound; volume, Stop, and Reset control playback. Our laptop setup remains available too.

We also built an evidence pipeline in **Tiger Data** that turns saved run events into queryable timelines and a judge-facing chart. That chart is a saved database-query snapshot; new cloud runs are not automatically ingested yet.

The current interaction uses real recorded speech, with a fresh run for each configuration. Microphone and telephone input remain future work.

## How we built it

We built three connected pieces: a model-adaptation workflow, a replay agent, and an evidence interface.

For the model, we started with Pipecat's **Smart Turn v3.2** and real podcast recordings referenced by **SEP-28k**. Using the source-pinned community **haan** converter, we recovered the released FP32 weights into a trainable PyTorch model. We checked numerical agreement with the original ONNX model, verified a training update, and tested export back to ONNX.

We then ran real training and development evaluations using podcast speech examples and replay data from the original task. Our comparisons included stock INT8, stock FP32, threshold changes, longer silence waits, and adapted candidates. We tracked both premature completion predictions and regressions on other speech.

The replay agent processes audio with **Silero VAD and ONNX Runtime**, maintains turn state, and streams events to the browser. Each run records its configuration, model hash, source recording, and event sequence.

Each sponsor has a specific role:

- **Google Gemini API — generating the reply.** When the turn policy decides to answer, we send the captured audio to Gemini. Its system instruction asks for a brief, useful response and avoids unsolicited commentary about how the person speaks. If their intent is unclear, it requests clarification.
- **ElevenLabs — producing the agent's speech.** Gemini's text goes to ElevenLabs streaming text-to-speech. The Vultr backend streams the returned PCM over the authenticated WebSocket. Web Audio plays it alongside the source recording on a shared timeline, with bounded buffering, volume control, and cancellation when the caller resumes. Generated reply text also appears in the console.
- **Tiger Data — explaining what happened.** We store run metadata in PostgreSQL and timestamped events in a TimescaleDB hypertable. SQL views reconstruct completion decisions, cancellations, and response timing. The saved database snapshot comes from an ingestion of **20 runs and 302 events**; analysis excludes superseded runs. The judge chart displays this query-generated snapshot.
- **Vultr — running the application.** Our existing instance hosts the HTTPS site and runs the Python backend, ONNX inference, Gemini requests, and ElevenLabs requests. Caddy proxies the HTTP/WebSocket API, while systemd manages the backend. Demo controls require authentication, provider keys stay server-side, and the small instance admits one replay at a time.

The frontend uses HTML, CSS, and JavaScript. It connects to the hosted backend while retaining a clearly labelled synthetic preview for interface testing.

## Challenges we ran into

**A model decision is not the same as an interruption.** A model can decide too early, but the caller may resume before speech generation finishes and cause the reply to be cancelled. We had to track completion, resumption, cancellation, and playback separately.

**Waiting longer is a real competitor.** Increasing a silence timeout can prevent some premature responses. Any adapted model needs to justify itself against that simpler option. We included longer-wait and threshold baselines instead of assuming a fine-tune would automatically be better.

**Improving one dataset can hurt another.** Some candidates reduced premature predictions on development examples but regressed on unfinished speech in the general-speech guard. The v1–v4 attempts did not pass their selection checks. Those failures helped us investigate how recording source, input duration, and automatically generated labels affected the model.

**The benchmark and agent must see comparable inputs.** We corrected a missing pre-roll issue in the replay path. Further parity checks exposed differences between offline checks and the streaming agent, including later-turn input boundaries. We documented those differences rather than treating the two paths as interchangeable.

**Moving a laptop demo into the cloud changes playback.** A headless server can run inference and receive generated speech, but delivering that speech to a visitor's speakers needs a browser audio transport. We added an authenticated PCM transport and a Web Audio player, then checked that real source and reply audio rendered in Chromium. Server sample schedules, browser buffering, and acoustic output remain distinct measurements.

## Accomplishments that we're proud of

- **A cloud-hosted voice-agent backend that actually runs.** Stock FP32 and exploratory candidate replays completed on Vultr with real Gemini replies and ElevenLabs speech rendered by the authenticated browser. We measured nonzero digital audio for both the source and reply. A later provider timeout is retained in the verification record; these smoke checks do not establish service reliability or model efficacy.
- **An adapted candidate running in the complete agent.** We exported and loaded an exploratory candidate and captured stock-versus-candidate runs on the same recording, with both laptop playback and browser playback from the hosted backend.
- **A verified route from released weights to training and back.** Our synthetic reconstruction and export checks matched reference probabilities within approximately **1.2 × 10⁻⁷**.
- **Evidence that can be traced.** Model identities, configurations, run logs, SQL queries, and saved results connect displayed observations to their underlying artifacts.
- **Tested integration boundaries.** Forty backend tests passed locally and on the Vultr host. Browser checks cover audio sequencing, cancellation, stale messages, and draining the final buffer. We also checked authenticated browser operation, rejected unauthenticated controls, restricted source selection, and the single-run limit.

Our current X1 candidate is **post-hoc and exploratory**, chosen after v4 results in a fifth look at reused development and guard data. It is not a v4 pass or a promoted release. Its agent runs demonstrate integration; broader improvement still requires human-reviewed confirmation and response-delay evaluation.

## What we learned

Turn-taking is a property of the whole system.

The model decides, the response generator takes time, speech synthesis produces audio, and the playback system may start or cancel that audio. Evaluating only the classifier misses what the person actually experiences.

Patience has to be measured alongside responsiveness. A system that rarely interrupts because it rarely answers is not the outcome we want.

Failed experiments were useful engineering results. They showed where our data and evaluation needed to improve, and prevented us from mistaking a promising development number for a reliable accessibility improvement.

## What's next for StutterTurn

1. Complete human review of pause, resumption, and completed-turn boundaries, retaining enough surrounding context to judge them.
2. Evaluate the fixed exploratory candidate on a frozen confirmation set before considering promotion.
3. Measure premature responses, completed-turn response delay, cancellations, and nonresponses together for both stuttered and fluent speech.
4. Expand browser compatibility and human listening checks, and automatically ingest new cloud runs into Tiger Data.
5. Expand to longer recordings, more speakers, and additional forms of disfluency, then explore microphone and telephone input.
6. Work with people who stutter to evaluate usefulness and interaction preferences.
7. Publish appropriate model and benchmark artifacts after confirming their release terms.

## Built with

Python · PyTorch · ONNX · ONNX Runtime · Hugging Face Transformers · NumPy · Smart Turn v3.2 · Silero VAD · Gemini API · ElevenLabs · Tiger Data · PostgreSQL · TimescaleDB · Vultr · Caddy · WebSockets · Web Audio API · JavaScript · HTML · CSS · haan · SEP-28k

## Try it out

- [Project website](https://64-177-51-1.sslip.io/)
- [Judge guide](https://64-177-51-1.sslip.io/judge/)
- [Hosted replay console — demo login required](https://64-177-51-1.sslip.io/live/)
- [Source repository — access required until made public](https://github.com/vinhbin/stutterturn)

The hosted console runs real inference and response generation on Vultr and displays the event trace. Click Start to hear the recording and generated speech; use volume, Stop, or Reset to control playback. The judge guide's saved chart describes its historical replay packet, not newly generated cloud runs.

## Credits and disclosures

Built by Vinh, Guttuu, Niko, and Kareem for the AI/ML track.

We build on Pipecat's Smart Turn, Whisper, Silero VAD, the haan converter, and SEP-28k. These are upstream contributions, not models or datasets we created. We credit the SEP-28k authors and the original podcast creators. Dataset annotations, underlying recordings, and adapted weights have separate usage and release considerations; we do not promise unrestricted commercial use.

Before the event, we researched concepts and prepared plans. The team changed direction to StutterTurn on Saturday morning; benchmark development and subsequent implementation took place during the event. Claude Code and Codex assisted with implementation, documentation, and review.

Our speech examples use real recordings; nobody imitates stuttering. StutterTurn is a research prototype, with community validation and broader efficacy evaluation still ahead.

---

## Optional sponsor-specific fields

**Best Use of ElevenLabs:** We integrated ElevenLabs streaming speech into a voice-agent replay system that investigates whether premature turn decisions become spoken interruptions. Generated speech streams from our Vultr backend to the browser and participates in the source/reply timeline, Stop, Reset, volume, and cancellation lifecycle. Chromium checks verify digital rendering of real ElevenLabs replies. Laptop playback remains available as well.

**Best Use of Gemini API:** Gemini receives captured audio when our turn policy decides to respond and generates the agent's reply. We use a dedicated system instruction for brief, useful responses without unsolicited commentary on the speaker's speech. Verified requests now run from Vultr as part of the complete response-generation pipeline.

**Best Use of Tiger Data:** We model voice-agent behavior as a time series, storing run metadata in PostgreSQL and timestamped events in a TimescaleDB hypertable. SQL views connect decisions, resumed speech, cancelled replies, and response timing. Our judge chart displays a reproducible database-query snapshot over real run logs; automatic ingestion of new Vultr runs is next.

**Best Use of Vultr:** Vultr hosts our public HTTPS site and runs our Python voice-agent backend, including ONNX turn-model inference, Gemini response requests, ElevenLabs speech generation, and the HTTP/WebSocket API used by the comparison console. We verified real stock and exploratory candidate replays on the instance, including source and generated speech rendered in Chromium. Demo controls are authenticated, API keys stay server-side, and systemd manages the service. Audio uses the authenticated WebSocket and Web Audio; measured acoustic timing remains future evaluation.

## Team-only publishing notes — do not paste into the story

- Repository is private as verified October 11. Give judges access or make the intended release public before describing its artifacts as publicly accessible. No visibility change was made by this update.
- Add the final video URL after verifying it. Source footage and demo captures exist; a finished public upload was not verified here.
- Provide the generated demo login through the intended judge-access channel. Do not publish provider keys or private configuration files.
- The hosted backend is deployed at `cad4d50fa292`; source/evidence are in [PR #46](https://github.com/vinhbin/stutterturn/pull/46), unmerged at this update. The source branch must be available wherever submitted evidence links point.
- [Cloud deployment and rollback](vultr-backend.md), [cloud proof](proofs/vultr-backend/README.md), [model results](model-results-2026-10-10.md), [model mechanics](proofs/model-mechanics/README.md), [Tiger snapshot provenance](../web/tiger/README.md).
- Cloud verification used a training-show clip. No model-quality, unseen-speaker or acoustic-outcome claim follows from those checks.
- Do not turn the historical 58% into a caller-level interruption rate, claim unchanged latency, or describe X1 as promoted. Do not claim Vultr training, Gemini Live rival benchmarking, live Tiger queries from the browser, or browser audio delivery.
- The prevalence source and [official sponsor prize descriptions](https://www.mlh.com/events/hacklanta-db/prizes) were fetched and checked October 11. Enter only the four implemented sponsor integrations above unless another qualifying integration is independently verified.
