# Five recordings: Stock FP32 and X1

Ten selected completed runs, one matched model pair for each of the five
original 3-second HeStutters sources. Both configurations generated speech
and rendered nonzero source/reply audio in Chromium on all five recordings.
Proof packets are in `docs/proofs/five-model-replays/`.

Both use the same 0.2 s silence gate. Stock FP32 threshold is 0.5; X1 is 0.6.
X1 is exploratory and unpromoted. These are short excerpts plus 5 seconds of
synthetic silence; the fallback decisions do not establish real turn endings
or completed-turn response delay. No aggregate efficacy claim is made.

The first three source pairs ran on `700d34762c1b`. The final two pairs ran on
`ed3d3ec93ce7`, which raises the Gemini request deadline from 10 to 20 seconds
and end-of-run reply draining from 15 to 30 seconds. Model weights, thresholds,
VAD and fallback settings are unchanged; both arms of each pair use the same
revision. `model-five.json` records both revisions and each model hash.

Earlier service attempts on HeStutters_5_123 are retained in
`../2026-10-11-provider-attempts/`: one stock run completed with speech, one X1
run hit the 10 s Gemini deadline, then another stock run hit that deadline.
These are selected working demo runs, not evidence of perfect service reliability.
All attempts are stored in Tiger Data; only this exact folder supplies the
five-model comparison. The historical Stock INT8/Patient packet is unchanged.
