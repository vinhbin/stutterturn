# StutterTurn: four-person team pitch

Prepared October 10, 2026. Presenters confirmed by Vinh: **Vinh, Guttuu, Niko and Kareem**. This is a new, shorter team cut; the approved [Vinh opening](pitch-script.md) is preserved separately.

**Format:** the project's planned three-minute presentation. Target finish: **2:57**, including an 18-second replay and speaker handoffs. Times below are rehearsal targets, not a measured delivery. Only the blockquotes are spoken.

**Evidence snapshot:** main `42d0446`, plus Niko's October 10, 22:10 EDT [X1 signoff](https://github.com/vinhbin/stutterturn/issues/2#issuecomment-6104497966). No X1 result was posted when this script was prepared. V1-v4 produced no qualifying candidate. V5 preparation is approved, but its training run is not. The demonstration below uses **stock/patient**, not an accepted adapted model. Recheck status before presenting.

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

*Screen: `/live/`, connected to the real backend. The input is a labeled recording. The two configurations are STOCK and PATIENT. Patient is a longer-wait setting using the stock model.*

> I built our replay agent. The same real recording goes through speech detection and Smart Turn; Gemini creates a reply, and ElevenLabs voices it.
>
> Here we're comparing the standard model with a longer-wait setting. Watch the decision and audio timelines separately.

*[Allow 18 seconds for the prepared stock/patient comparison. Stop speaking so judges can hear it. This duration must be checked with the actual selected clip and reply. Do not improvise or imitate stuttering.]*

> That's the path our adapted model has to improve.

### 1:42-2:21 | Niko: training and evaluation

*Screen: the evidence page or a prepared view of the cited training report. Show the current candidate status, not an unlabeled improvement chart.*

> I built the evaluation pipeline and helped establish the training and export path.
>
> One experiment mixed eighty percent original-model replay data with twenty percent stutter-focused examples.
>
> We test early decisions and missed completions on development examples. Waiting longer can trade fewer early decisions for slower replies.
>
> Candidates improved some development measures, but none has passed every selection check yet. Our final test remains sealed.
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

"The backend replays a source recording, detects speech and asks Smart Turn whether the speaker is finished. It can send the captured audio to Gemini for a response and use ElevenLabs to speak that response. We log completion decisions, generation, playback and cancellation separately. The browser controls the backend machine; this is not a deployed browser-microphone calling service."

**"Why distinguish a decision from an interruption?"**

"An early model decision can trigger generation, but the speaker might resume before audio begins. In our saved five-clip replay comparison, some replies were cancelled before audio. A model prediction alone cannot tell us whether someone heard an interruption."

**"Did you train Gemini or ElevenLabs?"**

"No. We adapted Smart Turn, the turn-completion model. Gemini generates replies, and ElevenLabs generates voice. I worked on the training harness and experiment execution as well as the agent. Niko owns the evaluation protocol and review."

### Niko: model results, data separation and Tiger Data

**"What did the eighty/twenty mix mean?"**

"It was a training sampling mix: eighty percent original-model replay examples, ten percent stutter-focused unfinished examples and ten percent completed-speech proxies. It was not an eighty/twenty train/test split. Those proxy labels still need human validation."

**"Did the adapted model improve?"**

"Some development measures improved. One checkpoint reduced premature predictions on stutter-gap proxies from about forty-seven percent to twenty percent. But it made five net extra errors on ordinary unfinished speech, so we rejected it. We have not yet earned a claim of fewer audible interruptions in real conversations."

*Evidence for that specific answer: W3 epoch 1 at threshold 0.60, 71/352 versus stock FP32 167/352; ordinary unfinished-speech guard 1413/1516 versus 1418/1516, with 22 losses and 17 gains. Do not combine this row with a different checkpoint or compare it with the historical 58% INT8 result.*

**"Why not just wait longer?"**

"That is a valid baseline, and we demonstrate it. We are testing whether adaptation can improve the tradeoff between premature decisions and delayed responses. We have not proved that changing the wait setting is insufficient."

**"How do you prevent data leakage?"**

"We froze source splits and track which examples experiments have seen. Our reserved final test remains sealed. Repeated development evaluation can still overfit those development examples, so an exploratory pass would also need a separate human-labeled confirmation set before promotion. Human-labeling an already-used source does not make it unseen data."

**"What does Tiger Data do?"**

"It stores our saved run events so we can inspect the sequence from decision to response. I ingested the logs and produced the database export used by the judge chart. The displayed chart is a saved snapshot, not a live database health indicator."

### Kareem: evidence, interface and reproducibility

**"What is the difference between these pages?"**

"The landing page introduces the problem. The judge page guides you through results and supporting evidence. The run console operates the replay and displays its events. I worked on the original pages and evidence organization; Vinh continued the interface and integration."

**"How can we verify what you showed?"**

