# StutterTurn Kill Test — RESULTS

> **Superseded for current claims (Niko, Oct 10, 19:00 EDT). This report is kept as recorded.** It is the afternoon **exploratory** kill test: stock INT8 only, energy-derived labels, all shows mixed with no held-out split, and a different machine. The current development evidence is:
> - [`docs/model-results-2026-10-10.md`](../docs/model-results-2026-10-10.md): stock INT8 vs FP32, the threshold and wait trade-offs on show-separated dev items, and both training outcomes;
> - [`docs/training-report-2026-10-10.md`](../docs/training-report-2026-10-10.md);
> - the eval pipeline in [`specs/`](specs/).
>
> Numbers below (for example the threshold results in §5) are on the exploratory clip sets and must not be quoted as current results. INT8 probabilities differ across platforms (`specs/eval-runner-v1.md`). The reserved test set stays sealed (D-009).

Run date: 2026-10-10. Machine: Windows 11 Home, Python 3.12.10, ffmpeg 9.0.1, RTX 3060 Ti 8GB (all inference was CPU), 49 GB free disk. ELEVENLABS_API_KEY present; NO Gemini key.
Work dir: `C:\Users\Binep\empty codex 2\stutterturn-killtest` — scripts in `scripts/`, eval CSVs and raw results in `data/`, clips in `audio/`, model repo in `smart-turn/`.

STATUS: COMPLETE. Every number below is measured on real SEP-28k podcast audio of people who stutter. Nothing simulated or fabricated; no stuttered speech was imitated.

## 1. License verdict (SEP-28k)

- Repo: github.com/apple/ml-stuttering-events-dataset. Downloaded `SEP-28k_labels.csv` (28,177 label rows), `SEP-28k_episodes.csv` (385 rows), `LICENSE.md`, `README.md` from raw.githubusercontent.com on 2026-10-10.
- **Dataset license, verbatim from README.md:** "The SEP-28k dataset is licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0). To view a copy of this license, visit https://creativecommons.org/licenses/by-nc/4.0/."
- **Code license (LICENSE.md, verbatim core grant):** "Apple grants you a personal, non-exclusive license, under Apple's copyrights in this original Apple software ... to use, reproduce, modify and redistribute the Apple Software, with or without modifications, in source and/or binary forms; provided that if you redistribute the Apple Software in its entirety and without modifications, you must retain this notice..." (AS IS, no warranty).
- README: "Audio files are not part of this released dataset but may be downloaded using URLs provided in the `*_episodes.csv` files. Original copyright remains with the podcast owners."
- **What CC BY-NC 4.0 permits:** share and adapt the annotations for NonCommercial purposes with attribution and indication of changes. A hackathon benchmark/demo (judged, non-commercial, nothing sold) fits; cite Lea et al., ICASSP 2021. Podcast audio copyright stays with the podcast owners — use for the benchmark, do not redistribute raw audio publicly.
- **Verdict: usable for the hackathon benchmark/demo with attribution. Not usable commercially without a different data source.**

## 2. Data acquisition

- Searched Hugging Face BEFORE downloading podcasts, as planned. Found **`miosipof/sep28k_full`**: an audiofolder of individual WAVs named `{Show}_{EpId}_{ClipId}.wav` — 28,177 SEP-28k podcast clips (all 8 shows; exactly matches the label row count) + 4,144 FluencyBank. 16 kHz mono, 3.00 s each: the official clip extraction, already done. **No episode downloads needed; 0 dead podcast links encountered because that path was skipped entirely.**
- Candidate selection from official labels (quality gate: excluded clips with >=2 votes on Unsure/PoorAudioQuality/DifficultToUnderstand/Music/NoSpeech):
  - BLOCK (Block >= 2): 3,116 qualifying (481 unanimous). Downloaded top 500, unanimous first.
  - FLUENT (NoStutteredWords >= 2 and Prolongation/Block/SoundRep/WordRep/Interjection all < 2): 11,340 qualifying. Downloaded top 300.
  - 0/800 missing on the mirror; all 800 downloaded (72 MB; 2 transient Windows file-lock errors succeeded on retry).
- Integrity: 763/800 clips are proper 3.00 s @ 16 kHz; **37 clips are empty (~0 s)**, 35 from HeStutters episode 0 (known mismatched source URL in SEP-28k). Excluded and tallied.

