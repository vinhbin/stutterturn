Development decision, not a publishable efficacy result. The candidate was ranked and selected on these dev items (pre-screen on M1, then up to 6 operating points); the claim comes only from the single test run in training-v1 §7.2.

Outcome: **dev_nothing_passes** (comparator_M1_below_B = True)

Out-id `sel-v4`; platform note: Windows 11, i7-13700HX, RTX 4070 Laptop (ORT CPU); runner platform: ['Windows-11-10.0.26200-SP0']; code commit cae125c23d91d9ef7d3fdcd58944c85438b52869.

## Summary (B, comparator, selected candidate, A)

| Row | M1 stutter premature | M2 fluent premature | M3 eow model-decided | M4 recall | M4b recall | M5 specificity |
|---|---|---|---|---|---|---|
| B: B stock-fp32 @0.50 | 47.4% (167/352; 42.3-52.7) | 50.5% (767/1518; 48.0-53.0) | 46.6% (317/680; 42.9-50.4) | 95.1% (1411/1484; 93.9-96.1) | 91.0% (1351/1484; 89.5-92.4) | 93.5% (1418/1516; 92.2-94.7) |
| comparator: C stock-fp32 @0.55 | 45.7% (161/352; 40.6-51.0) | 49.2% (747/1518; 46.7-51.7) | 45.1% (307/680; 41.4-48.9) | 94.8% (1407/1484; 93.6-95.8) | 90.5% (1343/1484; 88.9-91.9) | 93.9% (1423/1516; 92.5-95.0) |
| selected | none selected |  |  |  |  |  |
| A: A stock-int8 @0.50 | 57.4% (202/352; 52.2-62.5) | 60.4% (917/1518; 57.9-62.8) | 55.3% (376/680; 51.5-59.0) | n/a | n/a | n/a |

Cells: rate (k/n; Wilson 95% CI in points). Guard metrics are not computed for A.

## Constraint deltas vs B (point estimates bind; CIs and p-values are reported only)

**comparator: C stock-fp32 @0.55** (all constraints met: True)

| Metric | Delta vs B | Constraint | Met |
|---|---|---|---|
| M1 | -1.70 pt; Wald (paired) -3.06 to -0.35; (b,c)=(6,0); McNemar p=0.0312 | none (ranked) | - |
| M2 | -1.32 pt; Wald (paired) -1.89 to -0.74; (b,c)=(20,0); McNemar p=1.91e-06 | <= +1.0 pt | True |
| M3 | -1.47 pt; Wald (paired) -2.38 to -0.57; (b,c)=(10,0); McNemar p=0.00195 | >= -2.0 pt | True |
| M4 | -0.27 pt; Wald (paired) -0.53 to -0.01; (b,c)=(4,0); McNemar p=0.125 | >= -1.0 pt | True |
| M4b | -0.54 pt; Wald (paired) -0.91 to -0.17; (b,c)=(8,0); McNemar p=0.00781 | >= -1.0 pt | True |
| M5 | +0.33 pt; Wald (paired) +0.04 to +0.62; (b,c)=(0,5); McNemar p=0.0625 | >= 0 | True |

Note: on about 1.5k guard negatives, one flipped row decides ΔM5.

## Outcome

dev_nothing_passes: selected = none; comparator = C stock-fp32 @0.55; comparator_M1_below_B = True.

## Per-show M1 (stuttered, unfinished)

| Row | MyStutteringLife | StutteringIsCool |
|---|---|---|
| B: B stock-fp32 @0.50 | 46.0% (80/174) | 48.9% (87/178) |
| comparator: C stock-fp32 @0.55 | 43.1% (75/174) | 48.3% (86/178) |
| A: A stock-int8 @0.50 | 57.5% (100/174) | 57.3% (102/178) |

## Report-only arms (F patient waits, G turn-onset input)

