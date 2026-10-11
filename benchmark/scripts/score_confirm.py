"""Score the confirmation evaluation (spec: benchmark/specs/confirm-eval-v1.md, section 5).

  python benchmark/scripts/score_confirm.py                      # real locations; refuses if output exists

Checks (all must pass before anything is written): section 0 (decision-log freeze entry, build_confirm_items.py
--check, confirm.jsonl hash, exact conf-* run set, items_sha256), one env.platform across all runs, and the
model / VAD hashes of section 1. Computes section 2 metrics, section 3 criteria (candidate X vs stock S), and
writes decision.{json,md}. It changes no threshold, selects nothing, runs no model. Output is deterministic.

Test-only overrides (defaults are the real locations): --runs-dir, --items, --decision-log, --decision-log-hash
(repeatable; replaces reading the log), --out, --run-prefix (replaces 'conf-' in the run-ID table and the
extra-directory check).
"""
import argparse, json, os, re, statistics, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
REPO = os.path.dirname(BASE)
sys.path.insert(0, HERE)
from eval_runner import wilson, sha256_file  # noqa: E402
from select_candidate import mcnemar_p, pair_counts, wald_paired  # noqa: E402

DEF_RUNS = os.path.join(BASE, "runs")
DEF_ITEMS = os.path.join(BASE, "items", "confirm-v1", "confirm.jsonl")
DEF_LOG = os.path.join(REPO, "docs", "decision-log.md")
DEF_OUT = os.path.join(BASE, "selection", "confirm-x1")
CHECK_SCRIPT = os.path.join(HERE, "build_confirm_items.py")

X1_SHA = "d1a503fee1eca1e6d6ffe78e918d8ed312922eddb5f3dd19cc5315c1b824c025"
STOCK_SHA = "ab8dc64b88713f90b571c15b714bd1330e6c883cad8763dacf65c9376dc539be"
VAD_SHA = "2623a2953f6ff3d2c1e61740c6cdb7168133479b267dfef114a4a3cc5bdd788f"
FALLBACK_S = 3.0
MIN_CELL = 10
P_TARGET = 0.10
D_MARGIN = 0.050
EPS = 1e-9
GROUPS = ["stuttered", "fluent"]

TURN, SINGLE = "agent-v0.1-turn-checks", "agent-v0.1-single-checks"
# suffix -> (arm, model_id, model_sha, config_id, threshold, family, role)
RUNS = {
    "X-turn": ("X@0.5", "x1", X1_SHA, TURN, 0.5, "turn_onset", "X inference at 0.5 (not a criterion)"),
    "X-turn-th0.60": ("X", "x1", X1_SHA, TURN, 0.6, "turn_onset", "candidate X"),
    "S-turn": ("S", "stock-fp32", STOCK_SHA, TURN, 0.5, "turn_onset", "stock baseline S"),
    "C-turn-th0.55": ("C", "stock-fp32", STOCK_SHA, TURN, 0.55, "turn_onset", "comparator, report only"),
    "F04-turn": ("F04", "stock-fp32", STOCK_SHA, "agent-v0.1-patient-04-turn-checks", 0.5, "turn_onset",
                 "patient baseline 0.4"),
    "F06-turn": ("F06", "stock-fp32", STOCK_SHA, "agent-v0.1-patient-06-turn-checks", 0.5, "turn_onset",
                 "patient baseline 0.6"),
    "F08-turn": ("F08", "stock-fp32", STOCK_SHA, "agent-v0.1-patient-08-turn-checks", 0.5, "turn_onset",
                 "patient baseline 0.8"),
    "X-clip": ("X-clip@0.5", "x1", X1_SHA, SINGLE, 0.5, "clip_start", "secondary, report only"),
    "X-clip-th0.60": ("X-clip", "x1", X1_SHA, SINGLE, 0.6, "clip_start", "secondary, report only"),
    "S-clip": ("S-clip", "stock-fp32", STOCK_SHA, SINGLE, 0.5, "clip_start", "secondary, report only"),
}
CAND, BASELINE = "X-turn-th0.60", "S-turn"
FARMS = ["F04-turn", "F06-turn", "F08-turn"]
REPORT_ONLY = ["X-turn", "C-turn-th0.55", "X-clip-th0.60", "S-clip", "X-clip"]

