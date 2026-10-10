"""Spot-check: plot RMS profiles of 10 BLOCK eval samples with detected gap/resume markers."""
import csv, os
import numpy as np
import soundfile as sf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import sys
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "scripts"))
from build_eval_sets import analyze

DATA = os.path.join(BASE, "data")
AUDIO = os.path.join(BASE, "audio")
OUT = os.path.join(DATA, "spotcheck")
os.makedirs(OUT, exist_ok=True)

rows = list(csv.DictReader(open(os.path.join(DATA, "block_eval.csv"))))
# deterministic spread: every 20th sample
picks = rows[::20][:10]

fig, axes = plt.subplots(5, 2, figsize=(14, 16))
for ax, r in zip(axes.flat, picks):
    a = analyze(os.path.join(AUDIO, r["file"]))
    ax.plot(a["t"], a["db"], lw=0.8, color="#1f77b4")
    ax.axhline(a["th"], color="gray", ls=":", label=f"VAD th {a['th']:.0f} dB")
    gs, res = float(r["gap_start"]), float(r["resume"])
    ax.axvspan(gs, res, color="red", alpha=0.15)
    ax.axvline(gs, color="red", ls="--", lw=1)
    ax.axvline(res, color="green", ls="--", lw=1)
    ax.set_title(f"{r['file']}  gap={r['gap_dur']}s (Block votes={r['Block']})", fontsize=9)
    ax.set_xlabel("s"); ax.set_ylabel("RMS dBFS"); ax.set_ylim(-70, 0)
fig.suptitle("BLOCK spot-check: frame RMS, detected gap (red span) and resume (green)", y=1.0)
fig.tight_layout()
fig.savefig(os.path.join(OUT, "block_spotcheck_rms.png"), dpi=90)
print("saved", os.path.join(OUT, "block_spotcheck_rms.png"))
for r in picks:
    print(r["file"], "gap_start", r["gap_start"], "resume", r["resume"], "gap_dur", r["gap_dur"], "pre_speech", r["pre_speech"])
