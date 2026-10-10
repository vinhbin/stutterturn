# Agent contract

**Owner: Guttuu** · **Version: 0.1 (PROPOSED)** · **Status: nothing below is implemented yet.**

This is the interface between the voice agent (`agent/`) and its consumers: Vinh's demo UI (`web/demo-ui/adapter.js`), Kareem's judges page and Niko's evaluation (E1). Consumers may build against it now. Each section is marked **proposed** until a committed run proves it, then **implemented** with the commit. Breaking changes bump the version and are announced in issue #2 first.

## What a run is

One run replays **one real source recording** through **one configuration**, in a fresh session, and records what the agent decided and when it was audible.

```
source WAV (16 kHz mono, real time, 20 ms frames)
  -> VAD (Silero) -> end-of-turn model (Smart Turn v3.2 ONNX, or a candidate export)
  -> on "complete": Gemini reply -> ElevenLabs speech -> agent audio out
```

- The source keeps playing to its end after a decision; it is a recording and cannot be interrupted. Overlap is measured instead.
- After the source ends, 5 s of silence are fed so a late decision or a no-response can be observed.
- Nothing is imitated or synthesized on the caller side. Sources are SEP-28k clips fetched by `benchmark/scripts/download_clips.py`; audio is never committed.

## Time origin (proposed)

`t` = seconds since the **first sample of the source recording** entered the pipeline, from a monotonic clock. Source time is `t + source_offset_s` (0 unless a clip is replayed from an offset), so `t` lines up directly with annotation fields `block_onset_s`, `resumption_s` and `turn_end_s` in `benchmark/annotations/`.

## Configurations (proposed)

