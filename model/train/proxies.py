"""End-of-window completed proxies, exactly the eval-items rule (training-v2.md 2e).

One code path for training positives (train split) and for the in-loop M3s keys and the
section 8 check 2 rule identity (dev split). Mirrors benchmark/scripts/build_items.py
energy_pass: the fluent completed proxy and the cand_stu_cmp rule for block and
other_disfluent. Constants and functions are imported, not copied.
"""
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

sys.path.insert(0, os.path.join(C.BENCH, "scripts"))
import build_items as bi  # noqa: E402
import build_eval_sets as bes  # noqa: E402

GROUP = {"fluent": "fluent", "block": "stuttered", "other_disfluent": "stuttered"}


def split_rows(split):
    with open(os.path.join(C.BENCH, "splits", "v1", f"{split}.csv"), newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def make_gate():
    p = os.path.join(C.BENCH, "audio", "empty_on_mirror.txt")
    empty = {l.strip() for l in open(p) if l.strip()} if os.path.exists(p) else set()
    return bi.Gate(empty)


def completed_proxies(rows, gate=None):
    """Returns ([{clip_key, category, group, te, dur}], reason_counts) for rows whose
    category is fluent/block/other_disfluent, using the eval-items end-of-window rule."""
    gate = gate or make_gate()
    out, counts = [], {}

    def tick(cat, why):
        counts.setdefault(cat, {}).setdefault(why, 0)
        counts[cat][why] += 1

    for r in rows:
        cat, key = r["category"], r["clip_key"]
        if cat not in GROUP:
            continue
        reason, dur = gate(key)
        if reason:
            tick(cat, reason)
            continue
        ft = bes.fluent_features(bes.analyze(os.path.join(C.BENCH, "audio", key + ".wav")))
        if cat == "fluent":
            if ft is None or ft["total_speech"] < bi.MIN_FLUENT_SPEECH_S:
                tick(cat, "no_speech_detected")
                continue
            if ft["trailing"] < bi.MIN_TRAILING_S:
                tick(cat, "cmp_trailing_lt_0.5")
                continue
        else:
            if ft is None or ft["trailing"] < bi.MIN_TRAILING_S:
                tick(cat, "no_trailing_0.5")
                continue
        te = round(float(ft["speech_end"]), 3)
        if dur - te < bi.VAD_STOP_S:
            tick(cat, "post_end_too_short")
            continue
        tick(cat, "ok")
        out.append({"clip_key": key, "category": cat, "group": GROUP[cat], "te": te, "dur": dur})
    return out, counts
