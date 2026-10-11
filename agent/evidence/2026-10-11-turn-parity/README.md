# Turn-input parity: agent vs benchmark `turn_onset` (2026-10-11)

**Roadmap Package 1:** extend parity checks with delayed speech onset, pre-roll clipping at source start, a second turn after completion, and a pause shorter than the VAD threshold. Compare the exact input sample range, features, probability and decision point.

- **Tool:** [`agent/check_turn_parity.py`](../../check_turn_parity.py) at commit **`dd29875`** (clean `agent/` tree).
- **Run:** `python agent/check_turn_parity.py --model both --out report.json`, in Python 3.11 with the agent venv.
- **Records:** `report.json` (sha256 `bc867ffd…23d3`) and `console.txt`.
- **Result: PASS, 8 case runs** (4 cases × stock FP32 and stock INT8).

**Scope:**
- **Sources:** composed from the first two local agent sources, which are **HeStutters clips (a training show)**. This is a mechanics/parity check, not a model result.
- **Agent:** runs its real streaming loop in real time, with services off and no playback.
- **Benchmark side:** inputs are rebuilt with `benchmark/scripts/eval_runner.py`'s own `first_onset_frame`, `input_start_for` and `Model.predict`, at the `agent-v0.1-turn-checks` settings.

## What matches exactly

| Check | Result |
|---|---|
| H1: the captured agent model input equals the stream slice reconstructed from the decision frame | 16/16 checks |
| H2: preprocessing parity on the identical slice (features, probability) | max \|Δ\| **0.0** |
| H4: first-turn input start (first onset − 6 frames, clipped at sample 0 when pre-roll would precede the source) | Δ = 0 in every first-turn check, including `preroll_clipped` |
| H5: no model check inside a 0.064 s pause (agent needs 7 silent frames) | none |

## Two real differences (documented; they matter for interpretation)

1. **Check point (schedule):** the benchmark cuts at silence start **+ 0.200 s**; the agent checks after **7 × 32 ms = 0.224 s** of silence. Every benchmark input therefore ends **384 samples (24 ms) earlier** than the agent's (H3, 16/16). The model sees 24 ms more trailing silence in the agent.
2. **Later turns:** after any `turn_complete` (smart_turn or fallback), the agent restarts its input at the new turn's onset. `turn_onset` always uses the clip's **first** onset (`eval_runner.first_onset_frame` docstring). The checker asserts the divergence is exactly that. It occurred in the designed `second_turn` case and naturally in `delayed_onset`, where stock FP32 completed the first turn at p = 0.527 and the speaker resumed.

**Decision agreement** (each policy on its own slice, threshold 0.5): first-turn checks **10/10**; later-turn checks **5/6**. The disagreement is stock INT8, `second_turn`, check 2: the agent gives p = 0.908 (complete) where the benchmark's first-onset slice gives 0.016.

**Implication:** benchmark `turn_onset` results (including the selector's G arms) describe **first-turn** decisions at a 0.200 s check. They do not cover what the agent does on later turns in the same recording, and they can disagree there. Report G-arm numbers as first-turn evidence only.