"The judge page links to saved runs and reports in the repository. For a comparison, we identify the input, model, configuration and outcome being measured. We distinguish saved results from the run on screen, and model decisions from audible responses."

## Before rehearsal

- Guttuu chooses one suitable real source recording, checks its permitted use and attribution, and verifies both source and reply can be heard on the presentation machine. Reserve 18 seconds only if the actual comparison fits it. Do not predict a talk-over in the script unless it actually occurs and is measured.
- Use the real backend, with service credentials configured privately. A model-only run does not demonstrate Gemini or ElevenLabs. The existing synthetic preview is not experiment evidence.
- Guttuu verifies the actual active patient configuration. Documentation contains differing historical wait values; this script deliberately does not quote a wait duration. Record the configuration used in the run.
- If the real comparison will not fit or services are unavailable, use a pre-captured, verified excerpt of that same comparison. Keep **"Recorded demo"** visible and replace Guttuu's second paragraph with: **"This is a recording of our standard and longer-wait configurations using the same source clip. Watch the decision and audio timelines separately."** Do not call saved playback live inference.
- If neither real execution nor a verified recording is available, replace the demo with a saved event trace and say **"These are saved run events; this view does not demonstrate audible interruption behavior."** Do not play mock events as a result.
- Niko checks the current result and artifact before anyone changes the candidate-status sentence. An X1 development pass alone does not mean promotion or efficacy. Its required description is **post-hoc exploratory candidate selected after v4, fifth adaptive look, not a v4 pass**. Promotion still needs the specified confirmation labels, matched timing and audio checks.
- Kareem checks that the chart is labeled as a saved snapshot and the evidence links open. Keep the three-million, WellSpan and 116/200 sources available; do not imply WellSpan's agent was tested by this team.
- Rehearse aloud once with the actual replay and a stopwatch, then adjust to finish by 2:57. The spoken script is about 310 words: roughly 2:19 of speech at 135 words per minute, plus 18 seconds of replay, 6 seconds for handoffs and 14 seconds for deliberate pauses. It is not yet a timed human rehearsal.
- If a take runs long, cut Niko's final Tiger Data sentence first, then Guttuu's final handoff sentence. If still needed, cut the WellSpan sentence while preserving the opening human scenario and the scoped experimental result. Never cut the result qualification, configuration identity or current-model status to save time.

The repository supplies the planned time limit; an official judging rubric was not available in the materials checked. This script covers the problem, working behavior, technical work and evidence without inventing rubric requirements.

## Sources and credit record

| Spoken claim or assignment | Supporting source |
|---|---|
| More than three million Americans stutter | [NIDCD quick statistics](https://www.nidcd.nih.gov/health/statistics/quick-statistics-voice-speech-language) |
| WellSpan reports more than 160,000 patient calls monthly through one agent | [WellSpan announcement](https://www.wellspan.org/articles/2026/07/30/13/05/web---hippocractic-ai-partnership-expansion); adoption context, not a StutterTurn test |
| Historical 116/200 = 58% | [Claims ledger L-01](claims-ledger.md#l-01--stock-first-check-rate-the-58); Smart Turn v3.2 INT8, first offline checkpoint, automatically detected gaps |
| Replay pipeline and remaining audio limits | [Agent README](../agent/README.md), [replay v2](../agent/evidence/2026-10-10-replay-v2/README.md), [Guttuu's listening report](https://github.com/vinhbin/stutterturn/issues/3#issuecomment-6102558836) |
| W3 sampling mix and rejected result | [Training report](training-report-2026-10-10.md), [W3 result](https://github.com/vinhbin/stutterturn/issues/2#issuecomment-6103321119); this matched FP32 result is separate from the historical INT8 58% |
| X1 approved for one check; promotion still conditional | [Niko's exact-commit signoff](https://github.com/vinhbin/stutterturn/issues/2#issuecomment-6104497966), [confirmation worksheet PR #38](https://github.com/vinhbin/stutterturn/pull/38) |
| V5 preparation only | [D-014 response](https://github.com/vinhbin/stutterturn/issues/2#issuecomment-6104515955); no training or demo promotion authorized by that response |
| Roles and Kareem's continuing credit | [README team table](../README.md#team-and-repository), [handoff/ownership record](../PLAN.md); these support contribution credit, not claims of exclusive code authorship |
| Page purposes and Vinh's subsequent integration | [Web README](../web/README.md), [original page delivery PR #12](https://github.com/vinhbin/stutterturn/pull/12) |
| Tiger Data ingestion and saved export | [Niko's PR #26](https://github.com/vinhbin/stutterturn/pull/26), [saved chart data](../web/tiger/snapshot.json); schema/ingestion tooling and UI work also came from Vinh's lane |

Human-label completion, unseen-speaker generalization, an accepted adapted model, a measured reduction in audible interruptions and production calling are not established by this script.
