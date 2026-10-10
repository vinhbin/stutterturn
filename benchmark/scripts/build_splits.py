"""Build show-separated train/dev/test split manifests (v1) from SEP-28k labels.

Spec: benchmark/specs/splits-v1.md. Labels only; no audio dependency. Stdlib only.

  python benchmark/scripts/build_splits.py            # build v1; refuse if benchmark/splits/v1/ exists
  python benchmark/scripts/build_splits.py --check    # verify; exit 1 on any mismatch
  python benchmark/scripts/build_splits.py --out DIR  # build into DIR instead (for tests)
"""
import argparse
import csv
import datetime
import hashlib
import io
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent  # benchmark/
LABELS = BASE / "data" / "SEP-28k_labels.csv"
DEFAULT_OUT = BASE / "splits" / "v1"

SHOW_SPLIT = {
    "WomenWhoStutter": "train",
    "HeStutters": "train",
    "IStutterSoWhat": "train",
    "HVSA": "train",
    "StutteringIsCool": "dev",
    "MyStutteringLife": "dev",
    "StrongVoices": "test",
    "StutterTalk": "test",
}
SPLITS = ["train", "dev", "test"]
CATEGORIES = ["block", "fluent", "other_disfluent"]

EXPECTED_HEADER = ["Show", "EpId", "ClipId", "Start", "Stop", "Unsure", "PoorAudioQuality",
                   "Prolongation", "Block", "SoundRep", "WordRep", "DifficultToUnderstand",
                   "Interjection", "NoStutteredWords", "NaturalPause", "Music", "NoSpeech"]
QUALITY_BAD = ["Unsure", "PoorAudioQuality", "DifficultToUnderstand", "Music", "NoSpeech"]
DISFLUENCY = ["Prolongation", "Block", "SoundRep", "WordRep", "Interjection"]
RULES = {"quality_gate_votes": 2, "block_votes": 2, "fluent_votes": 2}

OUT_COLS = ["clip_key", "show", "ep_id", "clip_id", "start", "stop", "category", "block",
            "prolongation", "sound_rep", "word_rep", "interjection", "no_stuttered_words",
            "natural_pause"]

LIMITS = [
    "speaker identity unknown; separation by show only",
    "HeStutters and WomenWhoStutter share a host (same audio host domain and series title); kept together in train",
    "weak cross-show guest first-name matches only (geoff: HeStutters/StrongVoices; alex: StrongVoices/WomenWhoStutter); not verified",
    "gender skew: WomenWhoStutter mostly female, HeStutters mostly male, both in train",
    "two shows per dev/test split: show clustering reduces effective sample size",
    "at least 26 mirror clips are empty, consistent with truncated episode audio (e.g. HeStutters_0 after ~700 s, HeStutters_1 after ~1772 s); filtered when eval items are built, not here",
    "3 s clips: blocks longer than ~2.5 s cannot appear",
    "labels are SEP-28k annotator votes, not human-validated turn ends",
    "audio not included; rights remain with podcast owners",
]


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha256_file(p):
    return sha256_bytes(Path(p).read_bytes())


def read_labels():
    with open(LABELS, newline="", encoding="utf-8") as f:
        r = csv.reader(f)
        header = [h.strip() for h in next(r)]
        if header != EXPECTED_HEADER:
            sys.exit(f"ERROR: labels header mismatch: {header}")
        rows = []
        for raw in r:
            if not raw:
                continue
            fields = [x.strip() for x in raw]
            if len(fields) != len(header):
                sys.exit(f"ERROR: bad row width {len(fields)}: {raw}")
            d = dict(zip(header, fields))
            for k in header:
                if k != "Show":
                    d[k] = int(d[k])
            rows.append(d)
    return rows


def categorize(d):
    if d["Block"] >= RULES["block_votes"]:
        return "block"
    if d["NoStutteredWords"] >= RULES["fluent_votes"] and all(
            d[c] < RULES["fluent_votes"] for c in DISFLUENCY):
        return "fluent"
    return "other_disfluent"


def build_tables(rows):
    shows = {d["Show"] for d in rows}
    unassigned = shows - set(SHOW_SPLIT)
    missing = set(SHOW_SPLIT) - shows
    if unassigned or missing:
        sys.exit(f"ERROR: show assignment mismatch: unassigned={sorted(unassigned)} missing={sorted(missing)}")

    by_reason = Counter()
    excluded = 0
    kept = {s: [] for s in SPLITS}
    for d in rows:
        reasons = [c for c in QUALITY_BAD if d[c] >= RULES["quality_gate_votes"]]
        if reasons:
            excluded += 1
            by_reason.update(reasons)
            continue
        key = f"{d['Show']}_{d['EpId']}_{d['ClipId']}"
        kept[SHOW_SPLIT[d["Show"]]].append({
            "clip_key": key, "show": d["Show"], "ep_id": d["EpId"], "clip_id": d["ClipId"],
            "start": d["Start"], "stop": d["Stop"], "category": categorize(d),
            "block": d["Block"], "prolongation": d["Prolongation"], "sound_rep": d["SoundRep"],
            "word_rep": d["WordRep"], "interjection": d["Interjection"],
            "no_stuttered_words": d["NoStutteredWords"], "natural_pause": d["NaturalPause"],
        })
    for s in SPLITS:
        kept[s].sort(key=lambda r: (r["show"], r["ep_id"], r["clip_id"]))

    # Disjointness / uniqueness assertions
    all_keys = [r["clip_key"] for s in SPLITS for r in kept[s]]
    assert len(all_keys) == len(set(all_keys)), "duplicate clip_key"
    show_sets = {s: {r["show"] for r in kept[s]} for s in SPLITS}
    for i, a in enumerate(SPLITS):
        for b in SPLITS[i + 1:]:
            assert not (show_sets[a] & show_sets[b]), f"show in both {a} and {b}"
            assert not ({r["clip_key"] for r in kept[a]} & {r["clip_key"] for r in kept[b]}), \
                f"clip_key in both {a} and {b}"
    # Conservation
    assert len(rows) == excluded + len(all_keys), "conservation failed"

    excl = {"quality_total": excluded,
            "quality_by_reason": {c: by_reason.get(c, 0) for c in QUALITY_BAD}}
    return kept, excl


