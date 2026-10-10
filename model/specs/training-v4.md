# Spec: StutterTurn candidate v4 (weight interpolation; no training)

**Owner:** Niko (protocol, selection, sign-off) · **Executor:** Guttuu · **Status:** pre-registered about 19:50 EDT, **before any v4 number exists**. **Approval:** Vinh, [issue #2 comment 6103422097](https://github.com/vinhbin/stutterturn/issues/2#issuecomment-6103422097), conditional on this sign-off. That approval supersedes D-011's no-v4 rule and its 20:00 stop for this one experiment. **Proposal:** [Guttuu, comment 6103360382](https://github.com/vinhbin/stutterturn/issues/2#issuecomment-6103360382). **Code under review:** `guttuu/v4-interpolate` @ `c17e4bc`, plus the changes required in §3. **This is a delta on `model/specs/training-v3.md`; every section not changed here applies unchanged.**

## 0. What v4 is, and what it must disclose

`sel-v3` gave `dev_nothing_passes`, every operating point failing only or mainly on M5. The nearest miss was W3/e1.00 at 0.6, with M5 −0.33 pt (about 5 of 1,516 guard negatives). v4 tests whether **weight-space interpolation** (WiSE-FT, Wortsman et al. 2022) between stock FP32 and the already-trained W3 checkpoints keeps some of the M1 gain while restoring stock behaviour on Smart Turn's own negatives. **There is no new training and no new data.**

**Disclosure, required in every v4 description:** this is the **fourth adaptive attempt** on the same dev items and guard set. v1, v2 and v3 were all `dev_nothing_passes`. v4 was designed after seeing v3's dev and guard results, and its protocol was recorded before execution. Test stays sealed (D-009). A v4 selector pass makes a candidate **eligible for promotion checks only**; it isn't an efficacy claim, it doesn't put a model in the demo, and it doesn't authorize a test run.

## 1. Sources, grid and pinned identities

- **Sources:** exactly the `prescreen-v3.json` top 2 (sha256 `8a918f4a…3838`), in that order: `W3/ckpt-e2.00.pt` (sha `2377e3c6…`) and `W3/ckpt-e1.00.pt` (sha `1a60eb67…`). Their full hashes are the `ckpt_sha256` values in `W3/metrics.jsonl`, and `interpolate.py` verifies them.
- **Base:** stock FP32 `ab8dc64b…539be` via haan `540f97d`.
- **Grid:** α ∈ {0.25, 0.50, 0.75} × 2 sources = **6 blends**. Nothing else: no other α, sources, thresholds or data.
- **Formula:** θ = (1 − α)·θ_stock + α·θ_source on floating-point tensors. Non-float tensors must be identical and are copied.
- **Pinned and recorded in `X4/config.json`:**
  - source hashes;
  - W3 config sha `af0e6f0d…225c`;
  - `data-v2` manifest `92c11eb3…cebee` (validation sets only);
  - the stock hash;
  - `prescreen-v3.json` sha;
  - the exact code commit.

## 2. Ranking, tie rule and selection

- **Pre-screen: unchanged v2 rule** (`prescreen.py --v4`, output `prescreen-v4.json`), scored in-loop at threshold 0.5 against step 0 (= stock). Top 2 go to export.
- **Tie rule (frozen; replaces "α × source epoch"):** each blend's ordering field (`epoch` in `metrics.jsonl`, which `prescreen.py` and `select_candidate.py` read as "earlier") is its **L2 distance from stock**: `d = α · ‖θ_source − θ_stock‖₂`, over all floating-point tensors, computed in float64 and rounded to 6 decimals.
  - Ties on the ranking metric therefore go to the blend **closest to stock in weight space**, whichever source it comes from.
  - Any remaining exact tie goes to `prescreen-v3` top-2 order (e2.00 first), then to smaller α.
  - Record `‖θ_source − θ_stock‖₂` for both sources, and every `d`, in `config.json`.
- **Selection: unchanged.** Run `select_candidate.py --out-id sel-v4 --training-spec v4` with:
  - thresholds {0.4, 0.5, 0.6};
  - every constraint, **including M5 ≥ 0 on point estimates**;
  - the comparator from the stock threshold sweep.

  Stock arms may be re-run fresh. The stock guard file `5be10cdd…7883` may be reused, since it has the same model sha and guard manifest.

## 3. Required code changes before execution (Niko reviews the diff)

1. **`interpolate.py`:**
   - set the `epoch` field to `d` (§2), not α × source epoch;
   - record per-source norms;
   - before blending, run the existing stock-reconstruction parity check (haan stock vs ORT FP32 on 3 real dev feature arrays, ≤ 5e-5, CPU torch) and abort on failure;
   - **refuse to run on a dirty tree** (`git status --porcelain` non-empty under `model/` or `benchmark/`), and record the commit.
2. **`select_candidate.py` `LIMITS_V4`:** replace the line "Candidate 'epoch' is alpha x source epoch …" with "Candidate 'epoch' is the blend's L2 weight distance from stock (α·‖θ_source − θ_stock‖₂); 'ties → earlier' prefers the blend closest to stock."
3. **Promotion threshold mode** (Vinh's point 1), e.g. `interpolate.py --eval-ckpt NAME --threshold T`: re-run `train.validate(model, D, device, threshold=T)` for one blend and write `promotion-T.json`. It's used only after selection (§4).

The existing `--selftest` (α = 0 equals stock and α = 1 equals source, bit-exact) remains a **weight** check only. Probability parity comes from the stock-reconstruction check above and from `export.py` parity: ORT vs PyTorch ≤ 1e-5 at B = 1 and 2 for each exported blend.

## 4. Promotion checks (frozen now; only reached if `sel-v4` selects a candidate)

Let `(blend, T)` be the selected candidate and threshold.

- **(a) Selected-threshold proxies:** using the §3.3 mode at **T**, in-loop **M3s ≥ 0.2416 − 0.020** and **M3-crop ≥ 0.5147 − 0.020**. Those are stock FP32's in-loop step-0 values at 0.5, identical in v2 and v3. Scores at 0.5 can't satisfy this check when T ≠ 0.5.
- **(b) Matched `turn_onset` (Niko):** take `sel-v4` arm G (candidate and stock FP32 under `agent-v0.1-turn-checks`). The candidate's M1 shift from `clip_start` to `turn_onset` must be no worse than stock's own shift + 2.0 pt. Report its M2 and M3 shifts as well.
- **(c) Audio acceptance (Guttuu):** the issue #3 checklist, candidate vs `stock_fp32`, with saved run IDs and timing logs.
- **(d) Human endpoints:** score on `items/v2`, built from accepted A/B labels (blinded to predictions until the labels are recorded) and from **separately reviewed unfinished-fluent coverage**. Compare candidate vs stock FP32 at 0.5, the comparator at 0.55, and the patient wait. Report PLAN's gate per group with Wilson CIs as **feasibility**, since these are dev sources.

A candidate is promoted to the demo only if (a)–(d) all hold. The B cross-check needs a named second human.

## 5. Timebox

- Record the **start time** at Niko's approved execution start, before any blend is evaluated.
- **Stop at start + 45 min, or 20:45 EDT, whichever comes first.** Don't compress verification to fit.
- Post all six blends' pre-screen rows, the `sel-v4` outcome and every artifact identity, selected or rejected.
- **There is no v5 and no extra sweep.** Report the result and a failure analysis before any later research step.
