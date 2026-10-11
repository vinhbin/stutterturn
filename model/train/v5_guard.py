"""v5 preparation (D-014): a fresh guard set, disjoint from replay, crops and the old guard.

Proposal: issue #2 comment 6104449057. The old guard (data-v2/guard.jsonl, test-repo shards 0-3) has
guided four adaptive attempts plus X1; v5 selection uses this fresh guard instead and reports the old
one as secondary. Same source repo/revision and English filter as build_train_set.py; rows come only
from test-repo shards >= --first-shard (default 4, i.e. never read before).

  python model/train/v5_guard.py --work W --stage fetch          # cache English rows of shards 4.. (no scoring)
  python model/train/v5_guard.py --work W                        # select + write data-v5-guard/
  python model/train/v5_guard.py --selftest

Selection: drop any row whose id or wav_sha256 appears in the old guard or in replay (and so in any
crop parent); order the rest by sha256(seed:id); take --cap rows stratified by endpoint_bool in the
pool's ratio. Deterministic from the shard cache. No model is run.
"""
import argparse
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402
import build_train_set as B  # noqa: E402

DEFAULT_SEED = "v5-guard-1"


def seeded_key(seed, rid):
    return hashlib.sha256(f"{seed}:{rid}".encode()).hexdigest()


def select_fresh(pool, exclude_ids, exclude_wavs, cap, seed):
    """Pure selection: (chosen rows, counts)."""
    kept = [r for r in pool if r["id"] not in exclude_ids and r["wav_sha256"] not in exclude_wavs]
    # duplicates inside the new pool: keep the first by seeded order
    seen, uniq = set(), []
    for r in sorted(kept, key=lambda r: seeded_key(seed, r["id"])):
        if r["wav_sha256"] in seen:
            continue
        seen.add(r["wav_sha256"])
        uniq.append(r)
    pos = [r for r in uniq if r["endpoint_bool"]]
    neg = [r for r in uniq if not r["endpoint_bool"]]
    if len(uniq) < cap:
        sys.exit(f"REFUSING: only {len(uniq)} eligible rows for cap {cap}; fetch more shards")
    n_pos = int(round(cap * len(pos) / len(uniq)))
    chosen = pos[:n_pos] + neg[:cap - n_pos]
    return chosen, {"pool": len(pool), "excluded_overlap": len(pool) - len(kept),
                    "excluded_dup_in_pool": len(kept) - len(uniq), "eligible": len(uniq),
                    "chosen": len(chosen), "chosen_endpoint_true": n_pos}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work")
    ap.add_argument("--stage", choices=["fetch", "build"], default="build")
    ap.add_argument("--data", default="data-v2", help="dir holding the old guard + replay to exclude")
    ap.add_argument("--out", default="data-v5-guard")
    ap.add_argument("--first-shard", type=int, default=4)
    ap.add_argument("--cap", type=int, default=3000)
    ap.add_argument("--seed", default=DEFAULT_SEED)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.work:
        ap.error("--work required")
    w, root = os.path.realpath(a.work), os.path.realpath(C.ROOT)
    if os.path.commonpath([w, root]) == root:
        sys.exit(f"REFUSING: --work {a.work} is inside the repo; FLAC caches must stay outside git")
    old = json.load(open(os.path.join(a.work, a.data, "manifest.json")))["guard"]
    if a.first_shard < old["shards_read"]:
        sys.exit(f"REFUSING: --first-shard {a.first_shard} overlaps the old guard's shards 0-{old['shards_read'] - 1}")
    spec = dict(B.GUARD)
    shards = range(a.first_shard, spec["n_shards"])
    record_path = os.path.join(a.work, a.out + "-fetch.json")
    if a.stage == "fetch":
        if os.path.exists(record_path):
            sys.exit(f"REFUSING: {record_path} exists (the shard list is pinned once)")
        total, record = 0, []
        for k in shards:
            n = len(B.fetch_shard(a.work, spec, k))
            total += n
            record.append({"shard": k, "english_rows": n, "rows_jsonl_sha256": C.sha256_file(
                os.path.join(B.cache_dir(a.work, spec["tag"], k), "rows.jsonl"))})
            if total >= a.cap * 1.2:  # headroom for exclusions and stratification
                break
        C.write_json(record_path, {"source": {k: spec[k] for k in ("repo", "revision")}, "first_shard": a.first_shard,
                                   "cap": a.cap, "shards": record, "code_commit": C.git_commit()})
        print(f"FETCH DONE: {total} English rows from shards {[r['shard'] for r in record]}; pinned in {record_path}")
        return
    if not os.path.exists(record_path):
        sys.exit("no pinned shard list: run --stage fetch first")
    record = json.load(open(record_path))
    pinned = [r["shard"] for r in record["shards"]]
    cached = sorted(k for k in shards if os.path.exists(os.path.join(B.cache_dir(a.work, spec["tag"], k), "rows.jsonl")))
    if cached != pinned:
        sys.exit(f"REFUSING: cached guard shards {cached} != pinned fetch list {pinned}")
    pool, used = [], []
    for r in record["shards"]:
        p = os.path.join(B.cache_dir(a.work, spec["tag"], r["shard"]), "rows.jsonl")
        if C.sha256_file(p) != r["rows_jsonl_sha256"]:
            sys.exit(f"REFUSING: shard {r['shard']} rows.jsonl changed since fetch")
        pool += [json.loads(l) for l in open(p)]
        used.append(r["shard"])
    excl = [json.loads(l) for f in ("guard.jsonl", "orig_replay.jsonl") for l in open(os.path.join(a.work, a.data, f))]
    chosen, counts = select_fresh(pool, {r["id"] for r in excl}, {r["wav_sha256"] for r in excl}, a.cap, a.seed)
    out = os.path.join(a.work, a.out)
    if os.path.exists(out):
        sys.exit(f"REFUSING: {out} exists")
    os.makedirs(out)
    rows = [dict(r, label=int(r["endpoint_bool"])) for r in sorted(chosen, key=lambda r: r["id"])]
    sha = B.write_jsonl(os.path.join(out, "guard.jsonl"), rows)
    C.write_json(os.path.join(out, "manifest.json"), {
        "script": "model/train/v5_guard.py", "code_commit": C.git_commit(), "seed": a.seed,
        "source": {k: spec[k] for k in ("repo", "revision")}, "language_filter": "eng",
        "shards_used": used, "fetch_record_sha256": C.sha256_file(record_path),
        "excluded_against": {"data_dir": a.data,
                                                  "manifest_sha256": C.sha256_file(os.path.join(a.work, a.data, "manifest.json"))},
        "counts": counts, "guard_sha256": sha,
        "tally": {"n": len(rows), "endpoint_true": sum(r["endpoint_bool"] for r in rows),
                  "synthetic": sum(bool(r["synthetic"]) for r in rows),
                  "midfiller": sum(bool(r["midfiller"]) for r in rows),
                  "endfiller": sum(bool(r["endfiller"]) for r in rows)},
        "use": "v5 selection guard (M4/M4b/M5); never trained on; no model scored on it before v5 selection"})
    print(json.dumps({"guard_sha256": sha, **counts}))


