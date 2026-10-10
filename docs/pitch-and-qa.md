# StutterTurn — the pitch, and the hard questions

Team-internal prep. The pitch words first, then an adversarial Q&A: every question we'd ask if we were trying to sink this project, with the honest answer. Questions marked **OPEN** have no good answer yet — they are work items, not talking points.

**This document has two layers, and they are not interchangeable:**

1. **INTENDED FINAL WORDING** — the ambitious pitch, preserved exactly as drafted. It is the destination. The line-by-line map identifies required evidence and lines that must be revised even in the final delivery.
2. **READY NOW / GATED DEMO SCRIPTS** — a short evidence-backed statement for today, followed by conditional model and baseline scripts. A script is deliverable only when its stated evidence and live-demo gates pass.

Standing rule (D-006): the Smart Turn numbers are exploratory offline **completion predictions**; the ElevenLabs numbers are separately defined server-event timings. Neither establishes human-validated audible interruptions. Human annotations, matched runtime outcomes and rebuilt partitions are pending; label the exact outcome rather than calling it a hang-up. Gates: 2 PM feasibility/scope, 3 PM DEV improvement (model continue or corrected-benchmark commit happens **then**), 10 PM demo-variant lock ([PLAN.md](../PLAN.md), issues #2/#4).

---

## INTENDED FINAL WORDING — the pitch (3 minutes, the exact words)

> Preserved verbatim per Vinh's instruction (D-006). This historical draft is not ready to deliver verbatim. Preserve its ambition; replace unsupported lines and measured placeholders using the map below before delivery.

"AI already answers the phone in healthcare — one health system's AI agent alone handles 160,000 patient calls a month, and pharmacy refill lines are among the most automated calls in the country. We measured what happens when the caller stutters. On 200 real recordings of people who stutter, the standard open-source turn-taking model — the part that decides 'the caller is done talking' — interrupted 58% of stutter blocks. And no setting fixes it: wait longer, and everyone gets seconds of dead air on every turn.

Imagine calling to refill your own prescription, getting stuck on a word, and the AI talks over you. Over three million Americans stutter. Many just hang up.

So we fine-tuned the open model on real recordings of people who stutter. Same speed for fluent callers — one tenth of a second — but interruptions drop from 58% to X%. [THE TOGGLE MOMENT — judge presses it.] [THE JUDGE'S OWN CALL — they speak, instant answer.]

We're honest about scope: ElevenLabs' closed platform already handles short blocks well — we tested it live and we credit it. Our fix targets the open ecosystem every voice-agent startup builds on. And we ship it two ways: a drop-in model, and the first public benchmark of how voice agents treat people who stutter — so any vendor, including the ones answering those 160,000 calls, can test themselves. Apple fixed this inside Siri and kept it closed. We took Apple's own dataset where Apple stopped."

**The 10-second version (hallway):** "Voice agents hang up on people who stutter — we measured it: 58% of stutter blocks get interrupted. We trained the open turn-taking model to wait, without slowing anyone else down, and published the first benchmark."

### Line-by-line gate map for the final wording

Ledger IDs refer to [docs/claims-ledger.md](claims-ledger.md). Evidence gates permit supported wording; they never make an unsupported universal claim or an obsolete denominator valid as written.

| Draft line | Ledger | Status today | Unlocks when |
|---|---|---|---|
| "160,000 patient calls a month" | L-14 | ready | — |
| "pharmacy refill lines are among the most automated calls in the country" | L-19 | **unsupported** | a citable source is saved; otherwise cut |
| "interrupted 58% of stutter blocks" | L-01 | target (ready form: "predicted 'turn complete' during 58% of gaps") | human listen-through + audible-outcome pipeline measurement + partition rebuild/stock rerun |
| "And no setting fixes it" | L-07 | **unsupported**; even the scoped conclusion is pending | matched comparison of named settings and both outcome axes; revise to the supported result |
| "Imagine calling to refill your own prescription…" | — | ready (framing, no factual load) | — |
| "Over three million Americans stutter" | L-15 | ready | — |
| "Many just hang up." | — | **unsupported, no upgrade path** | recommend replacing even in final with L-16 survey wording — Vinh's call |
| "So we fine-tuned the open model…" | L-20/L-25 | target | immutable `stutterturn-vN.onnx` + final-test run |
| "Same speed for fluent callers — one tenth of a second" | L-21/L-03 | target; 0.1 s is a conditional offline crossing time, not deployed latency | verified ends, matched causal timing, full observation/censoring, per-group stock/candidate results |
| "interruptions drop from 58% to X%" | L-20 | target (placeholder) | frozen final test: stock rerun [S]% → candidate [X]% |
| "ElevenLabs… handles short blocks well — we tested it live" | L-08 | ready only as the defined n=20 event-timing observation | human-validated boundaries and audible outcomes before the stronger claim |
| "first public benchmark" / "drop-in model" | L-27/L-23 | target | current scoped prior-art review + publication + corrected method; export/reload + pipeline load |
| "Apple fixed this inside Siri and kept it closed…" | L-17/L-28 | ready only as dataset/prior-work attribution | verify exact outcome and shipped-setting linkage before stronger wording |
| 10-second version: "Voice agents hang up on people who stutter" | G (never-say) | **unsupported** (hang-up translation + overgeneral) | none — use the short ready-now statement below |

---

## READY NOW / GATED DEMO SCRIPTS

### The short version — ready now

> "In our first offline check, we tested an open turn-taking model on 200 real speech clips labeled as containing stutter blocks. It predicted 'done' in 116 energy-detected gaps. We are building StutterTurn to help callers finish speaking; human boundary validation and live response measurements are the next proof."

This is an offline observation and a stated goal. It does not claim a trained model, verified interruption rate or working live rig.

### Script A — successful-model template, not ready now

Deliver only after the development gate, human-validated final-test results and live rig exist. Fill [N], [S], [X], [Y] and [longest tested block] from that same saved evaluation; [Y] must name the completed-turn median-delay comparison for each group. Keep timeout/nonresponse rates visible. The audible stock/candidate contrast requires its own saved trace. If only the internal decision changes, narrate that trace instead of promising speech overlap.

> "Voice agents should let callers finish speaking. In our held-out test of [N] validated unfinished blocks, stock Smart Turn predicted 'done' in [S]%. We fine-tuned the model on real recordings of people who stutter. On the same test, those premature decisions fell to [X]%.
>
> [THE TOGGLE — only with a verified live rig] This is a real recording, credited on screen. Nobody on our team imitates stuttering. Compare STOCK and STUTTERTURN in fresh runs with the same input. The display separates when the model decides from when the agent actually starts speaking. [Describe only the audible difference established for this recording.]
>
> Waiting must not mean leaving the caller unanswered. We tested completed stuttered and fluent turns separately: [Y], with no worse timeout or no-response rates. We also checked that unfinished fluent turns were not cut off more often. Those claims come from the saved comparison, not this one demonstration.
>
> [THE JUDGE'S OWN CALL] Speak to it yourself. This checks the live interaction; the benchmark supplies the broader result.
>
> Our contribution is the measured change and a benchmark others can inspect. We build on Apple's SEP-28k dataset and Smart Turn. Our separate small ElevenLabs test is credited with its own event-timing definition. This evaluation covers [longest tested block] and the stated audio path; it does not establish performance on other conditions. [Name only artifacts actually released, their tested compatibility and resolved use terms.]"

### Script B — corrected-benchmark/comparison template, not ready now

This fallback still needs corrected labels, a reproducible evaluation and matched stock/patient pipeline evidence. Replace [configuration], [N], [outcome] and [delay/nonresponse result] from that comparison. A patient condition is a named setting, not a promise that it succeeds or that custom training is necessary.

> "We set out to make voice agents give people who stutter time to finish. Our first offline experiment found 116 completion predictions in 200 energy-detected gaps. That raised a concrete question, but it did not establish audible interruptions or actual response delays.
>
> We rebuilt the comparison around human-validated turns and the same working agent. Here are STOCK and [configuration], using the same real recording in fresh runs. The second condition is a patient/wait setting, not a trained StutterTurn model. [Describe only the observed difference; show decision, speech-resumption and audible-response events separately.]
>
> On [N] validated examples, [outcome]. For completed stuttered and fluent turns, [delay/nonresponse result]. The table retains missing responses and uncertainty. If an existing setting meets our target, that is a useful finding and we credit it.
>
> [THE JUDGE'S OWN CALL — only with the working rig] Try the interaction yourself. Our contribution is the corrected measurement and comparison, with the method and evidence available for others to check. The fine-tuned improvement has not been demonstrated, and we do not present it as completed work."

If the corrected comparison or agent is unavailable, use the short ready-now statement and show only the saved exploratory results with their limitations. Do not call that a completed corrected benchmark. If a backup video exists, label it as a recording of the same rig; a planned backup is not a delivered artifact.

**Timing:** these revised templates have not been rehearsed. Vinh must time the filled script together with the actual interaction, then shorten it to the confirmed judging limit; the earlier 341-word/44-second estimates no longer apply.

---

## Q&A — method and the 58%

> **Q&A status note:** answers are written for demo night. Until each gate passes, treat every 58%-family number as exploratory internal completion predictions (ledger L-01), rig/toggle statements as plans (L-30), and candidate statements as placeholders (L-20–L-25). Deliver only ledger-ready wording today.

**Q: How did you get 58%?**
The saved CSV records 116/200 Smart Turn completion predictions at +0.2 s into energy-detected gaps in clips labeled as containing blocks. The clip labels do not locate each block, and later energy does not establish that the same speaker was continuing an unfinished turn. The 68% result uses additional offline checkpoints. Neither number is a deployed audible-interruption rate; the exact method and limitations are in ledger L-01/L-02.

**Q: Why 0.2 s into the gap? Isn't that cherry-picked?**
That is the first checkpoint chosen by this harness. Equivalence to the deployed agent is unverified: we must pin its VAD and turn logic and log when checks actually occur. The repeated offline schedule is a separate experimental condition, not evidence of how every streaming agent runs. Fluent checks also start earlier (+0.1 s), so the old latency figure is not a matched runtime comparison (L-02/L-03/L-18).

**Q: How do you know your test harness isn't broken?**
The control attempt needs repair. It cut half a second before the last energy activity without checking whether the cut was mid-word; some cuts fall in saved pauses. Its later cutpoints were not verified sentence or turn ends either. The reported 31% and 70% cannot validate the labels by their ordering. Niko needs human-checked active-speech and true-end controls with per-example outputs (L-10).

**Q: Maybe those pauses were genuinely ambiguous — a human would also think the caller was done.**
Yes. Activity after a pause can be a new turn or another speaker. We need surrounding context and human labels to distinguish unfinished blocks from legitimate turn boundaries. The existing energy trace cannot decide that question.

**Q: Your ground truth comes from an energy-based VAD, not human ears.**
The current boundaries are proxies. Three annotators labeled the clip, not the exact gap selected by our code. The planned 30-example human review tests feasibility; every boundary in a claimed final evaluation needs its own verified label. Ten saved waveform plots are not a listen-through (L-01/L-12).

**Q: All your blocks are under 1.6 seconds. Real blocks last much longer.**
Our selected detected gaps range from 0.30 to 1.59 seconds. Three-second clips and the resumption requirement exclude longer/censored cases. We cannot infer real-world timeout rates or anyone else's long-block performance from that selection. Longer real examples remain a planned test (L-13).

**Q: SEP-28k labels are known to be noisy.**
Agreement on a clip-level Block label does not establish where the block occurs or whether the selected gap is unfinished speech. The current controls do not resolve that ambiguity. We retain the 116/200 arithmetic as an exploratory observation and require contextual annotation before a block-interruption claim.

**Q: You tested wideband podcast audio. Phone lines are 8 kHz.**
Known and untested — it's in the limits list and the plan (replay through the real phone path). If results shift on narrowband, the benchmark reports both conditions; the demo can run on a 16 kHz web call with that stated.

## Q&A — the fine-tune and how we test against other models

**Q: Your fine-tuned number doesn't exist yet. What if it fails?**
Correct until the 3 PM gate. Pre-registered success (issue #2): <10% premature block decisions on DEV, with completed fluent **and stuttered** turns each within +50 ms median of stock and no worse fallback/no-response rate — a checkpoint that wins one axis and loses the other fails. The continue-or-fallback decision happens **at 2 PM (feasibility) and 3 PM (measured DEV improvement)**, not late at night; if it fails, we commit then to the corrected benchmark + a clearly labeled stock/patient agent. 10 PM only locks which demo variant runs. The saved offline observation remains, with its limitations; the corrected fallback still has to be validated.

**Q: How do you avoid just training "wait longer" into the model?**
The planned development gate measures unfinished blocks, completed turns from both groups, unfinished fluent turns, and timeout/nonresponse rates on matched inputs. Completed-turn speed alone is insufficient. Preserve original completion/incompletion training labels, choose checkpoints on DEV only, and record the actual training mix; the proposed ~50/50 recipe is not yet a training result.

**Q: How do you avoid evaluating on your training data?**
The split-by-show rule is non-negotiable for any final number — not just by episode, because the same podcast hosts speak across episodes of the same show, so an episode split still leaks speakers. Honest status: the existing exploratory 200+200 eval spans all eight shows, which is exactly why PLAN.md requires rebuilding show-separated train/DEV/final-test manifests and rerunning stock before any stock-vs-candidate comparison. The decision threshold is chosen on DEV, never on the final test, and the final X% comes from one pre-registered final-test run.

**Q: Couldn't a transcript-based (semantic) turn detector solve this better? LiveKit and ElevenLabs use transcripts.**
That is a comparison to measure. Our offline probabilities and ElevenLabs server-event timings are different outcomes and do not rank the systems fairly. The same validated inputs and endpoint/audio metrics are needed before choosing between a semantic detector, a patient setting or a fine-tuned model.

**Q: Smart Turn supports 23 languages. Does your fine-tune break the other 22?**
**OPEN.** The intended scope is English only; other languages are untested and the model card must say "English fine-tune — use stock for other languages" unless we run at least a smoke test. Do not claim multilingual.

**Q: Does your model handle repetitions, prolongations, interjections — or only blocks?**
We target blocks because they're the silence-shaped failure that turn-taking misreads. Other disfluency types are in SEP-28k and in the benchmark's labels, so they're measurable, but our fine-tune's claim is blocks-only until we've evaluated the rest.

**Q: What about background noise, crosstalk, two speakers?**
Podcast audio includes some of this naturally (one spot-checked clip has a high noise floor), but we haven't stress-tested it separately. The planned demo environment is controlled; the limits list covers it.

**Q: Is your model slower than stock?**
Same architecture, same size (8M params; stock measures ~25 ms per inference on CPU in our runs), so the fine-tune changes weights, not expected cost — and we time the exported candidate before claiming it (ledger L-24).

**Q: Why Smart Turn and not some other base?**
Smart Turn is the base under investigation and an open component used with Pipecat. We must prove trainable-weight recovery, export and integration before promising a drop-in improvement. Other systems and adjustable settings remain relevant baselines; our experiment has not ruled them out.

## Q&A — prior art and "why are you the ones"

**Q: Hasn't Apple already solved this?**
Apple's Siri work is relevant prior art, and SEP-28k provides the clips for our exploratory experiment. Before quoting an exact improvement or linking a research result to a shipped setting, check the primary source and outcome definition. Apple's work does not establish the behavior of other agents (L-17/L-28).

**Q: What's genuinely new here? Fine-tuning a small model is not research.**
The intended contribution is a useful, measured improvement and an inspectable evaluation on stuttered speech. The earlier novelty conclusion in D-003 was superseded by D-006. Any "first" wording needs a current, scoped prior-art review with primary sources, including existing general turn-taking benchmarks. A finished artifact and valid measurement matter before that adjective (L-26/L-27).

**Q: ElevenLabs already does well — why does the open stack matter?**
Agent builders need evidence for the configuration they deploy. Our 20-session ElevenLabs conditions measured server-event timings against inferred boundaries; they neither rank all commercial systems nor establish a stutter-specific failure rate for Pipecat. The intended value is a comparison an open-stack builder can inspect and reproduce.

**Q: Why is a team with no speech-tech background credible here?**
Judge the saved artifacts and their limits. We have exploratory scripts and outputs; corrected labels, a pinned reproduction command and an integrated comparison remain evidence requirements. We will show what ran, how it was evaluated, and what is still pending.

**Q: Nobody on your team stutters. Why should you build this?**
True, and we won't pretend otherwise. We build on recordings and published research from people who stutter, we never imitate stuttering, and the deliverable is infrastructure (model + benchmark) that the community — including organizations like AImpower, who benchmark ASR for stuttered speech — can take further. We're seeking input from the stuttering community; if that lands before submission, their words speak, not ours.

**Q: If this matters, why hasn't pipecat done it?**
We cannot infer maintainers' priorities or establish absence from an unsuccessful search. We can compare the current released options on validated inputs and show whether our proposed change adds value.

## Q&A — adoption, impact, business

**Q: The caller can't install your fix — the clinic's vendor has to. Isn't your user unreachable?**
Adoption would be through agent builders. A reproducible benchmark and a compatible artifact could help them evaluate the change. Compatibility, rights and useful results must be established before promising a one-line integration or commercial adoption.

**Q: How big is the problem really?**
The prevalence and patient-call figures describe context, not the measured failure population. Our 58% is 116 predictions on 200 selected gaps, not 58% of callers and not a population estimate. Do not multiply it by prevalence or call volume.

**Q: What's the business model?**
It's a hackathon accessibility project, not a startup pitch: open model, open benchmark. If asked where value accrues: vendors adopt it to meet accessibility expectations, and the benchmark is the kind of thing advocacy orgs and procurement teams cite.

**Q: What's v2?**
Long-block robustness, other disfluency types, multilingual evaluation, 8 kHz-native training, and getting the benchmark adopted by one vendor or advocacy org. Each is listed because it's real, not because we'll finish it Sunday.

## Q&A — ethics, data, licensing

**Q: Is it OK to use these people's voices?**
SEP-28k is a published research dataset (Apple, ICASSP 2021) built from public podcasts hosted by people who stutter; annotations are CC BY-NC 4.0 and we attribute. Audio is not redistributed in the repo. Resolve the relevant permissions before streaming labeled excerpts in a demo; nobody imitates stuttering.

**Q: Your README says "open model" — but it's trained on non-commercial data. Can you even release the weights?**
Release terms are unresolved. SEP-28k annotations carry CC BY-NC 4.0, but that alone does not determine all audio/demo permissions or trained-weight release rights. Resolve each artifact's terms before distribution; the proposed research/noncommercial release is a plan, not a completed license decision (PLAN.md, issue #5).

**Q: You used AI to build the benchmark overnight. Is that allowed?**
Yes — the event requires disclosure, not abstinence. The benchmark was AI-assisted, team-directed and reviewed, built during the event. It's disclosed in the README now, and goes on the Devpost and the judges page when those exist.

**Q: Could this harm people who stutter — e.g., agents "detecting" stuttering?**
The intended model changes the endpoint decision; it is not a diagnostic or stutter-identification service. Verify actual logging and data handling in the implementation before claiming what is or is not stored. The benchmark labels datasets, not callers. We make no diagnostic claims and no medical claims.

**Q: Why AI/ML track and not Social Good?**
The intended contribution is a trained model and a benchmark, with a corrected-comparison fallback — AI/ML work with an accessibility stake. If the revealed rubric favors Social Good, the project fits there too; fetching the actual main-track rubric is an open task in PLAN.md (Vinh).

**Q: Is the demo fake? The caller is a recording.**
The caller is a labeled real recording; the agent's decisions are live — a fresh call per toggle press, decisions made in the room. We do it this way because nobody on the team will fake a stutter, and judges can verify liveness by talking to the agent themselves. (Rig status: this describes the planned demo — it becomes sayable when issue #4's rig runs and its timestamps are saved; ledger L-30.)

---

## Where we're genuinely exposed (internal, know these cold)

1. **The X% doesn't exist until the fine-tune works** — and the decision is at the 2 PM/3 PM gates, not 10 PM. If it fails, the submission is the corrected benchmark with a labeled stock/patient agent — strong honesty, weaker wow (Script B is written for exactly this).
2. **Everything measured so far is exploratory**: all-eight-show partition, VAD-derived gap labels, internal completion predictions. Until the listen-through, the pipeline-outcome measurement and the partition rebuild land, the 58% is "the model predicted," never "callers were interrupted."
3. **Short-gap selection.** The old selected gaps are under 1.6 s; longer blocks remain untested in our evaluation.
4. **Existing settings may suffice.** The small ElevenLabs event test is not a system ranking. If a matched baseline meets the target, credit it and state what contribution remains.
5. **Speaker leakage** if the split-by-show rule gets skipped under time pressure — the X% becomes indefensible. The eval split is not negotiable, and the current exploratory partition doesn't satisfy it yet.
6. **VAD-derived ground truth** until the human listen-through is done.
7. **Release terms** remain unresolved; a noncommercial qualifier alone does not establish audio/demo or weight-release rights.
