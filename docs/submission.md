# Demo and submission plan

**Format we're planning for: 3 minutes, ~2 judges at the table.** Confirm the actual format/rubric from the opening-ceremony materials and adjust.

## The 3-minute run-of-show

| Clock | What happens | Who |
|---|---|---|
| 0:00–0:30 | Hook: "AI answers 160,000 patient calls a month at one health system alone. We measured what happens when the caller stutters: the standard open model interrupts 58% of stutter blocks." | Vinh; screen shows both numbers |
| 0:30–1:30 | **The toggle.** Screen: "Real recording — person who stutters (SEP-28k)". STOCK: the live agent barges in mid-block (visible on the turn-state strip). A judge flips to STUTTERTURN; fresh live call, same clip: "holding…", the caller finishes, the agent answers. | **Judge presses the toggle** |
| 1:30–2:00 | **The judge's own call.** A judge speaks to the agent normally — instant answer, proving fluent callers lost nothing. | **Judge talks to the agent** |
| 2:00–2:40 | Benchmark page: the measured table (58% → X%), rerun-it-live button, license + AI-assistance disclosures. | Vinh, one scroll |
| 2:40–3:00 | Honest close: "ElevenLabs' platform already handles short blocks well — we fixed the open ecosystem everyone builds on and published the first benchmark. Drop-in model, open benchmark, built this weekend." | Vinh |

Reset: one tap, under 60 s. Connectivity fallback: recorded video of the same rig, labeled as a recording. Rehearse ×3 with someone unscripted before 10 PM.

## Rules we hold ourselves to

- Nobody imitates stuttering — only real recordings, always labeled on screen.
- Never say: "all voice agents fail" · anything medical · "we solved stuttering".
- Always say: the recordings are real and credited (CC BY-NC); long blocks (3+ s) untested everywhere including by us until the long-block run lands; our ElevenLabs numbers are our own small test.
- Nothing is claimed in the pitch or on the page without a saved result in `benchmark/`.

## Devpost checklist

- [ ] Title, description, problem, intended users (people who stutter calling AI-answered lines; agent builders adopting the model/benchmark).
- [ ] Track: AI/ML. MLH: Best Use of ElevenLabs. Roster complete and registered.
- [ ] Public repo + README; working demo instructions; judge needs nothing installed.
- [ ] 3-minute video, viewable logged out, same rig as the table demo.
- [ ] Technologies/datasets: Smart Turn v3.2 (BSD-2), SEP-28k (CC BY-NC, Lea et al. 2021, audio not redistributed), Gemini, ElevenLabs, Vultr, Tiger Data, Pipecat.
- [ ] Disclosures: pre-event planning; AI assistance (Claude) on the benchmark and code, team-directed and reviewed; the morning pivot from a prior concept.
- [ ] All README/pitch numbers reconciled against saved results; submit by 8:30, confirm received.

## Likely judge questions (have these ready)

**"How did you get the 58% number?"**
Apple's SEP-28k dataset: real podcast clips from people who stutter, each labeled by three human annotators. We took 200 clips marked as blocks, found the silent gap inside each block and the moment the speaker resumes — the resume proves the speaker was not done. We fed the audio up to 0.2 s into that gap to stock Smart Turn v3.2 with its production preprocessing; it declared the turn over on 116 of 200 (58%; 68% with repeated checks). Three controls prove the harness works: mid-word cuts → "done" 31%, real sentence ends → 70%, blocks → 58% — the ordering is correct. Fluent axis: median 0.1 s to fire after real end-of-speech. Everything reproduces from `benchmark/`.

**"Why should we believe the ground truth?"**
The ground truth isn't our opinion — it's the recording itself: the person audibly keeps talking after the gap, and three human annotators labeled the block. Known limits, stated openly: all testable gaps were under 1.6 s (3-second clips), audio is wideband not phone-line, and our team's human listen-through of the eval clips is part of the build plan.

**"Did you test the real clinic agents, like the ones answering 160,000 calls a month?"**
No — and deliberately. Probing a live patient phone line with recorded audio would be testing a medical system without consent. Instead we test the platforms those agents are built on, using our own agents: we ran 40 live sessions against an agent we built on ElevenLabs (their stock handled short blocks well — 5–10% on our 20-clip test, credited on our page), and the same harness extends to Gemini Live and agent vendors like Retell/Vapi via our own sandbox agents. For closed vendors with no sandbox (e.g., Hippocratic AI), the open benchmark is the mechanism: method, data recipe and harness are published — run it on your own stack and report your number.

**"Isn't this just a longer timeout?"**
We measured that exact alternative: a 0.8 s timeout still interrupts 20% of blocks and delays every caller by 0.8 s; long enough to stop interrupting means 1.5–3 s of dead air for everyone. The trade-off is in the model, so the fix is in the model — same speed for fluent callers, fewer interruptions on blocks, shown on one toggle.

**"Hasn't Apple already solved this?"**
For Siri, partially — and it's closed. Their published work cut Siri's cut-offs by ~79%, shipped as Siri-only settings. Nothing exists for the open agent stack that answers real phone lines. We use Apple's own dataset where Apple stopped, and we publish what they didn't: an open model and a public benchmark.
