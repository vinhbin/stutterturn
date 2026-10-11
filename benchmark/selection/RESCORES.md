# Threshold-rescore runs (not committed; regenerate on demand)

The `sel-v2`, `sel-v3` and `sel-v4` selections each produced threshold **rescores**:
- **arm C:** stock FP32 at 0.50–0.99;
- **arm E:** each candidate at 0.4, 0.5 and 0.6.

These are 330 run directories, about 212 MB. They're deterministic and need **0 model calls**: each is `eval_runner.py --rescore` of a committed inference run at another threshold. Their metrics are already in each selection's `decision.json`.

To keep the repository small, they aren't committed. [`rescores.tsv`](rescores.tsv) lists every one: `run_id`, the committed source run it was rescored from, the config, and the threshold.

## Regenerate

Run from the repository root, with the benchmark venv:

```bash
tail -n +2 benchmark/selection/rescores.tsv | while IFS=$'\t' read -r rid src cfg th; do
  python benchmark/scripts/eval_runner.py --rescore "benchmark/runs/$src" \
    --config "benchmark/configs/$cfg.json" --threshold "$th" --run-id "$rid"
done
```

## Verification (Niko, 2026-10-10)

- `sel-v3-C-main-th0.73`, `sel-v3-E1-main-th0.40` and `sel-v4-C-eow-th0.55` were regenerated from the committed source runs. Their `results.jsonl` and `summary.json` are **identical in content** to the originals: every row, field and value. The only byte differences are Windows line endings and formatting from the original machine.
- Independently of these files, every metric in all three `decision.json` files (`sel-v2` 60 rows, `sel-v3` 60, `sel-v4` 56) was recomputed from the committed inference runs and guard `per_row` files. All values match, and every outcome is `dev_nothing_passes` with comparator C @0.55.
- Original files: Guttuu's branch `guttuu/selection-evidence` @ `0a304f0` holds the full set, including these rescores.
