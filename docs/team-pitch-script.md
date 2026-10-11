# StutterTurn: four-person team pitch

> **Current plan (Oct 11, early morning):** the live demo is now **Stock FP32 vs. the X1 candidate** on the hosted Vultr console, not stock/patient. Rehearse from [the team prep packet](pitch-and-qa.md) (Part 1 script, Part 2 coordinator sheet). This file is kept for its sources and history.


Updated October 11, 2026. Presenters confirmed by Vinh: **Vinh, Guttuu, Niko and Kareem**. This is the team cut; the approved [Vinh opening](pitch-script.md) is preserved separately.

**Format:** a three-minute team pitch with the **live app demonstration**, not a demo-video narration script. Target finish: **2:57**, including a 40-second slot for two sequential replays and speaker handoffs. Times below are rehearsal targets, not a measured delivery. Only the blockquotes in the spoken-script section are spoken. The [live demo operator cues](#live-demo-operator-cues) match the actual console controls. The opening is shortened here to make room for real execution; the separately approved opening remains unchanged.

**Evidence snapshot:** main `b5a4dde`, the [X1 result](https://github.com/vinhbin/stutterturn/issues/2#issuecomment-6104584978), [Niko's verification](https://github.com/vinhbin/stutterturn/issues/2#issuecomment-6104602369), and local replay records from October 11 at 00:14-00:15 EDT. **X1 passed exploratory development selection and promotion checks (a)/(b). Audio acceptance (c) and human confirmation (d) remain incomplete.** V1-v4 produced no qualifying candidate; v5 preparation stopped at its failed crop gate, with no v5 training. A/B listening was deferred, not completed; the separate confirmation review remains pending. The main live demonstration uses **stock/patient: the same INT8 model with different silence waits**. Niko discusses X1 separately as exploratory research. The [promotion protocol](../benchmark/specs/confirm-eval-v1.md) still requires human confirmation and audio acceptance before X1 becomes an experimental demo configuration. A candidate appearing as available in the UI only confirms technical availability, not completion of those checks. Recheck evidence before presenting.

## Spoken script and screen cues

### 0:00-0:46 | Vinh: the problem and purpose

*Screen: landing page. Use the actual app, with no audio playing yet.*

> More than three million Americans stutter.
>
> Imagine calling to refill a prescription. You get stuck on a word, and the automated voice starts answering before you've finished.
>
> That pause can still be part of speaking.
>
> In our first offline check of two hundred recordings labeled with stutter blocks, Smart Turn predicted "finished" in a hundred and sixteen detected pauses: fifty-eight percent. Those are model decisions, not measured interruptions, and the boundaries still need human review.
>
> We're building StutterTurn to give people time to finish.
>
> Guttuu will show you how we test that.

### 0:46-1:50 | Guttuu: the live agent and comparison

*Screen: `/live/`, connected to the actual presentation backend, development preview off. Use one rehearsed recording, first `stock`, then `patient`. Keep the source and configuration visible. These are live executions over a recording, not live microphone input. See the exact control sequence below.*

> I built our replay agent with Gemini replies and ElevenLabs speech.
>
> This is a live replay of recorded speech. First stock, then the same model with a longer silence wait. Watch the decision and audio timelines separately.

*[Allow up to 40 seconds for both sequential runs and the configuration switch. Do not narrate over the source or generated speech. Show what actually happens; do not promise a particular interruption, cancellation or reply.]*

> That demonstrates the pipeline. It doesn't establish that our adapted model is better.

### 1:50-2:21 | Niko: training and evaluation

*Screen: the cited X1 result and current promotion status. Keep the required description visible: **"Post-hoc exploratory candidate selected after v4 results; fifth adaptive look at dev/guard; not a v4 pass."** Human confirmation and audio acceptance remain pending. Do not label exploratory differences as validated improvements.*

> I built the evaluation pipeline and helped establish the training and export path.
>
> One experiment mixed eighty percent original-model replay data with twenty percent stutter-focused examples.
>
> We test early decisions and missed completions on development examples. Waiting longer can trade fewer early decisions for slower replies.
>
> X1 passed a post-hoc exploratory development check. Human confirmation and audio acceptance are still pending. Our reserved final test remains sealed.

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

## Live demo operator cues

Before the presentation, prepare the backend and source on the machine connected to the room speakers. For the documented local setup, serve `web/` on port 8041 and run `agent/server.py --services on --play` in its configured Python environment; see the [agent setup](../agent/README.md#run). Use the local `/live/` page with `http://127.0.0.1:8765` as the backend. Keep credentials in the private backend environment. The browser controls the run but does not itself play source/reply audio.

| When | Operator action | What the team can say or show |
|---|---|---|
| Before judges arrive | Open **Connection & preview**, leave **Development preview** off, enter the backend URL and press **Connect**. Confirm `/v0/health` reports services and playback on. | Connected status plus real sources/configurations. A synthetic preview cannot substitute for this check. |
| Before the pitch | Choose a short, permitted recording from **Source recording**, such as `HeStutters_4_32.wav` if available. Rehearse the full stock/patient pair and verify source and reply audibility on the room speakers. | Use the same recording for both runs. Source availability comes from the backend; do not invent a selectable file. The proposed 40-second allowance must be timed. |
| Guttuu's first run | Select **Stock Smart Turn v3.2 (INT8)** (`stock`) and press **Start fresh run**. | Show **Call monitor**, **Turn complete**, **Agent audio (reported)** and the event ledger. A complete decision and a heard reply are separate observations. |
| Between runs | Let the first run finish. Note its **Run ID** and result before changing configuration. Select **Patient (longer wait, same model)** (`patient`), retain the same source, and press **Start fresh run** again. | The console shows one run at a time and clears its event table on a fresh run. It does not provide a simultaneous comparison or saved-log import. Backend logs retain both run IDs. |
| Guttuu's second run | Let it finish and show the new configuration/summary. | Stock and patient share the INT8 model and threshold 0.5; configured silence waits are 0.2 and 1.0 seconds. These are settings, not measured reply delays or proof of model adaptation. |
| Niko's handoff | Switch to the cited X1 research result and status. | Explicitly separate the live stock/patient pipeline from the saved X1 result. Human confirmation and audio acceptance remain pending. |
| Kareem's handoff | Open `/judge/`, then its evidence links and Tiger chart. | The judge page explains results; `/live/` operates runs. The chart is a saved Tiger Data snapshot. |

**Timing:** the engine adds five seconds of trailing silence to each source, plus inference and reply time. Two 10.4-second sources therefore already require about 31 seconds before additional delays. The prior 18-second slot was unsuitable for that full comparison. Use a rehearsed shorter source and the 40-second slot above. Do not truncate a run and then call it a completed conversation or hide a later decision.

**Current readiness check:** the default local endpoint `http://127.0.0.1:8765/v0/health` was unreachable when this update was checked. This script is matched to the implemented controls; it does not certify that a presentation backend is currently running. An HTTPS hosted page needs a reachable HTTPS/WSS backend; a visitor's localhost does not connect to the team's laptop. Recheck the actual presentation machine before using the live wording.

**If live execution is unavailable:** do not spend the pitch debugging. Show the published [stock/patient replay evidence](../agent/evidence/2026-10-10-replay-v2/README.md) in a separate browser tab and replace Guttuu's live-demo sentences with: "These are saved stock and longer-wait runs of the same recording. They show model decisions and reported response events; this is not a live execution or a verified acoustic demonstration." The console has no saved-log import feature. If services are off, say "This is a model-only replay; Gemini and ElevenLabs replies are disabled" and do not imply generated audio is playing.

**If X1 is approved for the live demo later:** first verify completion of the promotion protocol and the available artifact/metadata. Then replace the configuration pair with `stock_fp32` at 0.5 versus `candidate` at 0.6, with the same 0.2-second silence wait, and re-rehearse. Replace the comparison sentence with: "We'll replay the same source through stock FP32 and experimental X1. The model and threshold change; the silence wait stays the same." Do not reuse the stock/patient description or predict the run's outcome. The current script does not mark this promotion complete.

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

"The backend replays a source recording, detects speech and asks Smart Turn whether the speaker is finished. It can send the captured audio to Gemini for a response and use ElevenLabs to speak that response. We log completion decisions, generation, playback and cancellation separately. The browser controls the configured backend machine. Our live comparison is two sequential runs of the same recording; saved X1 research runs are separate evidence."

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

- Guttuu starts and checks the presentation backend, private service configuration, allowed source and room speakers. A working static page is not proof of a connected voice backend. Keep preview off and verify `services: on` plus `playback: on` before promising generated speech.
- Rehearse the same source/configuration pair and transitions used above. Allow each run to finish; retain both run IDs before the console clears the displayed ledger. Have the saved-evidence tab ready if the live connection fails.
- Niko checks the current candidate status. X1 selection and checks (a)/(b) passed; (c)/(d) remain incomplete. The matched `turn_onset` benchmark describes first-turn behavior only, so later-turn behavior needs separate evidence. Do not silently promote X1 because its artifact is loadable.
- Kareem checks the judge links and saved-snapshot label. Keep the three-million and 116/200 sources available. WellSpan remains optional context for questions; it is omitted from the live cut to leave room for execution.
- Rehearse aloud with the actual two runs and a stopwatch. Target 2:57, hard cap 3:00. The live spoken script is 277 words; the 40-second execution slot is an allowance, not a measured runtime. No new model run, paid API request or human listening acceptance was performed by this documentation update.
- If the full live sequence will not fit, use the explicitly labeled saved-evidence fallback. Cut decorative pauses first; never cut configuration identity, the separation between pipeline and model efficacy, or the current promotion status. Keep all four presenters credited.

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
