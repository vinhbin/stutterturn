# First stock/patient replay: 5 block clips

> **Correction (Oct 10, after review of Niko's questions on PR #11): these runs used a faulty model input.** At commit `a229787` the engine opened a turn only when speech was confirmed (7 frames after it began) and kept just the last 6 frames as "pre-roll", so the model saw **no audio before the speech and missed the first speech frame**, not the documented 0.2 s pre-roll. Fixed on `guttuu/niko-review`. A dry rerun (no services) with the fixed input changes two stock results: **2_57** becomes `turn_complete` at 2.176 s (p 0.72, before the 2.82 s resume) and **5_150** becomes `turn_complete` at 0.512 s (p 0.82, before the 0.93 s resume). Stock would then decide early in **4 of 5** clips, not 2 of 5; patient still makes no early decision. The tables below are kept as recorded and are **superseded** by [2026-10-10-replay-v2](../2026-10-10-replay-v2/README.md) (same clips and configs, fixed engine `bcf50d1`).
>
> **Log timing footnote (PR #15):** in 3 of these logs `run_ended.t` is a few milliseconds earlier than the last `agent_audio_end` (`stock-77f2`: 9.375 vs 9.378, `patient-597f`: 8.469 vs 8.470, `stock-4c2b`: 9.234 vs 9.245), because the final sleep can wake early on Windows. The engine now clamps `run_ended.t` to the last event time; these logs are kept as recorded, so readers should use `max(run_ended.t, last event t)`. Replay v2 was recorded before that clamp too, but none of its 10 logs end before their last event (checked).

**Recorded:** Saturday Oct 10, 2026, about 2:58–3:00 PM EDT, by Guttuu's agent on a Windows 11 laptop (CPU). **Commit:** `a229787` on `guttuu/web-agent`. **Contract:** agent v0.1.

## What ran

```bash
# for each clip in the first 5 rows of benchmark/data/block_eval.csv, both configs:
agent\.venv\Scripts\python.exe agent/run.py --config stock   --source <clip> --services on
agent\.venv\Scripts\python.exe agent/run.py --config patient --source <clip> --services on
```

| | stock | patient |
|---|---|---|
| End-of-turn model | Smart Turn v3.2 CPU ONNX, SHA-256 `2bb02631…967e4f` | same |
| Model runs after | 0.2 s of silence | 1.0 s of silence |
| Threshold / fallback | p > 0.5 / 3.0 s silence | same |
| Reply / voice | Gemini `gemini-3.8-flash` (thinking off), ElevenLabs `eleven_flash_v2_5` | same |

Each run replays the real SEP-28k clip in real time (32 ms frames), then 5 s of silence. `t` is seconds from the first source sample. Logs: the 10 `.jsonl` files in this folder (format in `agent/CONTRACT.md`). About 360 ElevenLabs characters were used.

## Results

`gap_start` / `resume` are the block start and resumption from `benchmark/data/block_eval.csv`: **exploratory, energy-derived labels, not human-reviewed.**

| Clip | gap_start | resume | Config | First model check | Turn complete at | Speaker resumed after decision | Reply cancelled | First agent audio | Audible interruption |
|---|---|---|---|---|---|---|---|---|---|
| HeStutters_1_133 | 0.88 | 1.35 | stock | incomplete 1.280 (p 0.04) | 4.864 fallback | no | no | 7.203 | no |
| | | | patient | incomplete 2.880 (p 0.03) | 4.864 fallback | no | no | 7.046 | no |
| HeStutters_2_57 | 1.93 | 2.82 | stock | incomplete 2.176 (p 0.42) | 5.984 fallback | no | no | 7.938 | no |
| | | | patient | complete 4.000 (p 0.97) | 4.000 model | no | no | 6.125 | no |
| HeStutters_4_32 | 0.86 | 1.47 | stock | **complete 1.120 (p 0.96)** | 1.120 model | **yes (1.536)** | yes, before audible | 7.735 | no |
| | | | patient | incomplete 3.008 (p 0.01) | 4.992 fallback | no | no | 6.938 | no |
| HeStutters_5_123 | 0.50 | 1.06 | stock | **complete 0.768 (p 0.95)** | 0.768 model | **yes** | yes, before audible | 6.969 | no |
| | | | patient | incomplete 3.040 (p 0.01) | 5.024 fallback | no | no | 6.672 | no |
| HeStutters_5_150 | 0.54 | 0.93 | stock | incomplete 0.512 (p 0.37) | 6.016 fallback | no | no | 8.313 | no |
| | | | patient | incomplete 1.312 (p 0.15) | 6.016 fallback | no | no | 7.750 | no |

Service timing across the 10 runs: Gemini reply 1.44–2.50 s, ElevenLabs first audio 0.22–0.25 s after the request.

## What this shows

- In **2 of 5 clips, stock decided "complete" inside the labelled block**, before the speaker resumed (4_32, 5_123). Patient did not decide early in any of these 5 clips.
- **Neither early decision became audible.** The speaker resumed about 0.3–0.4 s later, before Gemini answered, and the reply was cancelled. In this pipeline the reply delay (about 1.5–2.5 s) hid the premature decision.
- That changes with pipeline speed: a faster reply path, or a block longer than the reply delay, would turn the same decision into audible speech over the caller. Not tested here.
- Most runs (7 of 10) ended by the 3 s silence fallback, so first agent audio came 6–8 s into each run.

## Limits

- 5 clips, one run each, one show (HeStutters). No rates or percentages should be computed from this.
- Labels are exploratory, not human-reviewed (F3/F4 not consumed yet).
- SEP-28k clips are 3 s excerpts cut at fixed times, so the clip's end is usually not a real end of turn. That is why the model often says "incomplete" at the end and the fallback decides. Completed-turn delay cannot be judged from these clips.
- Agent audio timing is when the first speech sample was scheduled to play; laptop speaker delay is not measured. Service latency varies run to run.
- Patient's 1.0 s setting is provisional. In 2_57 patient decided earlier than stock (4.000 vs 5.984 fallback) because its later model check saw more silence; this is expected from the design, not a finding.
- No candidate model, live microphone or phone path was tested.
