# Agent contract

**Owner: Guttuu** · **Version: 0.1** · **Status: implemented on `guttuu/web-agent` (engine `8e47dad`, services `a229787`, server `18229dc`)** except where a section still says proposed. Current evidence: `agent/evidence/2026-10-10-replay-v2/` (fixed model input, `bcf50d1`; supersedes `2026-10-10-first-replay/`).

This is the interface between the voice agent (`agent/`) and its consumers: Vinh's demo UI (`web/demo-ui/adapter.js`), Kareem's judges page and Niko's evaluation (E1). Consumers may build against it now. Each section is marked **proposed** until a committed run proves it, then **implemented** with the commit. Breaking changes bump the version and are announced in issue #2 first.

## What a run is

One run replays **one real source recording** through **one configuration**, in a fresh session, and records what the agent decided and when it was audible.

```
source WAV (16 kHz mono, real time, 32 ms frames = 512 samples, as Silero v5 requires)
  -> VAD (Silero) -> end-of-turn model (Smart Turn v3.2 ONNX, or a candidate export)
  -> on "complete": Gemini reply -> ElevenLabs speech -> agent audio out
```

- The source keeps playing to its end after a decision. Explicit stop/reset aborts both source and agent output. Overlap is inferred from the scheduled timeline, not measured acoustically.
- After the source ends, 5 s of silence are fed so a late decision or a no-response can be observed.
- Nothing is imitated or synthesized on the caller side. Sources are SEP-28k clips fetched by `benchmark/scripts/download_clips.py`; audio is never committed.

## Time origin (implemented)

`t` = seconds since the **first sample of the source recording** entered the pipeline, from a monotonic clock. Source time is `t + source_offset_s` (0 unless a clip is replayed from an offset), so `t` lines up directly with annotation fields `block_onset_s`, `resumption_s` and `turn_end_s` in `benchmark/annotations/`.

## Configurations (implemented)

