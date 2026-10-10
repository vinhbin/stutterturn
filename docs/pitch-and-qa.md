# StutterTurn — the pitch, and the hard questions

Team-internal prep. The pitch words first, then an adversarial Q&A: every question we'd ask if we were trying to sink this project, with the honest answer. Questions marked **OPEN** have no good answer yet — they are work items, not talking points.

**This document has two layers, and they are not interchangeable:**

1. **INTENDED FINAL WORDING** — the ambitious pitch, preserved exactly as drafted. It is the destination. Each result-bearing line unlocks when its evidence lands; the line-by-line gate map below says what unlocks it.
2. **STATEMENTS READY TO DELIVER TODAY** — two full scripts (successful-model and corrected-benchmark fallback) built only from wording marked **ready** in the [claims ledger](claims-ledger.md). Anything spoken, filmed or published before a gate passes comes from this layer.

Standing rule (D-006): all 2026-10-10 numbers are exploratory model **completion predictions** until the human listen-through, pipeline-outcome measurement and show-separated partition rebuild land — never "callers interrupted," never hang-ups. Gates: 2 PM feasibility/scope, 3 PM DEV improvement (model continue or corrected-benchmark commit happens **then**), 10 PM demo-variant lock ([PLAN.md](../PLAN.md), issues #2/#4).

---

## INTENDED FINAL WORDING — the pitch (3 minutes, the exact words)

> Preserved verbatim per Vinh's instruction (D-006). Deliver only after the gate map below says every line is unlocked.

"AI already answers the phone in healthcare — one health system's AI agent alone handles 160,000 patient calls a month, and pharmacy refill lines are among the most automated calls in the country. We measured what happens when the caller stutters. On 200 real recordings of people who stutter, the standard open-source turn-taking model — the part that decides 'the caller is done talking' — interrupted 58% of stutter blocks. And no setting fixes it: wait longer, and everyone gets seconds of dead air on every turn.

Imagine calling to refill your own prescription, getting stuck on a word, and the AI talks over you. Over three million Americans stutter. Many just hang up.

So we fine-tuned the open model on real recordings of people who stutter. Same speed for fluent callers — one tenth of a second — but interruptions drop from 58% to X%. [THE TOGGLE MOMENT — judge presses it.] [THE JUDGE'S OWN CALL — they speak, instant answer.]

We're honest about scope: ElevenLabs' closed platform already handles short blocks well — we tested it live and we credit it. Our fix targets the open ecosystem every voice-agent startup builds on. And we ship it two ways: a drop-in model, and the first public benchmark of how voice agents treat people who stutter — so any vendor, including the ones answering those 160,000 calls, can test themselves. Apple fixed this inside Siri and kept it closed. We took Apple's own dataset where Apple stopped."

**The 10-second version (hallway):** "Voice agents hang up on people who stutter — we measured it: 58% of stutter blocks get interrupted. We trained the open turn-taking model to wait, without slowing anyone else down, and published the first benchmark."

### Line-by-line gate map for the final wording

Ledger IDs refer to [docs/claims-ledger.md](claims-ledger.md). "Unlocks when" = the evidence that makes the line deliverable as written.

| Draft line | Ledger | Status today | Unlocks when |
|---|---|---|---|
| "160,000 patient calls a month" | L-14 | ready | — |
| "pharmacy refill lines are among the most automated calls in the country" | L-19 | **unsupported** | a citable source is saved; otherwise cut |
| "interrupted 58% of stutter blocks" | L-01 | target (ready form: "predicted 'turn complete' during 58% of gaps") | human listen-through + audible-outcome pipeline measurement + partition rebuild/stock rerun |
| "And no setting fixes it" | L-07 | target (ready form: "none of the configurations we tested") | stays narrowed — no upgrade to the universal form |
| "Imagine calling to refill your own prescription…" | — | ready (framing, no factual load) | — |
| "Over three million Americans stutter" | L-15 | ready | — |
| "Many just hang up." | — | **unsupported, no upgrade path** | recommend replacing even in final with L-16 survey wording — Vinh's call |
| "So we fine-tuned the open model…" | L-20/L-25 | target | immutable `stutterturn-vN.onnx` + final-test run |
| "Same speed for fluent callers — one tenth of a second" | L-21/L-03 | target (0.1 s is stock's exploratory median, not the candidate's) | fine-resolution per-group latency, stock vs candidate |
| "interruptions drop from 58% to X%" | L-20 | target (placeholder) | frozen final test: stock rerun [S]% → candidate [X]% |
| "ElevenLabs… handles short blocks well — we tested it live" | L-08 | ready **with** "our own small n=20 unpublished test" label | — |
| "first public benchmark" / "drop-in model" | L-27/L-23 | target (ready form: search-scoped) | publication + corrected method; export/reload + pipeline load |
| "Apple fixed this inside Siri and kept it closed…" | L-17/L-28 | ready | — |
| 10-second version: "Voice agents hang up on people who stutter" | G (never-say) | **unsupported** (hang-up translation + overgeneral) | none — use the ready 10-second version below |

---

## STATEMENTS READY TO DELIVER TODAY

Two scripts. Script A assumes the 3 PM gate passed and Niko's final-test run is saved — its bracketed placeholders are filled from that run and from Guttuu's demo-rig evidence, nothing else. Script B is the corrected-benchmark fallback: stock versus an **explicitly labeled** patient/timeout configuration, no trained-model claims. Every unbracketed sentence in both is ready-status in the [claims ledger](claims-ledger.md) right now.

**Disclosures carried by both scripts, spoken and on screen:**
- "The caller you'll hear is a real recording of a person who stutters, from Apple's SEP-28k dataset — labeled on screen. Nobody on our team imitates stuttering, ever."
- If connectivity fails: "This is a recording of this same rig — labeled as a recording." (The fallback video must carry that label visibly.)
- ElevenLabs numbers always carry: "our own small live test — 20 clips, unpublished."

### Script A — successful-model pitch

Deliverable only with: 3 PM gate recorded as passed, immutable `stutterturn-vN.onnx` final-test run (fills [S]/[X]/[Y]), listen-through logged, demo rig working (issue #4). Two individual lines carry extra gates: "drop-in model" needs export→reload + pipeline-load evidence (ledger L-23); "first public benchmark" needs the benchmark actually public with the corrected method (L-27) — until then say the search-scoped form.

> "AI already answers the phone in healthcare — one health system reports its AI agent handles 160,000 patient calls a month. We measured what happens when the caller stutters. On [N] real recordings of people who stutter — from Apple's own dataset — the standard open-source turn-taking model, the part that decides 'the caller is done,' judged the caller done during **[S]%** of stutter blocks. A block is a silent pause mid-word; the model reads it as 'your turn is over.' In a 2026 survey, 58% of 53 people who stutter report exactly this: interrupted or timed-out voice input.
>
> [THE TOGGLE — judge presses it] This is a real recording of a person who stutters, labeled on screen — nobody on our team imitates stuttering. The agent is live; its decisions happen in this room. STOCK: watch the turn strip — the caller pauses mid-word, the agent barges in. Now STUTTERTURN — fresh call, same recording: holding… the caller finishes — now it answers.
>
> We fine-tuned the open model on real recordings of people who stutter. On our frozen held-out test, premature turn decisions on stutter blocks dropped from **[S]% to [X]%**, with completed turns for fluent and stuttered speakers each within **[Y] ms** of stock, and no worse no-response rate.
>
> [THE JUDGE'S OWN CALL] Talk to it yourself, normally. That speed is the point — and the claim comes from the measured table, not this one call.
>
> We're honest about scope: in our own small live test — 20 clips, unpublished — ElevenLabs' closed platform already handled short blocks well, and we credit it. Our fix targets the open ecosystem most voice agents are built on. Every block we could test was under 1.6 seconds; longer blocks are untested by everyone, including us. And we ship it two ways: a drop-in model for any pipecat agent, and — to our knowledge, after a documented search — the first public benchmark of how voice-agent turn-taking treats people who stutter. Research and non-commercial use, fully attributed. Apple fixed this inside Siri and kept it closed. We took Apple's own dataset where Apple stopped."

Spoken length: 341 words ≈ **2:16 at ~150 wpm**, leaving ~44 s inside the toggle and judge-call beats — fits 3:00. **Estimated only; not rehearsed. Vinh times it in rehearsal (issue #4 requires three rehearsals before 10 PM).**

### Script B — corrected-benchmark fallback (stock vs labeled patient/timeout agent)

Deliverable today, modulo the live rig: the comparison needs Guttuu's working web agent with an explicitly labeled patient/timeout configuration. If no agent runs at all, deliver the same words over the benchmark page alone and say "the live comparison isn't running; here is the saved data."

> "AI already answers the phone in healthcare — one health system reports its AI agent handles 160,000 patient calls a month. We measured what happens when the caller stutters. On 200 real recordings of people who stutter — clips Apple's annotators labeled as stutter blocks — the standard open-source turn-taking model predicted 'turn complete' during **58% of the silent gaps** on its first check, the moment production agents consult it. That's the model's own decision, measured today, and it rises to 68% if the model keeps checking. In a 2026 survey, 58% of 53 people who stutter report interrupted or timed-out voice input — this is the mechanism.
>
> [THE COMPARISON — judge presses it] A real recording, labeled on screen — nobody on our team imitates stuttering. Left: the stock configuration. Right: the same pipeline set **patient — that label means a longer wait, not a trained model.** Stock moves to answer mid-block; patient holds — and answers late. That trade-off is the finding: in the open stack you currently choose between talking over people who stutter and slowing every caller down. In our data, an 0.8-second timeout still expires inside 20% of block gaps and adds 0.8 seconds for everyone; none of the configurations we tested — timeouts, confidence thresholds, a patient mode — escaped the trade-off.
>
> [THE JUDGE'S OWN CALL] Talk to the stock agent — that's the speed everyone expects. Now the patient one — feel the wait.
>
> So what we ship is the measurement: a benchmark built this weekend from real recordings — no imitation, every number from a saved run — plus the saved method and data for anyone to extend. In our own small live test, 20 clips, unpublished, ElevenLabs' closed platform handled short blocks well — credited on our page. Every block we could measure was under 1.6 seconds; longer blocks are untested by everyone, including us. To our knowledge — a documented search — no public benchmark of voice-agent turn-taking on stuttered speech existed before. The trained fix is the obvious next step, and the training path and targets are in the repo."

Spoken length: 341 words ≈ **2:16 at ~150 wpm**, leaving ~44 s for the comparison and judge call — fits 3:00. **Estimated only; not rehearsed.**

### The 10-second version — ready today

> "We measured the open voice-agent stack on real recordings of people who stutter: it judged the caller 'done' during 58% of stutter blocks — and in our tests no timeout or threshold fixed it without slowing everyone down. We're building the open fix and publishing the benchmark."

---

## Q&A — method and the 58%

> **Q&A status note:** answers are written for demo night. Until each gate passes, treat every 58%-family number as exploratory internal completion predictions (ledger L-01), rig/toggle statements as plans (L-30), and candidate statements as placeholders (L-20–L-25). Deliver only ledger-ready wording today.

**Q: How did you get 58%?**
Apple's SEP-28k dataset: real podcast clips from people who stutter, each labeled by three human annotators. 200 clips with annotator-majority "block" labels; software finds the silent gap inside the block and the moment the speaker resumes — the resume shows the speaker wasn't done (energy-verified; our own listen-through is part of today's proof). We feed audio up to 0.2 s into the gap (when production agents consult the model) into stock Smart Turn v3.2 with its own preprocessing. It said "turn complete" on 116/200 = 58% (68% with repeated checks during the gap) — the model's internal prediction, exploratory until labels and pipeline outcomes are validated. Scripts, data and saved results are in `benchmark/`.

**Q: Why 0.2 s into the gap? Isn't that cherry-picked?**
It's the production default: pipecat consults the turn model when its voice-activity detector reports 0.2 s of silence. We also report "any check before resume" (68%), which is what a streaming agent actually experiences. Both numbers are in RESULTS.md.

**Q: How do you know your test harness isn't broken?**
Three controls, pre-run: audio cut mid-word (should be "not done") → the model said "done" 31% of the time; genuine sentence ends plus silence (should be "done") → 70%; stutter blocks → 58%. The ordering is correct, so the harness measures real signal — and it shows the model treats a block far more like "done" than like "mid-speech."

**Q: Maybe those pauses were genuinely ambiguous — a human would also think the caller was done.**
Sometimes, yes — and the recording answers it: the speaker resumes after the gap (energy-verified; the human listen-through confirming each case is part of today's proof), so "done" was the wrong call in every verified case. Separately, people who stutter report this exact experience (58% in a 2026 survey of 53 people who stutter report interrupted or timed-out input). A polite human waits; the model shouldn't be worse than a polite human.

**Q: Your ground truth comes from an energy-based VAD, not human ears.**
True, and we say so. The VAD confirms the gap-and-resume energy structure; the three-annotator block label carries the "this is a stutter" claim; and the team's human listen-through (the 30-example feasibility set, issue #1) is part of today's 12:30–2 PM proof — stutter-label training waits for it. 10/10 spot-checked clips showed the expected structure (automated RMS inspection — which is not human listening, and we say that too).

**Q: All your blocks are under 1.6 seconds. Real blocks last much longer.**
Correct — the dataset's 3-second clips censor long blocks, and we say this everywhere. Two implications we state plainly: our timeout-arm numbers are lower bounds (real-world timeouts do worse), and the multi-second regime is untested for every system including ours. The long-block run (FluencyBank or consented recordings) is in the plan.

**Q: SEP-28k labels are known to be noisy.**
Yes — annotator agreement is imperfect, which is why we required 2-of-3 majority, quality-gated clips, ran the controls, and scheduled the human listen-through. Noise in labels makes our 58% an estimate, not a decimal truth; it does not plausibly explain away a 58-vs-31 gap against the mid-speech control.

**Q: You tested wideband podcast audio. Phone lines are 8 kHz.**
Known and untested — it's in the limits list and the plan (replay through the real phone path). If results shift on narrowband, the benchmark reports both conditions; the demo can run on a 16 kHz web call with that stated.

## Q&A — the fine-tune and how we test against other models

**Q: Your fine-tuned number doesn't exist yet. What if it fails?**
Correct until the 3 PM gate. Pre-registered success (issue #2): <10% premature block decisions on DEV, with completed fluent **and stuttered** turns each within +50 ms median of stock and no worse fallback/no-response rate — a checkpoint that wins one axis and loses the other fails. The continue-or-fallback decision happens **at 2 PM (feasibility) and 3 PM (measured DEV improvement)**, not late at night; if it fails, we commit then to the corrected benchmark + a clearly labeled stock/patient agent. 10 PM only locks which demo variant runs. The measured stock finding stands on its own either way.

**Q: How do you avoid just training "wait longer" into the model?**
That's the central trap and the eval is built against it: every checkpoint is scored on both axes simultaneously, and the training mix is ~50/50 original Smart Turn data vs stutter data so fluent behavior isn't forgotten.

**Q: How do you avoid evaluating on your training data?**
The split-by-show rule is non-negotiable for any final number — not just by episode, because the same podcast hosts speak across episodes of the same show, so an episode split still leaks speakers. Honest status: the existing exploratory 200+200 eval spans all eight shows, which is exactly why PLAN.md requires rebuilding show-separated train/DEV/final-test manifests and rerunning stock before any stock-vs-candidate comparison. The decision threshold is chosen on DEV, never on the final test, and the final X% comes from one pre-registered final-test run.

**Q: Couldn't a transcript-based (semantic) turn detector solve this better? LiveKit and ElevenLabs use transcripts.**
Maybe partially — a block mid-sentence leaves an incomplete sentence, which semantic models can notice; that's plausibly why ElevenLabs did well on short blocks. Our benchmark is exactly how that question gets answered: we publish the harness and scores for every stack we can legally run (stock Smart Turn, timeouts, our model, ElevenLabs live, Gemini Live when keyed). We're not claiming the only fix; we're claiming the first open fix plus the measuring stick.

**Q: Smart Turn supports 23 languages. Does your fine-tune break the other 22?**
**OPEN.** We train and evaluate English only; other languages are untested and the model card must say "English fine-tune — use stock for other languages" unless we run at least a smoke test. Do not claim multilingual.

**Q: Does your model handle repetitions, prolongations, interjections — or only blocks?**
We target blocks because they're the silence-shaped failure that turn-taking misreads. Other disfluency types are in SEP-28k and in the benchmark's labels, so they're measurable, but our fine-tune's claim is blocks-only until we've evaluated the rest.

**Q: What about background noise, crosstalk, two speakers?**
Podcast audio includes some of this naturally (one spot-checked clip has a high noise floor), but we haven't stress-tested it separately. The demo environment is controlled; the limits list covers it.

**Q: Is your model slower than stock?**
Same architecture, same size (8M params; stock measures ~25 ms per inference on CPU in our runs), so the fine-tune changes weights, not expected cost — and we time the exported candidate before claiming it (ledger L-24).

**Q: Why Smart Turn and not some other base?**
It's what the open agent ecosystem (pipecat) actually ships, it's CPU-cheap, BSD-2, and its repo invites fine-tunes — the fix lands where the problem is. Alternatives are either closed (ElevenLabs, Deepgram) or heavier research models that don't drop into production stacks in a weekend.

## Q&A — prior art and "why are you the ones"

**Q: Hasn't Apple already solved this?**
For Siri, partially, and closed: their published work cut Siri's premature cut-offs ~79%, shipped as Siri-only accessibility settings. Nothing exists for third-party agents answering phone lines. We use Apple's own dataset where Apple stopped — open model, public benchmark.

**Q: What's genuinely new here? Fine-tuning a small model is not research.**
The novelty isn't the technique — it's that nobody we could find has applied it where it's needed and published the measurement. We searched and documented the search (decision log D-003): ElevenLabs' docs/changelog (zero stutter mentions in turn-taking), Smart Turn's repo and all public fine-tunes (language variants only), LiveKit/Deepgram/AssemblyAI docs, papers, and hackathon galleries. A search finding nothing is strong evidence, not proof of universal absence — so every "first" we say is scoped "to our knowledge." The field literally asked for this: an accessibility paper publishing two weeks after demo day calls turn-taking's fluency assumption the core flaw in speech tech.

**Q: ElevenLabs already does well — why does the open stack matter?**
Because it's what most agents are actually built from: the pipecat ecosystem is the default open stack for voice agents, and startups building clinic/pharmacy lines on it inherit the 58% behavior silently. Closed excellence doesn't fix open infrastructure. (Said at the table: this is also the honest version of sponsor respect — their platform is credited as best-in-class on short blocks in our own results.)

**Q: Why is a team with no speech-tech background credible here?**
The credibility is in the artifacts, not our résumés: a reproducible benchmark with controls, pre-registered success criteria, an abort gate we committed to in writing before training, and every claim on the page backed by a saved result. That's more measurement discipline than most published hackathon projects.

**Q: Nobody on your team stutters. Why should you build this?**
True, and we won't pretend otherwise. We build on recordings and published research from people who stutter, we never imitate stuttering, and the deliverable is infrastructure (model + benchmark) that the community — including organizations like AImpower, who benchmark ASR for stuttered speech — can take further. We're seeking input from the stuttering community; if that lands before submission, their words speak, not ours.

**Q: If this matters, why hasn't pipecat done it?**
Open turn-detection models are a 2024–25 development; the ecosystem is new and small, and the maintainers' roadmap is languages and modes. Their README explicitly invites fine-tunes. "Young ecosystem, nobody looked yet" is the benign reason this niche is empty — and we checked the damning alternatives (no demand? liability?) and found documented demand instead.

## Q&A — adoption, impact, business

**Q: The caller can't install your fix — the clinic's vendor has to. Isn't your user unreachable?**
Yes, adoption routes through agent builders, and we say so. That's why the deliverable is a drop-in (one line for any pipecat agent) plus a public benchmark that creates pressure: vendors can be asked "what's your score?" The analogy is accessibility audits — users don't install WCAG either.

**Q: How big is the problem really?**
3M+ Americans stutter (NIDCD, ~1%); AI now answers healthcare and pharmacy lines at scale (one health system: 160k calls/month). We won't invent a multiplied number — the honest claim is: a growing share of essential phone calls are AI-answered, and ~1% of callers hit a failure mode we measured at 58% in the open stack.

**Q: What's the business model?**
It's a hackathon accessibility project, not a startup pitch: open model, open benchmark. If asked where value accrues: vendors adopt it to meet accessibility expectations, and the benchmark is the kind of thing advocacy orgs and procurement teams cite.

**Q: What's v2?**
Long-block robustness, other disfluency types, multilingual evaluation, 8 kHz-native training, and getting the benchmark adopted by one vendor or advocacy org. Each is listed because it's real, not because we'll finish it Sunday.

## Q&A — ethics, data, licensing

**Q: Is it OK to use these people's voices?**
SEP-28k is a published research dataset (Apple, ICASSP 2021) built from public podcasts hosted by people who stutter; annotations are CC BY-NC 4.0 and we attribute. We don't redistribute the audio, we stream labeled excerpts in a research demo, and we never imitate stuttering.

**Q: Your README says "open model" — but it's trained on non-commercial data. Can you even release the weights?**
Sharp question, and we've scoped it: the training annotations are CC BY-NC, so our weights are released for research and non-commercial use with attribution — stated on the model card. "Open" means openly available and reproducible, not commercially unencumbered. A commercial version needs commercially licensed training data; that's v2 territory and we say so.

**Q: You used AI to build the benchmark overnight. Is that allowed?**
Yes — the event requires disclosure, not abstinence. The benchmark was AI-assisted, team-directed and reviewed, built during the event. It's disclosed in the README now, and goes on the Devpost and the judges page when those exist.

**Q: Could this harm people who stutter — e.g., agents "detecting" stuttering?**
Our model doesn't classify or flag anyone; it only decides "wait vs respond" from audio, the same decision stock makes, with no stored labels about the caller. The benchmark labels datasets, not callers. We make no diagnostic claims and no medical claims.

**Q: Why AI/ML track and not Social Good?**
The core contribution is a trained model and a benchmark — AI/ML work with an accessibility stake. If the revealed rubric favors Social Good, the project fits there too; fetching the actual main-track rubric is an open task in PLAN.md (Vinh).

**Q: Is the demo fake? The caller is a recording.**
The caller is a labeled real recording; the agent's decisions are live — a fresh call per toggle press, decisions made in the room. We do it this way because nobody on the team will fake a stutter, and judges can verify liveness by talking to the agent themselves. (Rig status: this describes the planned demo — it becomes sayable when issue #4's rig runs and its timestamps are saved; ledger L-30.)

---

## Where we're genuinely exposed (internal, know these cold)

1. **The X% doesn't exist until the fine-tune works** — and the decision is at the 2 PM/3 PM gates, not 10 PM. If it fails, the submission is the corrected benchmark with a labeled stock/patient agent — strong honesty, weaker wow (Script B is written for exactly this).
2. **Everything measured so far is exploratory**: all-eight-show partition, VAD-derived gap labels, internal completion predictions. Until the listen-through, the pipeline-outcome measurement and the partition rebuild land, the 58% is "the model predicted," never "callers were interrupted."
3. **Short-block censoring.** Our headline is about sub-1.6 s blocks; a judge who realizes long blocks are the worst case is right, and our only defense is "untested everywhere, it's in the plan."
4. **ElevenLabs did well.** If their staff says "so the best commercial system already handles this," our answer is the open ecosystem + the benchmark — it must be delivered confidently or the project sounds like it solved a solved problem.
5. **Speaker leakage** if the split-by-show rule gets skipped under time pressure — the X% becomes indefensible. The eval split is not negotiable, and the current exploratory partition doesn't satisfy it yet.
6. **VAD-derived ground truth** until the human listen-through is done.
7. **Weights licensing** — never say "fully open" without the non-commercial qualifier.
