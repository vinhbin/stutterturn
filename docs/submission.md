# Demo and submission plan

**Devpost fields and story:** [copy-ready current-prototype draft](devpost.md). Refresh its pending work and evidence links before submitting; this document remains the demo/release checklist.

**Format we're planning for: 3 minutes, ~2 judges at the table.** Confirm the actual format/rubric from the opening-ceremony materials and adjust.

**Gate alignment ([PLAN.md](../PLAN.md), issues #2/#4/#6):** 2 PM feasibility/scope decision → 3 PM DEV improvement decision (model continue **or** corrected-benchmark commit happens then, not later) → 10 PM demo-variant lock → Sun 1 AM feature freeze → submit 8:30 AM. This page keeps two conditional run-of-show templates until the 10 PM lock; neither is evidence that its rig or results exist. Every result-bearing sentence below follows [docs/claims-ledger.md](claims-ledger.md): ready wording only in anything delivered; placeholders stay bracketed until Niko's immutable run evidence lands; the Smart Turn numbers are exploratory offline predictions and the ElevenLabs numbers are separately defined server-event timings, not validated audible-interruption or hang-up rates.

## The 3-minute run-of-show

### Variant 1 — successful model (requires: 3 PM gate passed + saved `stutterturn-vN.onnx` final-test run; wording = [pitch Script A](pitch-and-qa.md))

| Clock | What happens | Who |
|---|---|---|
| 0:00–0:30 | Hook: 160,000 calls/month (one health system) + stock's measured rate — delivered as "the model judged the caller done during [S]% of stutter blocks," [S]% from the frozen final-test stock rerun (the exploratory first run measured 58%; ledger L-01/L-20). | Vinh; screen shows matched final-test counts and denominators |
| 0:30–1:30 | **The toggle.** Screen: "Real recording — person who stutters (SEP-28k)". STOCK: the live agent barges in mid-block (visible on the turn-state strip). A judge flips to STUTTERTURN; fresh live call, same clip: "holding…", the caller finishes, the agent answers. If only the internal decision differs, show that trace accurately — never stage an audible interruption. | **Judge presses the toggle** |
| 1:30–2:00 | **The judge's own call.** A judge speaks to the agent normally — this establishes liveness; the latency claim itself cites the measured completed-turn results for both caller groups, not this one interaction (ledger L-31). | **Judge talks to the agent** |
| 2:00–2:40 | Benchmark page: the matched measured table ([S]% → [X]%, pending Niko's final-test run), saved evidence and disclosures. Offer a live rerun only if that feature actually works. | Vinh, one scroll |
| 2:40–3:00 | Honest close: exact outcome and limits, credit for upstream work, and only artifacts actually released — wording in [pitch Script A](pitch-and-qa.md). Novelty claims need a current scoped review. | Vinh |

### Variant 2 — corrected-benchmark fallback (requires validated evaluation and a working matched stock/patient comparison; wording = [pitch Script B](pitch-and-qa.md))

| Clock | What happens | Who |
|---|---|---|
| 0:00–0:30 | Hook: 160,000 calls/month + "in our offline test, stock predicted 'turn complete' in 116 of 200 energy-detected gaps, or 58%, in clips labeled as containing blocks; the exact boundaries still need human validation" (exploratory framing spoken). | Vinh |
| 0:30–1:30 | **The comparison.** Same pipeline, same real labeled recording, fresh call each side: STOCK vs **PATIENT — on-screen label states it is a longer-wait configuration, not a trained model** (exact config per Guttuu). Describe only the difference established by the saved run. Do not assume stock interrupts or patient is slower; show decisions and audible events separately. | **Judge presses it** |
| 1:30–2:00 | **The judge's own call** on both configurations, if working. This establishes liveness, not a latency distribution. | **Judge talks to the agent** |
| 2:00–2:40 | Benchmark page: corrected matched comparison, outcome definitions, counts, completed-turn delays and censoring. Keep historical offline and ElevenLabs event results separately labeled; show release terms and disclosures. | Vinh, one scroll |
| 2:40–3:00 | Honest close: name the corrected method/artifacts actually delivered and remaining limits. A trained improvement remains unproved; existing configurations may already meet the target. | Vinh |

If the agent or corrected evaluation is unavailable, use the short ready-now statement in [the pitch document](pitch-and-qa.md), show only saved exploratory results and say which work is pending. Do not deliver the gated Script B or call the corrected benchmark complete.

Reset: one tap, under 60 s (verify before claiming — ledger L-30). Connectivity fallback: recorded video of the same rig, **labeled as a recording on screen**. Rehearse ×3 with someone unscripted before 10 PM (not yet done; the revised templates still need timing with the actual interaction).

## Rules we hold ourselves to

- Nobody imitates stuttering — only real recordings, always labeled on screen.
- Never say: "all voice agents fail" · anything medical · "we solved stuttering".
- Always say: the recordings are real and credited; the annotations are CC BY-NC and audio/demo rights are checked separately; long blocks (3+ s) untested in our evaluation until a verified long-block run lands; our ElevenLabs numbers are our own small unpublished n=20 test.
- Every claim needs applicable evidence, not merely agreement with the old report. External facts need sources; implementation claims need a working artifact; experimental results need the correct population and outcome definition.
- The 58%/68% are exploratory internal **completion predictions** (all-eight-show partition, VAD-derived gaps, listen-through pending) — never "callers interrupted," call abandonment, or hang-ups; 58% of tested blocks is not 58% of callers (D-006).
- No target, plan or placeholder is voiced in past tense as an achieved result; automated waveform inspection is not human listening. One-second censoring is not an observed three-second fallback, and conditional first-crossing times are not deployed response latency.
- "First" claims require a current scoped prior-art review and the completed contribution; "to our knowledge" alone does not validate the earlier superseded search conclusion (L-26/L-27).

## Devpost checklist

- [ ] Title, description, problem, intended users (people who stutter calling AI-answered lines; agent builders adopting the model/benchmark).
- [ ] Track: AI/ML. MLH: Best Use of ElevenLabs. Roster complete and registered.
- [ ] Public repo + README; working demo instructions; judge needs nothing installed.
- [ ] 3-minute video, viewable logged out, same rig as the table demo; prerecorded caller audio and any fallback footage labeled on screen.
- [ ] Technologies/datasets — list only what actually ran: Smart Turn v3.2, SEP-28k (Lea et al. 2021, annotations CC BY-NC; audio not redistributed) and the separate ElevenLabs test have saved exploratory outputs. Pipecat integration requires its own run evidence. Gemini (arm not run — needs key), Vultr and Tiger Data are planned, not integrated, as of Sat afternoon (ledger L-34) — add each only once it works; enter only sponsor prizes backed by actual disclosed use.
- [ ] Disclosures: pre-event planning; AI assistance (Claude) on the benchmark and code, team-directed and reviewed; the morning pivot from a prior concept.
- [ ] All README/pitch/page numbers reconciled against saved results **via [docs/claims-ledger.md](claims-ledger.md)** — every [N]/[S]/[X]/[Y] and comparison placeholder resolved from the applicable saved run or the sentence removed; submit by 8:30, confirm received.

## Likely judge questions (have these ready)

**"How did you get the 58% number?"**
The saved offline predictions crossed p > 0.5 on 116 of 200 first checkpoints, at +0.2 s into energy-detected gaps in clips labeled as containing blocks. Additional offline checks gave 136/200 (68%). The clip labels do not locate those blocks, and the energy trace does not establish same-speaker continuation. These are not measured audible interruptions. The old controls were not verified mid-word cuts or genuine turn endings, so their ordering cannot validate this interpretation (L-01/L-02/L-10).

**"Is the 58% validated?"**
Its arithmetic is supported by the saved predictions; its interpretation as a stutter-interruption rate is not. Contextual human labels, a rebuilt partition and a matched deployed comparison are pending. The 30-example feasibility review alone would not validate all 200 old examples. Any final comparison reruns stock and the candidate/settings on the same frozen test.

**"Why should we believe the ground truth?"**
The current boundaries are energy-derived proxies. Activity after a gap could be a different speaker or a new legitimate turn, and a clip-level Block label does not locate the selected gap. We need human-reviewed surrounding context, speaker identity and completed/unfinished-turn labels for every evaluated boundary. Missing or ambiguous labels must remain excluded or explicitly unresolved.

**"Did you test the real clinic agents, like the ones answering 160,000 calls a month?"**
No. The saved experiments use offline Smart Turn predictions and our own ElevenLabs test agent, not that health system's deployed stack. The ElevenLabs CSVs contain 40 sessions across two conditions with server-event timestamps; they do not establish a clinical agent's performance. Gemini Live and other vendor comparisons remain unrun unless new evidence is added.

**"Isn't this just a longer timeout?"**
A longer wait is a relevant baseline, and it may be sufficient. In the selected gaps, a pure 0.8 s timeout would expire before detected resumption in 40/200 cases; that is a duration calculation. The threshold sweep stops after at most one second of fluent silence, so it cannot show three-second fallback rates or reject all useful settings. Our planned gate compares the simplest patient/wait condition with the candidate on validated inputs and completed-turn delays for both groups (L-05–L-07).

**"What happens if the model isn't ready?"**
The 2 PM feasibility and 3 PM development gates choose the scope. The fallback is a corrected benchmark and clearly labeled stock/patient comparison, but it still needs validated labels, reproducible runs and a working comparison. If those are missing, report the saved work as exploratory and name the unresolved blockers; do not mark the fallback complete.

**"Hasn't Apple already solved this?"**
Apple's published Siri work is relevant prior art, and SEP-28k supplies our exploratory clips. We must check the precise source before quoting an exact improvement or asserting that a particular result shipped as a setting. It does not establish what other agents do. Our intended contribution is an inspectable, validated comparison and an improvement if the experiments support one (L-17/L-28).