## 3. Eval sets

Energy VAD: RMS on 30 ms frames, 10 ms hop; per-clip speech threshold = max(-45 dBFS, p95 frame dB − 25 dB); gap = contiguous non-speech >= 300 ms preceded by >= 200 ms cumulative speech; resume = first run of 5 consecutive speech frames after the gap.

- BLOCK (from 500): 11 empty wav | 16 no internal gap >= 300 ms | 84 gap but no preceding speech | 79 gap but **no resume** before clip end (silence runs to the clip edge — right-censored blocks) | 310 OK → **BLOCK eval N = 200** (capped, unanimous-first).
- FLUENT (from 300): 26 empty wav | 274 OK → **FLUENT eval N = 200** (capped).
  - Latency subset (needs >= 0.5 s trailing silence after end-of-speech): **N = 77**. Median trailing silence across all 200 is 0.05 s — random 3 s windows usually end mid-speech; 123 excluded, tallied.
  - Mid-utterance fluent pauses >= 300 ms with resume: 51 clips, 57 testable pauses.
- Files: `data/block_eval.csv`, `data/fluent_eval.csv`, `data/eval_tallies.json`.

## 4. Gap-duration distribution (BLOCK silent gaps, N = 200)

| stat | value |
|---|---|
| median | 0.58 s |
| p75 | 0.77 s |
| p90 | 0.93 s |
| min / max | 0.30 s / 1.59 s |
| > 0.5 s | 61.5% |
| > 0.8 s | 20.0% |
| > 1.5 s | 0.5% |
| > 3.0 s | 0.0% |

**CENSORING CAVEAT (read before using this table):** gaps live inside 3 s clips, so nothing longer than ~2.5 s can appear, and 79 further block clips whose silence ran past the clip edge were excluded. Clinical blocks can last many seconds. All block cut-off rates below are therefore for SHORT (< 1.6 s) blocks, and timeout-arm results are LOWER BOUNDS on real-world cut-offs.

## 5. Two-axis table: arm × block cut-off % × fluent added latency

