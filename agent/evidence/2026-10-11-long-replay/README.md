# Hosted longer replay: Stock FP32 versus X1

Two completed, sequential browser-audio runs from Vultr on October 11, 2026.
Source: `demo-long-WomenWhoStutter_19_1238s.wav`, 10.4 seconds, followed by
5 seconds of synthetic silence. Application revision: `667460f45fdd`.
The JSONLs were retrieved unchanged from `/opt/stutterturn/shared/runs`.
This is a selected demonstration, not a held-out or human-labelled benchmark.

| Configuration | Run | Silence gate | Decision threshold |
|---|---|---|---|
| Stock FP32 | `20261011T053423Z-stock_fp32-bbcf` | 0.2 s | 0.5 |
| Our X1 candidate | `20261011T053442Z-candidate-efd3` | 0.2 s | 0.6 |

At 1.664 s, Stock predicts complete (p=0.9016); X1 predicts incomplete
(p=0.5432). Stock schedules reply audio at 3.705 s, before detected speech
resumes at 3.808 s, then logs 0.200 s overlap before cancellation. X1 holds
through that pause and reports no audio overlap. The changed weights AND
threshold form this configuration comparison: it does not isolate weight
adaptation, and X1 at threshold 0.5 would cross at that first check.

Both predict complete at 7.072 s, before detected resumption at 7.680 s;
both cancel those replies before audio. Both decide again at 8.672 s.
Stock logs a Gemini timeout at 10.388 s; X1 schedules a reply at 10.649 s,
ending at 12.042 s. The timeout is retained, not counted as a model gain.
Audio timestamps are server sample schedules, not measured acoustic output.
Do not compare the two first-audio timestamps as end-of-turn response latency.
X1 remains post-hoc, exploratory and unpromoted.

`web/tiger/comparison.py` queries these exact runs from Tiger Data and verifies
every exported field against these logs. The judge page renders the saved
query result. PCM was not saved in the logs: its listening links start fresh
runs of the same source/configuration, whose generated replies may differ.
