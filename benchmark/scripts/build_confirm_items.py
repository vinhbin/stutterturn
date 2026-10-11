"""Build runner items from the adjudicated confirmation labels (spec: benchmark/specs/confirm-items-v1.md).

  python benchmark/scripts/build_confirm_items.py                  # writes benchmark/items/confirm-v1; refuses if it exists
  python benchmark/scripts/build_confirm_items.py --out DIR [--ann-dir DIR]   # scratch build
  python benchmark/scripts/build_confirm_items.py --check DIR      # re-verify every hash in DIR/manifest.json
  python benchmark/scripts/build_confirm_items.py --probe-forbidden   # test hook: forbidden reads must abort

Imports apply_annotations, Gate, ANN_HEADER, CATEGORIES, mk_item and prov_row from build_items.py.
Never calls energy_pass, build_queue or main, and never reads test, items/v1, runs, selection or evidence.
The freeze point is the decision-log entry of the adjudicated.csv sha256; no model may run on
confirm.jsonl before it exists.
"""
import argparse, builtins, csv, hashlib, json, os, shutil, sys, tempfile
from collections import Counter, defaultdict

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
    if rel[:3] == ["benchmark", "items", "v1"]:
        sys.exit("REFUSING: path is on the forbidden list: " + str(p))


def _guarded_open(file, *a, **k):
    _check_path(file)
    return _real_open(file, *a, **k)


builtins.open = _guarded_open

sys.path.insert(0, HERE)
import build_items as bi  # noqa: E402  (imported after the guard is installed)

CONFIRM_DIR = os.path.join(BASE, "confirm", "v1")
DEFAULT_ANN = os.path.join(BASE, "annotations", "confirm-v1")
DEFAULT_OUT = os.path.join(BASE, "items", "confirm-v1")
SPLIT = "confirm"
TARGET = 20
D009 = ("D-009: the confirmation items are built from human labels only, with no energy pass and no test "
        "read; no model runs on confirm.jsonl until the adjudicated.csv sha256 is in the decision log")
OUT_FILES = ["confirm.jsonl", "provenance.jsonl", "outcomes.csv"]


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def disp(p):
    ap = os.path.abspath(p)
    r = os.path.relpath(ap, REPO)
    return ap if r.startswith("..") else r


def fail(msg):
    sys.exit("REFUSING: " + msg)