| id | Model | Turn logic | available |
|---|---|---|---|
| `stock` | Smart Turn v3.2 CPU ONNX, upstream preprocessing, `p > 0.5` = complete | Model runs when VAD reports 0.2 s of silence; if incomplete, waits for more speech or a 3.0 s silence fallback (Pipecat's `LocalSmartTurnAnalyzerV3` defaults) | after first stock run |
| `patient` | Same model and threshold | Longer wait before acting. **Exact setting fixed after the first runs** and reported in `GET /configurations` and in every run log, so the on-screen label can state it precisely | after first patient run |
| `candidate` | Niko's export `stutterturn-v{N}.onnx` (see `model/CONTRACT.md`) | Same turn logic as `stock` | `false` until Niko's handoff; never faked |

`patient` is a waiting configuration, not a trained model. The UI must not present `candidate` when `available` is `false`.

## Running it (proposed)

```bash
pip install -r agent/requirements.txt
python agent/server.py            # serves http://127.0.0.1:8765
python agent/run.py --config stock --source HeStutters_2_57.wav   # one run, no server
```

Keys come from `agent/.env` (`GEMINI_API_KEY`, `ELEVENLABS_API_KEY`); see `agent/.env.example`. Never commit `.env`.

## HTTP (proposed)

| Request | Response |
|---|---|
| `GET /v0/health` | `{"ok": true, "contract": "0.1", "commit": "<sha>"}` |
| `GET /v0/configurations` | `[{id, label, detail, available, note, model, model_sha256, params}]`; matches the UI's `getConfigurations()` shape |
| `GET /v0/sources` | `[{source_id, file, duration_s, category, rights_note}]`; only clips present locally |
| `GET /v0/runs/{run_id}` | The saved run log (JSON lines) |

## WebSocket `ws://127.0.0.1:8765/v0/ws` (proposed)

One socket can carry several runs one after another; one run at a time.

**Client to agent**

```json
{"type": "start", "config": "stock", "source": "HeStutters_2_57.wav", "client_ref": "optional"}
{"type": "stop", "run_id": "20261010T142301Z-stock-a1b2"}
```

**Agent to client.** Every message carries `v`, `run_id` and `seq`, which increases by one per run.

```json
{"v":"0.1","type":"run_started","run_id":"20261010T142301Z-stock-a1b2","seq":0,
 "config":"stock","params":{...},"model":"smart-turn-v3.2-cpu","model_sha256":"...",
 "source":{"source_id":"HeStutters_2_57.wav","duration_s":3.0,"source_offset_s":0},
 "commit":"<sha>","t0_wall":"2026-10-10T18:23:01.123Z"}

{"v":"0.1","type":"event","run_id":"...","seq":7,"t":1.94,"kind":"decision",
 "name":"turn_complete","model":"smart-turn-v3.2-cpu","prob":0.81,"threshold":0.5,
 "trigger":"smart_turn","detail":"..."}

{"v":"0.1","type":"run_ended","run_id":"...","seq":42,"t":8.02,"reason":"completed",
 "summary":{...},"log":"agent/runs/<run_id>.jsonl"}

{"v":"0.1","type":"error","run_id":"... or null","seq":-1,"message":"..."}
```

`kind` uses the four values the UI already handles; `name` says exactly what happened.

| kind | name | Meaning |
|---|---|---|
| `state` | (field `state`: `speaking`, `silence`, `holding`, `agent`) | Display state. `holding` = model ran and said incomplete. Carries `prob` and `model` when known (the earlier proposed `{t, state, prob, model}` fields) |
| `info` | `speech_start`, `speech_stop` | VAD on the source |
| `decision` | `turn_incomplete` | Model ran, `prob <= threshold`; agent keeps waiting |
| `decision` | `turn_complete` | Agent decides the caller finished. `trigger`: `smart_turn` or `fallback_timeout` |
| `info` | `response_requested` | Reply generation started (Gemini) |
| `audible` | `agent_audio_start` | **First agent audio sample starts playing**; see measurement note |
| `audible` | `agent_audio_end` | Agent audio finished or was cut |
| `info` | `speaker_resumed` | Source speech starts again after a `turn_complete` |
| `info` | `cancelled` | Reply dropped because the speaker resumed. `before_audible`: `true` if no agent audio had played |
| `audible` | `overlap` | Agent audio and source speech audible at the same time: an audible interruption. `overlap_s` given at `agent_audio_end` |
| `info` | `no_response` | Source and trailing silence ended with no `turn_complete` |
| `info` | `timeout` | A service call (Gemini or ElevenLabs) exceeded its limit; names the service |

**Measurement note for `agent_audio_start`.** In replay mode the agent owns the output timeline: `t` is when the first decoded speech sample is scheduled to play, which is when it would reach the listener. Service latency (Gemini plus ElevenLabs time to first audio) is therefore included, and each part is reported separately in the summary. Speaker playback of the demo laptop adds a device delay that is not measured.

## Run log and summary (proposed)

Each run writes `agent/runs/<run_id>.jsonl`: the `run_started` line, every event, then `run_ended`. Run logs hold no audio, keys or personal data. `agent/runs/` is gitignored; runs used as evidence are copied to `agent/evidence/` and committed with the command that produced them.

`summary` in `run_ended`:

```json
{"first_turn_complete_t": 1.94, "trigger": "smart_turn",
 "first_agent_audio_t": 3.21, "llm_latency_s": 0.71, "tts_first_audio_s": 0.48,
 "speaker_resumed_after_decision": true, "cancelled": false,
 "audible_interruption": true, "overlap_s": 0.62,
 "no_response": false, "timeouts": []}
```

Evaluation compares `first_turn_complete_t` and `first_agent_audio_t` against human annotations; the agent does not judge whether a decision was premature. That is E1's job (Niko) using reviewed labels.

## Mapping to the demo UI adapter

| UI interface (`web/demo-ui/README.md`) | Contract |
|---|---|
| `getConfigurations()` | `GET /v0/configurations` |
| `start(configId, handlers)` returns `{runId, sourceRecording}` | send `start`, resolve on `run_started` |
| `handlers.onEvent({t, kind, state, prob, model, detail})` | each `event` message, unchanged field names |
| `handlers.onEnd()` / `onError(msg)` | `run_ended` / `error` |
| `stop()` | send `stop` |
| UI extension 1 to 5 (run id, time origin, decision vs audible, source id, run control) | all covered above |

## Open items

- Exact `patient` setting (first runs).
- Whether replay also plays audio through the laptop speakers for the live demo (planned: optional flag, timing unchanged).
- Microphone (live caller) mode: out of scope for 0.1. Demo uses recorded sources, labelled as recordings.
- Phone transport: not attempted; web only.
