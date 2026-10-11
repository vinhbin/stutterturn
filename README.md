# StutterTurn

**Let people finish.** A research prototype for more patient voice AI: an adapted turn-taking model, a cloud-hosted voice agent, and comparisons you can hear and inspect.

A pause can be part of a thought. StutterTurn replays real recorded speech through stock and exploratory adapted configurations, showing when the agent waits, responds, cancels a reply, or reports overlapping speech.

**Hacklanta '26 | AI/ML | Vinh, Guttuu, Niko, and Kareem**

## Try the demo

- [Project website](https://64-177-51-1.sslip.io/)
- [Judge guide and model comparisons](https://64-177-51-1.sslip.io/judge/)
- [Hosted replay console](https://64-177-51-1.sslip.io/live/) - demo login required; credentials supplied separately to judges
- [Devpost submission draft](docs/devpost.md)

Open the console, sign in, and wait for recordings and models to load. Select a recording, model configuration, and voice, then click **Start** to enable browser audio. Let the recording and generated reply finish before starting another run. Volume, Stop, and Reset control playback. The backend connects automatically; the instance admits one replay at a time.

The demo uses **recorded speech with fresh inference and response generation**. Microphone and telephone input are future work. The judge page shows saved database query results; its replay links let you run the selected configurations again.

## What works now

The backend runs on Vultr, performs ONNX turn-model inference, sends captured audio to Gemini, generates speech with ElevenLabs, and streams audio and events to the browser. The console offers stock models, a longer-wait configuration, and our exploratory X1 candidate.

Our current judge comparisons include a longer 10.4-second recording and five additional recordings, each comparing **Stock FP32 with X1**. All 12 selected runs completed with generated speech rendered in Chromium. Earlier unsuccessful provider attempts remain archived.

### A concrete interruption example

In the selected longer replay, stock decided to respond at **1.664 seconds**. Speech resumed at **3.808 seconds**, and stock reply audio began at **3.958 seconds**, reporting **0.050 seconds of overlap**. X1 held the early pause and reported no overlap. Both configurations later cancelled a premature reply before audio.

Both use a 0.2-second silence gate, with different model weights and thresholds (stock 0.5; X1 0.6). This is a configuration-level observation on one recording, based on server-scheduled audio rather than measured acoustic timing. X1 remains post-hoc, exploratory, and unpromoted; these examples do not establish a general interruption rate or isolated model-weight improvement.

[Longer replay evidence](agent/evidence/2026-10-11-long-replay-working/README.md) | [Five additional model pairs](agent/evidence/2026-10-11-model-five-replay/README.md)

## Sponsor integrations

| Technology | Role in the working application |
|---|---|
| **Google Gemini API** | Receives captured audio after a completion decision and generates a brief contextual reply. The policy avoids unsolicited comments about how the person speaks. |
| **ElevenLabs** | Streams generated speech into the browser audio pipeline, including volume, Stop, Reset, and cancellation when the speaker resumes. |
| **Tiger Data** | Stores run metadata in PostgreSQL and timestamped events in a TimescaleDB hypertable. SQL reconstructs decisions, resumption, cancellation, and response timing for the judge charts. |
| **Vultr** | Hosts the HTTPS website, Python backend, ONNX inference, provider requests, and authenticated HTTP/WebSocket API. Caddy serves/proxies traffic; systemd manages the backend. |

The Tiger Data evidence snapshot contains **37 runs and 631 events**, including earlier attempts and ten superseded runs excluded from current analysis. Exports are checked against the original logs. Ingestion is explicit; new console runs do not automatically update the saved charts.

[Integration details](docs/sponsors.md) | [Tiger Data queries and provenance](web/tiger/README.md) | [Vultr deployment](docs/vultr-backend.md)

## How it works

```text
Recorded speech -> Silero VAD -> Smart Turn / X1 turn policy
                                      -> completion decision
                               Gemini audio-to-reply
                                      |
                              ElevenLabs streaming TTS
                                      |
                         Authenticated WebSocket -> Web Audio

Run logs -> explicit Tiger Data ingestion -> SQL exports -> judge timelines
```

The agent tracks speech, completion decisions, response generation, cancellation, and audio separately. A premature decision may be cancelled before any agent speech plays, so a model prediction alone is not an audible interruption.

We adapted Pipecat's Smart Turn v3.2 using PyTorch and real podcast speech referenced by SEP-28k. The source-pinned haan converter supported recovery of the released FP32 weights and export back to ONNX. Reconstruction/export checks matched reference probabilities within approximately 1.2e-7 on synthetic checks.

[Model mechanics](docs/proofs/model-mechanics/README.md) | [Training report](docs/training-report-2026-10-10.md) | [Model results](docs/model-results-2026-10-10.md)

## Run locally

Follow the [agent setup](agent/README.md) for Python dependencies, pinned models, recordings, and provider configuration. Model/audio assets are downloaded separately; candidate inference requires the candidate ONNX file and matching metadata. Keep provider keys in the ignored local environment file.

Serve the frontend:

```bash
python -m http.server 8041 --bind 127.0.0.1 --directory web
```

Run the agent from the configured Python environment:

```bash
python agent/server.py --play
```

The local `--play` path uses laptop speakers. The deployed browser-audio configuration is documented in the [Vultr setup](docs/vultr-backend.md). A separate synthetic preview is labelled and is not evidence of live inference.

## Verification and evidence

- **47 backend tests** passed locally and on Vultr, including bounded empty-reply recovery and provider-error/timeout classification.
- Browser checks cover source/reply rendering, cancellation, stale messages, playback draining, authentication, and model/source presets.
- The selected longer pair and five additional pairs produced nonzero source and reply digital audio in Chromium. These are digital rendering checks, not acoustic measurements.
- The deployed backend at `ed3d3ec93ce7` allows 20 seconds for a Gemini reply, with one bounded retry for empty non-blocked responses. Stop and resumption still cancel pending work. Live provider requests can still fail or time out.

[Hosted comparison verification](docs/proofs/long-replay-judge/verification.json) | [Provider recovery evidence](docs/proofs/gemini-empty-recovery/README.md) | [Retained earlier attempts](agent/evidence/2026-10-11-provider-attempts/README.md)

The [historical Stock INT8/Patient packet](agent/evidence/2026-10-10-replay-v2/) remains separate from current Stock FP32/X1 comparisons. The [original benchmark](benchmark/RESULTS.md) recorded 116/200 first-check completion predictions in automatically detected gaps; this is not a measured percentage of callers interrupted.

## Next steps

Human-reviewed speech boundaries and a frozen confirmation set will support broader evaluation. We will measure premature replies, completed-turn response delay, cancellations, and nonresponses together. The five short X1 replays first completed via the three-second silence fallback, which does not establish prompt response timing at real turn endings.

We also plan to automate cloud-run ingestion, expand recordings and listening checks, and explore microphone and telephone input with people who stutter. StutterTurn targets turn-taking; it is not a medical or therapeutic product.

## Credits and project records

We build on **Smart Turn, Whisper, Silero VAD, haan, and SEP-28k**, and credit their creators and the original podcast speakers. These are upstream models, tools, and recordings. Nobody imitates stuttering in our examples. Annotation, audio, and model release terms are separate; research access does not imply unrestricted commercial rights.

Before the event, we researched concepts and prepared plans. The team changed direction to StutterTurn on Saturday morning; benchmark development and subsequent implementation took place during the event. Claude Code and Codex assisted with implementation, documentation, and review.

[Project plan and ownership](PLAN.md) | [Decision log](docs/decision-log.md) | [Claims ledger](docs/claims-ledger.md) | [Agent contract](agent/CONTRACT.md) | [Benchmark context](benchmark/README.md)
