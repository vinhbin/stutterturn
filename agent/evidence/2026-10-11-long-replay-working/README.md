# Working longer replay pair

Fresh runs on backend `700d34762c1b`, after empty-reply recovery was deployed:

- Stock FP32: `20261011T061006Z-stock_fp32-8d16`
- X1: `20261011T061024Z-candidate-f484`

Both replay the same 10.4 s source with identical silence settings, differing
models and thresholds (0.5 / 0.6). Both completed with generated replies, no
provider errors or timeouts, and nonzero source/reply digital audio in Chromium.
The original earlier comparison remains in `../2026-10-11-long-replay` and
`web/tiger/comparison-previous.json`; no records were edited or deleted.

Stock decides at 1.664 s; X1 holds. Speech resumes at 3.808 s. Stock's scheduled
reply arrives at 3.958 s and ends at 4.008 s, reporting **0.050 s overlap**.
X1 reports no overlap. Both decide before a later resumption and cancel before
audio. These are server-schedule observations, not measured acoustic timing
or an interruption rate. This is a selected working demo pair, not evidence
of provider reliability. X1 remains exploratory/unpromoted.

Browser proof: `docs/proofs/gemini-empty-recovery/`.
