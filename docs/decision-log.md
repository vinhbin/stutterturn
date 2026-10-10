# StutterTurn decision log

Dated entries, newest first. Confirmed team choices vs. proposals are kept distinct. A result claim requires saved test evidence.

## 2026-10-10 D-005 — Repo created ahead of the noon confirmation (Vinh's instruction)

Private repo with planning, phases, roles and a submission-ready README, modeled on the team's previous hackathon repos. The team's noon pick is still the gate for build work; if the pick changes, this repo is archived, not deleted (the benchmark stands on its own).

## 2026-10-10 D-004 — Demo ethics and design (confirmed)

**Nobody imitates stuttering, ever.** The live demo streams real SEP-28k recordings (labeled on screen) into a genuinely live agent call; the agent's decisions happen live. The judge presses the STOCK↔STUTTERTURN toggle and separately speaks to the agent to feel the unchanged fluent latency. 3 minutes, ~2 judges, reset under 60 s, labeled fallback video if connectivity dies.

## 2026-10-10 D-003 — Novelty claim wording (verified)

Searches of ElevenLabs docs/changelog/site, Smart Turn repo and forks, LiveKit/Deepgram/AssemblyAI docs, academic work and Devpost found no stutter-aware turn-taking anywhere. Closest prior art: Apple's closed, Siri-only atypical-speech work (Lea et al. 2023). The claim therefore always includes **"open"** and **"public benchmark"**. ElevenLabs framing is credit, not attack: their stock agents handled short blocks well in our own n=20 live test (labeled as our measurement). Unknown and said so if asked: whether Smart Turn's community training data incidentally contains stuttered speech.

## 2026-10-10 D-002 — Kill test results accepted (evidence: benchmark/RESULTS.md)

Real SEP-28k audio, 200 block + 200 fluent clips. Stock Smart Turn v3.2: 58% block interruptions first-check / 68% repeated, ~0.1 s fluent latency; timeouts and thresholds cannot reach <10% interruptions without multi-second latency for everyone; ElevenLabs stock 5–10% on short blocks (n=20). All measured gaps <1.6 s (3 s clip censoring) — long blocks untested. SEP-28k annotations CC BY-NC 4.0 (benchmark/demo use with attribution; no commercial use; audio not redistributed). None of the pre-registered abandon conditions met.

## 2026-10-10 D-001 — Pivot from CarSweep; StutterTurn selected for the final test round

Friday night an iPhone auto-detected the team's own Bluetooth tracker, confirming phones + free apps already do CarSweep's core job. After researched comparison rounds across all tracks, StutterTurn emerged as the lead: a measured failure in the open voice-agent stack, a named measurable advance, and a self-produced before/after stat. Fallbacks if its gates fail: CrossingClock, then StepLimit (see the team brief).