| Arm | M1 | M2 | M3 | Delta M1 vs B | Delta M2 vs B | Delta M3 vs B |
|---|---|---|---|---|---|---|
| F04 stock-fp32 vad_stop_s=0.4 | 37.5% (132/352; 32.6-42.7) | 45.1% (685/1518; 42.6-47.6) | 52.8% (359/680; 49.0-56.5) | -9.94 pt; Wald (paired) -14.72 to -5.17; (b,c)=(56,21); McNemar p=8.22e-05 | -5.40 pt; Wald (paired) -7.47 to -3.33; (b,c)=(172,90); McNemar p=4.56e-07 | +6.18 pt; Wald (paired) +3.81 to +8.54; (b,c)=(14,56); McNemar p=4.3e-07 |
| F06 stock-fp32 vad_stop_s=0.6 | 26.7% (94/352; 22.4-31.6) | 33.5% (508/1518; 31.1-35.9) | 54.7% (372/680; 50.9-58.4) | -20.74 pt; Wald (paired) -26.19 to -15.29; (b,c)=(92,19); McNemar p=1.12e-12 | -17.06 pt; Wald (paired) -19.60 to -14.52; (b,c)=(345,86); McNemar p=8.08e-38 | +8.09 pt; Wald (paired) +5.09 to +11.09; (b,c)=(29,84); McNemar p=2.2e-07 |
| F08 stock-fp32 vad_stop_s=0.8 | 12.8% (45/352; 9.7-16.7) | 15.3% (232/1518; 13.6-17.2) | 48.2% (328/680; 44.5-52.0) | -34.66 pt; Wald (paired) -40.33 to -28.99; (b,c)=(134,12); McNemar p=3.03e-27 | -35.24 pt; Wald (paired) -37.93 to -32.55; (b,c)=(579,44); McNemar p=4.48e-120 | +1.62 pt; Wald (paired) -1.80 to +5.04; (b,c)=(65,76); McNemar p=0.4 |
| G-B stock-fp32 turn_onset | 50.3% (177/352; 45.1-55.5) | 51.8% (786/1518; 49.3-54.3) | 47.8% (325/680; 44.1-51.5) | +2.84 pt; Wald (paired) +0.94 to +4.75; (b,c)=(1,11); McNemar p=0.00635 | +1.25 pt; Wald (paired) +0.49 to +2.01; (b,c)=(8,27); McNemar p=0.00188 | +1.18 pt; Wald (paired) +0.37 to +1.99; (b,c)=(0,8); McNemar p=0.00781 |

F compares across different config_ids (use compare_runs --allow-config-diff for the same pairs).

## Test plan (training-v1 §7.2)

```json
{
 "comparator": {
  "arm": "C",
  "threshold": 0.55,
  "note": "rescore stock FP32 on test at this threshold"
 },
 "arms_to_run": [
  "A stock INT8 @0.5",
  "B stock FP32 @0.5",
  "C stock FP32 rescored @0.55"
 ],
 "selected_candidate": null,
 "note": "no candidate met every constraint; no candidate to run on test"
}
```

## Limits

- Labels are energy-derived (energy_vad), not human-confirmed.
- End-of-window items are proxies for completed turns.
- The guard set is not perfectly independent of the upstream checkpoint choice.
- Shortcut-learning risk (training-v1 §10): the model may learn that a stutter-like voice means an incomplete turn and wait too long on completed stuttered turns; state this risk in every claim.
- On about 1.5k guard negatives, one flipped row decides the sign of ΔM5 (constraint ΔM5 ≥ 0).
- Stuttered completed turns are energy proxies only (in-loop M3s), not human-confirmed.
- Training-v2 positives and the M3 items share one end-of-window proxy definition; agreeing with M3 means agreeing with the proxy, not answering real turn ends.
- Disclosure: v4 (weight interpolation of stock FP32 and the W3 prescreen top 2, no new training) was designed after v1, v2 and v3 all failed (dev_nothing_passes) on these same dev items; dev has served four pre-registered attempts. The test set stays sealed under D-009; a v4 pass is a development decision only and does not authorize a test run.
- Candidate 'epoch' is the blend's relative L2 weight distance from stock (‖θ − θ_stock‖ / ‖θ_stock‖); 'ties -> earlier' prefers the blend closest to stock.
