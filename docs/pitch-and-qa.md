# StutterTurn — the pitch, and the hard questions

Team-internal prep. The pitch words first, then an adversarial Q&A: every question we'd ask if we were trying to sink this project, with the honest answer. Questions marked **OPEN** have no good answer yet — they are work items, not talking points.

---

## The pitch (3 minutes, the exact words)

"AI already answers the phone in healthcare — one health system's AI agent alone handles 160,000 patient calls a month, and pharmacy refill lines are among the most automated calls in the country. We measured what happens when the caller stutters. On 200 real recordings of people who stutter, the standard open-source turn-taking model — the part that decides 'the caller is done talking' — interrupted 58% of stutter blocks. And no setting fixes it: wait longer, and everyone gets seconds of dead air on every turn.

Imagine calling to refill your own prescription, getting stuck on a word, and the AI talks over you. Over three million Americans stutter. Many just hang up.

So we fine-tuned the open model on real recordings of people who stutter. Same speed for fluent callers — one tenth of a second — but interruptions drop from 58% to X%. [THE TOGGLE MOMENT — judge presses it.] [THE JUDGE'S OWN CALL — they speak, instant answer.]

We're honest about scope: ElevenLabs' closed platform already handles short blocks well — we tested it live and we credit it. Our fix targets the open ecosystem every voice-agent startup builds on. And we ship it two ways: a drop-in model, and the first public benchmark of how voice agents treat people who stutter — so any vendor, including the ones answering those 160,000 calls, can test themselves. Apple fixed this inside Siri and kept it closed. We took Apple's own dataset where Apple stopped."

**The 10-second version (hallway):** "Voice agents hang up on people who stutter — we measured it: 58% of stutter blocks get interrupted. We trained the open turn-taking model to wait, without slowing anyone else down, and published the first benchmark."

---

## Q&A — method and the 58%

**Q: How did you get 58%?**
Apple's SEP-28k dataset: real podcast clips from people who stutter, each labeled by three human annotators. 200 clips with annotator-majority "block" labels; software finds the silent gap inside the block and the moment the speaker resumes — the resume proves the speaker wasn't done. We feed audio up to 0.2 s into the gap (when production agents consult the model) into stock Smart Turn v3.2 with its own preprocessing. It said "turn complete" on 116/200 = 58% (68% with repeated checks during the gap). Reproducible from `benchmark/`.

**Q: Why 0.2 s into the gap? Isn't that cherry-picked?**
It's the production default: pipecat consults the turn model when its voice-activity detector reports 0.2 s of silence. We also report "any check before resume" (68%), which is what a streaming agent actually experiences. Both numbers are in RESULTS.md.

**Q: How do you know your test harness isn't broken?**
Three controls, pre-run: audio cut mid-word (should be "not done") → the model said "done" 31% of the time; genuine sentence ends plus silence (should be "done") → 70%; stutter blocks → 58%. The ordering is correct, so the harness measures real signal — and it shows the model treats a block far more like "done" than like "mid-speech."

**Q: Maybe those pauses were genuinely ambiguous — a human would also think the caller was done.**
Sometimes, yes — and the recording answers it: the speaker audibly continues, so "done" was the wrong call every time by definition of what happened. Separately, people who stutter report this exact experience (58% in a 2026 survey of 53 people who stutter report interrupted or timed-out input). A polite human waits; the model shouldn't be worse than a polite human.

**Q: Your ground truth comes from an energy-based VAD, not human ears.**
True, and we say so. The VAD confirms the gap-and-resume energy structure; the three-annotator block label carries the "this is a stutter" claim; and a human listen-through of the eval clips is Phase 0 of the build — no training before it passes. 10/10 spot-checked clips showed the expected structure.

**Q: All your blocks are under 1.6 seconds. Real blocks last much longer.**
Correct — the dataset's 3-second clips censor long blocks, and we say this everywhere. Two implications we state plainly: our timeout-arm numbers are lower bounds (real-world timeouts do worse), and the multi-second regime is untested for every system including ours. The long-block run (FluencyBank or consented recordings) is in the plan.

**Q: SEP-28k labels are known to be noisy.**
Yes — annotator agreement is imperfect, which is why we required 2-of-3 majority, quality-gated clips, ran the controls, and scheduled the human listen-through. Noise in labels makes our 58% an estimate, not a decimal truth; it does not plausibly explain away a 58-vs-31 gap against the mid-speech control.

**Q: You tested wideband podcast audio. Phone lines are 8 kHz.**
Known and untested — it's in the limits list and the plan (replay through the real phone path). If results shift on narrowband, the benchmark reports both conditions; the demo can run on a 16 kHz web call with that stated.

## Q&A — the fine-tune and how we test against other models

**Q: Your fine-tuned number doesn't exist yet. What if it fails?**
Correct until the 3 PM gate. Pre-registered success: <10% block interruptions with fluent latency within +50 ms of stock and no worse fallback rate — a checkpoint that wins one axis and loses the other fails. Pre-agreed abort at 10 PM: we ship the benchmark + a stock "patient" agent, honestly labeled. The 58% finding stands on its own either way.

**Q: How do you avoid just training "wait longer" into the model?**
That's the central trap and the eval is built against it: every checkpoint is scored on both axes simultaneously, and the training mix is ~50/50 original Smart Turn data vs stutter data so fluent behavior isn't forgotten.

**Q: How do you avoid evaluating on your training data?**
The 200+200 eval clips are held out, and the split is by show — not just by episode — because the same podcast hosts speak across episodes of the same show, so an episode split still leaks speakers. The decision threshold is chosen on a separate dev split, never on the eval set, and the final X% comes from one pre-registered eval run.

**Q: Couldn't a transcript-based (semantic) turn detector solve this better? LiveKit and ElevenLabs use transcripts.**
Maybe partially — a block mid-sentence leaves an incomplete sentence, which semantic models can notice; that's plausibly why ElevenLabs did well on short blocks. Our benchmark is exactly how that question gets answered: we publish the harness and scores for every stack we can legally run (stock Smart Turn, timeouts, our model, ElevenLabs live, Gemini Live when keyed). We're not claiming the only fix; we're claiming the first open fix plus the measuring stick.

**Q: Smart Turn supports 23 languages. Does your fine-tune break the other 22?**
**OPEN.** We train and evaluate English only; other languages are untested and the model card must say "English fine-tune — use stock for other languages" unless we run at least a smoke test. Do not claim multilingual.

**Q: Does your model handle repetitions, prolongations, interjections — or only blocks?**
We target blocks because they're the silence-shaped failure that turn-taking misreads. Other disfluency types are in SEP-28k and in the benchmark's labels, so they're measurable, but our fine-tune's claim is blocks-only until we've evaluated the rest.

**Q: What about background noise, crosstalk, two speakers?**
Podcast audio includes some of this naturally (one spot-checked clip has a high noise floor), but we haven't stress-tested it separately. The demo environment is controlled; the limits list covers it.

**Q: Is your model slower than stock?**
No — same architecture, same size (8M params, ~25 ms per inference on CPU in our runs). The fine-tune changes weights, not cost.

**Q: Why Smart Turn and not some other base?**
It's what the open agent ecosystem (pipecat) actually ships, it's CPU-cheap, BSD-2, and its repo invites fine-tunes — the fix lands where the problem is. Alternatives are either closed (ElevenLabs, Deepgram) or heavier research models that don't drop into production stacks in a weekend.

## Q&A — prior art and "why are you the ones"

**Q: Hasn't Apple already solved this?**
For Siri, partially, and closed: their published work cut Siri's premature cut-offs ~79%, shipped as Siri-only accessibility settings. Nothing exists for third-party agents answering phone lines. We use Apple's own dataset where Apple stopped — open model, public benchmark.

**Q: What's genuinely new here? Fine-tuning a small model is not research.**
The novelty isn't the technique — it's that nobody has applied it where it's needed and published the measurement. We verified the absence: ElevenLabs' docs/changelog (zero stutter mentions in turn-taking), Smart Turn's repo and all public fine-tunes (language variants only), LiveKit/Deepgram/AssemblyAI docs, papers, and hackathon galleries. The field literally asked for this: an accessibility paper publishing two weeks after demo day calls turn-taking's fluency assumption the core flaw in speech tech.

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
Yes — the event requires disclosure, not abstinence. The benchmark was AI-assisted, team-directed and reviewed, built during the event, and it's disclosed on the README, the Devpost, and the judges page.

**Q: Could this harm people who stutter — e.g., agents "detecting" stuttering?**
Our model doesn't classify or flag anyone; it only decides "wait vs respond" from audio, the same decision stock makes, with no stored labels about the caller. The benchmark labels datasets, not callers. We make no diagnostic claims and no medical claims.

**Q: Why AI/ML track and not Social Good?**
The core contribution is a trained model and a benchmark — AI/ML work with an accessibility stake. If the revealed rubric favors Social Good, the project fits there too; the decision is checked against the actual criteria (Phase 0 task).

**Q: Is the demo fake? The caller is a recording.**
The caller is a labeled real recording; the agent's decisions are live — a fresh call per toggle press, decisions made in the room. We do it this way because nobody on the team will fake a stutter, and judges can verify liveness by talking to the agent themselves.

---

## Where we're genuinely exposed (internal, know these cold)

1. **The X% doesn't exist until the fine-tune works.** If it fails, the submission is a benchmark paper with a stock agent — strong honesty, weaker wow.
2. **Short-block censoring.** Our headline is about sub-1.6 s blocks; a judge who realizes long blocks are the worst case is right, and our only defense is "untested everywhere, it's in the plan."
3. **ElevenLabs did well.** If their staff says "so the best commercial system already handles this," our answer is the open ecosystem + the benchmark — it must be delivered confidently or the project sounds like it solved a solved problem.
4. **Speaker leakage** if the split-by-show rule gets skipped under time pressure — the X% becomes indefensible. The eval split is not negotiable.
5. **VAD-derived ground truth** until the human listen-through is done.
6. **Weights licensing** — never say "fully open" without the non-commercial qualifier.
