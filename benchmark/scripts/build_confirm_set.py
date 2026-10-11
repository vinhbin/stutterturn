"""Build the confirmation review worksheet v1 (spec: benchmark/specs/confirm-set-v1.md).

  python benchmark/scripts/build_confirm_set.py                  # writes benchmark/confirm/v1; refuses if it exists
  python benchmark/scripts/build_confirm_set.py --out DIR        # scratch build
  python benchmark/scripts/build_confirm_set.py --out DIR --plant KEY   # hook: a planted exposed key must abort

Draws from dev recordings that no v1-v4 step touched. Inputs: SEP-28k category and
natural_pause vote (dev split) plus a sha256 hash order. No energy, VAD or model features
select or order clips. No model is run here beyond the E3 recomputation, which reuses
model/train/proxies.py exactly as the in-loop selection did.
"""
import argparse, builtins, csv, hashlib, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
REPO = os.path.dirname(BASE)

# ---- guarded file access: forbidden paths are refused for every open() in this process ----
_FORBIDDEN_DIRS = ("ru" + "ns", "sel" + "ection", "evi" + "dence")
_FORBIDDEN_PREFIX = "te" + "st"
_real_open = builtins.open


def _check_path(p):
    if isinstance(p, int):
        return
    ap = os.path.abspath(os.fspath(p))
    rel = os.path.relpath(ap, REPO).split(os.sep)
    if rel[0] == "..":
        return  # outside the repo (scratch dirs, venv, system)
    if any(x in _FORBIDDEN_DIRS for x in rel[:-1]) or rel[-1].startswith(_FORBIDDEN_PREFIX):
        sys.exit("REFUSING: path is on the forbidden list: " + str(p))
    if rel[:2] == ["benchmark", "items"] and any(x.startswith(_FORBIDDEN_PREFIX) for x in rel[2:]):
        sys.exit("REFUSING: path is on the forbidden list: " + str(p))


def _guarded_open(file, *a, **k):
    _check_path(file)
    return _real_open(file, *a, **k)


builtins.open = _guarded_open
ITEMS_ALLOWED = ("dev.jsonl", "dev_end_of_window.jsonl")


def open_items(name):
    if name not in ITEMS_ALLOWED:
        sys.exit("REFUSING: only " + ", ".join(ITEMS_ALLOWED) + " may be opened from items/")
    return open(os.path.join(BASE, "items", "v1", name), encoding="utf-8")


sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, "model", "train"))
import build_items as bi  # noqa: E402
import proxies as px  # noqa: E402

SPLITS_DIR = os.path.join(BASE, "splits", "v1")
DEFAULT_OUT = os.path.join(BASE, "confirm", "v1")
BUCKETS = [("unfinished_stutter_block", "block"), ("completed_stuttered_turn", "other_disfluent"),
           ("unfinished_fluent_pause", "fluent"), ("completed_fluent_turn", "fluent")]
PREVIEW = {"exposed": 2831, "unexposed": 3051, "overlap": 644, "pool": 2407}
RULE = ("no model is run on these keys until the reviewed labels are committed and their sha256 "
        "is recorded in the decision log")


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def sha256_str(s):
    return hashlib.sha256(s.encode()).hexdigest()


def hkey(s):
    return sha256_str("confirm-v1|" + s)


def jsonl_keys(name):
    with open_items(name) as f:
        return {json.loads(l)["clip_key"] for l in f if l.strip()}


def interleave_det(groups):
    total = sum(len(v) for v in groups.values())
    shows = sorted(groups)
    taken = {s: 0 for s in shows}
    out = []
    for i in range(1, total + 1):
        cand = [s for s in shows if taken[s] < len(groups[s])]
        best = min(cand, key=lambda s: (-(len(groups[s]) * i / total - taken[s]), s))
        out.append(groups[best][taken[best]])
        taken[best] += 1
    return out


def ref_for(r, urls):
    url = urls.get((r["show"], r["ep_id"]), "")
    return f"{url}#t={format(int(r['start']) / 16000, '.3f').rstrip('0').rstrip('.')}"


def overlaps(a, b):
    return a[0] < b[1] and b[0] < a[1]


