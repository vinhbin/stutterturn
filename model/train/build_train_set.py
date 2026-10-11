"""Build the training data references (model/specs/training-v1.md section 2).

  python model/train/build_train_set.py --work W --stage fetch   # stream shards -> English-row cache
  python model/train/build_train_set.py --work W                 # select + write jsonl + manifest
  python model/train/build_train_set.py --work W --out SCRATCH --plant-key <dev key>   # check 7

Writes <out>/{stutter_neg,orig_replay,guard}.jsonl (references, labels, weights; no audio)
and <out>/manifest.json (default <out> = W/data). Smart Turn shards are streamed one at a
time; only English rows' FLAC bytes are kept (W/data/shards/), then the shard is deleted.
Selection reads only that cache, so rebuilding gives identical jsonl hashes.
"""
import argparse
import csv
import hashlib
import io
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

sys.path.insert(0, os.path.join(C.BENCH, "scripts"))

REPLAY = {"repo": "pipecat-ai/smart-turn-data-v3.2-train",
          "revision": "f8c95d284595defb6b88a715c356cbc5c31b7ad1", "n_shards": 83, "tag": "replay"}
GUARD = {"repo": "pipecat-ai/smart-turn-data-v3.2-test",
         "revision": "dfc179241fee65b0efe81ca37786f41ce26f38ec", "n_shards": 10, "tag": "guard",
         "max_shards": 4}
META_COLS = ["id", "language", "endpoint_bool", "midfiller", "endfiller", "synthetic", "dataset"]
OFFSETS = [round(0.20 + 0.05 * k, 2) for k in range(9)]  # 0.20 .. 0.60


def sha_id(s):
    return hashlib.sha256(str(s).encode()).hexdigest()


def shard_name(k, n):
    return f"data/train-{k:05d}-of-{n:05d}.parquet"


# ---------------------------------------------------------------- shard cache
def cache_dir(work, tag, k):
    return os.path.join(work, "data", "shards", f"{tag}-{k:05d}")


def fetch_shard(work, spec, k):
    """Download shard k, keep English rows (FLAC bytes + metadata), delete the shard."""
    d = cache_dir(work, spec["tag"], k)
    done = os.path.join(d, "rows.jsonl")
    if os.path.exists(done):
        return [json.loads(l) for l in open(done)]
    import pyarrow.parquet as pq
    import soundfile as sf
    from huggingface_hub import hf_hub_download
    tmp = os.path.join(work, "tmp-shard")
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp)
    try:
        path = hf_hub_download(spec["repo"], shard_name(k, spec["n_shards"]), repo_type="dataset",
                               revision=spec["revision"], local_dir=tmp)
        meta = pq.read_table(path, columns=META_COLS).to_pylist()
        eng = [i for i, r in enumerate(meta) if r["language"] == "eng"]
        audio = pq.read_table(path, columns=["audio"]).column("audio").to_pylist()
        os.makedirs(os.path.join(d, "audio"), exist_ok=True)
        rows = []
        for i in eng:
            r, b = meta[i], audio[i]["bytes"]
            x, sr = sf.read(io.BytesIO(b), dtype="int16")
            if sr != C.SR:
                sys.exit(f"{spec['tag']} shard {k} row {r['id']}: {sr} Hz, expected {C.SR}")
            if x.ndim > 1:
                sys.exit(f"{spec['tag']} shard {k} row {r['id']}: not mono")
            fname = sha_id(r["id"])[:20] + ".flac"
            with open(os.path.join(d, "audio", fname), "wb") as f:
                f.write(b)
            rows.append({"id": r["id"], "id_sha256": sha_id(r["id"]), "shard": k,
                         "endpoint_bool": bool(r["endpoint_bool"]), "midfiller": r["midfiller"],
                         "endfiller": r["endfiller"], "synthetic": r["synthetic"], "dataset": r["dataset"],
                         "n_samples": int(len(x)), "wav_sha256": C.sha256_bytes(x.astype("<i2").tobytes()),
                         "audio": os.path.relpath(os.path.join(d, "audio", fname), work).replace("\\", "/")})
        with open(done + ".part", "w") as f:
            for r in rows:
                f.write(json.dumps(r, sort_keys=True) + "\n")
        os.replace(done + ".part", done)
        print(f"{spec['tag']} shard {k:05d}: {len(meta)} rows, {len(rows)} English", flush=True)
        return rows
    finally:
        shutil.rmtree(tmp, ignore_errors=True)  # never keep the ~500 MB shard


def collect(work, spec, cap, fetch):
    """Read shards in order until the English rows reach cap (or limits). Returns per-shard rows."""
    out, total = [], 0
    limit = spec.get("max_shards", spec["n_shards"])
    for k in range(limit):
        d = os.path.join(cache_dir(work, spec["tag"], k), "rows.jsonl")
        if not fetch and not os.path.exists(d):
            break
        rows = fetch_shard(work, spec, k)
        out.append(rows)
        total += len(rows)
        if total >= cap:
            break
    return out


