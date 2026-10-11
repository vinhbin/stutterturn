"""Fetch TRAIN-split SEP-28k clips into benchmark/audio/ (model/specs/training-v1.md 2a).

Same mirror, idiom and empty-on-mirror log as benchmark/scripts/fetch_split_audio.py,
which only allows dev/test. Also fetches the clips named in a legacy/eval items file
(--items-from) so the zero-step identity check (section 8 check 3) can run.

  python model/train/fetch_train_audio.py                     # train block clips
  python model/train/fetch_train_audio.py --items-from benchmark/runs/legacy-items/block.jsonl
"""
import argparse, csv, json, os, shutil, sys, time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASE = os.path.join(ROOT, "benchmark")
AUDIO = os.path.join(BASE, "audio")
EMPTY_LIST = os.path.join(AUDIO, "empty_on_mirror.txt")
MIN_BYTES = 1000
REPO = "miosipof/sep28k_full"


def split_keys(split, categories):
    with open(os.path.join(BASE, "splits", "v1", f"{split}.csv"), newline="") as f:
        return {r["clip_key"] for r in csv.DictReader(f) if r["category"] in categories}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--categories", nargs="+", default=["block"],
                    choices=["block", "fluent", "other_disfluent"])
    ap.add_argument("--items-from", help="items .jsonl whose clip_key audio to fetch instead")
    ap.add_argument("--workers", type=int, default=16)
    args = ap.parse_args()
    os.makedirs(AUDIO, exist_ok=True)

    if args.items_from:
        keys = sorted({json.loads(l)["clip_key"] for l in open(args.items_from) if l.strip()})
        source = os.path.relpath(args.items_from, ROOT)
    else:
        keys = sorted(split_keys("train", args.categories))
        held_out = split_keys("dev", {"block", "fluent", "other_disfluent"}) | \
            split_keys("test", {"block", "fluent", "other_disfluent"})
        leak = set(keys) & held_out
        if leak:
            sys.exit(f"REFUSING: {len(leak)} train keys also in dev/test, e.g. {sorted(leak)[:3]}")
        source = "train:" + "+".join(args.categories)

    by_base = defaultdict(list)
    for line in open(os.path.join(BASE, "data", "hf_miosipof_files.txt")):
        line = line.strip()
        if line:
            by_base[os.path.basename(line)].append(line)
    paths, unmapped, ambiguous = {}, [], []
    for k in keys:
        c = by_base.get(k + ".wav", [])
        if len(c) == 1:
            paths[k] = c[0]
        elif not c:
            unmapped.append(k)
        else:
            ambiguous.append(k)
    if unmapped or ambiguous:
        sys.exit(f"mirror mapping not unique: unmapped={len(unmapped)} ambiguous={len(ambiguous)}")

    known_empty = set()
    if os.path.exists(EMPTY_LIST):
        known_empty = {l.strip() for l in open(EMPTY_LIST) if l.strip()}
    print(f"{len(keys)} clips selected ({source}); {len(known_empty)} known empty on mirror")

    from huggingface_hub import hf_hub_download

    def fetch(k):
        dest = os.path.join(AUDIO, k + ".wav")
        if os.path.exists(dest) and os.path.getsize(dest) > MIN_BYTES:
            return "cached", k, ""
        if k in known_empty:
            return "known_empty", k, ""
        try:
            p = hf_hub_download(REPO, paths[k], repo_type="dataset")
            if os.path.getsize(p) <= MIN_BYTES:
                return "empty", k, ""
            tmp = dest + ".part"
            shutil.copyfile(p, tmp)
            os.replace(tmp, dest)  # atomic: a crash never leaves a truncated .wav
            return "ok", k, ""
        except Exception as e:
            return "fail", k, f"{k}: {e}"

    cnt = defaultdict(int)
    fails, new_empty = [], []
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(fetch, k) for k in keys]
        for i, fut in enumerate(as_completed(futs)):
            st, k, msg = fut.result()
            cnt[st] += 1
            if st == "fail":
                fails.append(msg)
            elif st == "empty":
                new_empty.append(k)
            if (i + 1) % 250 == 0:
                print(f"{i+1}/{len(keys)} " + " ".join(f"{a}={b}" for a, b in sorted(cnt.items())), flush=True)

    all_empty = sorted(known_empty | set(new_empty))
    with open(EMPTY_LIST, "w") as f:
        f.write("".join(k + "\n" for k in all_empty))
    print(f"FINAL ({source}): ok={cnt['ok']} cached={cnt['cached']} failed={cnt['fail']} "
          f"empty-on-mirror(new)={len(new_empty)} skipped-known-empty={cnt['known_empty']} "
          f"wall={time.time() - t0:.0f}s")
    for m in fails[:20]:
        print("FAIL:", m)
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
