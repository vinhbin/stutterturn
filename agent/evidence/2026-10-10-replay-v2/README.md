# Stock/patient replay v2: 5 block clips, fixed model input

**Recorded:** Saturday Oct 10, 2026, about 3:45–3:49 PM EDT, Windows 11 laptop (CPU). **Commit:** `bcf50d1` on `guttuu/niko-review` (clean; every log is stamped `bcf50d1`). **Contract:** agent v0.1. **Supersedes** [2026-10-10-first-replay](../2026-10-10-first-replay/README.md), whose model input was faulty (no pre-roll, first speech frame missing).

## What ran

```bash
# for each clip in the first 5 rows of benchmark/data/block_eval.csv, both configs:
agent\.venv\Scripts\python.exe agent/run.py --config stock   --source <clip> --services on
agent\.venv\Scripts\python.exe agent/run.py --config patient --source <clip> --services on
```

| | stock | patient |
|---|---|---|
| Model | `stock-int8`, Smart Turn v3.2 CPU INT8, SHA-256 `2bb02631…967e4f` | same |
| Model input | 0.192 s pre-roll + current turn, last 8 s | same |
| Model runs after | 0.224 s of silence (0.2 s rounded up to 32 ms frames) | 1.024 s (1.0 s rounded up) |
| Threshold / fallback | p > 0.5 / 3.0 s silence | same |
| Reply / voice | Gemini `gemini-3.8-flash` (thinking off), ElevenLabs `eleven_flash_v2_5` | same |

Each run replays the real clip in real time, then **5 s of synthetic silence**; fallback decisions on these 3 s clips happen during that padding. `t` is seconds from the first source sample. Logs: the 10 `.jsonl` files here. About 380 ElevenLabs characters used.

## Results

`gap_start` / `resume` from `benchmark/data/block_eval.csv`: **exploratory, energy-derived labels, not human-reviewed.** "VAD resume" is when the agent's own VAD heard speech again after its decision.

| Clip | gap_start | resume | Config | First model check | Turn complete at | VAD resume | Reply cancelled | First agent audio | Audible interruption |
|---|---|---|---|---|---|---|---|---|---|
| 1_133 | 0.88 | 1.35 | stock | incomplete 1.280 (p 0.03) | 4.864 fallback | – | no | 6.578 | no |
| | | | patient | incomplete 2.880 (p 0.03) | 4.864 fallback | – | no | 6.828 | no |
| 2_57 | 1.93 | 2.82 | stock | **complete 2.176 (p 0.72)** | 2.176 model | not heard* | no | 4.078 | no (see note) |
| | | | patient | complete 4.000 (p 0.97) | 4.000 model | – | no | 6.406 | no |
| 4_32 | 0.86 | 1.47 | stock | **complete 1.120 (p 0.85)** | 1.120 model | 1.536 | yes, before audible | 6.735 | no |
| | | | patient | incomplete 3.008 (p 0.01) | 4.992 fallback | – | no | 6.703 | no |
| 5_123 | 0.50 | 1.06 | stock | **complete 0.768 (p 0.95)** | 0.768 model | 1.088 | yes, before audible | 6.875 | no |
| | | | patient | incomplete 3.040 (p 0.01) | 5.024 fallback | – | no | 7.078 | no |
| 5_150 | 0.54 | 0.93 | stock | **complete 0.512 (p 0.82)** | 0.512 model | 1.472 | yes, before audible | 4.235 | no |
| | | | patient | incomplete 1.312 (p 0.11) | 6.016 fallback | – | no | 9.406 | no |

\* 2_57: the labelled resume at 2.82 s leaves only 0.18 s of speech before the clip ends at 3.0 s, shorter than the 0.2 s VAD start time, so the agent never registered the resumption. Its reply played at 4.078 s, after the recording ended; whether that would have overlapped the speaker cannot be observed from a 3 s clip.

Service timing: Gemini 1.38–3.17 s, ElevenLabs first audio 0.20–0.33 s after the request.

## What this shows

- **Stock decided "complete" before the labelled resume in 4 of 5 clips** (2_57, 4_32, 5_123, 5_150). Patient did not decide before the labelled resume in any of these 5.
- **None of those early decisions became audible in these runs.** In 3 clips the agent heard the speaker resume 0.32–0.96 s after its decision and cancelled the reply before any audio; in 2_57 the recording ended first (note above).
- The reply delay (Gemini plus TTS, about 1.6–3.5 s) is what kept the early decisions silent. A faster reply path or a longer block would make them audible; not tested.
- Patient's longer wait avoided the early decisions here but answered later: its first agent audio came at 6.4–9.4 s, mostly via the 3 s fallback during synthetic padding.

## Limits

- 5 clips, one run each, one show (HeStutters). Do not compute rates from this.
- Labels are exploratory, not human-reviewed. 5_150's stock decision at 0.512 s precedes the labelled gap start (0.54 s): the energy labels and the agent's Silero VAD disagree about where the pause begins.
- SEP-28k clips are 3 s excerpts, usually ending mid-turn, so completed-turn delay cannot be judged.
- Agent audio time is when the first speech sample was scheduled to play; speaker delay not measured. Service latency varies run to run.
- INT8 only here; the `stock_fp32` comparator was not run with services. Patient 1.0 s is provisional. No candidate, live microphone or phone path tested.
