# StutterTurn opening pitch

Vinh's first-speaker script for the three-minute team pitch, approved October 10, 2026. Aim for roughly 90 seconds, then hand off to the demonstration; rehearse aloud to confirm timing.

## Spoken script

**More than three million Americans stutter.**

Imagine calling to refill a prescription. You get stuck on a word, and the automated voice starts answering before you’ve finished.

For someone who stutters, that pause can still be part of speaking.

And these systems already handle important conversations. WellSpan says one of its AI agents handles **over 160,000 patient calls a month.**

So we tested the part of a voice agent that decides when someone is done.

In our first offline experiment, we used **200 real recordings labeled as containing stutter blocks.** An open turn-taking model predicted “finished” in **116 automatically detected pauses—58 percent.** Those are model decisions, not a measured interruption rate; the pause boundaries still need human review.

That’s why we’re building **StutterTurn: to give people who stutter time to finish.**

We’re adapting an open model using real speech recordings, and comparing when it decides to respond with when the agent actually speaks.

Now my teammate will show you the same recording through the standard model and a more patient configuration.

## Delivery notes

Say the first sentence slowly. Pause briefly after the prescription scenario and after “time to finish.” Turn toward your teammate on the final sentence. Keep dataset counts, model architecture, and detailed candidate results for the technical explanation.

The handoff describes the standard/patient configuration comparison. It does not announce a successful fine-tuned model. Recheck the demonstrated configuration and the [current project status](../PLAN.md#current-status) before delivery.

## Sources and number definitions

- **More than three million Americans stutter:** [NIDCD statistics](https://www.nidcd.nih.gov/health/statistics/quick-statistics-voice-speech-language).
- **Over 160,000 patient calls per month:** [WellSpan announcement](https://www.wellspan.org/articles/2026/07/30/13/05/web---hippocractic-ai-partnership-expansion). This establishes adoption; WellSpan's system was not tested by this team.
- **116 of 200, or 58 percent:** [Claims ledger, L-01](claims-ledger.md#l-01--stock-first-check-rate-the-58). Exploratory offline completion predictions from Smart Turn v3.2's INT8 build at the first checkpoint, 0.2 seconds after automatically detected gap onset. The recordings have clip-level stutter-block labels; the individual gaps and speaker continuation still need human validation. This is not a percentage of callers interrupted or calls abandoned.

The [pitch and Q&A](pitch-and-qa.md) retains the historical intended pitch, conditional demo scripts, and methodological answers.

## Presentation method

The structure follows the written scripts and plans in StephenSook's repositories: name the affected people and a concrete human moment; establish scale and urgency with sourced data; give one clearly scoped measurement; explain the product in plain language; then hand off to visible demo proof. Every number has a purpose. The wording, project evidence, and script above are StutterTurn's.

- [HOLD demo script](https://github.com/StephenSook/hold/blob/main/docs/video/script.md): concrete problem and stakes, a one-sentence solution, substantial demonstration time, then measured impact and technology.
- [Preflight narration](https://github.com/StephenSook/preflight/blob/main/docs/film/script.md): connect each demonstrated behavior to the evidence that supports it.
- [LOKA pitch plan](https://github.com/StephenSook/loka-pay/blob/main/KHADIM_TASKS.md): use sourced problem-scale figures and measured results that describe the user's outcome.

These references are written scripts and plans, not recordings of Stephen's delivery.
