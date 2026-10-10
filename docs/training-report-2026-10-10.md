# StutterTurn: model training and evaluation report

**Evidence snapshot: October 10, 2026, 18:45 EDT.** Prepared for judge questions and team handoff. Training v1 and v2 were run; neither produced a qualifying candidate. Training v3 was proposed and paused at that snapshot. The current demonstration uses stock/patient behavior, not an accepted fine-tuned model. This report checks repository methods against the executor's published results; it does not independently reproduce the training runs.

**Execution update, approximately 19:00 EDT:** Vinh [approved W3 only](https://github.com/vinhbin/stutterturn/issues/2#issuecomment-6103109431) under D-011. The protocol amendment is merged in PR #28; the reserved test remains sealed and the 20:00 stop remains. This approval does not supply a start confirmation, v3 score, or passing result. The results below remain the v1/v2 evidence snapshot.

## The 30-second explanation

We adapted Pipecat's existing Smart Turn v3.2 audio model to study when a voice agent should keep listening. We combined original complete/incomplete training examples with real podcast recordings containing stuttering. Our first attempt reduced premature decisions but also stopped recognizing many completed examples. The second added completed examples from the same podcast domain and improved that trade-off, but made more errors on ordinary unfinished speech, so we rejected it. These are development results using automatic endpoint proxies. We have not demonstrated a validated improvement for people who stutter, and the reserved final evaluation remains unrun.

## 1. What we trained

[Smart Turn](https://github.com/pipecat-ai/smart-turn) uses a Whisper Tiny backbone and classifier to predict whether an audio turn is complete. We fine-tuned the existing **FP32 Smart Turn v3.2** weights, recovered into PyTorch from the stock ONNX file through the pinned `haan` conversion implementation. We did not train a foundation model from scratch. Gemini generates replies and ElevenLabs generates speech; neither was fine-tuned by this project.

Our model input is mono 16 kHz audio: keep the latest eight seconds and left-pad shorter input with zeros, then compute Whisper features. The output is a completion probability. Training uses raw logits with binary cross-entropy; the ONNX export applies a sigmoid, even though its output tensor is named `logits`. Our usual benchmark check is 0.2 seconds after the detected start of silence. A model decision, a generated reply, and a reply actually heard by the speaker are different events.

The trainable-weight recovery and export/reload proof is saved in [model mechanics](proofs/model-mechanics/README.md). Successful export proves the mechanics, not useful adaptation.

## 2. Data and labels

| Source | Use in our work | Meaning and limitation |
|---|---|---|
| Original Smart Turn v3.2 training dataset | 6,000 English examples replayed during fine-tuning | Preserve the upstream `endpoint_bool` complete/incomplete label. The upstream dataset includes human and synthetic speech. |
| SEP-28k training shows: unfinished-gap examples | 941 clips; 6,190 cut references in the reported build | Stutter-event votes identify eligible clips; energy-derived gaps and subsequent speech define our incomplete targets. Resuming speech may belong to another speaker. |
| SEP-28k training shows: completed-window examples, added in v2 | 3,941 clips; 35,198 cut references | Trailing silence produces a completion proxy, not a human-confirmed end of a thought. Positive sampling assigns equal group weight to disfluent and fluent clips. |
| Original Smart Turn test dataset | 3,000 English examples used as a general-speech guard | Kept out of gradient updates, but repeatedly used for our selection. This is validation, not our untouched final test. |

Counts describe the executor's reported builds, not independent new counts. Cut references are multiple possible audio prefixes from a recording, not unique speakers or independently recorded examples. In v2, 179 train clips supply both negative and positive cuts at distinct times; this within-training reuse is not train/test leakage. See the [initial harness report](https://github.com/vinhbin/stutterturn/issues/2#issuecomment-6101744567) and [v2 data and prescreen report](https://github.com/vinhbin/stutterturn/issues/2#issuecomment-6102362802).

The [original replay dataset](https://huggingface.co/datasets/pipecat-ai/smart-turn-data-v3.2-train) provides the endpoint labels. [SEP-28k](https://github.com/apple-aiml-research/ml-stuttering-events-dataset) provides human stutter-event annotations on short podcast clips, **not turn-boundary annotations**. Our automatic endpoint labels must not be described as human ground truth. Training positives and the development completed-window metric share the same construction, so a better score can reflect learning that proxy.

### Partitions and leakage qualifications

The [frozen split specification](../benchmark/specs/splits-v1.md) assigns entire shows to train/development/reserved test: 4/2/2 shows and 13,282/5,882/7,051 eligible label rows. These totals are not the number of examples actually sampled for training or evaluation. Clip and show separation is enforced by the split design; **speaker separation is unverified**.

Replay uses original training data. The general-speech guard uses separate upstream test data, with decoded-waveform deduplication against replay reported by the executor. That guard may also have informed upstream checkpoint selection and now informs our repeated development decisions. It is distinct from the reserved SEP final test.

**The rebuilt reserved final evaluation has not run and remains sealed under [D-009](decision-log.md).** However, 58 of the original 200 exploratory block clips fall in the later reserved partition. We cannot claim every reserved source recording was never previously scored. Fresh, independently collected recordings would provide stronger confirmation after freezing the model and settings.

## 3. Training procedure and experiment history

The protocol uses AdamW, weight decay 0.01, gradient clipping 1.0, binary cross-entropy with a fixed mixture-derived positive weight, seed 0, and a 10% linear warmup followed by linear decay. Runs use learning rates `1e-5` or `3e-5`, two defined epochs, and checkpoints about every half epoch. The v1 executor reported batch size 32 and an RTX 4070; exact run environments belong in the saved run configurations.

An epoch here is a specified number of **weighted random draws with replacement**. It is not a pass through every recording or every cut reference. Source percentages are sampling probabilities, not a train/test split.

| Attempt | Training mixture and change | Reported outcome |
|---|---|---|
| v1, runs R1–R4 | Usually 60% original replay + 40% SEP unfinished cuts; one run used 75/25; one partially froze the encoder | All 16 checkpoints rejected under the amended prescreen. Completed-window decisions collapsed. |
| v2, runs V1–V4 | Usually 60% replay + 20% SEP unfinished + 20% SEP completed proxies; run V3 used 40/30/30; one partially froze the encoder | 4 of 16 checkpoints passed the prescreen; two were exported. Every final operating point failed the general-speech incomplete guard. |
| Proposed v3, W runs | More original replay; our recommendation is W3 only at 80/10/10 | No run or score reported at this snapshot. See the [proposed protocol](v3-recommendation-2026-10-10.md). |

**Naming:** `V3/ckpt-e0.51` is a run within training **v2**. It is not evidence that training **v3** happened.

**v1 chronology:** the completed-window M3 check was added after training and an initial prescreen had already run. Saved checkpoints were rescored, and the earlier selection was retained as superseded. Under the amended rule, all 16 failed: completed-window decisions fell from 46.62% to 8.24–22.06%, while stutter-gap premature decisions fell to 0.85–6.25%. This pattern is consistent with a podcast-domain shortcut; it does not establish the model's internal mechanism. Do not describe the whole v1 evaluation as fixed before any results were seen. [Executor's v1 report](https://github.com/vinhbin/stutterturn/issues/2#issuecomment-6101907402).

v2 was designed after inspecting v1. A future v3 would be a third adaptive attempt on the same development data and guard. Report that reuse explicitly.

## 4. Current score: development results only

There is no single meaningful overall accuracy score. We measure premature decisions, recognition of completed examples, and general-speech regressions separately.

All columns use threshold **0.5**. The SEP development metrics use the 0.2-second silence check; guard specificity scores each upstream example's full audio, with variable trailing silence. Values are from [Guttuu's official v2 selection report](https://github.com/vinhbin/stutterturn/issues/2#issuecomment-6102500044).

| Measure | Stock FP32 | v2 V3 / epoch 0.51 | v2 V2 / epoch 2.00 |
|---|---:|---:|---:|
| Stutter-gap premature decisions, lower is better | 47.4% (167/352) | 23.0% | 31.0% |
| Fluent-pause premature decisions, lower is better | 50.5% (767/1,518) | 40.7% | 51.2% |
| Fluent completed-window proxies decided at first check, higher is better | 46.6% (317/680) | 62.3% | 64.1% |
| General-speech unfinished guard correctly kept incomplete, higher is better | 93.5% (1,418/1,516) | 91.8% | 92.0% |

The nearest miss was **v2 V2 / epoch 2.00 at threshold 0.6**, compared with **stock FP32 at threshold 0.5**: stutter-gap premature decisions **18.5%**, versus stock's 47.4%; guard specificity **92.94%**, versus 93.54%. It met the other final constraints, but about nine additional errors among 1,516 unfinished guard examples violated the no-regression rule. **It failed; no custom model was selected.** The exact guard values appear in the [v2 prescreen/export report](https://github.com/vinhbin/stutterturn/issues/2#issuecomment-6102362802).

For context, stock FP32 at threshold 0.55 met every constraint with M1 45.7%. Stock checked after 0.8 seconds instead of 0.2 seconds reached M1 12.8% and completed-window M3 48.2%. That configuration deliberately checks 0.6 seconds later; this is not a measured increase in every audible reply's latency. These baselines prevent us from presenting a fine-tune against only the easiest comparator.

Selection compares point estimates under fixed constraints; the nearest miss cannot become a pass by relaxing a rule afterward. Confidence intervals do not remove label uncertainty or dependence among clips from the same shows. None of these figures is an audible interruption rate, a population efficacy estimate, or a measured completed-turn response delay.

## 5. What remains to establish

- **Human endpoint review:** confirm complete/incomplete turns with surrounding context, including stuttered completions and ordinary pauses. Fluent labels describe a clip, not a person's diagnosis.
- **Actual operating point:** the stuttered-completion and cropped-context prescreen checks use threshold 0.5. A selected threshold of 0.6 needs those checks too.
- **Agent input and audio behavior:** main selection uses `clip_start`; the agent-oriented `turn_onset` comparison is report-only. Preprocessing parity does not prove every selected benchmark input equals live-agent input. Measure response audio overlap, cancellation after playback begins, completed-turn delay, and nonresponse separately.
- **Independent confirmation:** freeze model, threshold, timing, and protocol before evaluating new examples. Keep the reserved set sealed unless Vinh explicitly changes that decision. Any new examples used to tune become development data.
- **Reproduction package:** executor-local raw selection outputs and candidate artifacts need a shareable, hash-verified handoff before another person can reproduce the claimed run.

Synthetic ElevenLabs speech and team-recorded scripted pauses can test engineering behavior. They do not establish performance for people who stutter. The current agent replays recordings; live microphone evaluation would require additional input support. The demo must identify recording/synthetic sources honestly.

## 6. Answers judges may ask for

**Did you train your own model?** We fine-tuned an existing open audio turn-completion model. Two training attempts ran, but neither passed all selection checks. We distinguish that research work from the stock/patient demo.

**Why mix original examples back in?** To preserve ordinary complete/incomplete behavior while adapting to the podcast domain. More replay is the v3 hypothesis; it is not a demonstrated fix.

**Is 18.5% your final error rate?** No. It is a development proxy result at one rejected operating point. It does not measure audible interruptions or unseen-user performance.

**Have you tested unknown data?** We evaluated shows outside fine-tuning and used a separate general-speech guard. Both informed selection. The reserved final evaluation has not run; some of its source clips had historical exploratory exposure. Fully fresh confirmation is still needed.

**Why reject a promising candidate?** It introduced additional premature decisions on ordinary unfinished speech. We kept that regression visible and retained the selection rule.

**Can generated stutters prove the system works?** They can expose playback and timing bugs. Authentic speech with reviewed endpoints is needed to assess usefulness for people who stutter.

## 7. Evidence and reproducibility handoff

Niko owns the specification/selection protocol; Guttuu owns execution and its raw artifacts. Vinh coordinates integration. Kareem's delivered landing/judge/evidence work remains credited in the [README](../README.md).

The report was checked against integrated branch `a36d1f7`, training harness `a78f21b`, selection report `sel-v2`, and proposed v3 spec `f720198`. The numerical source is the executor's report; raw `decision.json` and run directories remain on Guttuu's machine. No training, provider synthesis, model evaluation, or reserved-test inspection was performed to write this report.

For each executed experiment, preserve: full code/spec commit IDs; dataset revisions and actual train/dev reference hashes; decoded-audio and base-model hashes; environment/device; mixture, loss weight, learning rate, seed, batch size, actual sampled draws/steps; all checkpoint metrics; export/parity evidence and model hashes; every candidate/threshold and gate outcome; per-item probabilities; selection JSON and human-readable decision; and separately versioned audio acceptance results. Disclose incomplete runs and any changed rules. Do not include credentials or redistribute source audio without the required rights.

Method details: [training v1](../model/specs/training-v1.md), [training v2](../model/specs/training-v2.md), [selection protocol](../benchmark/specs/selection-v1.md), [current results](model-results-2026-10-10.md), and [v3 team proposal at the reviewed revision](https://github.com/vinhbin/stutterturn/blob/f7201981e2af591d14321ee2047b39a8e3371449/model/specs/training-v3.md).
