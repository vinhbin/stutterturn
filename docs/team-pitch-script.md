# StutterTurn: four-person team pitch

Updated October 11, 2026. Presenters confirmed by Vinh: **Vinh, Guttuu, Niko and Kareem**. This is the team cut; the approved [Vinh opening](pitch-script.md) is preserved separately.

**Format:** the project's planned three-minute presentation. Target finish: **2:57**, including an 18-second replay and speaker handoffs. Times below are rehearsal targets, not a measured delivery. Only the blockquotes are spoken.

**Evidence snapshot:** main `b5a4dde`, the [X1 result](https://github.com/vinhbin/stutterturn/issues/2#issuecomment-6104584978), [Niko's verification](https://github.com/vinhbin/stutterturn/issues/2#issuecomment-6104602369), and local replay records from October 11 at 00:14-00:15 EDT. **X1 passed exploratory development selection and promotion checks (a)/(b). Audio acceptance (c) and human confirmation (d) remain incomplete.** V1-v4 produced no qualifying candidate; v5 preparation stopped at its failed crop gate, with no v5 training. A/B listening was deferred, not completed; the separate confirmation review remains pending. The main script below discusses **saved stock-FP32/X1 research runs**, not a promoted model or a general improvement claim. A stock/patient fallback is supplied below. Recheck evidence before presenting.

## Spoken script and screen cues

### 0:00-0:57 | Vinh: the problem and purpose

*Screen: landing page. Use the actual app, with no audio playing yet.*

> More than three million Americans stutter.
>
> Imagine calling to refill a prescription. You get stuck on a word, and the automated voice starts answering before you've finished.
>
> That pause can still be part of speaking.
>
> These systems already handle important conversations: WellSpan reports over a hundred and sixty thousand patient calls a month through one AI agent.
>
> In our first offline check of two hundred recordings labeled with stutter blocks, Smart Turn predicted "finished" in a hundred and sixteen detected pauses: fifty-eight percent. Those are model decisions, not measured interruptions, and the boundaries still need human review.
>
> We're building StutterTurn to give people time to finish.
>
> Guttuu will show you how we test that.

### 0:57-1:42 | Guttuu: the working agent and comparison

*Screen: a verified recording or trace review of the selected first pause in the saved research runs listed below. Label **"Selected first-pause excerpt | Stock FP32 @0.5 / Experimental X1 @0.6 | Human turn-boundary review pending"**. These are different models at different thresholds, with the same configured silence wait. Keep their separate run identities visible. Use the stock/patient fallback if these saved records and their source cannot be presented clearly.*

> I built our replay agent with Gemini replies and ElevenLabs speech.
>
> Here are saved runs of stock and our experimental X1 candidate. At the first pause, stock predicts complete while X1 holds.

*[Allow 18 seconds for the selected first-pause comparison, including the following speech resumption. Stop speaking if verified run audio is playing. Retain the full run records and source context for review. An excerpt is not a clean end-to-end result; the qualification below must remain. Do not manufacture reply audio from model-only logs or imitate stuttering.]*

> Both complete at later pauses. This cropped example still needs human validation.

### 1:42-2:21 | Niko: training and evaluation

*Screen: the cited X1 result and current promotion status. Keep the required description visible: **"Post-hoc exploratory candidate selected after v4 results; fifth adaptive look at dev/guard; not a v4 pass."** Human confirmation and audio acceptance remain pending. Do not label exploratory differences as validated improvements.*

> I built the evaluation pipeline and helped establish the training and export path.
>
> One experiment mixed eighty percent original-model replay data with twenty percent stutter-focused examples.
>
> We test early decisions and missed completions on development examples. Waiting longer can trade fewer early decisions for slower replies.
>
> X1 passed a post-hoc exploratory development check. Human confirmation and audio acceptance are still pending. Our reserved final test remains sealed.
>
> I also ingested our saved run logs into Tiger Data so the comparison can be inspected.

### 2:21-2:46 | Kareem: making the work inspectable

*Screen: `/judge/`. Point to the evidence links, then the chart labeled as a saved database snapshot.*

> I worked on our landing and judge pages and organized links to the evidence.
>
> The judge page explains the results. The run console operates the replay. This chart is a saved Tiger Data snapshot.
>
> Our goal is a reusable turn-taking model that developers can evaluate and integrate.

### 2:46-2:57 | Vinh: close

*Screen: landing page or its "Let people finish" line. Stop clicking.*

> We want voice agents to answer promptly when someone finishes, and give them room when they haven't.
>
> StutterTurn: let people finish.

## Stock/patient fallback for Guttuu

Use this instead of Guttuu's entire section if presenting the established stock/patient agent. Do not combine its configuration description with X1 footage. Current code uses the same INT8 model and threshold in both configurations, with configured silence waits of 0.2 and 1.0 seconds; those settings are not measured response delays.

**Before the replay:** "I built our replay agent. Recorded speech goes through speech detection and Smart Turn; Gemini creates a reply, and ElevenLabs voices it. Here we're comparing the standard model with a longer-wait setting. Watch the decision and audio timelines separately."

**After the replay:** "That's the working pipeline we're testing our adapted model against."

Label saved playback **"Recorded demo"**. If services are off, use **"Model-only replay; no generated reply audio"** and explain the Gemini/ElevenLabs path as a separate implemented capability. An interface preview is not run evidence.

## Who owns which judge questions

These answers are outside the three-minute script. Answer the question directly, then offer the relevant evidence.

### Vinh: problem, product and team contribution

**"What did you personally work on?"**

"I coordinated the product and integration, built out the run console and interface, and prepared the evidence and pitch. Kareem contributed the original judge-facing pages and evidence organization. We kept the operating console separate from the judge guide so someone can understand a run without operating the backend."

**"Have you tested this with people who stutter?"**

"We have used real recorded speech from SEP-28k. That is different from testing the product with participants who stutter. We have not completed that user study or the human endpoint review needed for our efficacy claim."

**"What is the goal?"**

"Fewer audible interruptions during unfinished speech, prompt responses at real turn endings, and ordinary conversation preserved. We are working toward an open model and a reproducible way to measure that tradeoff."

### Guttuu: agent, training execution and audio behavior

**"What actually happens when you press Run?"**

"The backend replays a source recording, detects speech and asks Smart Turn whether the speaker is finished. It can send the captured audio to Gemini for a response and use ElevenLabs to speak that response. We log completion decisions, generation, playback and cancellation separately. The browser controls the configured backend machine. Our saved comparison is two separate runs of the same excerpt."

**"Why distinguish a decision from an interruption?"**

"An early model decision can trigger generation, but the speaker might resume before audio begins. In our saved five-clip replay comparison, some replies were cancelled before audio. A model prediction alone cannot tell us whether someone heard an interruption."

**"Does your latest clip prove the candidate waits until someone finishes?"**

"It shows a different first-pause decision in one selected example. Both models also declare completion at later pauses. The source was cropped, and its endpoint is not a human-verified turn ending. We need human review and broader confirmation before claiming improved conversation behavior."

**"Did you train Gemini or ElevenLabs?"**

"No. We adapted Smart Turn, the turn-completion model. Gemini generates replies, and ElevenLabs generates voice. I worked on the training harness and experiment execution as well as the agent. Niko owns the evaluation protocol and review."

### Niko: model results, data separation and Tiger Data

**"What did the eighty/twenty mix mean?"**

"It was a training sampling mix: eighty percent original-model replay examples, ten percent stutter-focused unfinished examples and ten percent completed-speech proxies. It was not an eighty/twenty train/test split. Those proxy labels still need human validation."

**"Did the adapted model improve?"**

"X1 passed the exploratory development rule and two follow-up checks. We chose it after seeing earlier results, so this was a fifth adaptive look at development data, not an independent confirmation or a version-four pass. Human confirmation and audio acceptance remain incomplete. We have not yet earned a claim of fewer audible interruptions in real conversations."

*Technical backup only: X1 at threshold 0.60 produced 110/352 premature predictions on development stutter-gap proxies; stock FP32 at 0.50 produced 167/352, and the qualifying stock comparator at 0.55 produced 161/352. The ordinary unfinished-speech guard was 1421/1516 versus stock 1418/1516, with 13 losses and 16 gains. These reused-data diagnostics are not independent improvement evidence. Do not compare them with the historical 58% INT8 result. Earlier W3 epoch 1 at 0.60 had 71/352 but failed the guard by five net examples; that rejected checkpoint is not the X1 blend.*

**"Why not just wait longer?"**

"That is a valid baseline, and our stock/patient configuration tests it. The X1 example uses a different model and threshold, not a longer wait. We are testing the tradeoff between premature decisions and delayed responses; we have not proved that changing the wait setting is insufficient."

**"How do you prevent data leakage?"**

"We froze source splits and track which examples experiments have seen. Our reserved final test remains sealed. Repeated development evaluation can still overfit those development examples, so X1 needs a separate human-labeled confirmation set before promotion. That review is unfinished. Human-labeling an already-used source does not make it unseen data."

**"What does Tiger Data do?"**

"It stores our saved run events so we can inspect the sequence from decision to response. I ingested the logs and produced the database export used by the judge chart. The displayed chart is a saved snapshot, not a live database health indicator."

### Kareem: evidence, interface and reproducibility

**"What is the difference between these pages?"**

"The landing page introduces the problem. The judge page guides you through results and supporting evidence. The run console operates the replay and displays its events. I worked on the original pages and evidence organization; Vinh continued the interface and integration."

**"How can we verify what you showed?"**

"The judge page links to saved runs and reports in the repository. For a comparison, we identify the input, model, configuration and outcome being measured. We distinguish saved results from the run on screen, and model decisions from audible responses."

## Before rehearsal

- Choose the saved stock-FP32/X1 research comparison or the stock/patient fallback before rehearsing. Use that version's narration and captions consistently. Discussing saved X1 research records does not promote X1 into an accepted agent configuration; promotion still requires (c) and (d).
- Guttuu checks the source's permitted use, attribution and context, and verifies any presented source/reply audio on the presentation machine. Reserve 18 seconds only if the actual excerpt fits it. Keep the following speech resumption in frame and preserve the full records. Do not infer a talk-over from a completion decision.
- Use the real backend, with service credentials configured privately. A model-only run does not demonstrate Gemini or ElevenLabs. The existing synthetic preview is not experiment evidence.
- Verify the actual configuration metadata. Stock/patient uses INT8 at threshold 0.5 with different wait settings. The cited X1 pair uses stock FP32 at 0.5 versus X1 at 0.6, both with `vad_stop_s=0.2`. Record run IDs and distinguish threshold changes from model-weight changes.
- Keep **"Recorded demo"** or **"Saved run trace"** visible as appropriate. If a recording is trimmed, label the selected interval. Do not call saved playback live inference or remove later events to imply a clean full run.
- If neither real execution nor a verified recording is available, replace the demo with a saved event trace and say **"These are saved run events; this view does not demonstrate audible interruption behavior."** Do not play mock events as a result.
- Niko checks the current result and artifact before anyone changes the candidate-status sentence. X1 selection and checks (a)/(b) passed; (c)/(d) remain incomplete. Its required description is **post-hoc exploratory candidate selected after v4, fifth adaptive look, not a v4 pass**. The matched `turn_onset` benchmark describes first-turn behavior only; the real agent resets its input after completion, so later-turn behavior needs separate evidence.
- Kareem checks that the chart is labeled as a saved snapshot and the evidence links open. Keep the three-million, WellSpan and 116/200 sources available; do not imply WellSpan's agent was tested by this team.
- Rehearse aloud once with the actual replay and a stopwatch, then adjust to finish by 2:57. The main spoken script is 309 words: about 2:17 of speech at 135 words per minute, plus 18 seconds for the excerpt and 6 seconds for handoffs, leaving about 16 seconds for deliberate pauses. Timing remains an estimate until a human rehearsal. Each teammate records their own lines if this text is adapted into video narration; no voices or video were generated by this update.
- If a take runs long, cut Niko's final Tiger Data sentence first, then the WellSpan sentence while preserving the opening human scenario and the scoped experimental result. Never cut the later-pause qualification, configuration identity or current-model status to save time.

The repository supplies the planned time limit; an official judging rubric was not available in the materials checked. This script covers the problem, working behavior, technical work and evidence without inventing rubric requirements.

## Latest local replay records and their limits

The records below were inspected, not executed again for this script. They are in the main checkout's ignored `agent/runs/` directory, not published evidence links. Package and hash the full logs and source provenance before using them as shareable supporting material. No human listening acceptance is asserted here.

| Run | Source and configuration | Recorded events |
|---|---|---|
| `20261011T041533Z-stock_fp32-cd9b` | `demo-long-WomenWhoStutter_19_1238s.wav`, 10.4 s; stock FP32 @0.5; commit `42d0446`; services on, HyperX playback | Complete at 1.664 s; reply scheduled at 3.313 s; VAD resumption at 3.808 s; software cut at 4.008 s. The logged 0.200 s overlap is not an acoustic measurement. Also completes at 7.072 and 8.672 s. |
| `20261011T041446Z-candidate-7091` | Same named 10.4 s source; X1 @0.6; commit `42d0446`; services on, HyperX playback | Holds at 1.664 s. Completes at 7.072 s, reply cancelled before audio at 7.680 s; completes again at 8.672 s, reply scheduled at 10.736 s, after the source excerpt ends. |

Earlier untrimmed `demo-short-WWS19.wav` records, `20261011T033509Z-stock_fp32-624e` and `20261011T033533Z-candidate-1998`, used a 17.48 s source with services off. Both complete at 7.072 and 8.672 s; speech resumes at 7.680 and 10.784 s. A 10.4 s cutoff retains both later decisions and removes the 10.784 s resumption. Source identity between differently named crops, exact original-source mapping, and human turn labels must be checked; the timing match alone is not a provenance proof. Never describe the cropped endpoint as the caller naturally finishing, or the candidate as waiting correctly throughout the full recording.

The named `WomenWhoStutter` source belongs to the **training-side show** in the [frozen split manifest](../benchmark/splits/v1/manifest.json). Exact excerpt overlap with training examples has not been established here. This selected example must not be described as unseen-data confirmation or a held-out test result.

The published promotion protocol remains [confirmation evaluation v1](../benchmark/specs/confirm-eval-v1.md). A later services-on replay supplies useful runtime evidence but does not automatically satisfy its human-review or audio-acceptance requirements.

## Sources and credit record

| Spoken claim or assignment | Supporting source |
|---|---|
| More than three million Americans stutter | [NIDCD quick statistics](https://www.nidcd.nih.gov/health/statistics/quick-statistics-voice-speech-language) |
| WellSpan reports more than 160,000 patient calls monthly through one agent | [WellSpan announcement](https://www.wellspan.org/articles/2026/07/30/13/05/web---hippocractic-ai-partnership-expansion); adoption context, not a StutterTurn test |
| Historical 116/200 = 58% | [Claims ledger L-01](claims-ledger.md#l-01--stock-first-check-rate-the-58); Smart Turn v3.2 INT8, first offline checkpoint, automatically detected gaps |
| Replay pipeline and remaining audio limits | [Agent README](../agent/README.md), [replay v2](../agent/evidence/2026-10-10-replay-v2/README.md), [Guttuu's listening report](https://github.com/vinhbin/stutterturn/issues/3#issuecomment-6102558836) |
| W3 sampling mix and rejected result | [Training report](training-report-2026-10-10.md), [W3 result](https://github.com/vinhbin/stutterturn/issues/2#issuecomment-6103321119); this matched FP32 result is separate from the historical INT8 58% |
| X1 exploratory pass; checks (a)/(b) passed, (c)/(d) incomplete | [Executor result](https://github.com/vinhbin/stutterturn/issues/2#issuecomment-6104584978), [Niko's verification](https://github.com/vinhbin/stutterturn/issues/2#issuecomment-6104602369), [frozen raw selection](https://github.com/vinhbin/stutterturn/blob/e2924f8/benchmark/selection/sel-x1/decision.json), [confirmation protocol and first-turn limit](../benchmark/specs/confirm-eval-v1.md) |
| V5 preparation stopped; no training | [Failed crop build](https://github.com/vinhbin/stutterturn/issues/2#issuecomment-6104950767), [Niko's confirmation](https://github.com/vinhbin/stutterturn/issues/2#issuecomment-6104966704) |
| Roles and Kareem's continuing credit | [README team table](../README.md#team-and-repository), [handoff/ownership record](../PLAN.md); these support contribution credit, not claims of exclusive code authorship |
| Page purposes and Vinh's subsequent integration | [Web README](../web/README.md), [original page delivery PR #12](https://github.com/vinhbin/stutterturn/pull/12) |
| Tiger Data ingestion and saved export | [Niko's PR #26](https://github.com/vinhbin/stutterturn/pull/26), [saved chart data](../web/tiger/snapshot.json); schema/ingestion tooling and UI work also came from Vinh's lane |

Human-label completion, unseen-speaker generalization, an accepted adapted model, a measured reduction in audible interruptions and production calling are not established by this script.
