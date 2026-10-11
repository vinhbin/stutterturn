# StutterTurn agent

**Owner: Guttuu.** Replays a real SEP-28k recording through VAD + an end-of-turn model (stock, patient or Niko's candidate), optionally answers with Gemini + ElevenLabs, and logs when it decided and when it was audible. Interface: [CONTRACT.md](CONTRACT.md). Current Stock FP32/X1 evidence: [longer replay](evidence/2026-10-11-long-replay-working/README.md) and [five additional pairs](evidence/2026-10-11-model-five-replay/README.md). The [historical Stock/Patient packet](evidence/2026-10-10-replay-v2/README.md) remains separately scoped.

## Setup (Windows, Python 3.11)

```bash
uv venv agent\.venv --python 3.11
uv pip install --python agent\.venv\Scripts\python.exe -r agent/requirements.txt
agent\.venv\Scripts\python.exe agent/fetch_assets.py 5
```

`fetch_assets.py` downloads Smart Turn v3.2 INT8 and FP32 ONNX (`pipecat-ai/smart-turn-v3` at `f766f81`) and Silero VAD v5.1.2 into `agent/models/`, checks every SHA-256 hash, and fetches N block + N fluent SEP-28k clips into `benchmark/audio/`. None of these files are committed.

For real replies, copy `agent/.env.example` to `agent/.env` and fill in `GEMINI_API_KEY` and `ELEVENLABS_API_KEY`. `agent/.env` is gitignored; never put keys in `.env.example`. Optional: `GEMINI_MODEL` (default `gemini-3.8-flash`), `ELEVENLABS_VOICE_ID`, `ELEVENLABS_MAX_CHARS` (default 3000 per process, protects credits), `CANDIDATE_MODEL` (path to Niko's ONNX export; its metadata JSON beside it supplies `sha256` and `threshold`, or set `CANDIDATE_SHA256`). A model whose hash does not match is refused.

## Reply policy

Gemini receives the reply policy as a system instruction and the caller audio
as user content. It should answer clear meaning in one short sentence without
unsolicited comments about pauses, speech delivery or a recording ending.
For an unclear fragment, the policy requests exactly: "What would you like
help with?" It must not invent missing intent. An explicit question about
speech or audio can still receive a relevant answer.

The [reply-policy smoke check](../docs/proofs/reply-policy/README.md) records
four live Gemini replies on two captured turn slices plus two text-only
probes. This is a bounded behavior check, not a guarantee of future responses
or evidence about end-of-turn accuracy. The offline regression checks that
the policy reaches the system field and audio reaches user content.

## Run

```bash
# one replay, no external services (decisions only)
agent\.venv\Scripts\python.exe agent/run.py --config stock --source HeStutters_4_32.wav --services off
# every local clip, model-only batch
agent\.venv\Scripts\python.exe agent/run.py --config patient --all --services off
# real reply and voice
agent\.venv\Scripts\python.exe agent/run.py --config stock --source HeStutters_4_32.wav --services on

# server for the demo UI / judges page
agent\.venv\Scripts\python.exe agent/server.py            # http://127.0.0.1:8765, services on
agent\.venv\Scripts\python.exe agent/ws_client_check.py stock HeStutters_4_32.wav

# live demo: judges hear the recording and the agent's reply on the laptop speakers
agent\.venv\Scripts\python.exe agent/server.py --play
agent\.venv\Scripts\python.exe agent/run.py --config stock --source HeStutters_4_32.wav --services on --play
```

`--play` needs `sounddevice` (in `requirements.txt`). Pick the output device in Windows sound settings before the demo; the run log records which device was used and its reported latency.

Each run writes `agent/runs/<run_id>.jsonl` (gitignored). Runs used as evidence are copied to `agent/evidence/<date>-<name>/` with a README giving the command, commit and limits.

## Offline playback checks

```powershell
agent\.venv\Scripts\python.exe -m unittest discover -s agent/tests -v
```

These checks need NumPy and the Python standard library, with no model files,
credentials, `.env` reads, network calls or real audio devices. They exercise the
actual player/engine against controlled PCM, fake sounddevice callbacks and fake
providers. Synthetic PCM here tests buffering, not stuttering or model efficacy.

The lifecycle increment fences retired reply generations, bounds pending agent
output to 8,000 samples (500 ms), paces fast TTS via an awaitable chunk callback,
reports timeline exhaustion/malformed PCM, and aborts source plus agent output on
stop even during inference. Normal completion drains accepted samples before
closing. See [CONTRACT.md](CONTRACT.md#playback-lifecycle-increment-october-10-softwareruntime-checks)
for timing provenance, cancellation, capacity and remaining measurement limits.

`--services off --play` still plays the caller recording; it generates no agent
response. Without `--play`, timestamps describe PCM receipt/duration and no device
opens. Scheduled sample indices and software cut positions are not acoustic
measurements. The [current-code runtime packet](../docs/proofs/playback-runtime/README.md)
records device source stop/restart and one real provider reply at `42b86d0`.
[Guttuu's later listening report](https://github.com/vinhbin/stutterturn/issues/3#issuecomment-6102558836)
passed source/reply audibility, explicit Stop during source and reply, and
clean restart on his demo laptop. Cancellation before audio followed by a
later audible reply also passed. Natural source resumption during an already
audible reply and acoustic timing remain untested. These are his reported
listening results; his raw run logs are still local.

## Files

| File | Purpose |
|---|---|
| `engine.py` | VAD, Smart Turn, turn logic, Gemini/ElevenLabs reply, run log |
| `run.py` | Command-line runs |
| `server.py` | HTTP + WebSocket per CONTRACT.md |
| `ws_client_check.py` | Minimal client to check the server |
| `playback.py` | `--play`: shared speaker timeline for the source and agent speech |
| `fetch_assets.py` | Pinned weights and source clips |
| `check_features.py` | Same clip through the benchmark's `predict()` and the agent; must match |
| `IMPLEMENTATION_STEPS.md` | Build steps and rules for this lane |

## Not covered

Live microphone input and phone transport are not implemented. The exploratory X1 candidate is available for replay but is not a promoted release. Earlier Windows device/CLI checks reported the driver's output latency; they did not measure acoustic delay. Natural source resumption while a reply is already audible, callback underrun telemetry and the provider-cap path remain unverified. The Vultr-hosted console streams source and generated reply audio over an authenticated WebSocket to Web Audio. Digital rendering was verified in Chromium; see the [hosted setup](../docs/vultr-backend.md) and [current comparison proof](../docs/proofs/long-replay-judge/verification.json). The local `--play` option still uses backend laptop speakers.
