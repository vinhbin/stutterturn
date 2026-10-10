# Demo and submission plan

**Format we're planning for: 3 minutes, ~2 judges at the table.** Confirm the actual format/rubric from the opening-ceremony materials and adjust.

**Gate alignment ([PLAN.md](../PLAN.md), issues #2/#4/#6):** 2 PM feasibility/scope decision → 3 PM DEV improvement decision (model continue **or** corrected-benchmark commit happens then, not later) → 10 PM demo-variant lock → Sun 1 AM feature freeze → submit 8:30 AM. This page keeps both demo variants ready until the 10 PM lock. Every result-bearing sentence below follows [docs/claims-ledger.md](claims-ledger.md): ready wording only in anything delivered; placeholders stay bracketed until Niko's immutable run evidence lands; the Oct-10 numbers are exploratory internal completion predictions, never "callers interrupted" or hang-ups.

## The 3-minute run-of-show

### Variant 1 — successful model (requires: 3 PM gate passed + saved `stutterturn-vN.onnx` final-test run; wording = [pitch Script A](pitch-and-qa.md))

| Clock | What happens | Who |
|---|---|---|
| 0:00–0:30 | Hook: 160,000 calls/month (one health system) + stock's measured rate — delivered as "the model judged the caller done during [S]% of stutter blocks," [S]% from the frozen final-test stock rerun (the exploratory first run measured 58%; ledger L-01/L-20). | Vinh; screen shows both numbers with their denominators |
| 0:30–1:30 | **The toggle.** Screen: "Real recording — person who stutters (SEP-28k)". STOCK: the live agent barges in mid-block (visible on the turn-state strip). A judge flips to STUTTERTURN; fresh live call, same clip: "holding…", the caller finishes, the agent answers. If only the internal decision differs, show that trace accurately — never stage an audible interruption. | **Judge presses the toggle** |
| 1:30–2:00 | **The judge's own call.** A judge speaks to the agent normally — this establishes liveness; the latency claim itself cites the measured completed-turn results for both caller groups, not this one interaction (ledger L-31). | **Judge talks to the agent** |
| 2:00–2:40 | Benchmark page: the measured table ([S]% → [X]%, pending Niko's immutable final-test run), rerun-it-live button, license + AI-assistance disclosures. | Vinh, one scroll |
| 2:40–3:00 | Honest close: ElevenLabs credit (our own n=20 unpublished test), open-ecosystem target, search-scoped "first" claims — exact words in [pitch Script A](pitch-and-qa.md). | Vinh |

### Variant 2 — corrected-benchmark fallback (stock vs explicitly labeled patient/timeout agent; wording = [pitch Script B](pitch-and-qa.md))

| Clock | What happens | Who |
|---|---|---|
| 0:00–0:30 | Hook: 160,000 calls/month + "stock predicted 'turn complete' during 58% of the silent gaps on first check — the model's own decision, measured on 200 real recordings" (exploratory framing spoken). | Vinh |
| 0:30–1:30 | **The comparison.** Same pipeline, same real labeled recording, fresh call each side: STOCK vs **PATIENT — on-screen label states it is a longer-wait configuration, not a trained model** (exact config per Guttuu). Stock moves to answer mid-block; patient holds and answers late — the trade-off is the finding. | **Judge presses it** |
| 1:30–2:00 | **The judge's own call** on stock (expected speed), then patient (feel the wait). Liveness only. | **Judge talks to the agent** |
| 2:00–2:40 | Benchmark page: tested-configurations table (timeouts, thresholds, ElevenLabs n=20), censoring caveat (<1.6 s), license + AI-assistance disclosures. | Vinh, one scroll |
| 2:40–3:00 | Honest close: we ship the measurement + method; trained fix is next; search-scoped benchmark novelty. | Vinh |

If no agent runs at all: deliver Script B's words over the benchmark page alone and say the live comparison isn't running.

Reset: one tap, under 60 s (verify before claiming — ledger L-30). Connectivity fallback: recorded video of the same rig, **labeled as a recording on screen**. Rehearse ×3 with someone unscripted before 10 PM (not yet done; scripts are length-estimated only).

## Rules we hold ourselves to

- Nobody imitates stuttering — only real recordings, always labeled on screen.
- Never say: "all voice agents fail" · anything medical · "we solved stuttering".
- Always say: the recordings are real and credited (CC BY-NC); long blocks (3+ s) untested everywhere including by us until the long-block run lands; our ElevenLabs numbers are our own small unpublished n=20 test.
- Nothing is claimed in the pitch or on the page without a saved result in `benchmark/`.
- The 58%/68% are exploratory internal **completion predictions** (all-eight-show partition, VAD-derived gaps, listen-through pending) — never "callers interrupted," call abandonment, or hang-ups; 58% of tested blocks is not 58% of callers (D-006).
- No target, plan or placeholder is ever voiced in past tense as an achieved result; automated waveform inspection is not human listening.
- "First" claims stay narrow and search-scoped: first **open** stutter-trained turn model, first **public** benchmark, "to our knowledge" (ledger L-26/L-27).

## Devpost checklist

- [ ] Title, description, problem, intended users (people who stutter calling AI-answered lines; agent builders adopting the model/benchmark).
- [ ] Track: AI/ML. MLH: Best Use of ElevenLabs. Roster complete and registered.
- [ ] Public repo + README; working demo instructions; judge needs nothing installed.
- [ ] 3-minute video, viewable logged out, same rig as the table demo; prerecorded caller audio and any fallback footage labeled on screen.
- [ ] Technologies/datasets — list only what actually ran: Smart Turn v3.2 (BSD-2), SEP-28k (CC BY-NC, Lea et al. 2021, audio not redistributed), ElevenLabs, Pipecat. Gemini (arm not run — needs key), Vultr and Tiger Data are planned, not integrated, as of Sat afternoon (ledger L-34) — add each only once it works; enter only sponsor prizes backed by actual disclosed use.
- [ ] Disclosures: pre-event planning; AI assistance (Claude) on the benchmark and code, team-directed and reviewed; the morning pivot from a prior concept.
- [ ] All README/pitch/page numbers reconciled against saved results **via [docs/claims-ledger.md](claims-ledger.md)** — every [S]/[X]/[Y] placeholder resolved from the immutable final-test run or the sentence removed; submit by 8:30, confirm received.

## Likely judge questions (have these ready)

**"How did you get the 58% number?"**
Apple's SEP-28k dataset: real podcast clips from people who stutter, each labeled by three human annotators. We took 200 clips marked as blocks, found the silent gap inside each block and the moment the speaker resumes — the resume shows the speaker was not done (energy-verified; our own listen-through is part of today's proof). We fed the audio up to 0.2 s into that gap to stock Smart Turn v3.2 with its production preprocessing; it declared the turn over on 116 of 200 (58%; 68% with repeated checks) — the model's internal prediction, exploratory until labels and pipeline outcomes are validated. Three controls order correctly: mid-word cuts → "done" 31%, real sentence ends → 70%, blocks → 58% — so the harness measures real signal. Fluent axis: median 0.1 s to fire after real end-of-speech (and 26% of fluent turns fell to the fallback timeout — we report that too). Scripts, data and saved results are in `benchmark/`.

**"Is the 58% validated?"**
It's our exploratory first measurement, and we say so: the gap/resume labels are energy-derived and the team's human listen-through plus a show-separated partition rebuild are running today ([PLAN.md](../PLAN.md) gates). What's solid already: three-annotator block labels, correct control ordering, and every number saved in `benchmark/`. Any final headline comes from a rerun of stock on the frozen, show-separated final test — not from reusing this number.

**"Why should we believe the ground truth?"**
The ground truth isn't our opinion — it's the recording itself: the energy trace shows the person resumes after the gap, and three human annotators labeled the block. Known limits, stated openly: all testable gaps were under 1.6 s (3-second clips), audio is wideband not phone-line, and our team's human listen-through of the eval clips is running today (issue #1) — until it's logged, we call the resume labels energy-verified, not human-verified.

**"Did you test the real clinic agents, like the ones answering 160,000 calls a month?"**
No — and deliberately. Probing a live patient phone line with recorded audio would be testing a medical system without consent. Instead we test the platforms those agents are built on, using our own agents: we ran 40 live sessions against an agent we built on ElevenLabs (their stock handled short blocks well — 5–10% on our 20-clip test, our own unpublished measurement, credited on our page), and the same harness extends to Gemini Live (not yet run — needs an API key) and agent vendors like Retell/Vapi via our own sandbox agents. For closed vendors with no sandbox (e.g., Hippocratic AI), the open benchmark is the mechanism: method, data recipe and harness are saved in the repo and go public at submission — run it on your own stack and report your number.

**"Isn't this just a longer timeout?"**
We measured that exact alternative: a 0.8 s timeout still expires inside 20% of the measured block gaps and delays every caller by 0.8 s; long enough to stop firing inside blocks means 1.5–3 s of dead air for everyone (all on short, censored blocks — lower bounds). The trade-off is in the model, so the fix belongs in the model — same speed for fluent callers, fewer premature decisions on blocks. That's the pre-registered target the 3 PM gate tests; we claim it only once the final-test run shows it, and the toggle demonstrates whichever condition actually ships.

**"What happens if the model isn't ready?"**
That decision already has a time on it: 2 PM feasibility, 3 PM measured DEV improvement. If either fails we commit then to the corrected benchmark plus a clearly labeled stock/patient comparison (Variant 2 above) — honestly named, no trained-model claims, and the measured stock finding stands on its own.

**"Hasn't Apple already solved this?"**
For Siri, partially — and it's closed. Their published work cut Siri's cut-offs by ~79%, shipped as Siri-only settings. We searched and found nothing comparable for the open agent stack that answers real phone lines (documented, D-003). We use Apple's own dataset where Apple stopped, and we publish what they didn't: a public benchmark — and the open model, once today's gate evidence lands.
