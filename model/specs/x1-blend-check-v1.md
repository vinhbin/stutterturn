# X1: bounded check of the existing blend at threshold 0.6 — pre-registration v1

**Status: DRAFT — not approved. Execution requires (1) Vinh's recorded authorization in the decision log and (2) Niko's sign-off on this exact file. V4 remains `dev_nothing_passes`. D-009: the reserved final test stays sealed.**

Owner of this spec: Vinh's session (model-takeover lane), consolidating Guttuu's proposed pre-registration (issue #2, comment 6103688105) and Niko's revised evaluation view (comment 6103719447). Evaluation owner: Niko.

## 1. What X1 is, in one paragraph

A single integrity-and-selection check of one **existing, already-inspected** checkpoint at one fixed threshold. It is the **fifth adaptive look at dev/guard**, disclosed as post-hoc everywhere it is reported. It is **not** a v4 pass, and a passing outcome is **not** evidence the model is better — the in-loop numbers were visible when this candidate was chosen. Its only purpose on pass is to give the promotion pipeline a real candidate for the checks that are *not* predetermined: agent load, matched-runtime comparison, audio acceptance, and human endpoints on a fresh frozen set.

## 2. Frozen inputs

| Item | Value |
|---|---|
| Candidate | `runs/X4/blend-a0.75-W3ee1.00.pt` |
| Candidate SHA-256 | `612df85bd3fd0570d4515ed45a37acf299473842ce5017a3b2c00b1c989c74b3` |
| Blend source | `runs/W3/ckpt-e1.00.pt`, SHA-256 `1a60eb6789244e2422fb6724601ce7d3e0d1e0c7dfaa2989cb393b7f6e3507f3` |
| Stock FP32 comparator | `smart-turn-v3.2-gpu.onnx`, SHA-256 `ab8dc64b88713f90b571c15b714bd1330e6c883cad8763dacf65c9376dc539be`, threshold 0.5 |
| Threshold | **0.6, fixed.** No other threshold is computed, reported, or inspected |
| Selection out-id | `sel-x1` |
| Datasets | The v4 dev/guard sets and reference files (data-v2 manifest, `m3s_refs.json`, crop references), byte-identical to the v4 run; hashes verified by preflight |

## 3. Procedure (in order; stop at first failure)

1. `model/train/preflight_x1.py` passes on the executing machine (hash, environment, and input-completeness gates; no scoring).
2. Export with parity: ONNX export of the candidate; ORT-vs-torch max probability error < 1e-5 on B=1,2; refuse existing outputs.
3. Full `guard_eval` on the exported candidate: M4, **M4b** (currently unverified for this blend), M5.
4. `select_candidate.py` with **this single candidate** and **threshold 0.6 only**, out-id `sel-x1`. If the selector as implemented sweeps thresholds or admits other candidates, it is not run; the same constraints are applied by a single-candidate driver instead. Every numerical bound is exactly the frozen v4/selection rule, evaluated at 0.6, unmodified — including **ΔM5 ≥ 0 vs stock**, the M4 bound, the M4b rule, and selected-threshold M3s / M3-crop.

## 4. Outcomes and mandatory wording

- `x1_fail`: any integrity or constraint failure. The candidate is rejected. No retry with modified settings; any new idea is a new pre-registration.
- `x1_pass_dev_exploratory`: all constraints hold. Mandatory wording wherever reported: **"post-hoc exploratory candidate selected after v4 results; not a v4 pass; fifth adaptive look at dev/guard."** A pass authorizes only entry into the promotion pipeline below; it is not quotable as improvement anywhere (page, pitch, README, Devpost).

**Stopping rule:** one execution of steps 2–4, ever, for this hypothesis. Outcome and artifacts are pushed with hashes either way.

## 5. What a pass feeds (the checks that actually matter)

1. Agent load + matched `turn_onset` runtime comparison vs stock FP32 @0.5 (and comparator @0.55, patient) per the input-policy parity notes.
2. Audio acceptance: actual playback, cancellation, completed-turn response timing, nonresponse.
3. **Human endpoints on a fresh frozen confirmation set** per Niko's revised view: recordings outside *every* v1–v4 selection exposure (dev clips never itemized or used in-loop, a held-out show, or new recordings), chosen and frozen before scoring, labeled without model predictions. A/B worksheets are validity-only feasibility evidence — never confirmation, never training.

## 6. Execution options (Vinh chooses)

- **Option A — Guttuu's machine** (all inputs already in place; ~10 min once approved). His assistant limit does not prevent manual execution; this spec plus preflight is the pre-registration he offered to write.
- **Option B — this machine** after a file transfer per Appendix A, using the verified CPU environment (`C:/Users/Binep/.codex/backups/stutterturn-model-proof-2026-10-10/.venv`). Slower: the dev/guard audio and data-v2 feature caches do not exist locally and must transfer or rebuild with hash verification.

## Appendix A — transfer manifest (Option B only; from `C:/Users/Guttu/st-train/work/`)

1. `runs/X4/blend-a0.75-W3ee1.00.pt` (verify `612df85b…` before loading)
2. `runs/W3/ckpt-e1.00.pt` (verify `1a60eb67…`)
3. `runs/X4/` config, metrics.jsonl and run metadata
4. data-v2 manifest + `m3s_refs.json` + crop references
5. Dev/guard audio for the v4 item sets, or validated feature caches (hash-listed)

**Never transfer or reference the reserved final test. No transfer request has been sent; Vinh sends it or directs it to be sent.**
