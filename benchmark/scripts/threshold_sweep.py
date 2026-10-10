"""Threshold sweep for Smart Turn v3.2: is there a decision-threshold setting that keeps
block cut-offs <10% while fluent added latency stays <300 ms?

Re-runs fluent latency WITHOUT early break to get full probability curves, then sweeps
thresholds over saved block/pause probabilities and fresh fluent curves.
NOTE: pipecat's LocalSmartTurnAnalyzerV3 hardcodes 0.5; sweeping requires a fork, so this
is 'one line of code away', not an exposed config knob.
"""
import csv, json, os
import numpy as np
import soundfile as sf

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
AUDIO = os.path.join(BASE, "audio")
import sys
sys.path.insert(0, os.path.join(BASE, "scripts"))
from run_model_arm import predict, FLUENT_CHECKPOINTS, SR  # reuses session/extractor

THRESHOLDS = [0.5, 0.7, 0.8, 0.9, 0.95, 0.99]

# ---- fluent full curves ----
fluent_rows = list(csv.DictReader(open(os.path.join(DATA, "fluent_eval.csv"))))
eligible = [r for r in fluent_rows if float(r["trailing_sil"]) >= 0.5]
curves = []
cache_path = os.path.join(DATA, "model_fluent_full_curves.json")
if os.path.exists(cache_path):
    curves = json.load(open(cache_path))
else:
    for n, r in enumerate(eligible):
        x, _ = sf.read(os.path.join(AUDIO, r["file"]), dtype="float32")
        speech_end, trailing = float(r["speech_end"]), float(r["trailing_sil"])
        probs = {}
        for t in FLUENT_CHECKPOINTS:
            if t > trailing:
                break
            probs[str(t)] = round(predict(x[:int((speech_end + t) * SR)]), 4)
        curves.append({"file": r["file"], "trailing": trailing, "probs": probs})
        if (n + 1) % 25 == 0:
            print(f"fluent curves {n+1}/{len(eligible)}", flush=True)
    json.dump(curves, open(cache_path, "w"), indent=1)

block_rows = list(csv.DictReader(open(os.path.join(DATA, "model_block_results.csv"))))
pause_rows = list(csv.DictReader(open(os.path.join(DATA, "model_fluent_pause_results.csv"))))

print(f"\n{'th':>5} | {'block cut first%':>16} | {'block cut any%':>14} | {'fluent lat med (decided)':>24} | {'fluent censored%':>16} | {'pause false%':>12}")
table = []
for th in THRESHOLDS:
    n = len(block_rows)
    first = sum(1 for r in block_rows if json.loads(r["probs"])[sorted(json.loads(r["probs"]))[0]] > th)
    anyc = sum(1 for r in block_rows if any(p > th for p in json.loads(r["probs"]).values()))
    lats, cens = [], 0
    for c in curves:
        lat = None
        for t in FLUENT_CHECKPOINTS:
            p = c["probs"].get(str(t))
            if p is not None and p > th:
                lat = t
                break
        if lat is None:
            cens += 1
        else:
            lats.append(lat)
    la = np.array(lats) if lats else np.array([np.nan])
    pf = sum(1 for r in pause_rows if float(r["prob"]) > th)
    row = {"threshold": th,
           "block_cutoff_first_pct": round(100 * first / n, 1),
           "block_cutoff_any_pct": round(100 * anyc / n, 1),
           "fluent_latency_median_s": round(float(np.nanmedian(la)), 2),
           "fluent_latency_p90_s": round(float(np.nanpercentile(la, 90)), 2) if lats else None,
           "fluent_censored_pct": round(100 * cens / len(curves), 1),
           "pause_false_pct": round(100 * pf / len(pause_rows), 1)}
    table.append(row)
    print(f"{th:>5} | {row['block_cutoff_first_pct']:>15}% | {row['block_cutoff_any_pct']:>13}% | "
          f"{row['fluent_latency_median_s']:>22}s | {row['fluent_censored_pct']:>15}% | {row['pause_false_pct']:>11}%")

json.dump(table, open(os.path.join(DATA, "threshold_sweep.json"), "w"), indent=1)
print("\nNote: fluent 'censored' = model never crossed threshold within the clip's trailing")
print("silence (max 1.0s tested) — in a real agent these turns fall back to a hard timeout.")
