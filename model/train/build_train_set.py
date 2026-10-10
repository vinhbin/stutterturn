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
    a = ap.parse_args()

    if a.stage == "fetch":
        g = collect(a.work, GUARD, a.guard_cap, fetch=True)
        r = collect(a.work, REPLAY, a.replay_cap, fetch=True)
        print(f"FETCH DONE: guard shards {len(g)} ({sum(map(len, g))} English), "
              f"replay shards {len(r)} ({sum(map(len, r))} English)")
        return

    out = a.out or os.path.join(a.work, "data")
    os.makedirs(out, exist_ok=True)
    stu, stu_counts, stu_info = stutter_negatives(a.plant_key)

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
    C.write_json(os.path.join(out, "manifest.json"), manifest)
    print(json.dumps({k: manifest[k] for k in ("jsonl_sha256",)}, indent=1))
    print(json.dumps({"stutter_neg": manifest["stutter_neg"], "replay_n": len(replay),
                      "replay_dedupe_dropped": dedupe_dropped, "guard_n": len(guard),
                      "replay_per_shard": manifest["orig_replay"]["english_rows_per_shard"],
                      "guard_per_shard": manifest["guard"]["english_rows_per_shard"]}))


if __name__ == "__main__":
    main()
