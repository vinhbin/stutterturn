"""v5 preparation (D-014): assemble data-v5 with the dev2 hold-out ENFORCED on every SEP pool.

Niko's binding review (#2, 2026-10-11T02:56Z), must-fix 2: data-v2's SEP files contain IStutterSoWhat
cuts, so v5 must not train on them as they are. This step filters every SEP pool by
benchmark/items/dev2-v1/heldout_keys.txt, asserts zero overlap, and records every sha.

  python model/train/v5_data.py --work W            # data-v2 + data-v5-crops + data-v5-guard -> data-v5
  python model/train/v5_data.py --selftest

Inputs must already exist and pass their own gates: dev2 items (heldout_keys.txt), the crop build
with a passing build-bound audit (v5_crops.require_audit), and the fresh guard. Writes
<out>/{stutter_neg,sep_pos,orig_replay,replay_crops,guard,old_guard}.jsonl + manifest.json.
No model is run; no training is authorized by this file.
"""
import argparse
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

HELDOUT = os.path.join(C.BENCH, "items", "dev2-v1", "heldout_keys.txt")
SEP_POOLS = ("stutter_neg.jsonl", "sep_pos.jsonl")


def load(path):
    return [json.loads(l) for l in open(path) if l.strip()]


def write(path, rows):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(json.dumps(r, sort_keys=True) + "\n")
    return C.sha256_file(path)


def assemble(sep, replay, crops, guard, old_guard, heldout):
    """Pure core: returns (outputs dict, report). Exits on any violated invariant."""
    out, report = {}, {"sep_removed_heldout": {}}
    for name, rows in sep.items():
        kept = [r for r in rows if r["clip_key"] not in heldout]
        report["sep_removed_heldout"][name] = len(rows) - len(kept)
        leak = {r["clip_key"] for r in kept} & heldout
        if leak:
            sys.exit(f"REFUSING: {name} still contains held-out keys {sorted(leak)[:5]}")
        out[name] = kept
    replay_ids, replay_wavs = {r["id"] for r in replay}, {r["wav_sha256"] for r in replay}
    guard_ids, guard_wavs = {r["id"] for r in guard}, {r["wav_sha256"] for r in guard}
    if replay_ids & guard_ids or replay_wavs & guard_wavs:
        sys.exit("REFUSING: fresh guard overlaps replay")
    if {r["id"] for r in old_guard} & guard_ids or {r["wav_sha256"] for r in old_guard} & guard_wavs:
        sys.exit("REFUSING: fresh guard overlaps the old guard")
    if not {c["parent_id"] for c in crops} <= replay_ids:
        sys.exit("REFUSING: a crop's parent is not a replay row")
    if {c["parent_id"] for c in crops} & guard_ids:
        sys.exit("REFUSING: a crop's parent is in the fresh guard")
    out.update({"orig_replay.jsonl": replay, "replay_crops.jsonl": crops, "guard.jsonl": guard,
                "old_guard.jsonl": old_guard})
    report["counts"] = {k: len(v) for k, v in out.items()}
    report["zero_overlap_asserted"] = ["SEP pools vs heldout_keys", "fresh guard vs replay", "fresh guard vs old guard",
                                       "crop parents within replay", "crop parents vs fresh guard"]
    return out, report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work")
    ap.add_argument("--data", default="data-v2")
    ap.add_argument("--crops", default="data-v5-crops")
    ap.add_argument("--guard", default="data-v5-guard")
    ap.add_argument("--out", default="data-v5")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.work:
        ap.error("--work required")
    w, root = os.path.realpath(a.work), os.path.realpath(C.ROOT)
    if os.path.commonpath([w, root]) == root:
        sys.exit(f"REFUSING: --work {a.work} is inside the repo")
    if not os.path.exists(HELDOUT):
        sys.exit("REFUSING: benchmark/items/dev2-v1/heldout_keys.txt missing (build dev2 items first)")
    import v5_crops
    audit = v5_crops.require_audit(a.work, a.crops)
    out_dir = os.path.join(a.work, a.out)
    if os.path.exists(out_dir):
        sys.exit(f"REFUSING: {out_dir} exists")
    heldout = {l.strip() for l in open(HELDOUT) if l.strip()}
    d = lambda *p: os.path.join(a.work, *p)  # noqa: E731
    out, report = assemble({n: load(d(a.data, n)) for n in SEP_POOLS}, load(d(a.data, "orig_replay.jsonl")),
                           load(d(a.crops, "replay_crops.jsonl")), load(d(a.guard, "guard.jsonl")),
                           load(d(a.data, "guard.jsonl")), heldout)
    os.makedirs(out_dir)
    shas = {name: write(os.path.join(out_dir, name), rows) for name, rows in out.items()}
    C.write_json(os.path.join(out_dir, "manifest.json"), {
        "script": "model/train/v5_data.py", "code_commit": C.git_commit(),
        "heldout_keys": {"path": "benchmark/items/dev2-v1/heldout_keys.txt", "sha256": C.sha256_file(HELDOUT),
                         "n": len(heldout)},
        "sources": {"data": {"dir": a.data, "manifest_sha256": C.sha256_file(d(a.data, "manifest.json"))},
                    "crops": {"dir": a.crops, "manifest_sha256": C.sha256_file(d(a.crops, "manifest.json")),
                              "audit_result_sha256": C.sha256_file(d(a.crops, "audit_result.json")),
                              "audit_passed": audit["passed"]},
                    "guard": {"dir": a.guard, "manifest_sha256": C.sha256_file(d(a.guard, "manifest.json"))}},
        "jsonl_sha256": shas, **report,
        "notes": ["old_guard.jsonl is the secondary report only; v5 selection uses guard.jsonl",
                  "v2 SEP length matching is not re-asserted after the hold-out filter; quantiles to be reported "
                  "by the v5 training preflight"]})
    print(json.dumps({"jsonl_sha256": shas, **report}, indent=1))