# ---- verbatim text from the spec (sections 3 and 4) ----
WORDING = ("X1 was a post-hoc exploratory candidate (fifth adaptive look at dev/guard). The confirmation set is "
           "untouched recordings from the same two dev shows (possibly the same speakers), human-labelled and blind.")
PASS_NOTE = ("A pass permits promotion **to the demo as an experimental configuration, alongside stock and "
             "patient**, once (c) audio acceptance has also passed. **It doesn't permit any efficacy claim; "
             "D-009's test stays sealed.**")
INSUFFICIENT_NOTE = ("**This outcome is likely:** confirm-set yields are expected to be low, especially for "
                     "`unfinished_fluent_pause`. Saying so up front is part of the pre-registration.")
LIMITS = [
    "- **Timing:** the agent checks 7 frames × 32 ms = 0.224 s after its VAD speech-stop; the runner checks 0.2 s "
    "after the labelled silence start. The offset is the same for every arm, so the X − S comparison stays fair, "
    "but absolute delays aren't the agent's.",
    "- **Mid-turn pauses:** the runner checks only at the labelled pause or turn end. The agent also checks at any "
    "VAD pause earlier in the clip, which isn't evaluated here.",
    "- **Not measured:** tail delay and audible response delay, which PLAN asks for. They belong to (c) audio "
    "acceptance, not here.",
    "- **Small n:** about 20 items or fewer per cell, the same two shows as dev, and proxy-free human labels. "
    "These are feasibility results.",
]
CRITERIA_TEXT = [
    "1. **Premature:** P(X) **< 10%** in **each** group, the PLAN target.",
    "2. **Fluent unfinished not worse:** P_fluent(X) ≤ P_fluent(S), on point estimates.",
    "3. **Completed-turn delay:** **mean** D(X) − mean D(S) ≤ **+0.050 s** in each group.",
    "4. **Fallback rate not worse:** R(X) ≤ R(S) in each group.",
    "5. **Minimum evidence:** at least **10** human-accepted items in each of the four group × kind cells. If any "
    "cell has fewer, the outcome is **`confirm_insufficient`**, with no promotion.",
]


def die(msg):
    print("REFUSED: " + msg, file=sys.stderr)
    sys.exit(2)


def jload(p, what):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        die(f"cannot read {what} {p}: {e}")


