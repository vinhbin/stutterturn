# StutterTurn — team prep packet (pitch, live demo, Q&A)

**For:** Vinh, Guttuu, Niko, Kareem · **Updated:** Sun Oct 11, 2026 · **Evidence:** pinned October 11 hosted replay pair and W3/X1 artifacts; judge-page presentation updated October 11

Read the whole thing once. Know your own section cold, and know **Part 3A** as a team. Every number here comes from a saved file or run in the repo. If a judge asks something not covered, answer only what you know and offer to show the evidence.

**Three rules for every answer:**
1. Say "model decision," not "interruption," unless we heard it.
2. X1 is an **exploratory candidate**. It is not proven, not promoted, and not "better."
3. Real recordings only. Nobody imitates stuttering, ever.

---

# Part 1 — The live pitch (3:00 cap)

Updated for the judge-page model/training story. Keep the approved human opening; the middle now connects training, interruption, and waiting. About 245 spoken words plus a target 40-second replay slot; time the actual delivery before judging. Only quoted text is spoken. Hypothetical call abandonment is motivation, not a measured outcome.

### 0:00–0:43 · Vinh — the person and the problem
*Screen: landing page. No audio playing.*

> More than three million Americans stutter.
>
> Imagine calling to refill a prescription. You get stuck on a word, and the automated voice starts answering before you've finished.
>
> You may have to repeat yourself—or give up on the call. A pause can still be part of speaking.
>
> In our first offline check, Smart Turn predicted “finished” in fifty-eight percent of detected pauses across two hundred block-labeled recordings. These were model decisions; the boundaries still need human review.
>
> StutterTurn asks: can we avoid those premature replies without making every response slower?

### 0:43–1:42 · Guttuu — hear the comparison
*Screen: hosted `/live/`, signed in. Use the same long source, Stock FP32 first, X1 second. Silence gate stays 0.2 s; thresholds are 0.50/0.60. Let each run finish before the next. Do not speak over the audio.*

> This is the same real recording through stock and our experimental candidate, X1. The model and threshold change; the silence wait stays the same. Listen for the speaker continuing, and watch when the agent decides to reply.

*[Target 40 seconds for two complete rehearsed runs. If the pair takes longer, shorten the surrounding spoken sections; never truncate it and claim completion.]*

### 1:42–2:13 · Niko — what we trained
*Screen: `/judge/#training`, then the model pipeline if asked.*

> We adapted Smart Turn with an eighty-twenty mix of original-model replay and stutter-focused examples. X1 blends the fine-tuned checkpoint with stock weights, then runs through ONNX.
>
> In our saved example, X1 holds an early pause that stock answers. We also show the wait for the final reply. X1 is exploratory; human confirmation is still pending.

### 2:13–2:42 · Kareem — show the evidence
*Screen: `/judge/#long-replay`. Point to both the overlap and final-reply timing cards. These are saved runs, not automatically the fresh pair just heard.*

> Vultr runs our inference and voice backend. Gemini generates replies; ElevenLabs voices them.
>
> Tiger Data stores the run events behind this comparison. We expose decisions, resumed speech, overlap, and response timing so you can inspect the tradeoff.

### 2:42–2:57 · Vinh — close
*Screen: landing page or judge-page opening. Stop clicking.*

> The goal is simple: room to finish, and a prompt reply when you're done.
>
> StutterTurn. Let people finish.

**Exact saved-pair answer if asked:** Stock reported 0.050 s scheduled overlap; X1 reported none. From the final VAD speech-stop event at 8.480 s to the next scheduled reply, stock took 1.916 s and X1 2.421 s. Both final decisions came 0.192 s after that detected stop. These are server-scheduled intervals, not acoustic measurements, human-confirmed completion delay, or evidence that the model caused the provider timing difference. Never describe the model score as “percent accurate.”

**If asked about restarting or hanging up:** “That is a consequence we are concerned about, not an outcome our replay measures. We have not measured call abandonment, and we do not claim most callers hang up.”

**Video:** This page/pitch update alone does not require a new video. Review the existing video for claims of validated improvement, call-abandonment rates, or a mislabeled stock/patient comparison before deciding whether a correction is necessary. The final video has not been audited in this pass.