README = """# Confirmation review set v1 - labelling protocol

Spec: `benchmark/specs/confirm-set-v1.md`. This directory holds a **worksheet only**
(`worksheet.csv`, exact PLAN header, every human field blank). It contains no model
outputs, energy times or proxy labels. Categories are *proposed*; humans decide.

Rule: no model is run on these keys until the reviewed labels are committed and their
sha256 is recorded in the decision log. Never used for training or for selecting among
candidates; used only to judge an already-selected candidate against stock FP32 @0.5, the
comparator @0.55 and patient.

## Blind
No model predictions are shown or available. Nobody runs a model on `benchmark/confirm/v1`
keys until labels are frozen.

## Working down the lists
Each category's rows are a ranked list (sample_id order = bucket order, then rank). Work
down each list in order and never skip ahead. Stop at 20 accepted per category, or at the
end of the time you have, and report the shortfall; it is not refilled. Yields are expected
to be low (near zero for `unfinished_fluent_pause`): every clip here was rejected by the
earlier energy pass. Record rejections as `accepted=false` with reviewer and reason, as in
the PLAN worksheet rules (see `docs/labeling/README.md`).

## Reviewers
Two people. The second cross-checks every row the first marks `uncertainty`, plus a random
10% chosen by `sha256("confirm-v1-xcheck|" + sample_id)`. Record reviewer identities, the
sampled rows and any disagreements.

## One adjudicated CSV (the freeze point)
The reviewed file is a single adjudicated CSV with the exact PLAN header:
`benchmark/annotations/confirm-v1/adjudicated.csv`. Cross-check identities, sampled rows
and disagreements go in a separate `crosscheck-note.md` (following the `docs/labeling`
convention); two reviewer CSVs in one directory would break the builder. Its sha256 then
goes in the decision log. That is the freeze point.

## Timing rules (the builder enforces them; confirm keys have no energy item to fall back on)
- All times are clip-relative, within 0-3.0 s (`time_origin=clip_start`).
- Unfinished rows need `block_onset_s` (or the pause onset) and `resumption_s`, with
  `resumption_s - block_onset_s > 0.2`.
- Completed rows need `turn_end_s <= clip length - 0.2 s`.
- Rows that cannot meet these are `accepted=false` with the reason.
- An accepted row with nonempty `uncertainty` is rejected by the builder.

## Out of scope for v1
Turning labels into items. A follow-up spec adds a `--confirm-only` mode to `build_items.py`
(dev rows restricted to the worksheet keys, no held-out pass, output only
`benchmark/items/confirm-v1/`). Until it exists and is reviewed, that step is NOT RUN.

## Limits (state wherever results from this set are reported)
- Same two dev shows as the exposed items, so possibly the same speakers. These are
  untouched *recordings*, not new speakers or a held-out show.
- The pool is skewed in every bucket: every clean clip is one the energy rules rejected, so
  its distribution differs from the exposed items. Low yields are expected and reported.
- 3-second windows: events must fall inside the clip to be scoreable. Context links allow
  judging the speaker and the turn.
- Small n (up to 20 accepted per category): feasibility evidence with Wilson CIs, not
  population rates.
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--plant", default=None, help="scratch hook: inject KEY into the worksheet before the disjointness assertion")
    a = ap.parse_args()
    out = os.path.abspath(a.out)
    if os.path.exists(out):
        sys.exit(f"REFUSING: {out} exists")

    # dev split sha pin (dev only; the other split files are never opened)
    dev_path = os.path.join(SPLITS_DIR, "dev.csv")
    dev_sha = sha256_file(dev_path)
    if not (dev_sha.startswith(bi.DEV_PINNED[0]) and dev_sha.endswith(bi.DEV_PINNED[1])):
        sys.exit(f"REFUSING: dev.csv sha256 {dev_sha} does not match spec")
    with open(dev_path, newline="", encoding="utf-8") as f:
        dev_rows = list(csv.DictReader(f))
    rowmap = {r["clip_key"]: r for r in dev_rows}
    assert len(rowmap) == len(dev_rows)
    iv = {k: (int(r["start"]), int(r["stop"])) for k, r in rowmap.items()}

    # E3: needs dev audio for block / other_disfluent
    need = [r["clip_key"] for r in dev_rows if r["category"] in ("block", "other_disfluent")]
    miss = [k for k in need if not os.path.isfile(os.path.join(bi.AUDIO, k + ".wav"))]
    if miss:
        sys.exit(f"STOP: {len(miss)} dev block/other_disfluent clips missing under benchmark/audio/ "
                 "(run fetch_split_audio.py --splits dev --categories block other_disfluent); e.g. " + ", ".join(miss[:3]))
    proxies, _ = px.completed_proxies(px.split_rows("dev"))
    e3 = sorted({p["clip_key"] for p in proxies if p["group"] == "stuttered"})
    assert len(e3) == 538, f"E3 recomputed {len(e3)} != 538"

    e1, e2 = jsonl_keys("dev.jsonl"), jsonl_keys("dev_end_of_window.jsonl")
    be_path = os.path.join(BASE, "data", "block_eval.csv")
    bc_path = os.path.join(BASE, "data", "block_candidates.csv")
    with open(be_path, newline="") as f:
        e4_all = {r["file"][:-4] if r["file"].endswith(".wav") else r["file"] for r in csv.DictReader(f)}
    e4 = {k for k in e4_all if k in rowmap}
    with open(bc_path, newline="") as f:
        e5_all = {f"{r['Show']}_{r['EpId']}_{r['ClipId']}" for r in csv.DictReader(f)}
    e5 = {k for k in e5_all if k in rowmap}
    for nm, s in [("E1", e1), ("E2", e2), ("E3", set(e3))]:
        assert s <= set(rowmap), f"{nm} has non-dev keys"

    exposed = e1 | e2 | set(e3) | e4
    unexposed = [k for k in rowmap if k not in exposed]
    by_ep = {}
    for k in exposed:
        by_ep.setdefault((rowmap[k]["show"], rowmap[k]["ep_id"]), []).append(iv[k])
    overlap_ex = sorted(k for k in unexposed
                        if any(overlaps(iv[k], b) for b in by_ep.get((rowmap[k]["show"], rowmap[k]["ep_id"]), [])))
    ov = set(overlap_ex)
    pool_pre = [k for k in unexposed if k not in ov]
    e5_removed = sorted(k for k in pool_pre if k in e5)
    pool = [k for k in pool_pre if k not in e5]
    cnt = {"dev_clips": len(rowmap), "exposed_E1_E4": len(exposed), "unexposed": len(unexposed),
           "overlap_excluded": len(overlap_ex), "pool_pre_E5": len(pool_pre),
           "E5_removed": len(e5_removed), "pool": len(pool),
           "E1": len(e1), "E2": len(e2), "E3": len(e3), "E4_dev": len(e4), "E5_dev": len(e5)}
    cnt["pool_pre_E5_by_category"] = {c: sum(1 for k in pool_pre if rowmap[k]["category"] == c) for c in ("block", "fluent", "other_disfluent")}
    cnt["E5_removed_by_category"] = {c: sum(1 for k in e5_removed if rowmap[k]["category"] == c) for c in ("block", "fluent", "other_disfluent")}
    cnt["pool_by_category"] = {c: sum(1 for k in pool if rowmap[k]["category"] == c) for c in ("block", "fluent", "other_disfluent")}
    cnt["pool_other_categories"] = sum(1 for k in pool if rowmap[k]["category"] not in cnt["pool_by_category"])
    cnt["pool_by_category_show"] = {}
    for k in pool:
        cnt["pool_by_category_show"].setdefault(rowmap[k]["category"], {}).setdefault(rowmap[k]["show"], 0)
        cnt["pool_by_category_show"][rowmap[k]["category"]][rowmap[k]["show"]] += 1

    # buckets
    fluent = sorted(k for k in pool if rowmap[k]["category"] == "fluent")
    to_pause = [k for k in fluent if int(sha256_str("confirm-v1-split|" + k), 16) % 2 == 0]
    to_comp = [k for k in fluent if int(sha256_str("confirm-v1-split|" + k), 16) % 2 == 1]
    cnt["fluent_split"] = {"unfinished_fluent_pause": len(to_pause), "completed_fluent_turn": len(to_comp)}

    def ordered(keys, tiered):
        def groups(ks):
            g = {}
            for k in sorted(ks, key=hkey):
                g.setdefault(rowmap[k]["show"], []).append(k)
            return g
        if not tiered:
            return interleave_det(groups(keys))
        hi = [k for k in keys if int(rowmap[k]["natural_pause"]) >= 1]
        lo = [k for k in keys if int(rowmap[k]["natural_pause"]) < 1]
        return interleave_det(groups(hi)) + interleave_det(groups(lo))

    lists = {
        "unfinished_stutter_block": ordered([k for k in pool if rowmap[k]["category"] == "block"], False),
        "completed_stuttered_turn": ordered([k for k in pool if rowmap[k]["category"] == "other_disfluent"], False),
        "unfinished_fluent_pause": ordered(to_pause, True),
        "completed_fluent_turn": ordered(to_comp, False),
    }
    cnt["natural_pause_ge1"] = {
        "fluent_pool": sum(1 for k in fluent if int(rowmap[k]["natural_pause"]) >= 1),
        "unfinished_fluent_pause_list": sum(1 for k in to_pause if int(rowmap[k]["natural_pause"]) >= 1),
        "completed_fluent_turn_list": sum(1 for k in to_comp if int(rowmap[k]["natural_pause"]) >= 1)}
    if a.plant:
        lists["unfinished_stutter_block"].insert(0, a.plant)
    cnt["bucket_sizes"] = {b: len(v) for b, v in lists.items()}

    # assertions before writing
    ws_keys = [k for b, _ in BUCKETS for k in lists[b]]
    assert len(ws_keys) == len(set(ws_keys)), "duplicate worksheet key"
    bad = sorted(set(ws_keys) & exposed)
    if bad:
        sys.exit(f"ABORT: worksheet keys in exposure set E1-E4: {bad[:5]}")
    bad = sorted(set(ws_keys) & set(e5))
    if bad:
        sys.exit(f"ABORT: worksheet keys in E5: {bad[:5]}")
    for k in ws_keys:
        if k not in iv:
            sys.exit(f"ABORT: worksheet key not a dev clip: {k}")
        for b in by_ep.get((rowmap[k]["show"], rowmap[k]["ep_id"]), []):
            if overlaps(iv[k], b):
                sys.exit(f"ABORT: worksheet key {k} time-overlaps an exposed clip")

    for k, v in cnt.items():
        print(f"{k}: {v}")
    pv = {"exposed": len(exposed), "unexposed": len(unexposed), "overlap": len(overlap_ex), "pool": len(pool_pre)}
    print("preview match (pre-E5):", pv == PREVIEW, pv)

    urls = bi.load_episode_urls()
    rows, n = [], 0
    for b, _ in BUCKETS:
        for k in lists[b]:
            n += 1
            rows.append({"sample_id": f"C{n:04d}", "source_id": k, "context_ref": ref_for(rowmap[k], urls),
                         "speaker_id": "", "category": b, "time_origin": "clip_start", "block_onset_s": "",
                         "resumption_s": "", "turn_end_s": "", "reviewer": "", "reviewed_at": "",
                         "uncertainty": "", "accepted": ""})

    os.makedirs(out)
    ws = os.path.join(out, "worksheet.csv")
    bi.write_csv(ws, bi.ANN_HEADER, rows)
    with open(os.path.join(out, "README.md"), "w", newline="\n") as f:
        f.write(README)
    with open(os.path.join(out, "exposure_keys.json"), "w") as f:
        json.dump({"exposed_E1_E4": sorted(exposed), "overlap_excluded": overlap_ex,
                   "E5_excluded": e5_removed}, f, indent=1, sort_keys=True)
        f.write("\n")
    rev = subprocess.run(["git", "-C", REPO, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    manifest = {
        "frozen": True, "rule": RULE, "git_head": rev,
        "script_sha256": sha256_file(os.path.abspath(__file__)),
        "splits_dev_sha256": dev_sha,
        "input_sha256": {
            "items/v1/dev.jsonl": sha256_file(os.path.join(BASE, "items", "v1", "dev.jsonl")),
            "items/v1/dev_end_of_window.jsonl": sha256_file(os.path.join(BASE, "items", "v1", "dev_end_of_window.jsonl")),
            "data/block_eval.csv": sha256_file(be_path),
            "data/block_candidates.csv": sha256_file(bc_path),
            "items/v1/review_queue_dev.csv": sha256_file(os.path.join(BASE, "items", "v1", "review_queue_dev.csv")),
            "E3_sorted_keys": sha256_str(json.dumps(e3))},
        "counts": cnt, "preview_expected_pre_E5": PREVIEW,
        "worksheet_sha256": sha256_file(ws),
        "exposure_keys_sha256": sha256_file(os.path.join(out, "exposure_keys.json")),
        "readme_sha256": sha256_file(os.path.join(out, "README.md")),
    }
    with open(os.path.join(out, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=1, sort_keys=True)
        f.write("\n")
    print("wrote", out, "worksheet sha256", manifest["worksheet_sha256"])


if __name__ == "__main__":
    main()