def jsonl(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


# ------------------------------------------------------------------ preconditions
def check_log(args, adj_sha, conf_sha):
    """Freeze entry: both hashes present in one decision-log entry (or the --decision-log-hash override)."""
    need = {adj_sha.lower(), conf_sha.lower()}
    if args.decision_log_hash:
        have = {h.lower() for h in args.decision_log_hash}
        if not need <= have:
            die(f"decision-log hashes given do not include both adjudicated.csv {adj_sha} and confirm.jsonl {conf_sha}")
        return "override"
    if not os.path.isfile(args.decision_log):
        die(f"decision log {args.decision_log} not found; no freeze entry")
    text = open(args.decision_log, encoding="utf-8").read().lower()
    entries = re.split(r"(?m)^## ", text)
    if not any(all(h in e for h in need) for e in entries):
        die("decision log has no entry containing both the adjudicated.csv sha256 "
            f"{adj_sha} and the confirm.jsonl sha256 {conf_sha} (no freeze entry)")
    return os.path.relpath(args.decision_log, REPO) if args.decision_log.startswith(REPO) else args.decision_log


def load_run(rdir, suffix, prefix, conf_sha):
    spec = RUNS[suffix]
    arm, model_id, model_sha, cfg_id, th, fam, _role = spec
    name = prefix + suffix
    run = jload(os.path.join(rdir, "run.json"), f"{name}/run.json")
    rp = os.path.join(rdir, "results.jsonl")
    if not os.path.isfile(rp):
        die(f"{name}: results.jsonl missing")
    if run.get("items_sha256") != conf_sha:
        die(f"{name}: items_sha256 {run.get('items_sha256')} != logged confirm.jsonl {conf_sha}")
    if run.get("model_sha256") != model_sha:
        die(f"{name}: model_sha256 {run.get('model_sha256')} != expected {model_sha}")
    if run.get("model_id") != model_id:
        die(f"{name}: model_id {run.get('model_id')!r} != expected {model_id!r}")
    want_vad = VAD_SHA if fam == "turn_onset" else None
    if run.get("vad_model_sha256") != want_vad:
        die(f"{name}: vad_model_sha256 {run.get('vad_model_sha256')!r} != expected {want_vad!r}")
    cfg = run.get("config") or {}
    if cfg.get("config_id") != cfg_id:
        die(f"{name}: config_id {cfg.get('config_id')!r} != expected {cfg_id!r}")
    if cfg.get("threshold") != th:
        die(f"{name}: threshold {cfg.get('threshold')!r} != expected {th!r}")
    if cfg.get("input_policy", "clip_start") != fam:
        die(f"{name}: input_policy {cfg.get('input_policy', 'clip_start')!r} != expected {fam!r}")
    if cfg.get("schedule") != "single":
        die(f"{name}: schedule {cfg.get('schedule')!r} != 'single' (R is defined for a single first check)")
    if not isinstance(cfg.get("vad_stop_s"), (int, float)):
        die(f"{name}: config.vad_stop_s missing")
    plat = (run.get("env") or {}).get("platform")
    if not plat:
        die(f"{name}: env.platform missing")
    return run, jsonl(rp), plat


# ------------------------------------------------------------------ metrics
def rate_entry(k, n):
    return {"k": k, "n": n, "rate": None if not n else round(k / n, 6), "wilson95": wilson(k, n)}


def arm_metrics(rows, vad):
    """Per group: P over unfinished, D and R over completed. D = vad_stop_s if trigger == 'model' else 3.0."""
    out = {}
    for g in GROUPS:
        unf = [r for r in rows if r["group"] == g and r["kind"] == "unfinished"]
        cmp_ = [r for r in rows if r["group"] == g and r["kind"] == "completed"]
        P = rate_entry(sum(1 for r in unf if r["premature"]), len(unf))
        ds = [vad if r.get("trigger") == "model" else FALLBACK_S for r in cmp_]
        R = rate_entry(sum(1 for r in cmp_ if r.get("trigger") != "model"), len(cmp_))
        D = {"n": len(ds), "mean": round(sum(ds) / len(ds), 6) if ds else None,
             "median": round(statistics.median(ds), 6) if ds else None, "vad_stop_s": vad}
        if ds:  # D = vad + (3 - vad) * R is monotone in R, so the Wilson interval maps exactly
            lo, hi = R["wilson95"]
            D["mean_ci95_from_R_wilson"] = [round(vad + (FALLBACK_S - vad) * lo, 4),
                                            round(vad + (FALLBACK_S - vad) * hi, 4)]
        out[g] = {"P": P, "D": D, "R": R}
    return out


def criteria(m_arm, m_base):
    c1 = {g: m_arm[g]["P"]["rate"] is not None and m_arm[g]["P"]["rate"] < P_TARGET - EPS for g in GROUPS}
    pa, pb = m_arm["fluent"]["P"]["rate"], m_base["fluent"]["P"]["rate"]
    c2 = pa is not None and pb is not None and pa <= pb + EPS
    c3, c4, dd = {}, {}, {}
    for g in GROUPS:
        a, b = m_arm[g]["D"]["mean"], m_base[g]["D"]["mean"]
        dd[g] = None if a is None or b is None else round(a - b, 6)
        c3[g] = dd[g] is not None and dd[g] <= D_MARGIN + EPS
        ra, rb = m_arm[g]["R"]["rate"], m_base[g]["R"]["rate"]
        c4[g] = ra is not None and rb is not None and ra <= rb + EPS
    allp = all(c1.values()) and c2 and all(c3.values()) and all(c4.values())
    return {"c1_premature_lt_10pct": c1, "c2_fluent_P_not_worse": c2,
            "c3_mean_D_delta_s": dd, "c3_mean_D_delta_le_0.050": c3, "c4_R_not_worse": c4,
            "criteria_1_to_4_all_hold": allp}


def paired(rows_arm, rows_base):
    res = {}
    for g in GROUPS:
        entry = {}
        for name, kind, f in [("P", "unfinished", lambda r: bool(r["premature"])),
                              ("R", "completed", lambda r: r.get("trigger") != "model")]:
            ev_b = {r["item_id"]: f(r) for r in rows_base if r["group"] == g and r["kind"] == kind}
            ev_a = {r["item_id"]: f(r) for r in rows_arm if r["group"] == g and r["kind"] == kind}
            if not ev_b:
                entry[name] = None
                continue
            b, c, n = pair_counts(ev_b, ev_a)
            d, ci = wald_paired(b, c, n)
            entry[name] = {"n": n, "b_S_true_X_false": b, "c_S_false_X_true": c, "delta_X_minus_S": round(d, 6),
                           "wald_paired95": ci, "mcnemar_p": mcnemar_p(b, c)}
        res[g] = entry
    return res


# ------------------------------------------------------------------ rendering
def pc(x):
    return "n/a" if x is None else f"{100 * x:.1f}%"


def ci(w):
    return "n/a" if w[0] is None else f"[{100 * w[0]:.1f}, {100 * w[1]:.1f}]"


def mdt(header, rows):
    return "\n".join(["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"] +
                     ["| " + " | ".join(str(x) for x in r) + " |" for r in rows])


def render_md(dec):
    L = ["# Confirmation evaluation v1: decision", "",
         f"**Outcome: `{dec['outcome']}`**", "", WORDING, ""]
    if dec["outcome"] == "confirm_pass_feasibility":
        L += [PASS_NOTE, ""]
    elif dec["outcome"] == "confirm_insufficient":
        L += ["No promotion: at least one group × kind cell has fewer than 10 items. " + INSUFFICIENT_NOTE, ""]
    else:
        L += ["No promotion: at least one of criteria 1–4 does not hold. It doesn't permit any efficacy claim; "
              "D-009's test stays sealed.", ""]
    L += ["## Evidence (criterion 5)", "",
          mdt(["group", "kind", "n", "need"], [[c["group"], c["kind"], c["n"], f">= {MIN_CELL}"]
                                              for c in dec["cells"]]), ""]
    L += ["## Criteria (candidate X = conf-X-turn-th0.60 vs stock S = conf-S-turn, turn_onset family)", ""]
    L += CRITERIA_TEXT + [""]
    x = dec["criteria_X_vs_S"]
    rowsx = [["1 P(X) < 10%", f"stuttered {x['c1_premature_lt_10pct']['stuttered']}, fluent {x['c1_premature_lt_10pct']['fluent']}"],
             ["2 P_fluent(X) <= P_fluent(S)", x["c2_fluent_P_not_worse"]],
             ["3 mean D delta <= +0.050 s", "; ".join(f"{g} {x['c3_mean_D_delta_s'][g]} -> {x['c3_mean_D_delta_le_0.050'][g]}" for g in GROUPS)],
             ["4 R(X) <= R(S)", "; ".join(f"{g} {x['c4_R_not_worse'][g]}" for g in GROUPS)],
             ["5 min evidence (>= 10 per cell)", dec["criterion_5_met"]]]
    L += [mdt(["criterion", "holds"], rowsx), ""]
    L += ["## Metrics per arm and group (Wilson 95% CI, n)", "",
          "P = premature share over unfinished items. D = vad_stop_s if trigger == model, else 3.0 s (censored "
          "items assumed to hit the fallback). R = completed items not decided at the first check.", ""]
    mrows = []
    for name, a in dec["arms"].items():
        for g in GROUPS:
            m = a["metrics"][g]
            mrows.append([a["run_id"], a["role"], g,
                          f"{pc(m['P']['rate'])} {ci(m['P']['wilson95'])} ({m['P']['k']}/{m['P']['n']})",
                          f"mean {m['D']['mean']}, median {m['D']['median']}, vad_stop_s {m['D']['vad_stop_s']}, n {m['D']['n']}",
                          f"{pc(m['R']['rate'])} {ci(m['R']['wilson95'])} ({m['R']['k']}/{m['R']['n']})"])
    L += [mdt(["run", "role", "group", "P", "D (s)", "R"], mrows), ""]
    L += ["## Patient baselines F04/F06/F08 vs S, criteria 1–4 (report, not a criterion on X)", ""]
    frows = [[n, dec["arms"][n]["run_id"], f["criteria_1_to_4_all_hold"],
              f["c1_premature_lt_10pct"], f["c2_fluent_P_not_worse"], f["c3_mean_D_delta_le_0.050"], f["c4_R_not_worse"]]
             for n, f in dec["criteria_F_vs_S"].items()]
    L += [mdt(["arm", "run", "all 1-4", "c1", "c2", "c3", "c4"], frows), ""]
    L += ["## Report-only arms vs S on criteria 1–4 (comparator C, X at 0.5, clip_start family)", ""]
    rrows = [[n, dec["arms"][n]["run_id"], f["criteria_1_to_4_all_hold"],
              f["c1_premature_lt_10pct"], f["c2_fluent_P_not_worse"], f["c3_mean_D_delta_le_0.050"], f["c4_R_not_worse"]]
             for n, f in dec["criteria_report_only_vs_baseline"].items()]
    L += [mdt(["arm", "run", "all 1-4", "c1", "c2", "c3", "c4"], rrows), "",
          "clip_start arms are compared with S-clip; the others with S (turn_onset).", ""]
    L += ["## Paired discordant counts, X vs S (b = S true and X false; c = S false and X true; McNemar exact)", ""]
    prow = []
    for g in GROUPS:
        for k, v in dec["paired_X_vs_S"][g].items():
            if v:
                prow.append([g, k, v["n"], v["b_S_true_X_false"], v["c_S_false_X_true"], v["delta_X_minus_S"],
                             v["wald_paired95"], v["mcnemar_p"]])
    L += [mdt(["group", "metric", "n", "b", "c", "delta X-S", "Wald paired 95%", "McNemar p"], prow), ""]
    L += ["## Limits", ""] + LIMITS + [""]
    L += ["## Inputs", "", f"- confirm.jsonl sha256: `{dec['inputs']['confirm_jsonl_sha256']}`",
          f"- adjudicated.csv sha256: `{dec['inputs']['adjudicated_csv_sha256']}`",
          f"- env.platform (all runs): `{dec['inputs']['env_platform']}`", ""]
    return "\n".join(L)


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs-dir", default=DEF_RUNS)
    ap.add_argument("--items", default=DEF_ITEMS)
    ap.add_argument("--decision-log", default=DEF_LOG)
    ap.add_argument("--decision-log-hash", action="append", default=[], metavar="HEX",
                    help="test-only: hashes treated as the freeze entry (repeatable); replaces reading the log")
    ap.add_argument("--out", default=DEF_OUT)
    ap.add_argument("--run-prefix", default="conf-", help="test-only: replaces 'conf-'")
    args = ap.parse_args()
    args.runs_dir, args.items, args.out = (os.path.abspath(p) for p in (args.runs_dir, args.items, args.out))
    args.decision_log = os.path.abspath(args.decision_log)
    pre = args.run_prefix

    jp, mp = os.path.join(args.out, "decision.json"), os.path.join(args.out, "decision.md")
    if os.path.exists(jp) or os.path.exists(mp):
        die(f"output exists ({args.out}); decision files are never overwritten")

    # section 0.2: items check + hash
    if not os.path.isfile(args.items):
        die(f"items file {args.items} not found")
    items_dir = os.path.dirname(args.items)
    if os.path.basename(args.items) != "confirm.jsonl":
        die("--items must be a file named confirm.jsonl")
    p = subprocess.run([sys.executable, CHECK_SCRIPT, "--check", items_dir], capture_output=True, text=True)
    if p.returncode != 0:
        die("build_confirm_items.py --check failed:\n" + (p.stdout + p.stderr).strip())
    conf_sha = sha256_file(args.items)
    man = jload(os.path.join(items_dir, "manifest.json"), "items manifest")
    if man["output_sha256"]["confirm.jsonl"] != conf_sha:
        die("confirm.jsonl sha256 differs from its manifest")
    adj_sha = man["adjudicated_sha256"]
    # section 0.1: freeze entry
    log_src = check_log(args, adj_sha, conf_sha)

    # section 0.3: exact run set
    expected = {pre + s: s for s in RUNS}
    if not os.path.isdir(args.runs_dir):
        die(f"runs dir {args.runs_dir} not found")
    present = {n for n in os.listdir(args.runs_dir) if n.startswith(pre)}
    extra, missing = sorted(present - set(expected)), sorted(set(expected) - present)
    if extra:
        die(f"unregistered {pre}* entries (an unregistered look): {extra}")
    if missing:
        die(f"missing registered runs: {missing}")
    for n in expected:
        if not os.path.isdir(os.path.join(args.runs_dir, n)):
            die(f"{n} is not a directory")

    items = jsonl(args.items)
    if any(it.get("label_source") != "human" for it in items):
        die("confirm.jsonl has non-human label_source items")
    ids = {it["item_id"] for it in items}
    if len(ids) != len(items):
        die("duplicate item_id in confirm.jsonl")
    kinds = {it["item_id"]: (it["group"], it["kind"]) for it in items}

    runs, rows, plats = {}, {}, {}
    for suffix in RUNS:
        run, rs, plat = load_run(os.path.join(args.runs_dir, pre + suffix), suffix, pre, conf_sha)
        got = [r.get("item_id") for r in rs]
        if len(got) != len(set(got)) or set(got) != ids:
            die(f"{pre + suffix}: results.jsonl item set differs from confirm.jsonl")
        if any((r["group"], r["kind"]) != kinds[r["item_id"]] for r in rs):
            die(f"{pre + suffix}: group/kind in results differ from confirm.jsonl")
        runs[suffix], rows[suffix], plats[suffix] = run, sorted(rs, key=lambda r: r["item_id"]), plat
    if len(set(plats.values())) != 1:
        die(f"runs do not share one env.platform: {sorted(set(plats.values()))}")
    platform_ = next(iter(plats.values()))

    # metrics
    cells = []
    for g in GROUPS:
        for k in ["unfinished", "completed"]:
            cells.append({"group": g, "kind": k, "n": sum(1 for v in kinds.values() if v == (g, k))})
    c5 = all(c["n"] >= MIN_CELL for c in cells)
    arms = {}
    for suffix, spec in RUNS.items():
        arms[spec[0]] = {"run_id": pre + suffix, "role": spec[6], "family": spec[5],
                         "metrics": arm_metrics(rows[suffix], runs[suffix]["config"]["vad_stop_s"])}
    mS = arms["S"]["metrics"]
    cx = criteria(arms["X"]["metrics"], mS)
    cf = {RUNS[s][0]: criteria(arms[RUNS[s][0]]["metrics"], mS) for s in FARMS}
    cr = {}
    for s in REPORT_ONLY:
        a = RUNS[s][0]
        base = "S-clip" if RUNS[s][5] == "clip_start" else "S"
        if a != "S-clip":
            cr[a] = criteria(arms[a]["metrics"], arms[base]["metrics"])
    if not c5:
        outcome = "confirm_insufficient"
    elif cx["criteria_1_to_4_all_hold"]:
        outcome = "confirm_pass_feasibility"
    else:
        outcome = "confirm_fail"
    dec = {
        "spec": "benchmark/specs/confirm-eval-v1.md", "outcome": outcome, "criterion_5_met": c5, "cells": cells,
        "criteria_X_vs_S": cx, "criteria_F_vs_S": cf, "criteria_report_only_vs_baseline": cr,
        "paired_X_vs_S": paired(rows[CAND], rows[BASELINE]), "arms": arms,
        "wording": WORDING, "limits": LIMITS,
        "inputs": {"confirm_jsonl_sha256": conf_sha, "adjudicated_csv_sha256": adj_sha,
                   "env_platform": platform_, "decision_log_source": log_src,
                   "run_ids": sorted(expected),
                   "run_config_sha256": {pre + s: runs[s].get("config_sha256") for s in sorted(RUNS)}},
    }
    md = render_md(dec)
    os.makedirs(args.out, exist_ok=True)
    try:
        with open(jp, "x", encoding="utf-8") as f:
            json.dump(dec, f, indent=1, sort_keys=True)
            f.write("\n")
        with open(mp, "x", encoding="utf-8") as f:
            f.write(md + "\n")
    except FileExistsError:
        die("output appeared meanwhile; not overwriting")
    print(f"outcome: {outcome}")
    print(f"wrote {jp} and {mp}")


if __name__ == "__main__":
    main()