def selftest():
    def row(i, ep, wav=None):
        return {"id": f"r{i}", "endpoint_bool": ep, "wav_sha256": wav or f"w{i}"}
    pool = [row(i, i % 2 == 0) for i in range(100)] + [row(100, True, "w5"), row(101, False, "dup"), row(102, True, "dup")]
    chosen, c = select_fresh(pool, {"r0", "r1"}, {"w2"}, 40, "s")
    ids = {r["id"] for r in chosen}
    ok = True
    for name, cond in [
        ("excluded ids never chosen", not ids & {"r0", "r1"}),
        ("excluded wav hashes never chosen", all(r["wav_sha256"] != "w2" for r in chosen)),
        ("no duplicate audio in the new guard", len({r["wav_sha256"] for r in chosen}) == len(chosen)),
        ("cap respected", len(chosen) == 40),
        ("stratified ~50/50", abs(sum(r["endpoint_bool"] for r in chosen) - 20) <= 1),
        ("deterministic", [r["id"] for r in select_fresh(pool, {"r0", "r1"}, {"w2"}, 40, "s")[0]] == [r["id"] for r in chosen]),
        ("seed changes selection", [r["id"] for r in select_fresh(pool, {"r0", "r1"}, {"w2"}, 40, "t")[0]] != [r["id"] for r in chosen]),
    ]:
        print(f"  {'ok' if cond else 'FAIL'}: {name}")
        ok &= bool(cond)
    print("SELFTEST " + ("PASSED" if ok else "FAILED"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
