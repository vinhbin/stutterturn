# X1: bounded check of the existing blend at threshold 0.6 — pre-registration v1.1

**Status: DRAFT v1.1 — authorized by Vinh (D-013, Option A); execution still requires Niko's sign-off on this exact file at a named commit. V4 remains `dev_nothing_passes`. D-009: the reserved final test stays sealed.**

Owner of this spec: Vinh's session (model-takeover lane), consolidating Guttuu's proposed pre-registration (issue #2, comment 6103688105) and Niko's revised evaluation view (comment 6103719447). Evaluation owner: Niko. **v1.1** applies Niko's five review points (comment 6103828754): unchanged selector with a frozen single-entry prescreen; the §6 comparator rule; identity-asserting preflight with clean tree and HEAD; one platform (Option A); the exact promotion-(a) command. Revision by Guttuu, with no other change to scope.

## 1. What X1 is, in one paragraph

A single integrity-and-selection check of one **existing, already-inspected** checkpoint at one fixed threshold. It is the **fifth adaptive look at dev/guard**, disclosed as post-hoc everywhere it is reported. It is **not** a v4 pass, and a passing outcome is **not** evidence the model is better — the in-loop numbers were visible when this candidate was chosen. Its only purpose on pass is to give the promotion pipeline a real candidate for the checks that are *not* predetermined: agent load, matched-runtime comparison, audio acceptance, and human endpoints on a fresh frozen set.

## 2. Frozen inputs (all asserted by `preflight_x1.py`)

| Item | Value |
|---|---|
| Candidate | `runs/X4/blend-a0.75-W3ee1.00.pt`, SHA-256 `612df85bd3fd0570d4515ed45a37acf299473842ce5017a3b2c00b1c989c74b3` |
| Blend source | `runs/W3/ckpt-e1.00.pt`, SHA-256 `1a60eb6789244e2422fb6724601ce7d3e0d1e0c7dfaa2989cb393b7f6e3507f3` |
| X4 run records | `runs/X4/config.json` `810e262ab2e82e83b4c788fafc9e96e108ee86ed32d791226d6fabfd16e8ae64`; `runs/X4/metrics.jsonl` `59cc83fff0351e7af0de41356ad4064bf8d102daa0b29a7af1b37567addaab29` |
| Stock FP32 | `agent/models/smart-turn-v3.2-gpu.onnx` `ab8dc64b88713f90b571c15b714bd1330e6c883cad8763dacf65c9376dc539be` |
| Stock INT8 (arm A, report only) | `agent/models/smart-turn-v3.2-cpu.onnx` `2bb026316b14a660486a75b1733cd3fbab8c2fd0314dc9af7be49f8cca967e4f` |
| VAD (arm G) | `agent/models/silero_vad.onnx` `2623a2953f6ff3d2c1e61740c6cdb7168133479b267dfef114a4a3cc5bdd788f` |
| Train manifest | `data-v2/manifest.json` `92c11eb3da502162f4321e221c18142098d3c8dc312d917d8478cfb01a8ebcee` |
| Dev items | `benchmark/items/v1/dev.jsonl` `742b645ba7213fecc0753d6c10376e330673b70c0d21d59881f0ca442e962ee3`; `dev_end_of_window.jsonl` `e30a456895cd61dd203fee319c864a9014097f720581a1fe87611cf6d7f52905` |
| Stock guard (reused, as in `sel-v3`/`sel-v4`) | `guard/stock-fp32.json` `5be10cddd69aef2be90896d2601d19cab7c5c3e7aec16bbd2f824a24737e7883` |
| Frozen prescreen | `model/specs/x1/prescreen-x1.json` (committed; `top2` = exactly `["X4/blend-a0.75-W3ee1.00.pt"]`; hash recorded by preflight and by the selector) |
| Decision threshold | **0.6 only** (see §4) |
| Selection out-id | `sel-x1` |
| Platform | **Option A only:** Guttuu's machine (Windows 11, i7-13700HX, ORT CPU), the platform of every `sel-v4` stock arm. |

## 3. Procedure (in order; stop at first failure; W = `C:/Users/Guttu/st-train/work`)

0. `python model/train/preflight_x1.py --work W --expect-head <signed commit>`: clean `model/` + `benchmark/scripts/` tree, HEAD equals the commit Niko signed, every hash in §2, outputs absent, D-009 seal. No scoring.
1. Export with parity (existing `export.py`, unchanged):
   `python model/train/export.py --haan H --work W --ckpt W/runs/X4/blend-a0.75-W3ee1.00.pt --name stutterturn-x1-rX4-blend-a0.75-W3ee1.00`
   ORT vs PyTorch ≤ 1e-5 at B = 1 and 2; refuses existing outputs.
2. Full guard (existing `guard_eval.py`, unchanged): `--model W/exports/stutterturn-x1-rX4-blend-a0.75-W3ee1.00.onnx --expected-sha256 <export sha> --out W/guard/stutterturn-x1-rX4-blend-a0.75-W3ee1.00.json` (M4, **M4b**, M5 per row).
3. Selector, **unchanged code**: `python benchmark/scripts/select_candidate.py --out-id sel-x1 --training-spec v4 --prescreen model/specs/x1/prescreen-x1.json --candidate W/exports/stutterturn-x1-rX4-blend-a0.75-W3ee1.00.onnx --guard stock-fp32=W/guard/stock-fp32.json --guard stutterturn-x1-rX4-blend-a0.75-W3ee1.00=W/guard/stutterturn-x1-rX4-blend-a0.75-W3ee1.00.json` plus the same stock, manifest, VAD and platform-note arguments as `sel-v4`. Stock arms (A, B, C sweep, F, G-B) are re-run fresh on the same platform.
4. Only if X1 passes (§4): promotion check (a), which reads the existing in-loop records only:
   `python model/train/interpolate.py --work W --promotion-a X4/blend-a0.75-W3ee1.00.pt --threshold 0.6`
   (M3s and M3-crop at 0.6 ≥ stock@0.5 − 0.020, i.e. ≥ 0.2216 and ≥ 0.4947).

## 4. Decision rule (pre-registered; only the 0.60 row decides)

From `benchmark/selection/sel-x1/decision.json`, let **R** be the `metric_table` row with arm `E1` and threshold `0.6`, and **C\*** the tool's `comparator` (best constrained stock threshold; `sel-v4` gave C @0.55, M1 45.7%).

**X1 passes iff both hold:**
1. **R meets every constraint bound vs B** (stock FP32 @0.5), as computed by the tool: ΔM2 ≤ +1.0 pt, ΔM3 ≥ −2.0, ΔM4 ≥ −1.0, ΔM4b ≥ −1.0, **ΔM5 ≥ 0** (point estimates), i.e. `R.flags.all == true`.
2. **§6 comparator rule:** R's M1 premature count is **below C\***'s, with paired discordant counts favouring the candidate (b > c). The selector asserts `b − c = k(C*) − k(R)`, so this is the same condition as k(R) < k(C\*). Report b, c and McNemar p (from `pair_sel_vs_comp` when the tool selects R; otherwise from the run directories).

**By-products, published verbatim but not used for the X1 decision:** the selector always also scores the candidate at 0.40 and 0.50 (arms D1/E1) and writes its own `outcome`. These rows and the tool's `outcome` are labelled **"computed by the tool, not used for the X1 decision"**. If R passes, the tool's own selection is R (M1 can only fall as the threshold rises), so the two agree; any disagreement is reported, and §4 governs.

## 5. Outcomes and mandatory wording

- `x1_fail`: any integrity or decision-rule failure. The candidate is rejected. No retry with modified settings; any new idea is a new pre-registration.
- `x1_pass_dev_exploratory`: §4 holds. Mandatory wording wherever reported: **"post-hoc exploratory candidate selected after v4 results; not a v4 pass; fifth adaptive look at dev/guard."** A pass authorizes only entry into the promotion pipeline below; it is not quotable as improvement anywhere (page, pitch, README, Devpost).

**Stopping rule:** one execution of steps 1–3, ever, for this hypothesis. Outcome and artifacts are pushed with hashes either way.

## 6. What a pass feeds (the checks that actually matter)

1. (a) Selected-threshold proxies (§3 step 4).
2. Agent load + matched `turn_onset` runtime comparison vs stock FP32 @0.5 (and comparator @0.55, patient) per the input-policy parity notes.
3. Audio acceptance: actual playback, cancellation, completed-turn response timing, nonresponse.
4. **Human endpoints on a fresh frozen confirmation set** (Niko's `benchmark/specs/confirm-set-v1.md`): recordings outside *every* v1–v4 selection exposure, chosen and frozen before scoring, labeled without model predictions. **X1 can run before that set exists; promotion cannot.** A/B worksheets are validity-only feasibility evidence (all 30 recordings were used in v1–v4 selection) — never confirmation, never training.
