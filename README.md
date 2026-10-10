# StutterTurn

**Voice AI answers real phone calls now — and when the caller stutters, the standard open-source turn-taking model talks over them on 58% of stutter blocks. We measured it. StutterTurn is the first open turn-taking model trained on stuttered speech, with the first public benchmark of how voice agents treat people who stutter.**

> We take Apple's own dataset where Apple stopped: Apple fixed this inside Siri and kept it closed. We fix it for the open ecosystem every phone agent is built on, and we publish the benchmark.

| Hacklanta '26 | |
|---|---|
| **Main track** | AI/ML |
| **MLH prize entered** | Best Use of ElevenLabs (their voice runs our live agent; their platform is credited in our results) |
| **Sponsors doing real work** | Gemini (the agent's brain + its end-of-speech setting benchmarked as a rival) · Vultr (training + hosted benchmark) · ElevenLabs (voice + honest baseline) · Tiger Data (turn-event time series) |
| **Team** | Vinh · Guttuu · Niko · Kareem |
| **Demo video** | _link added before submission_ |
| **Devpost** | _link added before submission_ |

**What works right now is in [Build status](#build-status).** Anything not marked ✅ there is planned, not working.

## The problem

- **AI already answers the phone in healthcare.** One health system's AI agent alone handles **160,000+ patient calls a month** ([WellSpan, Jul 2026](https://www.wellspan.org/articles/2026/07/30/13/05/web---hippocractic-ai-partnership-expansion)); pharmacy refill lines are among the most automated calls in the country.
- **More than 3 million Americans stutter** ([NIDCD](https://www.nidcd.nih.gov/health/statistics/quick-statistics-voice-speech-language)). A stutter block is a silent pause mid-word or mid-sentence — exactly what turn-taking models read as "the caller is done."
- **People who stutter already report this.** Apple's study of 61 people who stutter: they want to use speech tech but are "frequently cut off, misunderstood" ([Lea et al., 2023](https://arxiv.org/abs/2302.09044)). A new survey of 53 people who stutter: 58% report interrupted or timed-out input, because speech tech assumes "communication happens at a fluent pace" ([Liu et al., ASSETS 2026](http://www.shaomei.info/pdfs/ASSETS26_speculative_design.pdf)).
- **We measured it (Oct 10, real recordings, no simulation).** On 200 real stutter-block clips from Apple's SEP-28k dataset, the standard open turn model (Smart Turn v3.2, the pipecat ecosystem default) declared the turn over during **58%** of blocks on its first check — 68% if it keeps checking — while adding only ~0.1 s for fluent callers. Full method and numbers: [benchmark/RESULTS.md](benchmark/RESULTS.md).
- **No existing knob fixes it.** Waiting 0.8 s still interrupts 20% of blocks and delays every caller by 0.8 s. Raising the model's confidence bar to 0.99 stops interruptions only because the model stops firing — everyone gets ~3 s of dead air. The trade-off is structural; the fix has to be in the model.

## What StutterTurn is

1. **The model:** Smart Turn v3.2 (open, 8M parameters, runs on CPU) fine-tuned on real recordings of people who stutter (SEP-28k), evaluated on both axes at once — interruptions on stutter blocks AND added delay for fluent callers. Target: 58% → under 10%, with fluent latency unchanged.
2. **The benchmark:** the first public test of how voice-agent turn-taking treats stuttered speech. Any agent builder can run their stack against it. It didn't exist before this weekend.
3. **The live agent:** a phone agent (Gemini brain, ElevenLabs voice) running our model, so the difference is heard, not just charted.
4. **A drop-in:** the fine-tuned model loads anywhere stock Smart Turn does.

## Measured results so far

| Arm | Stutter-block interruptions (N=200) | Added delay for fluent callers |
|---|---|---|
| Smart Turn v3.2 stock, first check | **58.0%** | ~0.1 s (unchanged baseline) |
| Smart Turn v3.2 stock, repeated checks | **68.0%** | — |
| Silence timeout 0.8 s | 20.0% | +0.8 s for everyone |
| Silence timeout 1.5 s | 0.5%* | +1.5 s for everyone |
| Confidence bar 0.99 | 0.0% (model stops firing) | ~3 s fallback for everyone |
| ElevenLabs agents, stock (our live test, n=20) | 5–10% | — |
| ElevenLabs agents, "patient" (n=20) | 5% | visibly slower; 6/20 got no response in-window |
| **StutterTurn (fine-tuned)** | **target <10%** | **target: unchanged** |

\* Every block we could test was under 1.6 s (the dataset's clips are 3 s long). Real blocks can last much longer — that regime is untested for every system, including the commercial ones.

**Credit where due:** ElevenLabs' closed platform already handled short blocks well in our small live test. Our target is the open ecosystem — and the untested long-block regime.

## What it can't do (we say this out loud)

- It makes the agent **wait**; it does not recognize stuttered words better (that's ASR, e.g. [AImpower's work](https://aimpower.org/fair-speech-ai/)).
- All measured blocks were **under 1.6 s** — long blocks (3+ s) are unproven here and everywhere.
- Our ElevenLabs numbers are our own small unpublished measurement (20 clips, short blocks).
- Results are on wideband audio; **8 kHz phone-line transfer is untested.**
- Whether Smart Turn's original training data accidentally includes stuttered speech is unknown (community data, unaudited).
- The benchmark dataset is **CC BY-NC**: research and demo use with attribution, not commercial use.
- No person who stutters is on the team; we evaluate on real recorded speech and are seeking community input. This is a research prototype, not a medical or therapeutic tool.

## The demo (3 minutes, nobody imitates stuttering — ever)

A **real recording of a person who stutters** (labeled on screen) is streamed into a **genuinely live** agent call — the agent's turn-taking decisions happen live. A judge presses one toggle: STOCK interrupts the caller mid-block; STUTTERTURN holds, the caller finishes, the agent answers. Then the judge talks to the agent themselves, normally, and feels that nothing got slower. If connectivity dies, a recorded video of the same rig plays — labeled as a recording.

## Run it

```bash
# Reproduce the benchmark (audio is fetched, not redistributed — see benchmark/README.md)
cd benchmark
pip install -r requirements.txt        # added with the first build commit
python scripts/download_clips.py       # fetches clips via the HF mirror using the official labels
python scripts/run_model_arm.py        # stock + fine-tuned, both axes
```

_Live demo and agent instructions are added as each part works._

## Prior work we build on

- **Apple:** SEP-28k dataset and the Siri atypical-speech work ([Lea et al. 2023](https://arxiv.org/abs/2302.09044), [Siri settings](https://support.apple.com/guide/iphone/change-siri-accessibility-settings-iphaff1d606/ios)) — closed, Siri-only.
- **pipecat-ai [Smart Turn](https://github.com/pipecat-ai/smart-turn)** (BSD-2) — the open model we fine-tune; its README invites exactly this.
- **[AImpower](https://aimpower.org/fair-speech-ai/)** — stuttered-speech ASR benchmarks (the recognition half of the problem).
- **ElevenLabs** agents platform — the strongest commercial turn-taking we measured on short blocks.

**What's ours:** the first open stutter-trained turn model, the first public benchmark, and the live two-axis demo.

## Pre-existing work disclosure

Hacklanta requires disclosing anything created before or outside the event window.

- **Before the event:** concept research and planning documents only (AI-assisted, reviewed by the team). The team pivoted to StutterTurn from a different concept on Saturday morning of the event; prior project planning is in the team's earlier repository history.
- **During the event, AI-assisted:** the benchmark in `benchmark/` (scripts, evaluation, results) was built during the event with AI assistance (Claude), directed and reviewed by the team. All further code is written during the event; the commit history shows when.
- **Datasets and models:** SEP-28k (Apple, CC BY-NC 4.0, [Lea et al. 2021](https://github.com/apple/ml-stuttering-events-dataset)); clip audio via the `miosipof/sep28k_full` mirror (podcast audio copyright remains with the owners; not redistributed here); Smart Turn v3.2 (BSD-2).
- **Accounts/APIs:** existing ElevenLabs account; Gemini and Vultr credentials obtained during the event.

## Team

| Name | Role |
|---|---|
| Vinh | Demo UI (toggle rig, turn-state display), pitch, video, Devpost |
| Niko | Fine-tune, two-axis evaluation, the benchmark |
| Guttuu | Live agent plumbing (telephony, Pipecat), demo rig hardware |
| Kareem | Judges page with live-run buttons, results database (Tiger Data), README/disclosures |

## Build status

Legend: ⬜ not started · 🟡 in progress · ✅ working, with saved evidence · ✂️ cut

| Capability | Status | Evidence |
|---|---|---|
| Benchmark: stock-model baseline measured on real recordings | ✅ | [benchmark/RESULTS.md](benchmark/RESULTS.md) |
| Label listen-through (human check of ~30 clips) | ⬜ | |
| Fine-tune beats stock without slowing fluent callers | ⬜ | |
| Live phone agent running the model | ⬜ | |
| Judge toggle rig (stock ↔ StutterTurn) | ⬜ | |
| Long-block test | ⬜ | |
| Gemini end-of-speech rival arm | ⬜ | needs an API key |
| Judges page with live-run buttons | ⬜ | |

## Repo map

```
README.md            this file (judges: start here)
PLAN.md              phases, owners, gates, status (team: start here)
docs/                decision log, demo + submission plan
benchmark/           the measured kill test: scripts, data, RESULTS.md
model/               fine-tune code + eval (added during build)
agent/               live phone agent (added during build)
web/                 judges page (added during build)
```

_License: chosen by the team before publication. The repository stays private until submission._
