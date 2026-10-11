# Five matched model comparisons with browser speech

The selected working pairs are in `HeStutters_1_133`, `HeStutters_2_57`,
`HeStutters_4_32`, `HeStutters_5_123-final`, and `HeStutters_5_150`.
Each report contains both Stock FP32 and X1 run IDs, browser audio peaks,
run summaries, and errors. All ten selected runs produced source and reply
audio in Chromium and completed without provider errors or timeouts.

`HeStutters_5_123` and `HeStutters_5_123-retry` retain earlier attempts:
the candidate and then a stock run hit the real 10 s Gemini deadline.
These failed attempts remain as raw logs, not overwritten by the final pair.
The last two selected pairs ran after increasing that deadline to 20 s and
run-end draining to 30 s. Each pair uses one backend revision for both arms;
the SQL export lists both revisions. Model weights and turn settings did not
change. These are selected working demos, not a service reliability sample.

The exact ten displayed logs are copied to
`agent/evidence/2026-10-11-model-five-replay`, ingested into Tiger Data, and
queried by `web/tiger/model_five.py`. Six Python evidence checks verify the
current two chart packets, fixed historical scope, and retained old failure.

Reproduce one pair with the audio browser check's `--source NAME.wav
--replay-only --access-file PRIVATE_JSON --out OUTPUT_DIR` options. This
starts real paid API requests. Digital Web Audio checks do not measure
human listening, acoustic latency, or model efficacy.
