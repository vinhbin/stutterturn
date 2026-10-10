"""Download selected SEP-28k clips from the HF mirror miosipof/sep28k_full."""
import csv, os, shutil, sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from huggingface_hub import hf_hub_download

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
AUDIO = os.path.join(BASE, "audio")
os.makedirs(AUDIO, exist_ok=True)

files = set()
for name in ["block_candidates.csv", "fluent_candidates.csv"]:
    with open(os.path.join(DATA, name)) as f:
        for row in csv.DictReader(f):
            files.add(row["file"])
print(f"{len(files)} unique files to fetch")

def fetch(f):
    dest = os.path.join(AUDIO, os.path.basename(f))
    if os.path.exists(dest) and os.path.getsize(dest) > 1000:
        return ("cached", f)
    try:
        p = hf_hub_download("miosipof/sep28k_full", f, repo_type="dataset")
        shutil.copyfile(p, dest)
        return ("ok", f)
    except Exception as e:
        return ("fail", f"{f}: {e}")

ok = fail = cached = 0
fails = []
with ThreadPoolExecutor(max_workers=16) as ex:
    futs = [ex.submit(fetch, f) for f in sorted(files)]
    for i, fut in enumerate(as_completed(futs)):
        status, msg = fut.result()
        if status == "ok": ok += 1
        elif status == "cached": cached += 1
        else:
            fail += 1; fails.append(msg)
        if (i + 1) % 100 == 0:
            print(f"{i+1}/{len(files)} done (ok={ok} cached={cached} fail={fail})", flush=True)

print(f"FINAL: ok={ok} cached={cached} fail={fail}")
for m in fails[:20]:
    print("FAIL:", m)
