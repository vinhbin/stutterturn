# StutterTurn agent

**Owner: Guttuu.** Replays a real SEP-28k recording through VAD + an end-of-turn model (stock, patient or Niko's candidate), optionally answers with Gemini + ElevenLabs, and logs when it decided and when it was audible. Interface: [CONTRACT.md](CONTRACT.md). First evidence: [evidence/2026-10-10-first-replay](evidence/2026-10-10-first-replay/README.md).

## Setup (Windows, Python 3.11)

```bash
uv venv agent\.venv --python 3.11
uv pip install --python agent\.venv\Scripts\python.exe -r agent/requirements.txt
agent\.venv\Scripts\python.exe agent/fetch_assets.py 5
```

`fetch_assets.py` downloads Smart Turn v3.2 INT8 and FP32 ONNX (`pipecat-ai/smart-turn-v3` at `f766f81`) and Silero VAD v5.1.2 into `agent/models/`, checks every SHA-256 hash, and fetches N block + N fluent SEP-28k clips into `benchmark/audio/`. None of these files are committed.

For real replies, copy `agent/.env.example` to `agent/.env` and fill in `GEMINI_API_KEY` and `ELEVENLABS_API_KEY`. `agent/.env` is gitignored; never put keys in `.env.example`. Optional: `GEMINI_MODEL` (default `gemini-3.8-flash`), `ELEVENLABS_VOICE_ID`, `ELEVENLABS_MAX_CHARS` (default 3000 per process, protects credits), `CANDIDATE_MODEL` (path to Niko's ONNX export; its metadata JSON beside it supplies `sha256` and `threshold`, or set `CANDIDATE_SHA256`). A model whose hash does not match is refused.

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

Live microphone input, phone transport and a real candidate model have not been tested. Speaker playback works on the Windows dev laptop (Realtek speakers); its acoustic delay is reported by the driver, not measured, and other demo machines or devices have not been tried.
