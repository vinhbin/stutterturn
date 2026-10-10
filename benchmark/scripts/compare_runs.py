"""Compare two eval runs on the same items: python compare_runs.py RUN_A RUN_B [--allow-config-diff]

Prints data for the PLAN 3 PM checks; it does not issue verdicts (the gate belongs to the team).
"""
import argparse, json, os, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from eval_runner import wilson  # noqa: E402

TARGET_DELAY_DIFF_S = 0.050


def load(d):
    run = json.load(open(os.path.join(d, "run.json")))
    rows = [json.loads(l) for l in open(os.path.join(d, "results.jsonl")) if l.strip()]
    return run, {r["item_id"]: r for r in rows}


def fmt_rate(k, n):
    lo, hi = wilson(k, n)
    return f"{k}/{n} = {k / n:.1%} (95% CI {lo:.1%}-{hi:.1%})" if n else "0/0"


def q(a, p):
    return float(np.percentile(a, p)) if len(a) else None


def f(x):
    return "n/a" if x is None else f"{x:.3f}s"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_a"); ap.add_argument("run_b")
    ap.add_argument("--allow-config-diff", action="store_true")
    a = ap.parse_args()
    ra, A = load(a.run_a)
    rb, B = load(a.run_b)
    if ra["items_sha256"] != rb["items_sha256"]:
        print(f"REFUSED: items_sha256 differ ({ra['items_sha256'][:12]} vs {rb['items_sha256'][:12]})", file=sys.stderr)
        sys.exit(2)
    ca, cb = ra["config"], rb["config"]
    # grid_scope: absent == "full"; checks-only outcomes are proven identical (specs/checks-only-grid-v1.md)
    ca = dict(ca, grid_scope=ca.get("grid_scope", "full"))
    cb = dict(cb, grid_scope=cb.get("grid_scope", "full"))
    diff = sorted(k for k in set(ca) | set(cb) if ca.get(k) != cb.get(k))
    allowed = {"threshold"}
    if "grid_scope" in diff and set(diff) <= {"threshold", "grid_scope", "config_id"}:
        allowed |= {"grid_scope", "config_id"}
    other = [k for k in diff if k not in allowed]
    if other and not a.allow_config_diff:
        print(f"REFUSED: configs differ in {other} (besides threshold); use --allow-config-diff", file=sys.stderr)
        sys.exit(2)
    print(f"A: {ra['run_id']}  model={ra['model_id']} ({ra['model_sha256'][:12]})")
    print(f"B: {rb['run_id']}  model={rb['model_id']} ({rb['model_sha256'][:12]})")
    print(f"items_sha256: {ra['items_sha256'][:16]}  preproc: {ra['preproc_version']} / {rb['preproc_version']}")
    print("config differences:", {k: (ca.get(k), cb.get(k)) for k in diff} or "none")
    if other:
        print("WARNING: non-threshold config differences allowed by --allow-config-diff")
    if set(A) != set(B):
        print(f"WARNING: item sets differ (only A: {len(set(A) - set(B))}, only B: {len(set(B) - set(A))}); using the intersection")
    ids = sorted(set(A) & set(B))
    groups = {}
    for i in ids:
        r = A[i]
        groups.setdefault((r["split"], r["group"], r["kind"], r["label_source"]), []).append(i)
    for (split, group, kind, ls), gi in sorted(groups.items()):
        print(f"\n== split={split} group={group} kind={kind} label_source={ls} (n={len(gi)})")
        if kind == "unfinished":
            ka = sum(A[i]["premature"] for i in gi); kb = sum(B[i]["premature"] for i in gi)
            print(f"  premature A: {fmt_rate(ka, len(gi))}")
            print(f"  premature B: {fmt_rate(kb, len(gi))}")
            ab = sum(1 for i in gi if A[i]["premature"] and not B[i]["premature"])
            ba = sum(1 for i in gi if B[i]["premature"] and not A[i]["premature"])
            print(f"  discordant pairs: A premature/B not = {ab}; B premature/A not = {ba}")
        else:
            def stats(R):
                dec = [R[i] for i in gi if R[i]["outcome"] == "decided"]
                return {"d": np.array([r["delay_s"] for r in dec]),
                        "model": sum(r["trigger"] == "model" for r in dec),
                        "fb": sum(r["trigger"] == "fallback" for r in dec),
                        "cens": len(gi) - len(dec)}
            sa, sb = stats(A), stats(B)
            for nm, s in (("A", sa), ("B", sb)):
                print(f"  {nm}: decided={len(s['d'])} by_model={s['model']} by_fallback={s['fb']} censored={s['cens']}"
                      f" | delay median={f(q(s['d'], 50))} p90={f(q(s['d'], 90))}")
            ma, mb = q(sa["d"], 50), q(sb["d"], 50)
            md = None if ma is None or mb is None else mb - ma
            print(f"  median delay B-A = {'n/a' if md is None else f'{md * 1000:+.0f} ms'} (PLAN target: <= +{TARGET_DELAY_DIFF_S * 1000:.0f} ms; data, not a verdict)")
            pa, pb = q(sa["d"], 90), q(sb["d"], 90)
            print(f"  p90 delay A={f(pa)} B={f(pb)}")
            print(f"  censored worse in B? {sb['cens'] > sa['cens']} ({sa['cens']} -> {sb['cens']}); "
                  f"fallback worse in B? {sb['fb'] > sa['fb']} ({sa['fb']} -> {sb['fb']})")
    print("\nPLAN 3 PM checks are reported above as data; the gate decision belongs to the team.")


if __name__ == "__main__":
    main()
