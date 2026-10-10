# F2 agent: implementation steps

**For:** whoever continues Guttuu's F2 work (human or a lower-effort model). Follow the steps in order. Every design decision is already made here; do not redesign. If a step's check fails and the fix is not obvious, stop and report to Guttuu with the exact command and output.

**Goal (PLAN.md row F2):** a runnable stock/patient voice agent that replays a real SEP-28k recording and saves a timing log: model decision, speech resumption, first audible response, cancellation, timeout, no response. Interface: [CONTRACT.md](CONTRACT.md) v0.1.

## Already done (Oct 10, Guttuu)

| Item | Where |
|---|---|
| Contract v0.1 proposed, pushed | `agent/CONTRACT.md`, commit `538dacf` on `guttuu/web-agent` |
| Key template, ignores | `agent/.env.example`, `agent/.gitignore` (`.env`, `runs/`, `models/`, `.venv/` stay local) |
| Python 3.11 venv with pinned deps | `agent/.venv`, from `agent/requirements.txt` |
| Model + VAD weights, SHA-256 verified | `python agent/fetch_assets.py` → `agent/models/smart-turn-v3.2-cpu.onnx`, `agent/models/silero_vad.onnx` |
| 10 real clips (5 block, 5 fluent) | `benchmark/audio/*.wav`, 16 kHz mono, about 3 s each |

## Rules (repo-enforced; read before writing code)

1. **Write only under `agent/`.** Branch `guttuu/web-agent`. Never edit `web/`, `model/`, `benchmark/` (read-only use is fine), `PLAN.md`, root `.gitignore` or root `README.md`.
2. **Secrets:** keys live only in `agent/.env`. Never print, log, commit or paste them in chat. Do not ask Guttuu to paste keys in chat; he edits `.env` himself.
3. **No fabricated evidence.** Never invent timings, results or "it works" claims. A dry run (no services) is not an audible run. Label everything with what actually ran.
4. **No imitated stuttering, no synthetic caller audio.** Callers are SEP-28k recordings only. Audio files are never committed.
5. **ElevenLabs credits are limited (about 10,000).** Use model `eleven_flash_v2_5`, one-sentence replies, and the per-process character cap in Step 3. Develop with `--services off` first. Do not batch-run TTS over many clips without Guttuu's OK.
6. **Commits:** small, owned paths only, message ends with the `Co-Authored-By` line the session gives you. Push to `origin guttuu/web-agent`. **Ask Guttuu before** opening a PR or commenting on GitHub issues. PRs use **Change / Validation / Remaining acceptance** and must not say `Closes #2`.
7. Use the venv for everything: `agent\.venv\Scripts\python.exe` (Windows). Stay on Python 3.11.

## Target file layout

```
agent/
  engine.py        Step 1-3: VAD, Smart Turn, turn logic, services, run + log
  run.py           Step 2: CLI, one run or a list of clips
  server.py        Step 5: HTTP + WebSocket per CONTRACT.md
  ws_client_check.py  Step 5: tiny client used to test the server
  README.md        Step 6: how to run
  runs/            local raw logs (gitignored)
  evidence/        committed evidence runs (Step 4)
```

## Step 1: `engine.py` core (no network)

### Constants

```python
SR = 16000
FRAME = 512                  # Silero v5 needs 512 samples at 16 kHz -> 32 ms frames
FRAME_S = FRAME / SR         # 0.032
TRAILING_SILENCE_S = 5.0     # fed after the source ends
CONTRACT_VERSION = "0.1"
```

Paths: `AGENT = dirname(abspath(__file__))`, models in `AGENT/models`, sources in `ROOT/benchmark/audio`, logs in `AGENT/runs`.

### Silero VAD wrapper (exact v5 ONNX interface)

```python
class SileroVAD:
    def __init__(self, path):
        so = ort.SessionOptions(); so.inter_op_num_threads = 1; so.intra_op_num_threads = 1
        self.sess = ort.InferenceSession(path, sess_options=so, providers=["CPUExecutionProvider"])
        self.reset()
    def reset(self):
        self.state = np.zeros((2, 1, 128), dtype=np.float32)
        self.context = np.zeros((1, 64), dtype=np.float32)
    def __call__(self, frame):            # frame: float32 shape (512,)
        x = np.concatenate([self.context, frame[None, :]], axis=1)   # (1, 576)
        out, self.state = self.sess.run(None, {"input": x, "state": self.state,
                                               "sr": np.array(SR, dtype=np.int64)})
        self.context = x[:, -64:]
        return float(out[0][0])           # speech probability
```

Speech frame = prob `>= 0.5`. Create a **new** `SileroVAD` per run (fresh session rule).