Smart Turn v3.2 = stock pipecat-ai model (`smart-turn-v3.2-cpu.onnx`, int8, repo's own preprocessing: 16 kHz, last-8 s window, WhisperFeatureExtractor(chunk_length=8, do_normalize=True), complete if p > 0.5). "First check" = model consulted 0.2 s into the silent gap (pipecat runs Smart Turn at VAD stop, default stop_secs 0.2); "any check" = consulted repeatedly during the gap until resume (streaming reality). Compute cost: 25 ms mean / 28 ms p95 per inference on this CPU (n=1,164).

| Arm | BLOCK cut-off % (N=200 unless noted) | FLUENT added latency |
|---|---|---|
| Smart Turn v3.2 stock, first check | **58.0%** | median **0.10 s** (+~25 ms compute); p90 0.40 s; 26% of fluent turns never judged complete → fall to the fallback timeout (pipecat default stop_secs 3 s) |
| Smart Turn v3.2 stock, any check before resume | **68.0%** | same as above |
| Smart Turn v3.2, threshold 0.9 (fork required — not an exposed knob) | 35.5% first / 48.5% any | median 0.10 s; 40% fall to fallback timeout |
| Smart Turn v3.2, threshold 0.95 | 22.5% first / 37.0% any | median 0.20 s; 48% fall to fallback timeout |
| Smart Turn v3.2, threshold 0.99 | 0.0% | model stops firing: **98.7%** of fluent turns fall to the fallback timeout — equivalent to a 3 s timeout for everyone |
| Silence timeout 0.5 s | 61.5% | +0.50 s |
| Silence timeout 0.8 s | 20.0% | +0.80 s |
| Silence timeout 1.5 s | 0.5%* | +1.50 s |
| Silence timeout 3.0 s | 0.0%* | +3.00 s |
| ElevenLabs Agents live, turn_eagerness=normal (stock), N=20 live sessions | 5% strict / 10% likely | response ~+2.7 s after audio stops (includes LLM+TTS; proxy — see §7); 3/20 no response in window |
| ElevenLabs Agents live, turn_eagerness=patient, N=20 | 5% strict / 5% likely | response ~+3.0 s proxy; **6/20 no response in window** (patient is visibly slower/withholding) |

\* censored data: no gap > 1.6 s exists in 3 s clips, so timeout arms look better than they are for real multi-second blocks.

Smart Turn v3.2 also declared "complete" at **59.6%** of fluent speakers' own mid-utterance pauses (57 pauses tested at +0.2–0.3 s of silence) — on conversational podcast audio it endpoints most sub-second pauses, stuttered or not. (Many such pauses do follow semantically complete sentences; human listen-through required to split those.)

**Harness sanity controls (Smart Turn):** mid-speech cuts (should be incomplete): 31% judged complete (N=49). True fluent end + 0.4 s silence (should be complete): 70% (N=50). Block gaps: 58%. Ordering mid-speech < block-gap < true-end is correct, so the harness measures real signal — and the model treats a stutter block much closer to "turn over" than to "still talking".

## 6. Spot-check notes

- `data/spotcheck/block_spotcheck_rms.png`: RMS profiles of 10 BLOCK samples (every 20th of the eval set), with detected gap (red span) and resume (green). All 10 show the expected structure: speech → silent gap well below threshold → clear resumption. HeStutters_18_51 shows low-level in-gap activity (breath/gasp — consistent with a block); MyStutteringLife_25_11 has a high noise floor (~−40 dB) but valid structure.
- **Human listening by the team is still required** — the VAD confirms gap+resume energy structure, not that the gap is a stutter block (the Block >= 2/3-annotator label carries that claim) nor that "resume" isn't an interlocutor. 10-clip listen-through is Niko's first task.

## 7. ElevenLabs "patient" arm (live, bounded)

- (a) **Eagerness is API-configurable:** `conversation_config.turn.turn_eagerness` ∈ {eager, normal, patient} (verified by PATCH + readback on a real agent; agent also exposes `turn_timeout` 1–30 s, `turn_model: turn_v3`, `mode: turn`). Docs: elevenlabs.io/docs/agents-platform/customization/conversation-flow ("Turn eagerness ... Patient — The assistant waits longer before taking its turn").
- (b) **Streaming prerecorded audio works:** ConvAI websocket (signed URL) accepts `user_audio_chunk` base64 PCM-16 kHz; server emits user_transcript / agent_response / audio / interruption / ping events. Fully practical — ran it.
- Live run: agent `agent_9901m4k3jsfyehcry084sqnk3vyv` (blank first message, 1-sentence LLM). 20 BLOCK clips (gap >= 0.5 s), streamed in real time (100 ms chunks) + 5 s trailing silence, 2 conditions = 40 sessions (~7 min total ConvAI usage — minimal spend). `scripts/elevenlabs_arm.py`, results `data/elevenlabs_{normal,patient}_results.csv`.
- Cut-off = agent audio/response arriving before the labeled resume (strict), or before resume+0.5 s or an `interruption` event right after resume (likely). **normal: 1/20 strict (5%), 2/20 likely (10%). patient: 1/20 strict and likely (5%)** — same clip (HeStutters_21_144) barged in under both settings.
- Latency proxy (first agent event after clip end; includes ASR finalize + LLM + TTS, and clips end mid-speech, so this is NOT a clean end-of-speech latency): normal mean +2.71 s with 3/20 silent; patient mean +2.99 s with **6/20 silent in a ~6 s window**. Patient clearly costs responsiveness; a clean fluent-latency comparison (stream FLUENT clips, subtract TTS/LLM) remains to be run.
- Interpretation limits: (i) this measures audible barge-in, not the internal turn decision — EL may cancel a pending response when speech resumes (speculative_turn=true), which is genuinely to its credit at the user level; (ii) gaps tested were 0.5–0.96 s only (clip censoring): nothing here shows what EL does during a real 3–10 s block, where its transcript-based turn model plus `turn_timeout` (default 7 s) will eventually fire.

## 8. Gemini Live arm — NOT RUN

- **Needs GOOGLE_API_KEY from the team.** Exact knob to test, per ai.google.dev/gemini-api/docs/live-api/capabilities ("Automatic VAD configuration", fetched 2026-10-10): `realtimeInputConfig.automaticActivityDetection` with `end_of_speech_sensitivity` (`END_SENSITIVITY_LOW`/`HIGH`), `silence_duration_ms` (server default ≈ 800 ms; docs recommend 500–800 ms and warn 2000 ms+ "increasing perceived latency"), `prefix_padding_ms`, `start_of_speech_sensitivity`; audio in as `audio/pcm;rate=16000`. Same harness as the ElevenLabs arm will work (stream clip + silence, log `interrupted`/`turnComplete` events).

## 9. Telephony note (recorded, not run)

All results are on wideband 16 kHz podcast audio. Real phone channels are 8 kHz narrowband (G.711); VADs and turn models can behave differently there. Phone-channel transfer is UNTESTED.

## 10. VERDICT against the abandon conditions

1. **"An existing knob keeps block cut-offs < 10% while adding < 300 ms fluent latency" — FAIL (condition not met → do not abandon).** Timeouts: 0.8 s gives 20% cut-offs at +800 ms; 1.5 s gives 0.5% (censored) at +1500 ms — nothing passes both bars, and that is on short blocks only. Smart Turn threshold (not even an exposed knob): 0.95 still cuts 22.5% and sends 48% of fluent turns to a 3 s fallback; 0.99 reaches 0% only by never firing (= 3 s timeout for everyone). ElevenLabs `patient`: cut-offs 5% (passes the 10% bar on N=20 short blocks) but its latency cost is plainly > 300 ms (6/20 fluent-ish turns got no response at all in-window) — and untested on real multi-second blocks.
2. **"Stock cut-offs already under 10%" — SPLIT, mostly FAIL (→ do not abandon, but narrow the target).** Smart Turn v3.2 stock (the open-source/pipecat ecosystem standard): **58–68%** cut-offs — the problem is real and large. ElevenLabs stock (normal): 5–10% on N=20 sub-second blocks — at/near the bar; with N=20 the 95% CI on 1/20 is roughly 0.1–25%, so NOT determinable, and only for blocks < 1 s.
3. **"Fewer than ~300 usable clips" — NOT met (→ do not abandon).** 763 usable audio clips obtained; 310 BLOCK clips passed the gap+resume pipeline; eval sets of 200+200 built.
4. **"Labels fail sanity checks" — NOT met (→ do not abandon).** 10/10 spot-checks show the gap+resume structure; positive/negative controls order correctly (31% / 58% / 70%); label-derived selection behaved as expected. Human listen-through still pending.

**Net: the kill test does NOT kill StutterTurn, but it sharpens it.** The measured, defensible wedge is: (a) the open-source voice-agent stack (pipecat + Smart Turn v3, VAD timeouts) cuts off people who stutter on 58–68% of sub-second blocks, and no existing setting fixes it without multi-second latency for everyone; (b) the best commercial stack (ElevenLabs) already handles sub-second blocks well, so the pitch must NOT claim "all voice agents fail" — it should target the open ecosystem and the untested multi-second-block regime. Weakest point of this evidence: all blocks tested were < 1.6 s (3 s clip censoring).

## 11. What remains for Niko

1. **Human listen-through** (30 min): the 10 spot-check clips + HeStutters_21_144 (the EL barge-in) + 20 random BLOCK eval clips — confirm gaps are blocks, resumes are the same speaker.
2. **ElevenLabs fluent-latency arm**: stream the 77 FLUENT latency clips at normal vs patient; measure first-agent-event delta between modes (isolates the patient latency cost from LLM/TTS). Agent `agent_9901m4k3jsfyehcry084sqnk3vyv` is live and configured; `scripts/elevenlabs_arm.py` needs ~20 lines changed.
3. **Long-block test** (the censoring gap): FluencyBank interview recordings or team-recorded consented samples with 2–8 s blocks → rerun all arms. This is the make-or-break number for the ElevenLabs comparison.
4. **Gemini Live arm**: needs GOOGLE_API_KEY; knob and harness spec in §8.
5. **Fine-tune go/no-go**: Smart Turn v3 training stack is open (train.py in `smart-turn/`); SEP-28k gives ~3.1k Block>=2 clips (CC BY-NC — benchmark/demo OK). The 58%→target gap is the headline; decide after the listen-through.
6. 8 kHz telephony transfer (§9) if the demo targets phone calls.
