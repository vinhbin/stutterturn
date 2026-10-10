"""Select BLOCK and FLUENT eval candidates from SEP-28k labels and verify against HF file list."""
import csv, os, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")

DISFLUENCY = ["Prolongation", "Block", "SoundRep", "WordRep", "Interjection"]
QUALITY_BAD = ["Unsure", "PoorAudioQuality", "DifficultToUnderstand", "Music", "NoSpeech"]

rows = []
with open(os.path.join(DATA, "SEP-28k_labels.csv")) as f:
    r = csv.DictReader(f)
    for row in r:
        row = {k.strip(): (v.strip() if v else v) for k, v in row.items()}
        for k in row:
            if k not in ("Show",):
                try:
                    row[k] = int(row[k])
                except (ValueError, TypeError):
                    pass
        rows.append(row)

print(f"label rows: {len(rows)}")

hf_files = set(open(os.path.join(DATA, "hf_miosipof_files.txt")).read().split("\n"))

def fname(row):
    return f"data/{row['Show']}/{row['Show']}_{row['EpId']}_{row['ClipId']}.wav"

block, fluent = [], []
missing_on_hf = 0
for row in rows:
    f = fname(row)
    on_hf = f in hf_files
    # quality gate: skip clips that >=2 annotators flagged as bad audio / no speech / music
    bad = any(row[c] >= 2 for c in QUALITY_BAD)
    if row["Block"] >= 2 and not bad:
        if not on_hf:
            missing_on_hf += 1
            continue
        block.append(row)
    elif (row["NoStutteredWords"] >= 2
          and all(row[c] < 2 for c in DISFLUENCY)
          and not bad):
        if not on_hf:
            missing_on_hf += 1
            continue
        fluent.append(row)

print(f"BLOCK candidates (Block>=2, quality-gated): {len(block)}")
print(f"  of which Block==3 (unanimous): {sum(1 for r in block if r['Block']==3)}")
print(f"FLUENT candidates (NoStutteredWords>=2, all disfluencies<2, quality-gated): {len(fluent)}")
print(f"candidates missing on HF mirror: {missing_on_hf}")

# Prioritize: BLOCK by Block count desc (unanimous first), then stable order.
block.sort(key=lambda r: (-r["Block"],))
# FLUENT: NoStutteredWords==3 and zero disfluency votes first
fluent.sort(key=lambda r: (-r["NoStutteredWords"], sum(r[c] for c in DISFLUENCY)))

N_BLOCK = 500   # extra headroom: many will be excluded for no detectable internal gap
N_FLUENT = 300
sel_block = block[:N_BLOCK]
sel_fluent = fluent[:N_FLUENT]

cols = ["Show", "EpId", "ClipId", "Start", "Stop", "Prolongation", "Block", "SoundRep",
        "WordRep", "Interjection", "NoStutteredWords", "NaturalPause", "file"]
for name, sel in [("block_candidates.csv", sel_block), ("fluent_candidates.csv", sel_fluent)]:
    with open(os.path.join(DATA, name), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for row in sel:
            w.writerow([row[c] for c in cols[:-1]] + [fname(row)])
    print(f"wrote {name}: {len(sel)} rows")