---

# Part 2 — Live demo coordinator sheet

**Coordinator:** Vinh (runs the pre-flight; calls the fallback). **Operator during the pitch:** Guttuu (drives `/live/` in his slot). **Backups:** Niko (X1 tab), Kareem (`/judge/` tab).

**The live demo is the base model vs. our candidate:** Stock Smart Turn v3.2 (FP32) first, then StutterTurn candidate (X1), on the same recording. Patient is cut for time. This replaces the stock/patient plan in `docs/team-pitch-script.md`.

**Primary path: the hosted console on Vultr.** Both the site and the voice backend run on our Vultr server. The console streams the recording and the agent's reply to your browser, so sound comes out of whatever laptop is presenting. You don't need a local backend. The local setup below is backup #1, and saved evidence is backup #2.

## Pre-flight (start 30 minutes before judges)

| # | Do this | Check |
|---|---|---|
| 1 | Open https://64-177-51-1.sslip.io/live/ and sign in with the **demo credentials** (Vinh shares them privately; never write them in a doc or the repo). | Console loads behind the login |
| 2 | Click anywhere on the page once (browsers only allow audio after a click), then set the laptop's volume and connect to the room speakers. | — |
| 3 | Pick source `demo-long-WomenWhoStutter_19_1238s.wav` (the clip from our video; about 15 s per run). If it isn't listed, use `HeStutters_4_32.wav` (about 8 s per run). Rehearse **Stock FP32 → candidate** once each. | You **hear** both the recording and the reply; write both run IDs down |
| 4 | Only one run can play at a time on the server. Make sure no teammate is running a test during the pitch. | — |
| 5 | Open backup tabs: replay-v2 evidence, the X1 result comment, and the hosted `/judge/` (https://64-177-51-1.sslip.io/judge/). | All load |
| 6 | Close every unrelated app and notification. Laptop on power. Volume set. | — |

**Backup #1, local backend** (only if the hosted console fails; same laptop as the speakers):
1. Check nothing holds port 8765: `netstat -ano | findstr 8765`
2. Start the backend: `agent\.venv\Scripts\python.exe agent\server.py --services on --play`. Confirm `/v0/health` shows services and playback on.
3. Start the site: `agent\.venv\Scripts\python.exe -m http.server 8041 --bind 127.0.0.1 --directory web`
4. Open `http://127.0.0.1:8041/live/`, then **Connection & preview** → `http://127.0.0.1:8765` → **Connect**, with preview off.

**If the hosted agent misbehaves** (for example a Gemini timeout or no reply), restart it over SSH: `ssh root@64.177.51.1`, then `systemctl restart stutterturn-agent`. Do this before or after the pitch, never during it. A restart also resets the per-process ElevenLabs character cap.

## During the pitch

| Clock | Speaker | Operator does | If it goes wrong |
|---|---|---|---|
| 0:00 | Vinh | Landing page up | — |
| 0:43 | Guttuu | Switch to `/live/`. **Stock Smart Turn v3.2 (FP32)** → **Start fresh run** | Gemini timeout → keep talking; finish on the decision row. Restart the server after the pitch, not during. |
| ~1:05 | Guttuu | When the run ends, note the run ID. Select **StutterTurn candidate**, same source → **Start fresh run** | No audio → check the laptop's output device and that you clicked the page first. Otherwise point at the timeline. |
| 1:42 | Niko | Switch to `/judge/#training` | — |
| 2:13 | Kareem | Switch to `/judge/` → evidence links → Tiger chart | Hosted page down → local `http://127.0.0.1:8041/judge/` |
| 2:42 | Vinh | Landing page. Hands off. | — |

**Fallback line if the backend is down** (Guttuu says it instead of the live lines): *"These are saved runs of the same recording through the stock model and our candidate. They show model decisions and reported response events; this is not a live execution."* Then show the saved long-replay comparison on the hosted `/judge/` page. Do not debug in front of judges.

**What to expect on the long clip** (from our saved runs; don't promise it out loud, it can vary):
- **Stock:** decides "COMPLETE" at about 1.7 s, mid-block, around 0.9 confidence. The reply usually gets cancelled when she resumes, so you may not *hear* a cut-off. The decision row shows it either way.
- **Candidate:** "WAIT" at the same moment (0.54, below its 0.6 cutoff). It makes a later early call at about 7.1 s that gets cancelled before any audio, then decides at about 8.7 s and speaks around 10.7 s.

Say "watch the decision row," not "listen for the interruption."

**Framing rule for this demo:** X1 remains exploratory. Show both the early hold and final reply timing. Describe the observed pair precisely; broader improvement and human confirmation remain unestablished. The spoken explanation in Part 1 and the visible evidence labels carry this distinction.

---

# Part 3 — Q&A bank

## 3A · Whole team — the questions judges are most likely to ask (everyone knows these)

**Q: In one sentence, what is StutterTurn?**
An open benchmark and a fine-tuned version of Smart Turn, the open turn-taking model voice agents use to decide when a caller is done, aimed at not cutting off people who stutter.

**Q: What's the actual problem?**
A stutter block is a silent pause mid-word. Turn-taking models hear silence and decide the caller is finished. On 200 real recordings labeled with stutter blocks, stock Smart Turn (INT8 build) predicted "finished" in 116 detected pauses (58%). Those are model decisions, not measured interruptions.

**Q: Did you test with people who stutter?**
No. We used real recorded speech from Apple's SEP-28k dataset, which is not the same as a user study. We haven't done one, and we don't make medical or therapeutic claims.

**Q: Is your model better than the original?**
Not proven. On development data, X1 at its threshold made premature decisions on 31.3% of stutter blocks versus 47.4% for stock. But it was picked after seeing results (a fifth look at that data), its safety margins are thin, and the human-labeled confirmation set and audio acceptance aren't done. So it's an exploratory candidate, not a validated improvement.

**Q: Why not just make the agent wait longer?**
It's a real baseline, and we measured it. On the same development items, stock checking after 0.8 s instead of 0.2 s made premature decisions on 12.8% of stutter blocks, which is better than X1's 31.3%. The cost is speed: every caller's first check comes 0.6 s later. X1 keeps the 0.2 s check, and it decides at that check on 53.2% of completed-turn proxies (stock with the 0.8 s wait decides on 48.2%, and only at 0.8 s). When the model says "not done," every setting falls back to the same 3 s timer. So the wait is better at not cutting people off, and X1 is quicker for people who've finished. Neither dominates; they're different trade-off points and can be combined. We have not shown that changing the wait is insufficient. These are configured check times on proxy labels, not measured response delays.

**Q: What's new here? Hasn't someone done this?**
Apple improved Siri for atypical speech, but that work is closed. In our web search (Oct 10) we didn't find a public benchmark of how open turn-taking models treat stuttered speech. We built one, plus a pre-registered, show-separated evaluation with a sealed test set. Say "the first public benchmark we found," never "the first ever."

**Q: Is any of this production-ready?**
No. It's a research prototype. SEP-28k is CC BY-NC (non-commercial), and our model isn't released.

**Q: Are the recordings real? Is any footage or voice AI-generated?**
Every stuttered recording is real SEP-28k audio, labeled on screen, and nobody imitates stuttering. In the video, the mood b-roll (pharmacy, phone, server room, waveform, sunrise) was generated with Higgsfield, and two narration segments ("Just wait longer?" and "How we built it") use Vinh's ElevenLabs voice clone with his consent. Everything else is real: the product footage, the run data, and every other voice. If asked, say exactly this.

**Q: What would you do with another week?**
Finish the human-labeled confirmation set and audio acceptance for X1, run a held-out-show evaluation, test long blocks (3+ seconds, untested by anyone including us), test 8 kHz phone audio, and release the benchmark and model card.

## 3B · The model — what we built and how

**Q: What model did you use?**
Smart Turn v3.2 from pipecat-ai (BSD-2): about 8M parameters, a Whisper-Tiny audio encoder with a classifier head. It listens to the last 8 seconds of audio and outputs one probability that the caller has finished. We didn't build a new architecture. We fine-tuned this one so it stays a drop-in.

**Q: How did you train it?**
We recovered the official FP32 weights into PyTorch (reconstruction matched the official model within 1.2e-7) and fine-tuned from those stock weights on Guttuu's RTX 4070 laptop with PyTorch 2.8. The W3 recipe used learning rate 1e-5, 2 epochs, seed 0, and a sampling mix of 80% original Smart Turn replay data, 10% SEP-28k stutter "unfinished" examples, and 10% SEP-28k completed-speech proxies. Training data came from training shows only.

**Q: What is X1 exactly?**
A weight interpolation (α = 0.75) between stock FP32 and the W3 epoch-1 checkpoint, run at a decision threshold of 0.6 (stock uses 0.5). It's exported to ONNX (export matched PyTorch within 1e-5), runs on CPU, and is a 32 MB file with the same input and output as stock Smart Turn.

**Q: Why so many attempts? What went wrong?**
- **v1:** trained only on stutter-block cuts as "unfinished." It learned a shortcut, roughly "podcast audio means not done," and stopped recognizing finished turns.
- **v2:** balanced the podcast data and fixed that, but failed the general-speech safety guard.
- **W3 (v3):** the 80/10/10 mix. Its nearest miss reached 20.2% but failed the guard by 5 examples.
- **v4:** six weight blends; none passed.
- **X1:** a post-hoc check of an existing v4 blend at threshold 0.6. It passed.
- **v5:** preparation stopped at a failed pre-registered data gate. No training ran.

We published every failure.

**Q: What's different between X1 and the original model?**
Same architecture, size, input, and speed class. Different weights (fine-tuned plus interpolated) and a higher threshold (0.6 vs 0.5). On development data:

| | Stock FP32 @ 0.5 | X1 @ 0.6 |
|---|---|---|
| Premature on stutter blocks (M1) | 47.4% | 31.3% |
| Premature on fluent pauses (M2) | 50.5% | 43.0% |
| Completed proxies decided at first check (M3) | 46.6% | 53.2% |
| Guard recall (M4) | 95.1% | 94.3% |
| Guard specificity (M5) | 93.5% | 93.7% (+3 examples) |

The guard margins are thin; M5 is effectively a tie.

**Q: Why INT8 vs FP32? Why two stock numbers?**
The shipped CPU file is INT8 (compressed). The same weights in FP32 make fewer premature decisions: 87/200 (43.5%) vs 116/200 (58%) on the exploratory clips. So we compare our candidate against **FP32**. Otherwise undoing the compression would look like a training gain.

## 3C · Evaluation — how we measured it

**Q: How did you avoid testing on your training data?**
We split by **podcast show**, not by clip, because the same hosts speak across episodes:
- **Training shows:** WomenWhoStutter, HeStutters, IStutterSoWhat, HVSA
- **Development:** StutteringIsCool, MyStutteringLife
- **Final test:** StrongVoices, StutterTalk. These stay **sealed**; we haven't opened them.

**Q: What do you measure?**
Both sides of the trade-off, on development items:
- **M1:** premature "finished" on stutter blocks (352)
- **M2:** premature on fluent pauses (1,518)
- **M3:** completed proxies decided at the first check (680)
- **M4 / M5:** recall and specificity on a general-speech guard set from Smart Turn's own test audio (about 1,500 each)

**Q: What were the pass rules?**
They were fixed before each run. A candidate must beat the best stock setting (threshold 0.55, M1 45.7%) on M1, with paired evidence. It can't worsen the other metrics beyond set bounds (M2 ≤ +1.0 pt, M3 ≥ −2.0, M4 ≥ −1.0, M4b ≥ −1.0, M5 ≥ 0). We never relaxed a rule after seeing results.

**Q: How strong is X1's result statistically?**
Against stock's best setting, X1 avoided a premature decision on 67 blocks where stock made one, and the reverse happened 16 times (McNemar p = 1.4e-8). The guard tie (13 lost, 16 gained) is not significant (p ≈ 0.71). An independent recomputation from the raw logs matched exactly.

**Q: Does it hold up with the agent's real input?**
Promotion check (b): with the agent's actual audio window ("turn onset"), stock is at 50.3% and X1 at 34.7%. X1's shift stayed within the pre-registered allowance.

**Q: What are the labels? Are they human-checked?**
The block timings are automatic, energy-derived proxies from SEP-28k's clip labels. Human review isn't done. That's exactly what the confirmation set is for, and why we don't make efficacy claims.

**Q: What's still missing before you'd call it better?**
Check (c), audio acceptance on the live agent, and check (d), a human-labeled confirmation set never used in any selection. Then one sealed final-test run.

## 3D · Why we stand out

**Q: Why should we pick you?**
- **A real, specific problem**, measured on real recordings.
- **A drop-in fix to the open model** voice agents already use, rather than a new app.
- **Unusual scientific discipline for a hackathon:** pre-registered pass rules, show-separated splits, a sealed test set, and every failed attempt published.
- **Decision vs. audible outcome:** we separate the model's decision from what a caller actually hears.

**Q: Isn't this just a threshold tweak?**
No, and we checked. Raising stock's threshold to its best qualifying setting (0.55) only reaches 45.7%. Pushing stock to 0.95 gets 22.2% premature, but it then decides at first check on only 27.9% of finished turns. X1 is fine-tuned weights plus a threshold, and the selection rule required beating stock's best threshold.

**Q: What can other developers do with this?**
Run their own turn-taking stack against the benchmark, and (once released) load the model anywhere stock Smart Turn loads. It has the same input and output.

## 3E · Technical — the agent and the pipeline

**Q: What happens when you press Run?**
1. The backend replays a recording in real time in 20 ms frames.
2. Silero VAD detects speech and silence.
3. After 0.2 s of silence (1.0 s for patient), Smart Turn decides finished or not.
4. If it decides finished, Gemini writes a reply and ElevenLabs speaks it.

Every event (decision, generation, playback, cancellation) is logged separately as JSONL and streamed to the browser over a WebSocket. On the hosted version, all of this runs on our Vultr server, and the recording plus the agent's reply are streamed to your browser and played there.

**Q: Why is there still a ~2 s pause before the agent answers?**
Separate the decision from scheduled playback. In the pinned pair, the final VAD speech-stop event is at 8.480 s and both configurations decide at 8.672 s: 0.192 s later. Reply audio is scheduled at 10.396 s for stock and 10.901 s for X1, giving intervals of 1.916 s and 2.421 s from that detected stop. Provider and scheduling time contribute; this is not measured acoustic latency or a human-labeled turn ending.

**Q: What does "COMPLETE 0.83" mean?**
A turn-completion score, not seconds or measured accuracy. The model outputs 0.83 and X1 crosses its decision threshold at 0.60. We have not established that this score is calibrated to an 83% chance of being correct.

**Q: Why separate a decision from an interruption?**
A premature decision starts reply generation, but if the caller resumes before the audio starts, the reply is cancelled and nobody hears it. In replay v2, stock decided "finished" inside the gap on 4 of 5 clips, but 3 replies were cancelled before audio. Fast reply paths would turn more of those into audible cut-offs.

**Q: Did X1 ever decide early in the demo clip?**
Yes, once at 7.07 s at a later pause (confidence 0.97). She resumed at 7.68 s, so that reply was cancelled before any audio. We say "it holds through the block," not "it never decides early."

**Q: Is it phone-ready?**
Not tested. Our audio is wideband. 8 kHz phone audio and long blocks (3+ s) are untested.

**Q: How fast is the model?**
About 25 ms per inference on CPU for stock in our runs. X1 has the same architecture and size.

## 3F · Sponsors

**Q: How did you use ElevenLabs?**
ElevenLabs is the agent's voice: every live reply is synthesized with `eleven_flash_v2_5`, and timing events are logged per run. Earlier we also measured ElevenLabs' own agents platform on 20 real stutter clips. Its stock setting cut in on short blocks only 5–10% of the time, which we credit openly. That's our own small, unpublished test.

**Q: How did you use Gemini?**
Gemini (`gemini-3.8-flash`, thinking off) writes the agent's replies. Our reply prompt tells it never to comment on how the caller speaks. We didn't train Gemini.

**Q: How did you use Vultr?**
Vultr hosts the whole product on one Ubuntu 24.04 server in Atlanta (1 CPU, 1 GB RAM, no GPU) at https://64-177-51-1.sslip.io:
- **Frontend:** the landing page, judge guide, and run console, served over HTTPS by Caddy.
- **Backend:** the voice agent (Silero VAD, Smart Turn and X1 in ONNX on CPU, Gemini, ElevenLabs), running as a systemd service.

The console streams the recording and the reply to your browser. Model calls took about 176–213 ms on that CPU in our deployment check, and 30 of 30 backend tests passed on the server.

**Q: Can anyone on the internet use your hosted agent and run up your API bill?**
No. The landing page and judge guide are public, but the run console, run endpoints, and WebSocket require a login (HTTPS basic authentication). The Python server only listens on the machine itself, behind Caddy. It allows one run at a time, rejects connections from other websites, and keeps the API keys on the server, never in the browser or the repo.

**Q: How did you use Tiger Data?**
As the database for run logs. See 3G.

## 3G · Database (Tiger Data / TimescaleDB)

**Q: What's in the database?**
Every saved agent run: a `runs` table (config, model hash, commit, summary) and an `events` **hypertable** with one row per event (VAD, decisions, cancellations, audio), keyed by wall-clock time plus the event offset. Niko ingested 20 runs, 302 events.

**Q: Why a time-series database?**
A run *is* a time series: what matters is the ordering and gaps between "speech stopped," "model decided," and "audio started." The judge questions are SQL views: decision timeline, first completion per clip, decision-to-audio gap, cancellations before audio, and run outcomes.

**Q: Is the chart live?**
No. It's a saved snapshot of those Tiger Data queries (generated 2026-10-10 21:43 UTC), labeled as such. It is not a live database health indicator.

**Q: How do I reproduce it?**
`web/tiger/` has the schema, `ingest.py` (with a no-database dry run), and `snapshot.py`. Point them at a Tiger service and rerun.

## 3H · Questions for each person

### Vinh — product, console, pitch, hosting, video
- **"What did you personally build?"** Coordinated the product and integration, built out the run console and interface, deployed the site on Vultr, prepared the evidence and pitch, and produced the video. Kareem contributed the original judge pages and evidence organization.
- **"Why a console instead of an app?"** Judges and developers need to see the decision and the audio separately. A chat app would hide the very thing we measure.
- **"What's the goal?"** Fewer audible interruptions for people who stutter, prompt answers at real turn endings, and ordinary conversation preserved, all measured openly.
- **"Who decided what to claim?"** We kept a claims ledger: every public sentence maps to a saved file or run. Rules were set before results, and we recorded decisions (D-001…D-014) in the decision log.

### Guttuu — the agent, training execution, audio
- **"What actually happens when you press Run?"** See 3E. He built the replay engine, the server contract, Silero/Smart Turn/Gemini/ElevenLabs wiring, and speaker playback.
- **"Did you train Gemini or ElevenLabs?"** No. We adapted Smart Turn only; Gemini writes replies and ElevenLabs speaks them. Guttuu built and ran the training harness on his RTX 4070.
- **"Does the demo clip prove X1 waits until people finish?"** No. It shows a different first-pause decision on one selected clip. The clip is a cropped excerpt from a training-side show, and its endpoint isn't a human-verified turn end.
- **"How do you know playback works?"** Guttuu did a human listening check (source and reply audible, Stop and restart work). Audible cancellation on natural resumption is still untested.

### Niko — evaluation, data separation, Tiger Data
- **"What did the 80/20 mean?"** A training *sampling* mix: 80% original replay, 10% stutter-unfinished, 10% completed proxies. It is not a train/test split.
- **"Did the adapted model improve?"** X1 passed the exploratory development rule and checks (a) and (b), on a fifth adaptive look at development data. Human confirmation and audio acceptance are pending, so no claim of fewer real interruptions yet.
- **"How do you prevent leakage?"** Show-separated splits, frozen manifests with hashes, tracking of which examples each attempt saw, and a sealed test set. Re-labeling an already-used clip doesn't make it unseen.
- **"What does Tiger Data do?"** Stores the run events so we can query decision-to-response sequences. Niko ingested the logs and produced the snapshot behind the judge chart.

### Kareem — pages, evidence, reproducibility
- **"What's the difference between these pages?"** The landing page introduces the problem. The judge page guides you through results and evidence. The console runs the replay.
- **"How can we verify what you showed?"** Every claim on the judge page links to a saved run or report in the repo, with the input, model, configuration, and outcome identified. Saved results are labeled separately from the live run.
- **"What's next for the evidence?"** Packaging the full run logs with hashes and source provenance so anyone can re-run the comparison.

## 3I · Data, ethics, licensing

**Q: Where does the data come from, and can you use it?**
Apple's SEP-28k: real podcast clips from people who stutter, labeled by three annotators. Its license is CC BY-NC (non-commercial). We don't redistribute the audio; scripts fetch it. The Smart Turn model and data are BSD-2 and CC-BY-4.0.

**Q: Isn't it risky to build "for" people who stutter without them?**
Yes, and we say so. No one on the team stutters. We use only real recordings, never imitation, and the next step is input from the stuttering community before any claims about their experience.

**Q: Did you test real clinic phone lines?**
No, deliberately. Probing a live patient phone line without consent would be wrong. We test the open model those systems can be built on, and we publish the method so vendors can test their own stacks.

---

# Archive — October 10 drafts (superseded by the packet above; kept for history)

Earlier pitch drafts, gated scripts and Q&A. Where anything here conflicts with the packet above, the packet wins.

## StutterTurn — the pitch, and the hard questions

**For Vinh's approved first-speaker opening, use [the pitch script](pitch-script.md).** It contains the approximately 90-second spoken text, sources, delivery notes, and presentation-method references. The ambitious historical draft below remains evidence-gated.

Team-internal prep. The pitch words first, then an adversarial Q&A: every question we'd ask if we were trying to sink this project, with the honest answer. Questions marked **OPEN** have no good answer yet — they are work items, not talking points.

**This document has two layers, and they are not interchangeable:**

1. **INTENDED FINAL WORDING** — the ambitious pitch, preserved exactly as drafted. It is the destination. The line-by-line map identifies required evidence and lines that must be revised even in the final delivery.
2. **READY NOW / GATED DEMO SCRIPTS** — a short evidence-backed statement for today, followed by conditional model and baseline scripts. A script is deliverable only when its stated evidence and live-demo gates pass.

Standing rule (D-006): the Smart Turn numbers are exploratory offline **completion predictions**; the ElevenLabs numbers are separately defined server-event timings. Neither establishes human-validated audible interruptions. Human annotations, matched runtime outcomes and rebuilt partitions are pending; label the exact outcome rather than calling it a hang-up. Gates: 2 PM feasibility/scope, 3 PM DEV improvement (model continue or corrected-benchmark commit happens **then**), 10 PM demo-variant lock ([PLAN.md](../PLAN.md), issues #2/#4).

---

### INTENDED FINAL WORDING — the pitch (3 minutes, the exact words)

> Preserved verbatim per Vinh's instruction (D-006). This historical draft is not ready to deliver verbatim. Preserve its ambition; replace unsupported lines and measured placeholders using the map below before delivery.

"AI already answers the phone in healthcare — one health system's AI agent alone handles 160,000 patient calls a month, and pharmacy refill lines are among the most automated calls in the country. We measured what happens when the caller stutters. On 200 real recordings of people who stutter, the standard open-source turn-taking model — the part that decides 'the caller is done talking' — interrupted 58% of stutter blocks. And no setting fixes it: wait longer, and everyone gets seconds of dead air on every turn.

Imagine calling to refill your own prescription, getting stuck on a word, and the AI talks over you. Over three million Americans stutter. Many just hang up.

So we fine-tuned the open model on real recordings of people who stutter. Same speed for fluent callers — one tenth of a second — but interruptions drop from 58% to X%. [THE TOGGLE MOMENT — judge presses it.] [THE JUDGE'S OWN CALL — they speak, instant answer.]

We're honest about scope: ElevenLabs' closed platform already handles short blocks well — we tested it live and we credit it. Our fix targets the open ecosystem every voice-agent startup builds on. And we ship it two ways: a drop-in model, and the first public benchmark of how voice agents treat people who stutter — so any vendor, including the ones answering those 160,000 calls, can test themselves. Apple fixed this inside Siri and kept it closed. We took Apple's own dataset where Apple stopped."

**The 10-second version (hallway):** "Voice agents hang up on people who stutter — we measured it: 58% of stutter blocks get interrupted. We trained the open turn-taking model to wait, without slowing anyone else down, and published the first benchmark."

#### Line-by-line gate map for the final wording

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

### READY NOW / GATED DEMO SCRIPTS

#### The short version — ready now

> "In our first offline check, we tested an open turn-taking model on 200 real speech clips labeled as containing stutter blocks. It predicted 'done' in 116 energy-detected gaps. We are building StutterTurn to help callers finish speaking; human boundary validation and live response measurements are the next proof."

This is an offline observation and a stated goal. It does not claim a trained model, verified interruption rate or working live rig.

#### Script A — successful-model template, not ready now

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

#### Script B — corrected-benchmark/comparison template, not ready now

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

### Q&A — method and the 58%

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

**Q: Your own agent replay showed no audible interruption — doesn't that mean stock is fine?**
No. In the saved [replay v2](../agent/evidence/2026-10-10-replay-v2/README.md) (5 SEP-28k block clips × stock/patient, executed on `bcf50d1`; it supersedes the first replay, whose model input lacked the pre-roll), stock decided "complete" inside the labelled gap in 4 of 5 clips. In 3 of those, the speaker resumed before the reply arrived and it was cancelled before any audio; in the fourth, the 3 s clip ended before overlap could be observed. The roughly 1.6–3.5 s reply delay is what hid those premature decisions — a faster reply path or a longer block would make them audible, and that was not tested. Patient made no early in-gap decision on these 5 clips, but 5 clips support no rates, and this does not show that the patient configuration prevents interruptions. Labels remain exploratory, energy-derived and not human-reviewed.

### Q&A — the fine-tune and how we test against other models

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

### Q&A — prior art and "why are you the ones"

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

### Q&A — adoption, impact, business

**Q: The caller can't install your fix — the clinic's vendor has to. Isn't your user unreachable?**
Adoption would be through agent builders. A reproducible benchmark and a compatible artifact could help them evaluate the change. Compatibility, rights and useful results must be established before promising a one-line integration or commercial adoption.

**Q: How big is the problem really?**
The prevalence and patient-call figures describe context, not the measured failure population. Our 58% is 116 predictions on 200 selected gaps, not 58% of callers and not a population estimate. Do not multiply it by prevalence or call volume.

**Q: What's the business model?**
It's a hackathon accessibility project, not a startup pitch: open model, open benchmark. If asked where value accrues: vendors adopt it to meet accessibility expectations, and the benchmark is the kind of thing advocacy orgs and procurement teams cite.

**Q: What's v2?**
Long-block robustness, other disfluency types, multilingual evaluation, 8 kHz-native training, and getting the benchmark adopted by one vendor or advocacy org. Each is listed because it's real, not because we'll finish it Sunday.

### Q&A — ethics, data, licensing

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

### Where we're genuinely exposed (internal, know these cold)

1. **The X% doesn't exist until the fine-tune works** — and the decision is at the 2 PM/3 PM gates, not 10 PM. If it fails, the submission is the corrected benchmark with a labeled stock/patient agent — strong honesty, weaker wow (Script B is written for exactly this).
2. **Everything measured so far is exploratory**: all-eight-show partition, VAD-derived gap labels, internal completion predictions. Until the listen-through, the pipeline-outcome measurement and the partition rebuild land, the 58% is "the model predicted," never "callers were interrupted."
3. **Short-gap selection.** The old selected gaps are under 1.6 s; longer blocks remain untested in our evaluation.
4. **Existing settings may suffice.** The small ElevenLabs event test is not a system ranking. If a matched baseline meets the target, credit it and state what contribution remains.
5. **Speaker leakage** if the split-by-show rule gets skipped under time pressure — the X% becomes indefensible. The eval split is not negotiable, and the current exploratory partition doesn't satisfy it yet.
6. **VAD-derived ground truth** until the human listen-through is done.
7. **Release terms** remain unresolved; a noncommercial qualifier alone does not establish audio/demo or weight-release rights.