| id | Model | Turn logic | available |
|---|---|---|---|
| `stock` | `stock-int8`: Smart Turn v3.2 CPU INT8 ONNX, upstream preprocessing, `p > 0.5` = complete | Model runs when VAD reports 0.2 s of silence; if incomplete, waits for more speech or a 3.0 s silence fallback (Pipecat's `LocalSmartTurnAnalyzerV3` defaults) | yes |
| `patient` | Same model and threshold | Model runs only after **1.0 s** of silence (stock 0.2 s); same 3.0 s fallback. Provisional; reported in `GET /v0/configurations` `detail` and every run log `params`. Label text: "Same model and threshold; acts only after 1.0 s of silence (stock: 0.2 s). A waiting configuration, not a trained model" | yes (1.0 s, provisional) |
| `stock_fp32` | `stock-fp32`: the unquantized export `smart-turn-v3.2-gpu.onnx` (runs on CPU) | Same turn logic as `stock` | yes |
| `candidate` | Niko's export `stutterturn-v{N}.onnx` (see `model/CONTRACT.md`) | Same turn logic as `stock`; threshold from its metadata | `false` until Niko's handoff; never faked |

`patient` is a waiting configuration, not a trained model. The UI must not present `candidate` when `available` is `false`.

**Comparator.** Candidates are compared against `stock_fp32`, not INT8 (`model/CONTRACT.md` 5.4): INT8 and FP32 probabilities differ by a lot on some clips (`HeStutters_0_26`: 0.23 vs 0.83 on the whole clip), so INT8-vs-candidate would mix quantization with training.

**Model hashes (implemented).** The agent refuses to load any model whose SHA-256 differs from its expected value: pinned values for `stock-int8` (`2bb02631…`) and `stock-fp32` (`ab8dc64b…`); for `candidate`, the `sha256` in the metadata JSON beside the ONNX file (same name, `.json`, schema in `model/CONTRACT.md` 5), or `CANDIDATE_SHA256` if there is no metadata file. A mismatching candidate is listed with `available: false` and refused by `start`.

**Model input (implemented).** The model sees the **current turn's audio**: 0.2 s of pre-roll before the turn's first speech frame, then everything since, up to and including the frame on which the check runs; the last 8 s are used (left zero-padded if shorter). A turn opens at the first speech start and closes when the speaker resumes after a `turn_complete`; the resumed speech starts a new turn with its own pre-roll. Agent audio is never part of the input. This differs from the offline benchmark, which feeds the clip from its start: the two inputs are identical only when the clip's first speech segment starts within 0.2 s of the clip start and no turn reset happens before the check. `input_s` on each decision gives the input length. The preprocessing itself matches the benchmark exactly: `python agent/check_features.py` (same clip, benchmark `predict()` vs agent) gave zero difference in features and probabilities on 10 clips × both stock models.

**Check schedule.** One model check per pause, when silence reaches `vad_stop_s` (rounded up to whole 32 ms frames: 0.2 s → 7 frames = 0.224 s, which is the `silence_s` reported), then the `fallback_s` timeout. No re-checks during continued silence.

**Synthetic trailing silence.** Every run appends 5 s of digital zeros after the source. `fallback_timeout` and `no_response` outcomes on 3 s clips therefore happen during that padding; cite them as such (the offline benchmark treats them as censored).

## Running it (implemented)

```bash
pip install -r agent/requirements.txt
python agent/server.py            # serves http://127.0.0.1:8765; add --services off for no Gemini/ElevenLabs
python agent/run.py --config stock --source HeStutters_2_57.wav   # one run, no server
```

Keys come from `agent/.env` (`GEMINI_API_KEY`, `ELEVENLABS_API_KEY`); see `agent/.env.example`. Never commit `.env`.

## HTTP (implemented)

| Request | Response |
|---|---|
| `GET /v0/health` | `{"ok": true, "contract": "0.1", "commit": "<sha>"}` |
| `GET /v0/configurations` | `[{id, label, detail, available, note, model, model_sha256, params}]`; matches the UI's `getConfigurations()` shape |
| `GET /v0/sources` | `[{source_id, file, duration_s, category, rights_note}]`; only clips present locally. `file` is a **bare file name** (no `/` or `\`, e.g. `HeStutters_4_32.wav`, located in `benchmark/audio/`) and is the value clients send as `source` in `start` |
| `GET /v0/runs/{run_id}` | The saved run log (JSON lines) |

## WebSocket `ws://127.0.0.1:8765/v0/ws` (implemented)

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
 "commit":"<sha>","t0_wall":"2026-10-10T18:23:01.123Z","services":"on"}

{"v":"0.1","type":"event","run_id":"...","seq":7,"t":1.94,"kind":"decision",
 "name":"turn_complete","model":"smart-turn-v3.2-cpu","prob":0.81,"threshold":0.5,
 "trigger":"smart_turn","detail":"..."}

{"v":"0.1","type":"run_ended","run_id":"...","seq":42,"t":8.02,"reason":"completed",
 "summary":{...},"log":"agent/runs/<run_id>.jsonl"}

{"v":"0.1","type":"error","run_id":"... or null","seq":-1,"message":"..."}
```

`run_ended.t` is never earlier than the last emitted event's `t`.

`kind` uses the four values the UI already handles; `name` says exactly what happened.

| kind | name | Meaning |
|---|---|---|
| `state` | (field `state`: `speaking`, `silence`, `holding`, `agent`) | Display state. `holding` = model ran and said incomplete. Carries `prob` and `model` when known (the earlier proposed `{t, state, prob, model}` fields) |
| `info` | `speech_start`, `speech_stop` | VAD on the source |
| `decision` | `turn_incomplete` | Model ran, `prob <= threshold`; agent keeps waiting |
| `decision` | `turn_complete` | Agent decides the caller finished. `trigger`: `smart_turn` or `fallback_timeout` |
| | (both decision events) | Also carry `model_id`, `prob`, `threshold`, `complete`, `silence_s` (silence included in the input when the check ran; for the fallback, silence elapsed), `infer_ms` (feature extraction + inference, milliseconds; `null` for the fallback) and `input_s` (model input length). These are the per-call fields of `model/CONTRACT.md` 7; `run_started.params` carries `time_origin: "source_audio_start"` and `pre_roll_s`. `infer_ms` measured about 180–220 ms on the Windows dev laptop, not the 25 ms reference from another machine |
| `info` | `response_requested` | Reply generation started (Gemini) |
| `audible` | `agent_audio_start` | First complete PCM sample accepted: scheduled output position with `--play`, receipt time without it; see measurement note |
| `audible` | `agent_audio_end` | Agent audio finished or was cut |
| `info` | `speaker_resumed` | Source speech starts again after a `turn_complete` |
| `info` | `cancelled` | Reply dropped because the speaker resumed. `before_audible` describes whether the accepted scheduled interval was empty at the cut, not an acoustic observation |
| `audible` | `overlap` | Scheduled agent interval overlaps resumed source speech. `overlap_s` given at `agent_audio_end`; late-chunk gaps and device delay limit this estimate |
| `info` | `no_response` | Source and trailing silence ended with no `turn_complete` |
| `info` | `timeout` | A service call (Gemini or ElevenLabs) exceeded its limit; names the service |
| `info` | `playback_error` | Output problem; `code` is `timeline_capacity`, `malformed_pcm`, `output_stalled`, or `device_cleanup`. Details are diagnostic, not proof of physical silence |

**Measurement note for `agent_audio_start`.** Without `--play`, `t` is first complete PCM receipt and end is receipt plus accepted sample duration; no output device is opened. With `--play`, `t` is the first accepted output sample index divided by 16,000. Both include provider delay, but neither measures when sound reaches a listener. The legacy `audible` kind and summary names remain for v0.1 consumer compatibility.

**Playback mode (`--play`, implemented).** `run.py --play` or `server.py --play` also plays the run on the machine's speakers: the source recording and the agent's speech are mixed on one 16 kHz timeline, where sample *i* plays *i*/16000 s after the run starts. In this mode `agent_audio_start` / `agent_audio_end` are positions on that timeline, so they line up with source times as a listener hears them. Agent speech starts no earlier than the device's next writable block (256 samples); a late TTS chunk is placed at the next playable position rather than dropped, and `summary.playback_late_chunks` counts these. On barge-in the agent's audio is silenced from the stop time. Both tracks share the device output latency, reported in `run_started.playback.reported_output_latency_s` (Realtek laptop speakers, MME: 0.096 s) but not measured acoustically. `run_started.playback` is `null` without `--play`, and `GET /v0/health` reports `playback: "on" | "off"`. Decisions and VAD events are unaffected by playback.

### Playback lifecycle increment (October 10; software/runtime checks)

The HTTP/WebSocket version remains **0.1**. Additive `timing.v: "playback-v1"`
identifies the following software provenance; it is not a claim of DAC or acoustic measurement:

- Starts and natural ends identify `basis: "scheduled_output_samples"` in play mode. Without playback they use `pcm_receipt` and `pcm_receipt_plus_duration` respectively.
- Cuts use `basis: "software_cut"`, the actual `accepted_cut_sample`, and `acoustic_stop_t: null`. Barge-in also records `requested_cut_sample`. The player clamps a cut to its next unsubmitted sample; buffers already handed to the device cannot be withdrawn by editing the timeline. The end event is bounded by the latest accepted audio, even while the provider is pending. A cut before scheduled start yields a zero-length interval at the scheduled start; the earlier cut sample remains explicit in provenance.
- `run_started.playback.stream_start_call_s` brackets the host call to start output. Host `t0` is set immediately before that call, after device construction. Source sample time, this host bracket and reported device latency remain distinct; no sample-to-DAC synchronization or callback-clock calibration is claimed.

`Player.begin_agent()` returns a generation token. The engine carries it through
all writes and cuts; old callbacks cannot modify a later reply. Cutting retires
the generation, while the next explicit begin clears the cut and admits a new
reply. Empty chunks do not begin an interval; an unmatched final PCM16 byte emits
`playback_error/malformed_pcm`. Complete samples already accepted may drain.

Pending agent output is bounded at **8,000 samples (500 ms)**, excluding the
initial scheduling offset; gaps inside the pending span count conservatively
toward the bound. `Player.add_agent` rejects a whole write on capacity exhaustion
without advancing `agent_next`. `Run` splits oversized chunks and awaits device
consumption on pending-capacity pressure, so a fast provider is paced. Total
timeline exhaustion remains a visible `timeline_capacity` error. The source plus
30-second allocated timeline remains finite. `Services.stream_tts` supports sync
callbacks and awaits awaitable callback results; injected service implementations
must likewise await the engine callback. Existing provider timeouts still apply.

Stop invalidates reply callbacks, cancels provider work, silences both software
tracks and attempts device abort/close immediately. It releases a pending model
await and discards the result; native inference can continue in its worker thread.
Cached model prediction is serialized so restart does not concurrently reuse its
feature extractor. Normal completion waits for the output callback to consume the
source/accepted-agent tail and closes the device before `run_ended`. A stalled
callback produces `output_stalled`; device cleanup errors produce `device_cleanup`
and `summary.playback_device_errors`. Failed device operations cannot establish
that hardware released successfully. Stops do not wait for normal drain.

The fake-device tests verify software queue/cancellation behavior only. The
[current-code runtime packet](../docs/proofs/playback-runtime/README.md)
additionally records real-device open/drain/abort, source stop/restart, and one
real provider reply at `42b86d0`. Human listening and acoustic stop/flush remain
pending; the source-stop check did not stop an active generated reply. Callback
underruns/status and late-chunk overlap refinement remain unverified. Inference
still blocks source-frame processing while awaited in
an active run; its schedule has not been redesigned.

## Run log and summary (implemented)

Each run writes `agent/runs/<run_id>.jsonl`: the `run_started` line, every event, then `run_ended`. Run logs hold no audio or keys, but can contain generated reply text; review it before sharing. `agent/runs/` is gitignored; runs used as evidence are copied to `agent/evidence/` with the command that produced them. A stop during model loading can emit `model_sha256: null` because validation did not finish.

`summary` in `run_ended`:

```json
{"first_turn_complete_t": 1.94, "trigger": "smart_turn",
 "first_agent_audio_t": 3.21, "llm_latency_s": 0.71, "tts_first_audio_s": 0.48,
 "speaker_resumed_after_decision": true, "cancelled": false,
 "audible_interruption": true, "overlap_s": 0.62,
 "no_response": false, "timeouts": [], "reply_text": "...",
 "services": "on", "chars_used": 29, "turns": 2}
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

## Dry mode (implemented)

`--services off` skips Gemini and ElevenLabs: `turn_complete` is followed by `info/response_requested` with `detail: "services off"` and no generated reply; `first_agent_audio_t` is null and `services` is `off`. With `--play`, the source recording still plays. Without `--play`, no output device opens.

## Open items

- `patient` 1.0 s is provisional; Guttuu decides any change and records it in the evidence README.
- Hardware listening/stop/flush acceptance for the lifecycle increment above remains outstanding.
- Microphone (live caller) mode: out of scope for 0.1. Demo uses recorded sources, labelled as recordings.
- Phone transport: not attempted; web only.