### Smart Turn wrapper (copy the benchmark preprocessing exactly)

Same as `benchmark/scripts/run_model_arm.py` `predict()`: keep the last 8 s (left zero-pad if shorter), `WhisperFeatureExtractor(chunk_length=8)` with `sampling_rate=16000, return_tensors="np", padding="max_length", max_length=8*16000, truncation=True, do_normalize=True`, input name `input_features` float32 `[1,80,800]`, output is already a probability. `complete = prob > threshold` (0.5). Load the session once per process (it is stateless); record `model_sha256` (hash the file once at startup).

`candidate` config: same wrapper, model path from env `CANDIDATE_MODEL` (Niko's `stutterturn-v{N}.onnx`). If unset or missing, `available: false` and `start` must refuse it with an `error`.

### Configurations

```python
CONFIGS = {
  "stock":   {"label": "Stock Smart Turn v3.2", "model": "smart-turn-v3.2-cpu",
              "vad_stop_s": 0.2, "vad_start_s": 0.2, "threshold": 0.5, "fallback_s": 3.0},
  "patient": {"label": "Patient (longer wait, same model)", "model": "smart-turn-v3.2-cpu",
              "vad_stop_s": 1.0, "vad_start_s": 0.2, "threshold": 0.5, "fallback_s": 3.0},
  "candidate": {... same as stock, model from CANDIDATE_MODEL ...},
}
```

`patient` value `vad_stop_s = 1.0` is **provisional**. Keep it unless Step 4 shows a problem; whatever is used must appear in `params` in `run_started` and in `GET /v0/configurations` `detail`, worded exactly, e.g. "Same model and threshold; acts only after 1.0 s of silence (stock: 0.2 s)".

### Turn state machine (per run)

Variables: `in_speech=False`, `speech_run=0` frames, `silence_run=0` frames, `turn_audio` (list of frames since the current turn's first speech, plus 0.2 s pre-roll), `turn_index=0`, `decided=False` for the current turn, `checked_this_pause=False`.

For each frame (source frames, then trailing silence frames):

1. `p = vad(frame)`; append frame to a rolling pre-roll buffer (last 0.2 s) and, if a turn is open, to `turn_audio`.
2. **Speech start:** if `p >= 0.5`, `speech_run += 1`, `silence_run = 0`. When `not in_speech and speech_run * FRAME_S >= vad_start_s`: `in_speech = True`, emit `info/speech_start` with `t` of the **first** speech frame of that run (not the frame that crossed the threshold); emit `state speaking`. If no turn is open, open one (`turn_audio = pre-roll + frames so far`). If the current turn was already decided (`turn_complete` emitted), emit `info/speaker_resumed`, handle barge-in (below), then open a new turn (`turn_index += 1`).
3. **Silence:** if `p < 0.5`, `silence_run += 1`, `speech_run = 0`. When `in_speech and silence_run * FRAME_S >= vad_stop_s`: `in_speech = False`, emit `info/speech_stop` (t = first silent frame), `state silence`. If the turn is open and not decided and `not checked_this_pause`: run Smart Turn on `turn_audio`, `checked_this_pause = True`.
   - `prob > threshold`: emit `decision/turn_complete` (`trigger: "smart_turn"`, `prob`, `threshold`, `model`), mark decided, start the reply task (Step 3).
   - else: emit `decision/turn_incomplete` with `prob`, emit `state holding`.
4. **Fallback:** while silent, open turn, not decided, and `silence_run * FRAME_S >= fallback_s` (counted from the first silent frame): emit `decision/turn_complete` with `trigger: "fallback_timeout"`, `prob: null`, start the reply task.
5. Reset `checked_this_pause = False` whenever a new speech start happens.

End of input: if no `turn_complete` happened in the run, emit `info/no_response`. Wait for an in-flight reply task to finish (max 15 s) before `run_ended`.

### Real-time pacing and time

`t0 = time.monotonic()` just before the first frame. Frame `i` is processed no earlier than `t0 + i * FRAME_S` (sleep with `await asyncio.sleep(...)` when ahead; never sleep when behind). Event time for VAD/decisions = frame time `i * FRAME_S` of the frame named above. Event time for service events (`response_requested` result, `agent_audio_start`, `timeout`) = `time.monotonic() - t0` when it happened. Run Smart Turn via `await asyncio.to_thread(...)` so pacing catches up afterwards.

### Events, seq and logging

One `Run` object holds `run_id = f"{utc:%Y%m%dT%H%M%SZ}-{config}-{4 hex}"`, `seq` counter, an `asyncio.Queue` or callback for listeners, and the open log file `agent/runs/<run_id>.jsonl`. Every message is written to the log **and** sent to the listener. Message shapes are exactly as in CONTRACT.md (`v`, `type`, `run_id`, `seq`, `t`, `kind`, `name`, ...). Round `t` to 3 decimals. `run_started` includes `params`, `model`, `model_sha256`, `source` (`source_id`, `duration_s`, `source_offset_s: 0`), `commit` (`git rev-parse --short HEAD`, or `"unknown"`), `t0_wall` (UTC ISO with ms), and `services: "on"|"off"`.

### Step 1 check

```bash
agent\.venv\Scripts\python.exe -c "import sys; sys.path.insert(0,'agent'); import engine; print(engine.CONFIGS.keys())"
```

## Step 2: `run.py` CLI and dry runs

```bash
agent\.venv\Scripts\python.exe agent/run.py --config stock --source HeStutters_2_57.wav --services off
agent\.venv\Scripts\python.exe agent/run.py --config stock --all --services off
```

- `--source` takes a file name in `benchmark/audio/`; `--all` runs every local clip one after another (fresh run each).
- Print one line per event (`t kind name prob`) and the summary; print the log path.
- `--services off`: no Gemini/ElevenLabs. On `turn_complete` emit `info/response_requested` with `detail: "services off"` and nothing audible. The summary sets `first_agent_audio_t: null`, `services: "off"`.

**Check (must pass before Step 3):** 10 clips, both `stock` and `patient`, `--services off`. Every run has `run_started` first and `run_ended` last, `seq` increases by 1, `t` never decreases within VAD/decision events, and each run ends in `turn_complete` or `no_response`. Total time per clip is about 3 s + 5 s trailing silence. Commit Steps 1-2 now (`feat(agent): replay engine and CLI (dry runs)`), push.

## Step 3: services (Gemini reply + ElevenLabs voice)

Needs `agent/.env` with `GEMINI_API_KEY` and `ELEVENLABS_API_KEY` (Guttuu fills these). Load with `python-dotenv` from `agent/.env`. If a key is missing and `--services on`, fail with a clear message naming the missing variable (not its value).

Reply task (an `asyncio.Task`, started at `turn_complete`):

1. Emit `info/response_requested`.
2. **Gemini** (`google-genai` 2.29): turn audio → text.
   ```python
   client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
   wav = io.BytesIO(); sf.write(wav, turn_audio, SR, format="WAV", subtype="PCM_16")
   resp = await asyncio.wait_for(client.aio.models.generate_content(
       model=os.getenv("GEMINI_MODEL", "gemini-3.8-flash"),   # 2.5-flash is closed to new users (Oct 10)
       contents=[types.Part.from_bytes(data=wav.getvalue(), mime_type="audio/wav"), PROMPT],
       config=types.GenerateContentConfig(max_output_tokens=60, temperature=0.4,
           thinking_config=types.ThinkingConfig(thinking_budget=0))), timeout=10)
   text = (resp.text or "").strip()[:120]
   ```
   `PROMPT = "You are a helpful voice assistant on a phone line. The caller's audio is attached. Reply in one short sentence, at most 20 words. Never comment on how the caller speaks."`
   If the model name is rejected, list available models with `client.models.list()`, pick a current Flash model, set `GEMINI_MODEL` in `.env`, and note it in the run log params. Record `llm_latency_s`.
3. **ElevenLabs** streaming TTS (raw HTTP with aiohttp):
   ```
   POST https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream?output_format=pcm_16000
   headers: xi-api-key, Content-Type: application/json
   body: {"text": text, "model_id": "eleven_flash_v2_5"}
   ```
   `voice_id` = `ELEVENLABS_VOICE_ID` or, if empty, the first `voice_id` from `GET https://api.elevenlabs.io/v1/voices` (cache it per process). Read the response with `iter_chunked(3200)`. On the **first chunk**: emit `audible/agent_audio_start`, `state agent`, record `tts_first_audio_s` (from TTS request start). Total bytes / 2 / 16000 = agent audio duration; schedule `audible/agent_audio_end` at `agent_audio_start + duration` unless barged in. Timeout 10 s → `info/timeout` with `service: "elevenlabs"`.
4. **Credit guard:** module-level `chars_used`; refuse TTS when `chars_used + len(text) > int(os.getenv("ELEVENLABS_MAX_CHARS", "3000"))`, emit `info/timeout` with `service: "elevenlabs", detail: "local character cap reached"`. Print `chars_used` in the summary.

Barge-in (called from the state machine on `speaker_resumed`):
- reply task not yet audible → cancel the task, emit `info/cancelled` with `before_audible: true`;
- agent audio playing → emit `audible/overlap` at the resume time, stop agent audio after `vad_start_s` (barge-in detection delay), emit `audible/agent_audio_end` then, and `info/cancelled` with `before_audible: false`; `overlap_s` = stop time - first speech frame of the resumption.

Summary (in `run_ended`) exactly as in CONTRACT.md, plus `services`, `chars_used`, `turns` (count).

Optional, only if time allows: `--play` flag that also plays agent audio on the laptop speakers (`sounddevice`); timings unchanged.

**Check:** with keys set, one run: `run.py --config stock --source HeStutters_2_57.wav --services on`. Expect `response_requested`, then `agent_audio_start` within a few seconds, a non-empty reply text in the log (`detail`), and `chars_used` > 0. Commit (`feat(agent): Gemini reply and ElevenLabs audio timing`), push.

## Step 4: first evidence runs (stock vs patient)

Use the 5 block clips (`benchmark/data/block_eval.csv` first 5 rows; they have `gap_start` and `resume` = where the stutter block starts and the speaker resumes). For each clip run `stock` then `patient` with `--services on` (10 runs, about 1,000 TTS characters).

Save under `agent/evidence/2026-10-10-first-replay/`:
- the 10 `.jsonl` logs (copied from `agent/runs/`),
- `README.md`: exact command(s), commit SHA, configs and params, date/time, machine (Windows 11 laptop, CPU), and a table per clip: `gap_start`, `resume` (from block_eval.csv, **exploratory energy-derived labels, not human-reviewed**), stock `first_turn_complete_t` / `first_agent_audio_t` / `audible_interruption`, same for patient.
- State limits plainly: 5 clips, exploratory labels, one run each, service latency varies, laptop speaker delay not measured. Do not compute percentages or claim improvement.

If `patient` with 1.0 s never responds within 8 s on fluent clips, or behaves identically to stock, report that; do not tune silently. Guttuu decides any change and it gets recorded in the README.

Commit (`docs(agent): first stock/patient replay evidence`), push.

## Step 5: `server.py` (HTTP + WebSocket)

aiohttp app on `127.0.0.1:8765` implementing CONTRACT.md: `GET /v0/health`, `/v0/configurations`, `/v0/sources` (local `benchmark/audio/*.wav`; `category` from block/fluent eval CSVs, `rights_note: "SEP-28k podcast audio; rights remain with owners; not redistributed"`), `/v0/runs/{run_id}`, WebSocket `/v0/ws` with `start` / `stop`. One run at a time per socket; a second `start` while running → `error`. Add CORS header `Access-Control-Allow-Origin: *` on HTTP routes so the demo UI served on another localhost port can call them. `--services on|off` flag on the server too.

`ws_client_check.py`: connects, sends `start` for `stock` and one clip, prints messages until `run_ended`, exits non-zero on `error`.

**Check:** server running in one terminal, `ws_client_check.py` in another; output matches the CLI run for the same clip (same event names, similar times). `curl http://127.0.0.1:8765/v0/configurations` lists three configs with `candidate.available == false` (unless `CANDIDATE_MODEL` is set). Commit (`feat(agent): HTTP/WebSocket server per contract v0.1`), push.

## Step 6: contract update, README, PR

1. Update `CONTRACT.md`: frames are 32 ms (512 samples), not 20 ms; add `services: "on"|"off"` and `--services off` dry mode; mark each implemented section **implemented (commit `<sha>`)**; keep anything not built marked proposed. Bump to 0.2 only if a field changed incompatibly; adding fields is fine in 0.1.
2. `agent/README.md`: setup (`uv venv agent\.venv --python 3.11`, `uv pip install -r agent/requirements.txt`, `fetch_assets.py`, copy `.env.example` to `.env`), the CLI and server commands, where logs go.
3. Ask Guttuu, then open the PR `guttuu/web-agent` → `main` with **Change / Validation / Remaining acceptance**: commands, commit, evidence folder link, what was not tested (live mic, phone, candidate model, speaker delay), blocker owners (Niko for candidate export). No `Closes #2`.
4. Ask Guttuu, then post a short note in issue #2 for Vinh (adapter can be implemented against contract v0.1, server command) and Niko (`CANDIDATE_MODEL` hook; `run.py --all --services off` for model-only batch runs).

## When to stop and ask Guttuu

- Any step check fails twice.
- A choice not covered here (new dependency outside `agent/requirements.txt` other than `sounddevice`, changing configs, touching files outside `agent/`).
- Anything that would post to GitHub, spend many ElevenLabs credits, or need a new account.
