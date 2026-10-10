"""Fetch dev/test split audio from the HF mirror miosipof/sep28k_full into benchmark/audio/.

Spec: benchmark/specs/eval-items-v1.md. Default: block + fluent clips of dev and test.
Files already present (> 1000 bytes) are skipped. Files that are empty on the mirror are
recorded in audio/empty_on_mirror.txt and never re-fetched. Writes audio/fetch_log.json.
"""
import argparse, csv, json, os, shutil, sys, time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIO = os.path.join(BASE, "audio")
EMPTY_LIST = os.path.join(AUDIO, "empty_on_mirror.txt")
MIN_BYTES = 1000
REPO = "miosipof/sep28k_full"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--splits", nargs="+", default=["dev", "test"], choices=["dev", "test"])
    ap.add_argument("--categories", nargs="+", default=["block", "fluent"],
                    choices=["block", "fluent", "other_disfluent"])
    ap.add_argument("--workers", type=int, default=16)
    args = ap.parse_args()
    os.makedirs(AUDIO, exist_ok=True)

    by_base = defaultdict(list)
    for line in open(os.path.join(BASE, "data", "hf_miosipof_files.txt")):
        line = line.strip()
        if line:
            by_base[os.path.basename(line)].append(line)

    keys = []
    for sp in args.splits:
        with open(os.path.join(BASE, "splits", "v1", f"{sp}.csv"), newline="") as f:
            keys += [r["clip_key"] for r in csv.DictReader(f) if r["category"] in args.categories]
    keys = sorted(set(keys))
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
    print(f"{len(keys)} clips selected ({'+'.join(args.splits)}; {'+'.join(args.categories)}); "
          f"{len(known_empty)} known empty on mirror")

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
    log = {"selected": len(keys), "splits": args.splits, "categories": args.categories,
           "ok": cnt["ok"], "cached": cnt["cached"], "failed": cnt["fail"],
           "empty_on_mirror_new": len(new_empty), "skipped_known_empty": cnt["known_empty"],
           "empty_on_mirror_total": len(all_empty), "failures": sorted(fails)[:100],
           "wall_s": round(time.time() - t0, 1)}
    json.dump(log, open(os.path.join(AUDIO, "fetch_log.json"), "w"), indent=1)
    print(f"FINAL: ok={cnt['ok']} cached={cnt['cached']} failed={cnt['fail']} "
          f"empty-on-mirror(new)={len(new_empty)} skipped-known-empty={cnt['known_empty']} "
          f"empty-on-mirror(total list)={len(all_empty)}")
    for m in fails[:20]:
        print("FAIL:", m)
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