def select(per_shard, cap):
    """All English rows of full shards; the last shard is cut to the remaining count,
    stratified by endpoint_bool in that shard's ratio, lowest sha256(id) first."""
    chosen = []
    for rows in per_shard:
        need = cap - len(chosen)
        if need <= 0:
            break
        if len(rows) <= need:
            chosen += rows
            continue
        pos = sorted([r for r in rows if r["endpoint_bool"]], key=lambda r: r["id_sha256"])
        neg = sorted([r for r in rows if not r["endpoint_bool"]], key=lambda r: r["id_sha256"])
        n_pos = int(round(need * len(pos) / len(rows)))
        chosen += pos[:n_pos] + neg[:need - n_pos]
    return chosen


# ---------------------------------------------------------------- stutter negatives
def split_keys(name):
    with open(os.path.join(C.BENCH, "splits", "v1", f"{name}.csv"), newline="") as f:
        return [r for r in csv.DictReader(f)]


def stutter_negatives(plant_key=None):
    import build_items as bi
    import build_eval_sets as bes
    train_rows = split_keys("train")
    train_keys = {r["clip_key"] for r in train_rows}
    held = {r["clip_key"] for s in ("dev", "test") for r in split_keys(s)}
    man = json.load(open(os.path.join(C.BENCH, "items", "v1", "manifest.json")))
    annotated = set(man.get("annotated_dev_test_keys", []))
    blocks = [r["clip_key"] for r in train_rows if r["category"] == "block"]
    if plant_key:
        blocks.append(plant_key)
    for k in blocks:  # leakage asserts (section 2a)
        if k not in train_keys or k in held or k in annotated:
            sys.exit(f"REFUSING: clip {k} is not a train-only key (dev/test/annotated leakage)")
    empty_path = os.path.join(C.BENCH, "audio", "empty_on_mirror.txt")
    empty = {l.strip() for l in open(empty_path) if l.strip()} if os.path.exists(empty_path) else set()
    gate = bi.Gate(empty)
    rows, counts = [], {}
    for key in sorted(blocks):
        reason, _ = gate(key)
        if reason:
            counts[reason] = counts.get(reason, 0) + 1
            continue
        a = bes.analyze(os.path.join(C.BENCH, "audio", key + ".wav"))
        gs, rs, _pre, why = bes.find_first_gap(a)
        if why != "ok":
            counts[why] = counts.get(why, 0) + 1
            continue
        gap = float(rs - gs)
        offs = [t for t in OFFSETS if t < gap - 0.05 - 1e-9]
        if not offs:
            counts["no_offset_fits"] = counts.get("no_offset_fits", 0) + 1
            continue
        counts["ok"] = counts.get("ok", 0) + 1
        for t in offs:
            if len(offs) == 1:
                w = 1.0
            elif t == 0.20:
                w = 0.5
            else:
                w = 0.5 / (len(offs) - 1)
            rows.append({"id": f"stu-{key}-t{t:.2f}", "clip_key": key, "audio": f"audio/{key}.wav",
                         "gap_start_s": round(float(gs), 3), "resume_s": round(float(rs), 3),
                         "offset_s": t, "cut_samples": int(round((float(gs) + t) * C.SR)),
                         "label": 0, "weight": round(w, 6)})
    return rows, counts, {"blocks_in_train": len(blocks) - (1 if plant_key else 0),
                          "annotated_dev_test_keys": len(annotated)}


