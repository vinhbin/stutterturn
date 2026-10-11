"""v5 preparation (D-014): dev2 = one training show held out of v5 training, itemized with v1's rules.

Proposal: issue #2 comment 6104449057. Hold-out rule (pre-registered, counts only): the smallest
training show with >= 100 block clips -> IStutterSoWhat. v5 retrains from stock, so these speakers
are scored by no selection in v1-v4. dev2 is the v5 SELECTOR set; promotion uses Niko's frozen
confirmation set (benchmark/confirm/v1).

  python benchmark/scripts/build_dev2_items.py              # build benchmark/items/dev2-v1; refuse if it exists
  python benchmark/scripts/build_dev2_items.py --selftest

Items come from build_items.energy_pass (the exact v1 energy-VAD rules) run on the held-out show's
rows of splits/v1/train.csv; only ids/split labels are renamed dev -> dev2. Also writes
heldout_keys.txt, which v5 training must exclude from every SEP pool. No model is run.
"""
import argparse, collections, datetime, json, os, sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_items as BI  # noqa: E402

OUT = os.path.join(BI.BASE, "items", "dev2-v1")
MIN_BLOCKS = 100


def choose_show(train_rows):
    """Smallest show (by clip count) with >= MIN_BLOCKS block clips (pure; counts only)."""
    clips, blocks = Counter(), Counter()
    for r in train_rows:
        clips[r["show"]] += 1
        blocks[r["show"]] += r["category"] == "block"
    eligible = sorted([s for s in clips if blocks[s] >= MIN_BLOCKS], key=lambda s: (clips[s], s))
    return (eligible[0] if eligible else None), {s: {"clips": clips[s], "block": blocks[s]} for s in sorted(clips)}


def rename(item):
    it = dict(item)
    assert it["item_id"].startswith("dev-") and it["split"] == "dev", it["item_id"]
    it["item_id"], it["split"] = "dev2-" + it["item_id"][4:], "dev2"
    return it


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    out = os.path.abspath(a.out)
    if os.path.exists(out):
        sys.exit(f"REFUSING: {out} exists (items are immutable)")
    BI.verify_splits()
    train = BI.read_csv(os.path.join(BI.SPLITS_DIR, "train.csv"))
    show, show_counts = choose_show(train)
    if show != "IStutterSoWhat":
        sys.exit(f"REFUSING: hold-out rule picked {show}, but the proposal pre-registered IStutterSoWhat")
    rows = [r for r in train if r["show"] == show]
    held = {r["clip_key"] for s in ("dev", "test") for r in BI.read_csv(os.path.join(BI.SPLITS_DIR, f"{s}.csv"))}
    assert not {r["clip_key"] for r in rows} & held, "held-out show overlaps dev/test"
    empty = set()
    ep = os.path.join(BI.AUDIO, "empty_on_mirror.txt")
    if os.path.exists(ep):
        empty = {l.strip() for l in open(ep) if l.strip()}
    T = defaultdict(Counter)
    # split="dev" so energy_pass applies the dev rules (incl. stuttered-completed candidates)
    main_, eow, prov, _fts, cand = BI.energy_pass("dev", rows, BI.Gate(empty), T)
    mi = sorted((rename(i) for i in main_.values()), key=lambda i: i["item_id"])
    ei = sorted((rename(i) for i in eow.values()), key=lambda i: i["item_id"])
    si = sorted((rename(i) for i in cand), key=lambda i: i["item_id"])
    pv = sorted((dict(p, item_id="dev2-" + p["item_id"][4:]) for p in prov.values()), key=lambda p: (p["item_id"], p["file"]))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    os.mkdir(out)
    BI.write_jsonl(os.path.join(out, "dev2.jsonl"), mi)
    BI.write_jsonl(os.path.join(out, "dev2_end_of_window.jsonl"), ei)
    BI.write_jsonl(os.path.join(out, "dev2_stuttered_completed.jsonl"), si)
    BI.write_jsonl(os.path.join(out, "provenance.jsonl"), pv)
    with open(os.path.join(out, "heldout_keys.txt"), "w", newline="\n") as f:
        f.write("\n".join(sorted(r["clip_key"] for r in rows)) + "\n")
    names = ["dev2.jsonl", "dev2_end_of_window.jsonl", "dev2_stuttered_completed.jsonl", "provenance.jsonl", "heldout_keys.txt"]
    cnt = lambda items: dict(Counter(f"{i['group']}/{i['kind']}" for i in items))  # noqa: E731
    manifest = {
        "version": "dev2-v1", "created_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "script": "benchmark/scripts/build_dev2_items.py", "script_sha256": BI.sha256_file(os.path.abspath(__file__)),
        "build_items_sha256": BI.sha256_file(os.path.join(HERE, "build_items.py")),
        "build_eval_sets_sha256": BI.sha256_file(os.path.join(HERE, "build_eval_sets.py")),
        "train_csv_sha256": BI.sha256_file(os.path.join(BI.SPLITS_DIR, "train.csv")),
        "holdout_rule": f"smallest training show with >= {MIN_BLOCKS} block clips (counts only)",
        "show_counts": show_counts, "heldout_show": show, "heldout_clips": len(rows),
        "vad_params": BI.vad_params(), "tallies": {k: dict(sorted(v.items())) for k, v in sorted(T.items())},
        "item_counts": {"main": cnt(mi), "end_of_window": cnt(ei), "stuttered_completed": cnt(si)},
        "output_sha256": {n: BI.sha256_file(os.path.join(out, n)) for n in names},
        "labels": "energy_vad proxies (same as items/v1); not human-confirmed",
        "use": "v5 selector set only; v5 training must exclude every key in heldout_keys.txt; "
               "no model has been scored on these items"}
    with open(os.path.join(out, "manifest.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(manifest, f, indent=1)
    print(json.dumps({"heldout_show": show, "item_counts": manifest["item_counts"]}, indent=1))


def selftest():
    rows = ([{"show": "Big", "category": "block"}] * 500 + [{"show": "Big", "category": "fluent"}] * 500 +
            [{"show": "Mid", "category": "block"}] * 120 + [{"show": "Mid", "category": "fluent"}] * 300 +
            [{"show": "Tiny", "category": "block"}] * 60)
    show, _ = choose_show(rows)
    ok = True
    for name, cond in [
        ("rule picks the smallest show with >= 100 blocks", show == "Mid"),
        ("rename dev -> dev2", rename({"item_id": "dev-stu-unf-K_1_2", "split": "dev"})["item_id"] == "dev2-stu-unf-K_1_2"),
        ("no eligible show -> None", choose_show([{"show": "A", "category": "block"}] * 5)[0] is None),
    ]:
        print(f"  {'ok' if cond else 'FAIL'}: {name}")
        ok &= bool(cond)
    # the real split must give IStutterSoWhat
    real, counts = choose_show(BI.read_csv(os.path.join(BI.SPLITS_DIR, "train.csv")))
    print(f"  {'ok' if real == 'IStutterSoWhat' else 'FAIL'}: real split -> {real} {counts.get(real)}")
    ok &= real == "IStutterSoWhat"
    print("SELFTEST " + ("PASSED" if ok else "FAILED"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