def selftest():
    sep = {"stutter_neg.jsonl": [{"clip_key": "A_1_1"}, {"clip_key": "H_1_1"}],
           "sep_pos.jsonl": [{"clip_key": "A_1_2"}, {"clip_key": "H_1_2"}, {"clip_key": "H_1_3"}]}
    replay = [{"id": "r1", "wav_sha256": "w1"}, {"id": "r2", "wav_sha256": "w2"}]
    crops = [{"parent_id": "r1"}]
    guard = [{"id": "g1", "wav_sha256": "wg1"}]
    old = [{"id": "o1", "wav_sha256": "wo1"}]
    held = {"H_1_1", "H_1_2", "H_1_3"}
    ok = True

    def refuses(fn):
        try:
            fn()
        except SystemExit:
            return True
        return False
    out, rep = assemble(sep, replay, crops, guard, old, held)
    for name, cond in [
        ("held-out keys removed from every SEP pool",
         all(r["clip_key"] not in held for n in sep for r in out[n]) and rep["sep_removed_heldout"] ==
         {"stutter_neg.jsonl": 1, "sep_pos.jsonl": 2}),
        ("fresh guard overlapping replay refused",
         refuses(lambda: assemble(sep, replay, crops, [{"id": "x", "wav_sha256": "w2"}], old, held))),
        ("fresh guard overlapping old guard refused",
         refuses(lambda: assemble(sep, replay, crops, [{"id": "o1", "wav_sha256": "z"}], old, held))),
        ("crop with non-replay parent refused",
         refuses(lambda: assemble(sep, replay, [{"parent_id": "zz"}], guard, old, held))),
        ("counts recorded", rep["counts"]["sep_pos.jsonl"] == 1 and rep["counts"]["replay_crops.jsonl"] == 1),
    ]:
        print(f"  {'ok' if cond else 'FAIL'}: {name}")
        ok &= bool(cond)
    print("SELFTEST " + ("PASSED" if ok else "FAILED"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