def csv_bytes(recs):
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(OUT_COLS)
    for r in recs:
        w.writerow([r[c] for c in OUT_COLS])
    return buf.getvalue().encode("utf-8")


def git_head():
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=BASE, capture_output=True,
                             text=True, check=True)
        return out.stdout.strip() or None
    except Exception:
        return None


def build_all():
    rows = read_labels()
    kept, excl = build_tables(rows)
    blobs = {f"{s}.csv": csv_bytes(kept[s]) for s in SPLITS}
    return rows, kept, excl, blobs


def make_manifest(rows, kept, excl, blobs):
    files = {}
    for s in SPLITS:
        name = f"{s}.csv"
        cats = Counter(r["category"] for r in kept[s])
        shows = Counter(r["show"] for r in kept[s])
        files[name] = {
            "sha256": sha256_bytes(blobs[name]),
            "rows": len(kept[s]),
            "by_category": {c: cats.get(c, 0) for c in CATEGORIES},
            "by_show": dict(sorted(shows.items())),
        }
    return {
        "version": "v1",
        "created_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "code_commit": git_head(),
        "script": "benchmark/scripts/build_splits.py",
        "script_sha256": sha256_file(__file__),
        "labels_csv": "benchmark/data/SEP-28k_labels.csv",
        "labels_sha256": sha256_file(LABELS),
        "show_split": SHOW_SPLIT,
        "rules": RULES,
        "exclusions": excl,
        "files": files,
        "limits": LIMITS,
    }


def print_summary(rows, kept, excl):
    print(f"input rows: {len(rows)}")
    print(f"quality exclusions: {excl['quality_total']}  by reason: {excl['quality_by_reason']}")
    hdr = f"{'split':<8}" + "".join(f"{c:>17}" for c in CATEGORIES) + f"{'total':>10}"
    print(hdr)
    tot = Counter()
    for s in SPLITS:
        cats = Counter(r["category"] for r in kept[s])
        tot.update(cats)
        print(f"{s:<8}" + "".join(f"{cats.get(c, 0):>17,}" for c in CATEGORIES)
              + f"{len(kept[s]):>10,}")
    print(f"{'all':<8}" + "".join(f"{tot.get(c, 0):>17,}" for c in CATEGORIES)
          + f"{sum(tot.values()):>10,}")


def do_build(out):
    if out.exists():
        print(f"ERROR: {out} already exists; splits are immutable (no --force).", file=sys.stderr)
        return 1
    rows, kept, excl, blobs = build_all()
    manifest = make_manifest(rows, kept, excl, blobs)
    out.mkdir(parents=True, exist_ok=False)
    for name, b in blobs.items():
        (out / name).write_bytes(b)
    with open(out / "manifest.json", "w", encoding="utf-8", newline="\n") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")
    print_summary(rows, kept, excl)
    print(f"wrote {out}")
    for name in blobs:
        print(f"  {name} sha256={manifest['files'][name]['sha256']}")
    return 0


def do_check(out):
    mpath = out / "manifest.json"
    if not mpath.is_file():
        print(f"FAIL: {mpath} missing", file=sys.stderr)
        return 1
    manifest = json.loads(mpath.read_text(encoding="utf-8"))
    ok = True

    def fail(msg):
        nonlocal ok
        ok = False
        print(f"FAIL: {msg}", file=sys.stderr)

    rows, kept, excl, blobs = build_all()
    for name, info in manifest["files"].items():
        p = out / name
        if not p.is_file():
            fail(f"{name} missing")
            continue
        data = p.read_bytes()
        if sha256_bytes(data) != info["sha256"]:
            fail(f"{name} sha256 differs from manifest")
        nrows = data.count(b"\n") - 1
        if nrows != info["rows"]:
            fail(f"{name} row count {nrows} != manifest {info['rows']}")
        if name not in blobs or data != blobs[name]:
            fail(f"{name} bytes differ from in-memory rebuild")
    if set(manifest["files"]) != set(blobs):
        fail("manifest file set differs from expected")
    if sha256_file(LABELS) != manifest["labels_sha256"]:
        fail("labels_sha256 does not match current labels file")
    if sha256_file(__file__) != manifest["script_sha256"]:
        print("WARNING: script_sha256 differs from manifest (script edited since build)",
              file=sys.stderr)
    if ok:
        print(f"OK: {out} verified")
        return 0
    return 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="verify existing manifests")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT, help="output directory")
    args = ap.parse_args()
    out = args.out.resolve()
    return do_check(out) if args.check else do_build(out)


if __name__ == "__main__":
    sys.exit(main())