def wquantiles(values, weights, qs):
    """Weighted quantiles (inverse CDF on the cumulative normalized weight)."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    v = [values[i] for i in order]
    w = [weights[i] for i in order]
    total, acc, cum = sum(w), 0.0, []
    for x in w:
        acc += x
        cum.append(acc / total)
    out = []
    for q in qs:
        lo, hi = 0, len(cum) - 1
        while lo < hi:  # first index with cum >= q
            mid = (lo + hi) // 2
            if cum[mid] >= q:
                hi = mid
            else:
                lo = mid + 1
        out.append(v[lo])
    return out


def sep_positives(stu, plant_key=None, allow_length_mismatch=False):
    """training-v2 2e: SEP-28k train-show completed proxies (label 1), length-matched to
    the 2a cut-length distribution, stuttered/fluent groups weighted 0.5 each."""
    import proxies as P
    train_rows = split_keys("train")
    train_keys = {r["clip_key"] for r in train_rows}
    held = {r["clip_key"] for s in ("dev", "test") for r in split_keys(s)}
    man = json.load(open(os.path.join(C.BENCH, "items", "v1", "manifest.json")))
    annotated = set(man.get("annotated_dev_test_keys", []))
    cand = [r for r in train_rows if r["category"] in P.GROUP]
    if plant_key:
        cand.append({"clip_key": plant_key, "category": "fluent"})
    for r in cand:
        k = r["clip_key"]
        if k not in train_keys or k in held or k in annotated:
            sys.exit(f"REFUSING: clip {k} is not a train-only key (dev/test/annotated leakage)")
    clips, counts = P.completed_proxies(cand)

    lens = [r["cut_samples"] for r in stu]
    lw = [r["weight"] for r in stu]
    by_group = {"stuttered": [c for c in clips if c["group"] == "stuttered"],
                "fluent": [c for c in clips if c["group"] == "fluent"]}
    rows = []
    for group, gclips in by_group.items():
        for c in gclips:
            offs = [t for t in OFFSETS if c["te"] + t <= c["dur"] - 0.01 + 1e-9]
            if not offs:
                continue
            clip_w = 0.5 / len(gclips)
            for t in offs:
                if len(offs) == 1:
                    w = 1.0
                elif t == 0.20:
                    w = 0.5
                else:
                    w = 0.5 / (len(offs) - 1)
                cut = int(round((c["te"] + t) * C.SR))
                u = int(hashlib.sha256(f"{c['clip_key']}|{t:.2f}".encode()).hexdigest(), 16) / 2 ** 256
                L = int(wquantiles(lens, lw, [u])[0])
                rows.append({"id": f"pos-{c['clip_key']}-t{t:.2f}", "clip_key": c["clip_key"],
                             "audio": f"audio/{c['clip_key']}.wav", "category": c["category"],
                             "group": group, "te_s": c["te"], "offset_s": t, "cut_samples": cut,
                             "keep_samples": L, "label": 1, "weight": round(clip_w * w, 9)})
    # overlap assert: a clip feeding both 2a and 2e must keep its cuts > 0.05 s apart
    neg_cuts = {}
    for r in stu:
        neg_cuts.setdefault(r["clip_key"], []).append(r["cut_samples"])
    both = 0
    for key in {r["clip_key"] for r in rows} & set(neg_cuts):
        both += 1
        for p in (r["cut_samples"] for r in rows if r["clip_key"] == key):
            for n in neg_cuts[key]:
                if abs(p - n) <= 0.05 * C.SR:
                    sys.exit(f"REFUSING: {key} has a negative/positive cut pair within 0.05 s")
    q = [0.1, 0.5, 0.9]
    q2a = [x / C.SR for x in wquantiles(lens, lw, q)]
    q2e = [x / C.SR for x in wquantiles([r["keep_samples"] if r["keep_samples"] < r["cut_samples"]
                                         else r["cut_samples"] for r in rows],
                                        [r["weight"] for r in rows], q)]
    # check 1 as amended in training-v2.md (5e0af13, before any v2 run): within 0.1 s at
    # p10 and p50, and 2e must not exceed 2a at any quantile (structural p90 gap is recorded)
    length_ok = (all(abs(a - b) <= 0.1 + 1e-9 for a, b in zip(q2a[:2], q2e[:2]))
                 and all(b <= a + 1e-9 for a, b in zip(q2a, q2e)))
    if not length_ok and not allow_length_mismatch:
        sys.exit(f"REFUSING: length matching off: 2a {q2a} vs 2e {q2e} "
                 "(use --allow-length-mismatch only for scratch diagnostics)")
    info = {"clips_by_group": {g: len({r["clip_key"] for r in rows if r["group"] == g}) for g in by_group},
            "samples": len(rows), "clip_outcomes": counts, "clips_in_both_2a_2e": both,
            "length_s_p10_p50_p90": {"2a": [round(x, 3) for x in q2a], "2e_after_matching": [round(x, 3) for x in q2e]},
            "length_match_ok": length_ok,
            "length_rule": "training-v2 check 1 (amended 5e0af13): |2e-2a| <= 0.1 s at p10 and p50; 2e <= 2a at p10/p50/p90",
            "length_residual_gap_s": [round(b - a, 3) for a, b in zip(q2a, q2e)],
            "weight_by_group": {g: round(sum(r["weight"] for r in rows if r["group"] == g), 6) for g in by_group}}
    return rows, info


def write_jsonl(path, rows):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(json.dumps(r, sort_keys=True) + "\n")
    return C.sha256_file(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--out", help="output dir (default W/data); use a scratch dir for checks")
    ap.add_argument("--stage", choices=["fetch", "build"], default="build")
    ap.add_argument("--replay-cap", type=int, default=6000)
    ap.add_argument("--guard-cap", type=int, default=3000)
    ap.add_argument("--plant-key", help="check 7: add this key to the candidates; must refuse")
    ap.add_argument("--v2", action="store_true", help="training-v2: also build 2e SEP-28k positives")
    ap.add_argument("--allow-length-mismatch", action="store_true",
                    help="scratch diagnostics only: record (not refuse) a 2a/2e length mismatch")
    a = ap.parse_args()

    if a.stage == "fetch":
        g = collect(a.work, GUARD, a.guard_cap, fetch=True)
        r = collect(a.work, REPLAY, a.replay_cap, fetch=True)
        print(f"FETCH DONE: guard shards {len(g)} ({sum(map(len, g))} English), "
              f"replay shards {len(r)} ({sum(map(len, r))} English)")
        return

    out = a.out or os.path.join(a.work, "data-v2" if a.v2 else "data")
    os.makedirs(out, exist_ok=True)
    stu, stu_counts, stu_info = stutter_negatives(None if a.v2 else a.plant_key)
    pos, pos_info = sep_positives(stu, a.plant_key, a.allow_length_mismatch) if a.v2 else (None, None)

    g_shards = collect(a.work, GUARD, a.guard_cap, fetch=False)
    r_shards = collect(a.work, REPLAY, a.replay_cap, fetch=False)
    if not g_shards or not r_shards:
        sys.exit("shard cache empty: run --stage fetch first")
    guard = select(g_shards, a.guard_cap)
    replay_sel = select(r_shards, a.replay_cap)
    guard_hashes = {r["wav_sha256"] for r in guard}
    replay = [r for r in replay_sel if r["wav_sha256"] not in guard_hashes]
    dedupe_dropped = len(replay_sel) - len(replay)
    if not replay or not guard:
        sys.exit("language == 'eng' filter kept 0 rows")

    def label(rows):
        return [dict(r, label=int(r["endpoint_bool"])) for r in rows]

    hashes = {"stutter_neg.jsonl": write_jsonl(os.path.join(out, "stutter_neg.jsonl"), stu),
              "orig_replay.jsonl": write_jsonl(os.path.join(out, "orig_replay.jsonl"), label(replay)),
              "guard.jsonl": write_jsonl(os.path.join(out, "guard.jsonl"), label(guard))}
    if pos is not None:
        hashes["sep_pos.jsonl"] = write_jsonl(os.path.join(out, "sep_pos.jsonl"), pos)

    def tally(rows):
        return {"n": len(rows), "endpoint_true": sum(r["endpoint_bool"] for r in rows),
                "synthetic": sum(bool(r["synthetic"]) for r in rows),
                "midfiller": sum(bool(r["midfiller"]) for r in rows),
                "endfiller": sum(bool(r["endfiller"]) for r in rows)}

    manifest = {
        "spec": "model/specs/training-v1.md", "code_commit": C.git_commit(),
        "train_csv_sha256": C.sha256_file(os.path.join(C.BENCH, "splits", "v1", "train.csv")),
        "items_manifest_sha256": C.sha256_file(os.path.join(C.BENCH, "items", "v1", "manifest.json")),
        "jsonl_sha256": hashes,
        "stutter_neg": {"clips_ok": stu_counts.get("ok", 0), "samples": len(stu),
                        "weight_total": round(sum(r["weight"] for r in stu), 4),
                        "clip_outcomes": stu_counts, **stu_info, "offsets_s": OFFSETS},
        "orig_replay": {**{k: REPLAY[k] for k in ("repo", "revision")}, "shards_read": len(r_shards),
                        "english_rows_per_shard": [len(s) for s in r_shards], "cap": a.replay_cap,
                        "selected_before_dedupe": len(replay_sel), "dedupe_dropped": dedupe_dropped,
                        **tally(replay)},
        "guard": {**{k: GUARD[k] for k in ("repo", "revision")}, "shards_read": len(g_shards),
                  "english_rows_per_shard": [len(s) for s in g_shards], "cap": a.guard_cap, **tally(guard)},
        "language_filter": "eng",
    }
    if pos is not None:
        manifest["spec"] = "model/specs/training-v2.md (delta on training-v1.md)"
        manifest["sep_pos"] = pos_info
    C.write_json(os.path.join(out, "manifest.json"), manifest)
    print(json.dumps({k: manifest[k] for k in ("jsonl_sha256",)}, indent=1))
    print(json.dumps({"stutter_neg": manifest["stutter_neg"], "replay_n": len(replay),
                      "replay_dedupe_dropped": dedupe_dropped, "guard_n": len(guard),
                      "replay_per_shard": manifest["orig_replay"]["english_rows_per_shard"],
                      "guard_per_shard": manifest["guard"]["english_rows_per_shard"]}))
    if pos is not None:
        print(json.dumps({"sep_pos": pos_info}))


if __name__ == "__main__":
    main()
