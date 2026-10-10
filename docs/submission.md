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