def read_dict_csv(p):
    with open(p, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def classify(outcome):
    if outcome.startswith("human_unfinished") or outcome.startswith("human_completed"):
        return "accepted"
    if outcome.startswith("human_rejected"):
        return "human_rejected"
    return outcome


def load_inputs(ann_dir):
    """Validate everything; returns a context dict. Writes nothing."""
    ws_path = os.path.join(CONFIRM_DIR, "worksheet.csv")
    man_path = os.path.join(CONFIRM_DIR, "manifest.json")
    ws_sha = sha256_file(ws_path)
    with open(man_path, encoding="utf-8") as f:
        cman = json.load(f)
    if ws_sha != cman["worksheet_sha256"]:
        fail(f"worksheet.csv sha256 {ws_sha} != manifest.json {cman['worksheet_sha256']}")
    ws = read_dict_csv(ws_path)
    ws_by_sid = {r["sample_id"]: r for r in ws}
    buckets = defaultdict(list)  # category -> [sample_id] in worksheet order
    for r in ws:
        buckets[r["category"]].append(r["sample_id"])
    pos = {sid: i for b in buckets.values() for i, sid in enumerate(b)}

    if not os.path.isdir(ann_dir):
        fail(f"annotations dir {disp(ann_dir)} does not exist")
    csvs = sorted(fn for fn in os.listdir(ann_dir) if fn.endswith(".csv"))
    if csvs != ["adjudicated.csv"]:
        fail(f"annotations dir must hold exactly one CSV named adjudicated.csv, found {csvs}")
    note_path = os.path.join(ann_dir, "crosscheck-note.md")
    if not os.path.isfile(note_path):
        fail("crosscheck-note.md is missing from the annotations dir")
    adj_path = os.path.join(ann_dir, "adjudicated.csv")

    rows = []
    with open(adj_path, newline="", encoding="utf-8") as f:
        rd = csv.reader(f)
        hdr = [h.strip() for h in next(rd, [])]
        if hdr != bi.ANN_HEADER:
            fail(f"adjudicated.csv header mismatch: {hdr}")
        for raw in rd:
            if not raw or not any(x.strip() for x in raw):
                continue
            rows.append(dict(zip(hdr, [x.strip() for x in raw])))

    # 1. worksheet join (exact)
    for d in rows:
        w = ws_by_sid.get(d["sample_id"])
        if w is None or w["source_id"] != d["source_id"]:
            fail(f"annotation row ({d['sample_id']}, {d['source_id']}) is not a worksheet row")

    # 2. no skipping: annotated ids are a contiguous prefix of each bucket
    annotated = {d["sample_id"] for d in rows}
    for cat, sids in buckets.items():
        idx = sorted(pos[s] for s in sids if s in annotated)
        if idx:
            missing = sids[: idx[-1] + 1]
            missing = [s for s in missing if s not in annotated]
            if missing:
                fail(f"bucket {cat}: gap in annotated prefix, missing {missing}")

    # 3. category-mismatch filter (before apply_annotations)
    kept, mismatch = [], []
    for d in rows:
        if bi.parse_bool(d["accepted"]) is True and d["category"] != ws_by_sid[d["sample_id"]]["category"]:
            mismatch.append(d)
        else:
            kept.append(d)
    return {"ws": ws, "ws_by_sid": ws_by_sid, "buckets": buckets, "ws_sha": ws_sha, "cman": cman,
            "man_path": man_path, "adj_path": adj_path, "note_path": note_path, "rows": rows,
            "kept": kept, "mismatch": mismatch}


def build(ctx, tmp):
    """Stage, apply labels, validate. Returns dict of results; writes only under tmp."""
    cman = ctx["cman"]
    dev_path = os.path.join(BASE, "splits", "v1", "dev.csv")
    dev_sha = sha256_file(dev_path)
    if dev_sha != cman["splits_dev_sha256"]:
        fail(f"splits/v1/dev.csv sha256 {dev_sha} != confirm manifest {cman['splits_dev_sha256']}")
    keys = {r["source_id"] for r in ctx["ws"]}
    dev = {}
    for r in read_dict_csv(dev_path):
        if r["clip_key"] in keys:
            dev[r["clip_key"]] = r
    absent = sorted(keys - set(dev))
    if absent:
        fail(f"worksheet keys not in dev.csv: {absent[:5]}")
    rowmap = {k: (SPLIT, r) for k, r in dev.items()}

    stage = os.path.join(tmp, "stage")
    os.makedirs(stage)
    staged = os.path.join(stage, "adjudicated.csv")
    with open(staged, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(bi.ANN_HEADER)
        for d in ctx["kept"]:
            w.writerow([d[h] for h in bi.ANN_HEADER])

    ep = os.path.join(bi.AUDIO, "empty_on_mirror.txt")
    empty = set()
    if os.path.exists(ep):
        with open(ep) as f:
            empty = {l.strip() for l in f if l.strip()}
    gate = bi.Gate(empty)
    state = {SPLIT: {"main": {}, "eow": {}, "prov": {}, "fts": {}}}
    T = defaultdict(Counter)
    ann_files, annotated_keys = {}, set()
    out = bi.apply_annotations(stage, rowmap, state, gate, None, T, ann_files, annotated_keys)

    outcomes = {}  # sample_id -> list of outcome strings
    for _fn, sid, oc in out:
        outcomes.setdefault(sid, []).append(oc)
    for d in ctx["mismatch"]:
        outcomes.setdefault(d["sample_id"], []).append("category_mismatch")
    outrows = []
    for sid in sorted(outcomes):
        w = ctx["ws_by_sid"][sid]
        for oc in outcomes[sid]:
            outrows.append({"sample_id": sid, "source_id": w["source_id"], "category": w["category"],
                            "outcome": oc})

    quota = {}
    for cat in sorted(ctx["buckets"]):
        c = Counter()
        n_rev = 0
        for sid in ctx["buckets"][cat]:
            for oc in outcomes.get(sid, []):
                n_rev += 1
                c[classify(oc)] += 1
        acc = c.pop("accepted", 0)
        quota[cat] = {"accepted": acc, "rows_reviewed": n_rev, "target": TARGET,
                      "shortfall": max(0, TARGET - acc), "rejections": dict(sorted(c.items()))}

    items = [state[SPLIT]["main"][k] for k in sorted(state[SPLIT]["main"])]
    prov = [state[SPLIT]["prov"][k] for k in sorted(state[SPLIT]["prov"], key=lambda t: t[1])]
    # self-validate with the runner's loader (needs the file on disk)
    chk = os.path.join(tmp, "confirm.jsonl")
    with open(chk, "w") as f:
        for it in items:
            f.write(json.dumps(it) + "\n")
    import eval_runner as er  # noqa: E402
    if items:
        er.load_items(chk)
    else:
        print("WARNING: no accepted items", file=sys.stderr)
    return {"items": items, "prov": prov, "outrows": outrows, "quota": quota, "staged": staged,
            "staged_sha": sha256_file(staged), "dev_sha": dev_sha, "T": T}


def write_outputs(out, ctx, res):
    os.makedirs(out)  # refuses (raises) if it appeared meanwhile
    with open(os.path.join(out, "confirm.jsonl"), "w") as f:
        for it in res["items"]:
            f.write(json.dumps(it) + "\n")
    with open(os.path.join(out, "provenance.jsonl"), "w") as f:
        for p in res["prov"]:
            f.write(json.dumps(p) + "\n")
    with open(os.path.join(out, "outcomes.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["sample_id", "source_id", "category", "outcome"], lineterminator="\n")
        w.writeheader()
        w.writerows(res["outrows"])
    cnt = Counter(f"{it['group']}|{it['kind']}|{it['label_source']}" for it in res["items"])
    manifest = {
        "script_sha256": sha256_file(os.path.abspath(__file__)),
        "build_items_sha256": sha256_file(os.path.join(HERE, "build_items.py")),
        "worksheet_sha256": ctx["ws_sha"],
        "confirm_manifest_sha256": sha256_file(ctx["man_path"]),
        "splits_dev_sha256": res["dev_sha"],
        "adjudicated_path": disp(ctx["adj_path"]),
        "adjudicated_sha256": sha256_file(ctx["adj_path"]),
        "crosscheck_note_path": disp(ctx["note_path"]),
        "crosscheck_note_sha256": sha256_file(ctx["note_path"]),
        "ann_files": {"adjudicated.csv(staged)": res["staged_sha"]},
        "category_mismatch_dropped": len(ctx["mismatch"]),
        "counts": {"items": len(res["items"]), "by_group_kind_label_source": dict(sorted(cnt.items()))},
        "quota_report": res["quota"],
        "output_sha256": {fn: sha256_file(os.path.join(out, fn)) for fn in OUT_FILES},
        "blind": True, "test_read": False, "items_v1_read": False,
        "d009_note": D009,
    }
    with open(os.path.join(out, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=1, sort_keys=True)
        f.write("\n")
    return manifest


def print_quota(q):
    print("QUOTA REPORT (accepted / target; rows reviewed; rejections)")
    for cat, v in q.items():
        flag = "  SHORTFALL %d" % v["shortfall"] if v["shortfall"] else ""
        print(f"  {cat}: {v['accepted']}/{v['target']}; reviewed {v['rows_reviewed']}; {v['rejections']}{flag}")


def do_check(d):
    mp = os.path.join(d, "manifest.json")
    if not os.path.isfile(mp):
        print("FAIL: no manifest.json in " + d)
        return 1
    with open(mp) as f:
        m = json.load(f)
    bad = []

    def eq(name, path, want):
        got = sha256_file(path) if os.path.isfile(path) else "MISSING"
        if got != want:
            bad.append(f"{name}: {got} != {want}")

    eq("script", os.path.abspath(__file__), m["script_sha256"])
    eq("build_items.py", os.path.join(HERE, "build_items.py"), m["build_items_sha256"])
    eq("worksheet.csv", os.path.join(CONFIRM_DIR, "worksheet.csv"), m["worksheet_sha256"])
    eq("confirm manifest", os.path.join(CONFIRM_DIR, "manifest.json"), m["confirm_manifest_sha256"])
    eq("splits dev.csv", os.path.join(BASE, "splits", "v1", "dev.csv"), m["splits_dev_sha256"])
    eq("adjudicated.csv", os.path.join(REPO, m["adjudicated_path"]), m["adjudicated_sha256"])
    eq("crosscheck-note.md", os.path.join(REPO, m["crosscheck_note_path"]), m["crosscheck_note_sha256"])
    for fn, h in m["output_sha256"].items():
        eq(fn, os.path.join(d, fn), h)
    if bad:
        print("CHECK FAILED:\n  " + "\n  ".join(bad))
        return 1
    print("CHECK OK: all hashes in " + d + " verified")
    return 0


def probe_forbidden():
    ok = True
    for rel in [("benchmark", "items", "v1", "test.jsonl"), ("benchmark", "runs", "x")]:
        p = os.path.join(REPO, *rel)
        try:
            open(p)
            print("PROBE FAIL: open succeeded: " + p)
            ok = False
        except SystemExit as e:
            print(f"PROBE OK: aborted {p}: {e}")
        except Exception as e:  # file-not-found etc. would mean the guard did not fire
            print(f"PROBE FAIL: guard did not fire for {p}: {e!r}")
            ok = False
    return 0 if ok else 1


def main():
    global CONFIRM_DIR
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--ann-dir", default=DEFAULT_ANN, help="scratch override of benchmark/annotations/confirm-v1")
    ap.add_argument("--confirm-dir", default=CONFIRM_DIR, help="scratch override of benchmark/confirm/v1 (tests)")
    ap.add_argument("--check", metavar="DIR")
    ap.add_argument("--probe-forbidden", action="store_true")
    a = ap.parse_args()
    CONFIRM_DIR = os.path.abspath(a.confirm_dir)
    if a.probe_forbidden:
        sys.exit(probe_forbidden())
    if a.check:
        sys.exit(do_check(os.path.abspath(a.check)))
    out = os.path.abspath(a.out)
    if os.path.exists(out):
        fail(f"{out} already exists (confirmation items are immutable)")
    ctx = load_inputs(os.path.abspath(a.ann_dir))
    with tempfile.TemporaryDirectory(prefix="confirm-items-") as tmp:
        res = build(ctx, tmp)
        manifest = write_outputs(out, ctx, res)
    print_quota(res["quota"])
    print(f"items: {len(res['items'])}; category_mismatch dropped: {len(ctx['mismatch'])}")
    print(f"RECORD IN DECISION LOG: adjudicated.csv sha256 = {manifest['adjudicated_sha256']}, "
          f"confirm.jsonl sha256 = {manifest['output_sha256']['confirm.jsonl']}")


if __name__ == "__main__":
    main()
