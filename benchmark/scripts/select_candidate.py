"""Candidate selection on dev, v1 (benchmark/specs/selection-v1.md; implements model/specs/training-v1.md section 6).

Runs arms A, B, C, D, E, F (and G with --vad-model) through eval_runner.py, computes M1-M5 + M4b, applies the
pre-registered constraints/rule, and writes benchmark/selection/<out-id>/{decision.json,decision.md}.
Development decision only; the efficacy claim comes from the single test run in training-v1 section 7.2.

  python benchmark/scripts/select_candidate.py --out-id X --platform-note "..." --stock-int8 P --stock-fp32 P \
     --prescreen prescreen.json --train-manifest manifest.json --candidate C.onnx [--candidate ...] \
     --guard stock-fp32=G0.json --guard <model_id>=G1.json [--vad-model P --vad-sha256 H] [--stock-only]
  python benchmark/scripts/select_candidate.py --selftest
"""
import argparse, csv, json, math, os, subprocess, sys, time
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
BENCH = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from eval_runner import wilson, sha256_file, git  # noqa: E402

RUNNER = os.path.join(HERE, "eval_runner.py")
RUNS = os.path.join(BENCH, "runs")
SELDIR = os.path.join(BENCH, "selection")
CFG_DIR = os.path.join(BENCH, "configs")
ITEMS_DIR = os.path.join(BENCH, "items", "v1")
PIN_INT8 = "2bb026316b14a660486a75b1733cd3fbab8c2fd0314dc9af7be49f8cca967e4f"
PIN_FP32 = "ab8dc64b88713f90b571c15b714bd1330e6c883cad8763dacf65c9376dc539be"
CFG_MAIN = "agent-v0.1-single-checks.json"
CFG_TURN = "agent-v0.1-turn-checks.json"
CFG_PATIENT = [("04", "agent-v0.1-patient-04-checks.json"), ("06", "agent-v0.1-patient-06-checks.json"),
               ("08", "agent-v0.1-patient-08-checks.json")]
C_THRESHOLDS = [round(0.50 + 0.01 * i, 2) for i in range(50)]
E_THRESHOLDS = [0.40, 0.50, 0.60]
TOL = 1e-9
# (direction, bound) on the point-estimate difference arm - B
CONSTRAINTS = {"M2": ("max", 0.010), "M3": ("min", -0.020), "M4": ("min", -0.010),
               "M4b": ("min", -0.010), "M5": ("min", 0.0)}
METRICS = ["M1", "M2", "M3", "M4", "M4b", "M5"]
OPENING = ("Development decision, not a publishable efficacy result. The candidate was ranked and selected on "
           "these dev items (pre-screen on M1, then up to 6 operating points); the claim comes only from the "
           "single test run in training-v1 §7.2.")
ARGS_SPEC = "v1"  # set from --training-spec in main()
LIMITS = [
    "Labels are energy-derived (energy_vad), not human-confirmed.",
    "End-of-window items are proxies for completed turns.",
    "The guard set is not perfectly independent of the upstream checkpoint choice.",
    "There are no stuttered completed turns in items/v1, so the stuttered counterpart of M3 cannot be measured.",
    "Shortcut-learning risk (training-v1 §10): the model may learn that a stutter-like voice means an incomplete "
    "turn and wait too long on completed stuttered turns; state this risk in every claim.",
    "On about 1.5k guard negatives, one flipped row decides the sign of ΔM5 (constraint ΔM5 ≥ 0).",
]
# training-v2 (model/specs/training-v2.md §0, §10): replaces the stuttered-M3 line and adds the disclosure.
LIMITS_V2 = [x for x in LIMITS if not x.startswith("There are no stuttered completed turns")] + [
    "Stuttered completed turns are energy proxies only (in-loop M3s), not human-confirmed.",
    "Training-v2 positives and the M3 items share one end-of-window proxy definition; agreeing with M3 means "
    "agreeing with the proxy, not answering real turn ends.",
    "Disclosure: training v2 was designed after v1 failed (dev_nothing_passes) on these same dev items; dev has "
    "served two pre-registered attempts. Test stays sealed; only the training-v1 §7.2 single test run is evidence.",
]
# training-v3 (model/specs/training-v3.md §0): three attempts; test sealed under D-009.
LIMITS_V3 = [x for x in LIMITS_V2 if not x.startswith("Disclosure: training v2")] + [
    "Disclosure: training v3 was designed after v1 and v2 both failed (dev_nothing_passes) on these same dev "
    "items; dev has served three pre-registered attempts. The test set stays sealed under D-009; a v3 pass is a "
    "development decision only and does not authorize a test run.",
]
# proposed v4 (issue #2 comment 6103360382): weight interpolation of stock and the W3 prescreen top 2.
LIMITS_V4 = [x for x in LIMITS_V3 if not x.startswith("Disclosure: training v3")] + [
    "Disclosure: v4 (weight interpolation of stock FP32 and the W3 prescreen top 2, no new training) was designed "
    "after v1, v2 and v3 all failed (dev_nothing_passes) on these same dev items; dev has served four "
    "pre-registered attempts. The test set stays sealed under D-009; a v4 pass is a development decision only "
    "and does not authorize a test run.",
    "Candidate 'epoch' is the blend's relative L2 weight distance from stock (‖θ − θ_stock‖ / ‖θ_stock‖); "
    "'ties -> earlier' prefers the blend closest to stock.",
]
LIMITS_BY_SPEC = {"v1": LIMITS, "v2": LIMITS_V2, "v3": LIMITS_V3, "v4": LIMITS_V4}


def die(msg):
    print("REFUSED: " + msg, file=sys.stderr)
    sys.exit(2)


# ======================================================================== pure statistics / rule
def mcnemar_p(b, c):
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1))
    return min(1.0, 2 * tail / 2 ** n)


def counts(ev):
    return sum(1 for v in ev.values() if v), len(ev)


def pair_counts(ev_base, ev_arm):
    """b = true under base and false under arm; c = the reverse."""
    if set(ev_base) != set(ev_arm):
        die("paired comparison on different item sets")
    b = sum(1 for i, v in ev_base.items() if v and not ev_arm[i])
    c = sum(1 for i, v in ev_base.items() if (not v) and ev_arm[i])
    return b, c, len(ev_base)


def wald_paired(b, c, n):
    d = (c - b) / n
    se = math.sqrt(max(0.0, b + c - (b - c) ** 2 / n)) / n
    return d, [round(d - 1.96 * se, 4), round(d + 1.96 * se, 4)]


def rate(ev):
    k, n = counts(ev)
    return k / n if n else None


def metric_entry(ev, base_ev=None):
    k, n = counts(ev)
    e = {"k": k, "n": n, "rate": None if not n else round(k / n, 6), "wilson95": wilson(k, n)}
    if base_ev is not None:
        b, c, nn = pair_counts(base_ev, ev)
        d, ci = wald_paired(b, c, nn)
        e.update(vs_B={"b_true_under_B_false_under_arm": b, "c_false_under_B_true_under_arm": c,
                       "delta": round(d, 6), "wald_paired95": ci, "mcnemar_p": mcnemar_p(b, c)})
    return e


def deltas(row, base):
    """Point-estimate differences arm - B for every metric both have."""
    out = {}
    for m in METRICS:
        if m in row["ev"] and m in base["ev"]:
            out[m] = rate(row["ev"][m]) - rate(base["ev"][m])
    return out


def constraint_flags(row, base):
    d = deltas(row, base)
    flags = {}
    for m, (kind, bound) in CONSTRAINTS.items():
        if m not in d:
            flags[m] = None
        elif kind == "max":
            flags[m] = d[m] <= bound + TOL
        else:
            flags[m] = d[m] >= bound - TOL
    flags["all"] = all(v is True for v in flags.values())
    return flags


def m1k(row):
    return counts(row["ev"]["M1"])[0]


def sel_key(r):
    ep = r["epoch"] if r.get("epoch") is not None else float("inf")
    return (m1k(r), ep, r["top2_pos"], abs(r["threshold"] - 0.5), r["threshold"], r["arm"])


def comp_key(r):
    return (m1k(r), abs(r["threshold"] - 0.5), r["threshold"])


def choose(base, cand_rows, c_rows):
    """training-v1 section 6 rule. Rows: {arm, threshold, epoch, top2_pos, ev:{metric:{item:bool}}}.
    Annotates each row with row['flags']. Returns the decision dict (without test_plan)."""
    for r in list(cand_rows) + list(c_rows):
        r["flags"] = constraint_flags(r, base)
    ok = [r for r in cand_rows if r["flags"]["all"]]
    sel = min(ok, key=sel_key) if ok else None
    cok = [r for r in c_rows if r["flags"]["all"]]
    # C includes threshold 0.50, which is B itself with every delta = 0, so a comparator always exists
    # and training-v1 section 6's matched-M3/M4 fallback can never trigger.
    if not cok:
        raise RuntimeError("no arm-C row meets the constraints (arm C must include threshold 0.50 = B)")
    comp = min(cok, key=comp_key)
    below = m1k(comp) < m1k(base)
    res = {"selected": sel, "comparator": comp, "comparator_M1_below_B": below, "pair_sel_vs_comp": None}
    if sel is None:
        res["outcome"] = "dev_nothing_passes"
        return res
    b, c, n = pair_counts(comp["ev"]["M1"], sel["ev"]["M1"])
    if b - c != m1k(comp) - m1k(sel):
        raise RuntimeError("identity b - c = n*(M1_comp - M1_cand) violated")
    res["pair_sel_vs_comp"] = {"b_premature_under_comparator_not_candidate": b,
                               "c_premature_under_candidate_not_comparator": c, "n": n,
                               "mcnemar_p": mcnemar_p(b, c)}
    if m1k(sel) < m1k(comp) and b > c:
        res["outcome"] = "dev_candidate_passes"
    elif below:
        res["outcome"] = "dev_threshold_suffices"
    else:
        res["outcome"] = "dev_stock_suffices"
    return res


def guard_events(per_row, th):
    ev = {"M4": {}, "M4b": {}, "M5": {}}
    nulls = 0
    for r in per_row:
        if r["label"] == 1:
            ev["M4"][r["id"]] = r["p_full"] > th
            if r["p_cut"] is None:
                nulls += 1
            else:
                ev["M4b"][r["id"]] = r["p_cut"] > th
        else:
            ev["M5"][r["id"]] = r["p_full"] <= th
    return ev, nulls


# ======================================================================== input checks
def norm_parts(p):
    p = os.path.normcase(p).lower()
    drive, rest = os.path.splitdrive(p)
    return [x for x in rest.replace("\\", "/").split("/") if x]


def refuse_test_item_path(path):
    """Refuse an item path with any component or basename starting with 'test' (case-insensitive). Paths inside
    the repo are judged relative to benchmark/ (and, under benchmark/tests/, relative to that directory, so
    fixtures are allowed); paths elsewhere are judged on every component."""
    tests_dir = os.path.normcase(os.path.realpath(os.path.join(BENCH, "tests"))).lower()
    bench_dir = os.path.normcase(os.path.realpath(BENCH)).lower()
    for cand in {os.path.abspath(path), os.path.realpath(path)}:
        n = os.path.normcase(cand).lower()
        if n.startswith(tests_dir + os.sep):
            parts = norm_parts(n[len(tests_dir) + 1:])
        elif n.startswith(bench_dir + os.sep):
            parts = norm_parts(n[len(bench_dir) + 1:])
        else:
            parts = norm_parts(n)
        bad = [x for x in parts if x.startswith("test")]
        if bad:
            die(f"item path {path!r} has component {bad[0]!r} starting with 'test' (test items are never used here)")


def load_json(path, what):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        die(f"cannot read {what} {path}: {e}")


def check_items(args, manifest):
    scratch_override = args.items_main or args.items_eow
    if scratch_override and not args.scratch:
        die("--items-main/--items-eow are only allowed with --scratch")
    if bool(args.items_main) != bool(args.items_eow):
        die("give both --items-main and --items-eow, or neither")
    main = args.items_main or os.path.join(ITEMS_DIR, "dev.jsonl")
    eow = args.items_eow or os.path.join(ITEMS_DIR, "dev_end_of_window.jsonl")
    for p in (main, eow):
        refuse_test_item_path(p)
        if not os.path.isfile(p):
            die(f"item file missing: {p}")
    sm, se = sha256_file(main), sha256_file(eow)
    man = load_json(os.path.join(ITEMS_DIR, "manifest.json"), "items manifest")["output_sha256"]
    if sm in (man.get("test.jsonl"), man.get("test_end_of_window.jsonl")) or \
            se in (man.get("test.jsonl"), man.get("test_end_of_window.jsonl")):
        die("item file content equals a test item file")
    if not scratch_override:
        if sm != man["dev.jsonl"]:
            die(f"dev.jsonl sha256 {sm} != manifest {man['dev.jsonl']}")
        if se != man["dev_end_of_window.jsonl"]:
            die(f"dev_end_of_window.jsonl sha256 {se} != manifest {man['dev_end_of_window.jsonl']}")
    return main, eow, sm, se


def check_stock(args):
    for p, pin, nm in ((args.stock_int8, PIN_INT8, "stock INT8"), (args.stock_fp32, PIN_FP32, "stock FP32")):
        if not os.path.isfile(p):
            die(f"{nm} model missing: {p}")
        h = sha256_file(p)
        if h != pin:
            die(f"{nm} sha256 {h} != pinned {pin}")


def check_candidates(args, prescreen):
    top2 = prescreen.get("top2")
    if not isinstance(top2, list) or len(set(top2)) != len(top2):
        die("prescreen top2 missing, not a list, or has duplicates")
    if len(args.candidate) != len(top2):
        die(f"{len(args.candidate)} --candidate given but prescreen top2 has {len(top2)}")
    cands, seen_ids = [], set()
    for path in args.candidate:
        if not os.path.isfile(path):
            die(f"candidate missing: {path}")
        meta_path = os.path.splitext(path)[0] + ".json"
        if not os.path.isfile(meta_path):
            die(f"candidate metadata missing: {meta_path}")
        meta = load_json(meta_path, "candidate metadata")
        h = sha256_file(path)
        if h != str(meta.get("sha256", "")).lower():
            die(f"{path}: file sha256 {h} != metadata sha256 {meta.get('sha256')}")
        if meta.get("status") != "dev-candidate":
            die(f"{path}: metadata status {meta.get('status')!r} != 'dev-candidate'")
        if meta.get("threshold") != 0.5:
            die(f"{path}: metadata threshold {meta.get('threshold')!r} != 0.5")
        prov = meta.get("provenance") or {}
        if not prov.get("run_id") or not prov.get("checkpoint"):
            die(f"{path}: metadata provenance lacks run_id/checkpoint")
        cid = f"{prov['run_id']}/{prov['checkpoint']}"
        mid = meta.get("model_id")
        if not mid or mid == "stock-fp32":
            die(f"{path}: bad metadata model_id {mid!r}")
        if cid in seen_ids or mid in {c["model_id"] for c in cands}:
            die(f"duplicate candidate {cid} / {mid}")
        seen_ids.add(cid)
        cands.append({"path": os.path.abspath(path), "sha256": h, "cand_id": cid, "model_id": mid,
                      "epoch": prov.get("epoch"), "meta_path": os.path.abspath(meta_path)})
    if seen_ids != set(top2):
        die(f"candidate ids {sorted(seen_ids)} != prescreen top2 {sorted(top2)}")
    for c in cands:
        c["top2_pos"] = top2.index(c["cand_id"])
    cands.sort(key=lambda c: c["top2_pos"])
    return cands, top2


def check_guards(args, cands, manifest):
    try:
        n_expected = manifest["guard"]["n"]
    except Exception:
        die("train manifest lacks guard.n")
    want = {"stock-fp32": PIN_FP32}
    for c in cands:
        want[c["model_id"]] = c["sha256"]
    given = {}
    for g in args.guard:
        if "=" not in g:
            die(f"--guard must be KEY=PATH, got {g!r}")
        k, p = g.split("=", 1)
        if k in given:
            die(f"duplicate --guard key {k}")
        given[k] = p
    if args.stock_only:
        want = {"stock-fp32": PIN_FP32}
        given = {k: v for k, v in given.items() if k == "stock-fp32"}
    if set(given) != set(want):
        die(f"--guard keys {sorted(given)} != required {sorted(want)}")
    data, shas = {}, {}
    for k, p in given.items():
        g = load_json(p, "guard JSON")
        shas[k] = sha256_file(p)
        if g.get("model_sha256") != want[k]:
            die(f"guard {k}: model_sha256 {g.get('model_sha256')} != {want[k]}")
        pr = g.get("per_row")
        if not isinstance(pr, list) or g.get("n") != n_expected or len(pr) != n_expected:
            die(f"guard {k}: n={g.get('n')}, rows={len(pr) if isinstance(pr, list) else None}, "
                f"manifest guard n={n_expected}")
        for r in pr:
            if not all(f in r for f in ("id", "label", "p_full", "p_cut")):
                die(f"guard {k}: row lacks id/label/p_full/p_cut")
        data[k] = g
    ref_k = "stock-fp32"
    ref = data[ref_k]["per_row"]
    ids = [r["id"] for r in ref]
    if len(set(ids)) != len(ids):
        die("stock guard has duplicate ids")
    lab = {r["id"]: r["label"] for r in ref}
    nul = {r["id"] for r in ref if r["p_cut"] is None}
    for k, g in data.items():
        if {r["id"] for r in g["per_row"]} != set(ids) or len(g["per_row"]) != len(ids):
            die(f"guard {k}: id set differs from stock guard")
        if {r["id"]: r["label"] for r in g["per_row"]} != lab:
            die(f"guard {k}: labels differ from stock guard")
        if {r["id"] for r in g["per_row"] if r["p_cut"] is None} != nul:
            die(f"guard {k}: set of null-p_cut rows differs from stock guard")
        if any(r["label"] == 0 and r["p_cut"] is not None for r in g["per_row"]):
            die(f"guard {k}: a negative has non-null p_cut")
        ev, _ = guard_events(g["per_row"], 0.5)
        for m, key in (("M4", "M4_recall_full"), ("M5", "M5_specificity_full")):
            rec = rate(ev[m])
            if rec is None or abs(rec - g[key]) > 5e-5 + 1e-9:
                die(f"guard {k}: recomputed {m}={rec} at 0.5 != file {key}={g.get(key)}")
        if not ev["M4b"]:
            die(f"guard {k}: no positives with p_cut (M4b undefined)")
    return data, shas, n_expected


# ======================================================================== runs
class Ctx:
    pass


def run_dir(rid):
    return os.path.join(RUNS, rid)


def rid_for(ctx, arm, which, th=None):
    s = f"{ctx.out_id}-{arm}-{which}"
    return s + (f"-th{th:.2f}" if th is not None else "")


def plan_run(ctx, arm, which, kind, **kw):
    spec = {"arm": arm, "which": which, "kind": kind, "id": kw.pop("id"), **kw}
    ctx.plan.append(spec)
    return spec["id"]


def plan_arm_infer(ctx, arm, model_path, model_sha, model_id, cfg, stock, vad=False, final_th=None):
    ids = {}
    for which, items, isha in (("main", ctx.items_main, ctx.sha_main), ("eow", ctx.items_eow, ctx.sha_eow)):
        ids[which] = plan_run(ctx, arm, which, "infer", id=rid_for(ctx, arm, which), model=model_path,
                              model_sha=model_sha, model_id=model_id, cfg=cfg, items=items, items_sha=isha,
                              stock=stock, vad=vad, threshold=0.5)
    return ids


def plan_arm_rescore(ctx, arm, base_ids, cfg, th, stock, vad=False):
    ids = {}
    for which in ("main", "eow"):
        base = next(s for s in ctx.plan if s["id"] == base_ids[which])
        ids[which] = plan_run(ctx, arm, which, "rescore", id=rid_for(ctx, arm, which, th), base=base_ids[which],
                              model_sha=base["model_sha"], model_id=base["model_id"], cfg=cfg,
                              items_sha=base["items_sha"], stock=stock, vad=vad, threshold=th)
    return ids


def validate_existing(ctx, spec):
    """An existing run dir is reusable only if it is exactly the planned run."""
    d = run_dir(spec["id"])
    try:
        run = json.load(open(os.path.join(d, "run.json")))
        open(os.path.join(d, "results.jsonl")).close()
    except Exception as e:
        die(f"existing run dir {d} unreadable ({e})")
    cfg = json.load(open(os.path.join(CFG_DIR, spec["cfg"])))
    ok = (run.get("model_sha256") == spec["model_sha"] and run.get("items_sha256") == spec["items_sha"]
          and run["config"].get("config_id") == cfg["config_id"]
          and abs(run["config"]["threshold"] - spec["threshold"]) < 1e-9
          and (spec["kind"] == "infer") == ("rescored_from" not in run)
          and (spec["kind"] == "infer" or run.get("rescored_from") == spec["base"])
          and (run.get("vad_model_sha256") == ctx.vad_sha if spec["vad"] else True))
    if not ok:
        die(f"existing run dir {d} does not match the planned run (model/items/config/threshold/base)")


def execute(ctx, spec):
    d = run_dir(spec["id"])
    if spec.get("reuse"):
        ctx.reused.append(spec["id"])
        return
    cfg = os.path.join(CFG_DIR, spec["cfg"])
    if spec["kind"] == "infer":
        cmd = [sys.executable, RUNNER, "--model", spec["model"], "--model-id", spec["model_id"],
               "--expected-sha256", spec["model_sha"], "--items", spec["items"], "--config", cfg,
               "--run-id", spec["id"]]
        if spec["vad"]:
            cmd += ["--vad-model", ctx.vad_model, "--vad-sha256", ctx.vad_sha]
    else:
        cmd = [sys.executable, RUNNER, "--rescore", run_dir(spec["base"]), "--config", cfg,
               "--threshold", f"{spec['threshold']:.2f}", "--run-id", spec["id"]]
    if ctx.scratch:
        cmd.append("--scratch")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout[-2000:], file=sys.stderr)
        print(r.stderr[-3000:], file=sys.stderr)
        die(f"runner failed for {spec['id']} (exit {r.returncode})")
    run = json.load(open(os.path.join(d, "run.json")))
    ctx.executed.append(spec["id"])
    ctx.model_calls += run.get("model_calls", 0)
    print(f"  ran {spec['id']} (model_calls={run.get('model_calls')})", flush=True)


def load_pair(ctx, ids):
    """Events from a main/eow run pair: M1 (stuttered unfinished), M2 (fluent unfinished), M3 (fluent completed
    end-of-window, model trigger; censored rows stay in the denominator)."""
    runs = {}
    for which in ("main", "eow"):
        d = run_dir(ids[which])
        runs[which] = (json.load(open(os.path.join(d, "run.json"))),
                       [json.loads(l) for l in open(os.path.join(d, "results.jsonl")) if l.strip()])
        ctx.platforms.add(runs[which][0]["env"]["platform"])
    main_rows, eow_rows = runs["main"][1], runs["eow"][1]
    ev = {"M1": {r["item_id"]: bool(r["premature"]) for r in main_rows
                 if r["group"] == "stuttered" and r["kind"] == "unfinished"},
          "M2": {r["item_id"]: bool(r["premature"]) for r in main_rows
                 if r["group"] == "fluent" and r["kind"] == "unfinished"},
          "M3": {r["item_id"]: r["trigger"] == "model" for r in eow_rows
                 if r["group"] == "fluent" and r["kind"] == "completed"}}
    for m in ("M1", "M2", "M3"):
        if not ev[m]:
            die(f"run {ids['main']}/{ids['eow']}: no rows for {m}")
    for r in main_rows:
        ctx.clip_of[r["item_id"]] = r["clip_key"]
    return ev


# ======================================================================== reporting helpers
def fmt_pct(x):
    return "n/a" if x is None else f"{100 * x:.1f}%"


def build_row(ctx, arm, label, th, ids, guard, epoch=None, pos=0, model_id=None, extra=None):
    ev = load_pair(ctx, ids)
    nulls = None
    if guard is not None:
        gev, nulls = guard_events(guard["per_row"], th)
        ev.update(gev)
    row = {"arm": arm, "label": label, "model_id": model_id, "threshold": th, "epoch": epoch, "top2_pos": pos,
           "run_ids": dict(ids), "ev": ev, "M4b_null_p_cut_excluded": nulls}
    row.update(extra or {})
    return row


def table_entries(row, base):
    out = {}
    for m in METRICS:
        if m in row["ev"]:
            out[m] = metric_entry(row["ev"][m], base["ev"][m] if (base is not None and m in base["ev"]) else None)
    return out


def serial_row(row, base):
    d = {k: v for k, v in row.items() if k not in ("ev",)}
    d["metrics"] = table_entries(row, base)
    return d


def per_show(ctx, row):
    out = {}
    for iid, v in row["ev"]["M1"].items():
        show = ctx.show_of.get(ctx.clip_of.get(iid), "unknown")
        k, n = out.get(show, (0, 0))
        out[show] = (k + int(v), n + 1)
    return {s: {"k": k, "n": n, "rate": round(k / n, 4), "wilson95": wilson(k, n)} for s, (k, n) in sorted(out.items())}


def md_table(header, rows):
    s = "| " + " | ".join(header) + " |\n|" + "|".join("---" for _ in header) + "|\n"
    return s + "".join("| " + " | ".join(str(c) for c in r) + " |\n" for r in rows)


def cell(row_s, m):
    e = row_s["metrics"].get(m)
    if not e or not e["n"]:
        return "n/a"
    lo, hi = e["wilson95"]
    return f"{100 * e['rate']:.1f}% ({e['k']}/{e['n']}; {100 * lo:.1f}-{100 * hi:.1f})"


def delta_cell(row_s, m):
    e = row_s["metrics"].get(m)
    if not e or "vs_B" not in e:
        return "n/a"
    v = e["vs_B"]
    lo, hi = v["wald_paired95"]
    return (f"{100 * v['delta']:+.2f} pt; Wald (paired) {100 * lo:+.2f} to {100 * hi:+.2f}; "
            f"(b,c)=({v['b_true_under_B_false_under_arm']},{v['c_false_under_B_true_under_arm']}); "
            f"McNemar p={v['mcnemar_p']:.3g}")


def row_name(r):
    return f"{r['arm']} {r['label']} @{r['threshold']:.2f}"


def make_test_plan(sel_row, comp_row, cands_by_id, outcome):
    plan = {"comparator": {"arm": "C", "threshold": comp_row["threshold"],
                           "note": "rescore stock FP32 on test at this threshold"},
            "arms_to_run": ["A stock INT8 @0.5", "B stock FP32 @0.5",
                            f"C stock FP32 rescored @{comp_row['threshold']:.2f}"]}
    if sel_row is None:
        plan["selected_candidate"] = None
        plan["note"] = "no candidate met every constraint; no candidate to run on test"
        return plan
    c = cands_by_id[sel_row["model_id"]]
    plan["selected_candidate"] = {"file": c["path"], "model_id": c["model_id"], "cand_id": c["cand_id"],
                                  "sha256": c["sha256"], "threshold": sel_row["threshold"],
                                  "dev_outcome": outcome}
    plan["arms_to_run"].append(f"{c['model_id']} @{sel_row['threshold']:.2f}")
    if abs(sel_row["threshold"] - 0.5) > 1e-9:
        plan["section_7_1_requirement"] = (
            f"Selected threshold is {sel_row['threshold']:.2f}, not 0.5: training-v1 §7.1 must set the selected "
            f"export's metadata `threshold` to {sel_row['threshold']:.2f} (the agent reads it; export.py writes 0.5).")
    return plan


def render_md(ctx, dec, rows_s, base_s, comp_s, sel_s, a_s, report_only, shows):
    L = [OPENING, "", f"Outcome: **{dec['outcome']}**" + (f" (comparator_M1_below_B = {dec['comparator_M1_below_B']})"
         if dec["outcome"] == "dev_nothing_passes" else ""), ""]
    L.append(f"Out-id `{ctx.out_id}`; platform note: {ctx.platform_note}; runner platform: {sorted(ctx.platforms)}; "
             f"code commit {dec['inputs']['code_commit']}.\n")
    L.append("## Summary (B, comparator, selected candidate, A)\n")
    hdr = ["Row", "M1 stutter premature", "M2 fluent premature", "M3 eow model-decided", "M4 recall", "M4b recall",
           "M5 specificity"]
    trs = []
    for nm, r in (("B", base_s), ("comparator", comp_s), ("selected", sel_s), ("A", a_s)):
        if r is None:
            trs.append([nm, "none selected"] + [""] * 5)
        else:
            trs.append([f"{nm}: {row_name(r)}"] + [cell(r, m) for m in METRICS])
    L.append(md_table(hdr, trs))
    L.append("Cells: rate (k/n; Wilson 95% CI in points). Guard metrics are not computed for A.\n")
    L.append("## Constraint deltas vs B (point estimates bind; CIs and p-values are reported only)\n")
    for nm, r in (("comparator", comp_s), ("selected", sel_s)):
        if r is None:
            continue
        L.append(f"**{nm}: {row_name(r)}** (all constraints met: {r['flags']['all']})\n")
        L.append(md_table(["Metric", "Delta vs B", "Constraint", "Met"],
                          [[m, delta_cell(r, m),
                           {"M1": "none (ranked)", "M2": "<= +1.0 pt", "M3": ">= -2.0 pt", "M4": ">= -1.0 pt",
                            "M4b": ">= -1.0 pt", "M5": ">= 0"}[m], r["flags"].get(m, "-")] for m in METRICS]))
    L.append("Note: on about 1.5k guard negatives, one flipped row decides ΔM5.\n")
    L.append("## Outcome\n")
    ps = dec.get("pair_sel_vs_comp")
    if ps:
        L.append(f"Selected vs comparator on M1: b (premature under comparator, not candidate) = "
                 f"{ps['b_premature_under_comparator_not_candidate']}, c = {ps['c_premature_under_candidate_not_comparator']}, "
                 f"n = {ps['n']}, McNemar p = {ps['mcnemar_p']:.3g}. The b > c clause is implied by the M1 comparison "
                 f"(b - c = n * (M1_comp - M1_cand) exactly); it is not a significance test.\n")
    L.append(f"{dec['outcome']}: selected = {row_name(ctx.sel_raw) if ctx.sel_raw else 'none'}; "
             f"comparator = {row_name(ctx.comp_raw)}; comparator_M1_below_B = {dec['comparator_M1_below_B']}.\n")
    L.append("## Per-show M1 (stuttered, unfinished)\n")
    names = sorted({s for r in (base_s, comp_s, sel_s, a_s) if r for s in r["per_show_M1"]})
    trs = []
    for nm, r in (("B", base_s), ("comparator", comp_s), ("selected", sel_s), ("A", a_s)):
        if r is None:
            continue
        trs.append([f"{nm}: {row_name(r)}"] + [
            (lambda e: f"{100 * e['rate']:.1f}% ({e['k']}/{e['n']})")(r["per_show_M1"][s]) if s in r["per_show_M1"] else "n/a"
            for s in names])
    L.append(md_table(["Row"] + names, trs))
    L.append("## Report-only arms (F patient waits, G turn-onset input)\n")
    if report_only:
        L.append(md_table(["Arm", "M1", "M2", "M3", "Delta M1 vs B", "Delta M2 vs B", "Delta M3 vs B"],
                          [[r["arm"] + " " + r["label"]] + [cell(r, m) for m in ("M1", "M2", "M3")] +
                           [delta_cell(r, m) for m in ("M1", "M2", "M3")] for r in report_only]))
        L.append("F compares across different config_ids (use compare_runs --allow-config-diff for the same pairs).\n")
    else:
        L.append("none\n")
    if ctx.vad_model is None:
        L.append("Arm G not run: no --vad-model given.\n")
    L.append("## Test plan (training-v1 §7.2)\n")
    L.append("```json\n" + json.dumps(dec["test_plan"], indent=1) + "\n```\n")
    L.append("## Limits\n")
    L += [f"- {x}" for x in LIMITS_BY_SPEC[ARGS_SPEC]]
    L.append("")
    return "\n".join(L)


# ======================================================================== main
def build_parser():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out-id")
    ap.add_argument("--platform-note")
    ap.add_argument("--stock-int8")
    ap.add_argument("--stock-fp32")
    ap.add_argument("--prescreen")
    ap.add_argument("--train-manifest")
    ap.add_argument("--candidate", action="append", default=[])
    ap.add_argument("--guard", action="append", default=[], help="KEY=PATH; keys: stock-fp32 and candidate model_ids")
    ap.add_argument("--vad-model")
    ap.add_argument("--vad-sha256")
    ap.add_argument("--stock-only", action="store_true")
    ap.add_argument("--scratch", action="store_true")
    ap.add_argument("--items-main")
    ap.add_argument("--items-eow")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--training-spec", choices=["v1", "v2", "v3", "v4"], default="v1",
                    help="which training spec's limits/disclosure text to write")
    return ap


def main():
    t_start = time.time()
    ap = build_parser()
    args = ap.parse_args()
    global ARGS_SPEC
    ARGS_SPEC = args.training_spec
    if args.selftest:
        return selftest()
    for k in ("out_id", "platform_note", "stock_int8", "stock_fp32", "train_manifest"):
        if not getattr(args, k):
            ap.error(f"--{k.replace('_', '-')} is required")
    if not args.stock_only and not args.prescreen:
        ap.error("--prescreen is required (unless --stock-only)")
    if bool(args.vad_model) != bool(args.vad_sha256):
        ap.error("--vad-model and --vad-sha256 go together")
    if not all(ch.isalnum() or ch in "-_." for ch in args.out_id):
        die("out-id may contain only letters, digits, - _ .")

    ctx = Ctx()
    ctx.scratch = args.scratch
    ctx.out_id = ("scratch-" if args.scratch else "") + args.out_id
    ctx.platform_note = args.platform_note
    ctx.plan, ctx.executed, ctx.reused, ctx.model_calls, ctx.platforms = [], [], [], 0, set()
    ctx.clip_of = {}
    ctx.vad_model, ctx.vad_sha = args.vad_model, (args.vad_sha256.lower() if args.vad_sha256 else None)

    # ---------------- input checks (all before any inference)
    out_dir = os.path.join(SELDIR, ctx.out_id)
    stage_path = os.path.join(out_dir, "stock_stage.json")
    resume = False
    if os.path.exists(out_dir):
        if args.stock_only or not os.path.isfile(stage_path) or os.path.exists(os.path.join(out_dir, "decision.json")):
            die(f"selection dir exists: {out_dir}")
        resume = True
    check_stock(args)
    if ctx.vad_model:
        if not os.path.isfile(ctx.vad_model) or sha256_file(ctx.vad_model) != ctx.vad_sha:
            die("--vad-model missing or sha256 mismatch")
    manifest = load_json(args.train_manifest, "train manifest")
    ctx.items_main, ctx.items_eow, ctx.sha_main, ctx.sha_eow = check_items(args, manifest)
    if args.stock_only:
        cands, top2, prescreen_sha = [], [], None
        if args.candidate or args.prescreen:
            print("note: --stock-only ignores --candidate/--prescreen")
    else:
        prescreen = load_json(args.prescreen, "prescreen")
        prescreen_sha = sha256_file(args.prescreen)
        cands, top2 = check_candidates(args, prescreen)
    guards, guard_shas, guard_n = check_guards(args, cands, manifest)
    if resume:
        st = load_json(stage_path, "stock stage")
        for k, v in (("items_main_sha256", ctx.sha_main), ("items_eow_sha256", ctx.sha_eow),
                     ("stock_guard_sha256", guard_shas["stock-fp32"]), ("platform_note", ctx.platform_note),
                     ("vad_model_sha256", ctx.vad_sha)):
            if st.get(k) != v:
                die(f"stock stage {k} differs from this invocation")
    ctx.show_of = {}
    with open(os.path.join(BENCH, "splits", "v1", "dev.csv"), newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            ctx.show_of[r["clip_key"]] = r["show"]

    # ---------------- plan
    fp32_stock_ids = {}
    A = plan_arm_infer(ctx, "A", args.stock_int8, PIN_INT8, "stock-int8", CFG_MAIN, True)
    B = plan_arm_infer(ctx, "B", args.stock_fp32, PIN_FP32, "stock-fp32", CFG_MAIN, True)
    Cids = {th: plan_arm_rescore(ctx, "C", {w: B[w] for w in B}, CFG_MAIN, th, True) for th in C_THRESHOLDS}
    Fids = {}
    for tag, cfgf in CFG_PATIENT:
        Fids[tag] = plan_arm_infer(ctx, f"F{tag}", args.stock_fp32, PIN_FP32, "stock-fp32", cfgf, True)
    G_B = plan_arm_infer(ctx, "G-B", args.stock_fp32, PIN_FP32, "stock-fp32", CFG_TURN, True, vad=True) \
        if ctx.vad_model else None
    stage1_len = len(ctx.plan)
    D, E = {}, {}
    for c in cands:
        i = c["top2_pos"] + 1
        D[c["model_id"]] = plan_arm_infer(ctx, f"D{i}", c["path"], c["sha256"], c["model_id"], CFG_MAIN, False)
        E[c["model_id"]] = {th: plan_arm_rescore(ctx, f"E{i}", D[c["model_id"]], CFG_MAIN, th, False)
                            for th in E_THRESHOLDS}
    # pre-existence check for every planned run (G candidate runs are added after selection and checked then)
    for s in ctx.plan:
        if os.path.exists(run_dir(s["id"])):
            if not resume:
                die(f"run directory already exists: {run_dir(s['id'])}")
            validate_existing(ctx, s)
            s["reuse"] = True

    # ---------------- inference
    os.makedirs(out_dir, exist_ok=True)
    print(f"selection {ctx.out_id}: {len(ctx.plan)} planned runs", flush=True)
    for s in ctx.plan[:stage1_len]:
        execute(ctx, s)
    stock_ids = [s["id"] for s in ctx.plan[:stage1_len]]
    stock_new = len(ctx.executed)
    if args.stock_only:
        if len(ctx.platforms) > 1:
            die(f"runs have differing env.platform: {sorted(ctx.platforms)}")
        base = build_row(ctx, "B", "stock-fp32", 0.5, B, guards["stock-fp32"], model_id="stock-fp32")
        stage = {"completed": True, "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                 "run_ids": stock_ids, "items_main_sha256": ctx.sha_main, "items_eow_sha256": ctx.sha_eow,
                 "stock_guard_sha256": guard_shas["stock-fp32"], "platform_note": ctx.platform_note,
                 "vad_model_sha256": ctx.vad_sha, "runner_platforms": sorted(ctx.platforms),
                 "model_calls_new": ctx.model_calls, "B_M1": metric_entry(base["ev"]["M1"]),
                 "B_M2": metric_entry(base["ev"]["M2"])}
        json.dump(stage, open(stage_path, "w"), indent=1)
        print(f"stock-only stage done: new runs {len(ctx.executed)}, model_calls {ctx.model_calls}, "
              f"wall {time.time() - t_start:.1f}s")
        return
    for s in ctx.plan[stage1_len:]:
        execute(ctx, s)

    # ---------------- metrics
    gS = guards["stock-fp32"]
    base = build_row(ctx, "B", "stock-fp32", 0.5, B, gS, model_id="stock-fp32")
    a_row = build_row(ctx, "A", "stock-int8", 0.5, A, None, model_id="stock-int8")
    c_rows = [build_row(ctx, "C", "stock-fp32", th, Cids[th], gS, model_id="stock-fp32") for th in C_THRESHOLDS]
    cand_rows = []
    for c in cands:
        gc = guards[c["model_id"]]
        i = c["top2_pos"] + 1
        cand_rows.append(build_row(ctx, f"D{i}", c["cand_id"], 0.5, D[c["model_id"]], gc, c["epoch"], c["top2_pos"],
                                   c["model_id"]))
        for th in E_THRESHOLDS:
            cand_rows.append(build_row(ctx, f"E{i}", c["cand_id"], th, E[c["model_id"]][th], gc, c["epoch"],
                                       c["top2_pos"], c["model_id"]))
    f_rows = [build_row(ctx, f"F{tag}", f"stock-fp32 vad_stop_s=0.{tag[1]}", 0.5, Fids[tag], None,
                        model_id="stock-fp32") for tag, _ in CFG_PATIENT]
    res = choose(base, cand_rows, c_rows)
    sel, comp, outcome = res["selected"], res["comparator"], res["outcome"]
    ctx.sel_raw, ctx.comp_raw = sel, comp

    # ---------------- arm G (report only)
    g_rows = []
    if ctx.vad_model:
        g_rows.append(build_row(ctx, "G-B", "stock-fp32 turn_onset", 0.5, G_B, None, model_id="stock-fp32"))
        if sel is not None:
            c = next(x for x in cands if x["model_id"] == sel["model_id"])
            i = c["top2_pos"] + 1
            gd = plan_arm_infer(ctx, f"G-D{i}", c["path"], c["sha256"], c["model_id"], CFG_TURN, False, vad=True)
            gid = gd
            gnew = [s for s in ctx.plan[-2:]]
            for s in gnew:
                if os.path.exists(run_dir(s["id"])):
                    if not resume:
                        die(f"run directory already exists: {run_dir(s['id'])}")
                    validate_existing(ctx, s)
                    s["reuse"] = True
                execute(ctx, s)
            if abs(sel["threshold"] - 0.5) > 1e-9:
                gid = plan_arm_rescore(ctx, f"G-D{i}", gd, CFG_TURN, sel["threshold"], False, vad=True)
                for s in ctx.plan[-2:]:
                    if os.path.exists(run_dir(s["id"])):
                        if not resume:
                            die(f"run directory already exists: {run_dir(s['id'])}")
                        validate_existing(ctx, s)
                        s["reuse"] = True
                    execute(ctx, s)
            g_rows.append(build_row(ctx, f"G-D{i}", c["cand_id"] + " turn_onset", sel["threshold"], gid, None,
                                    model_id=c["model_id"]))
    if len(ctx.platforms) != 1:
        die(f"runs have differing env.platform: {sorted(ctx.platforms)}")

    # ---------------- outputs
    cands_by_id = {c["model_id"]: c for c in cands}
    test_plan = make_test_plan(sel, comp, cands_by_id, outcome)
    all_rows = [a_row, base] + c_rows + cand_rows
    rows_s = [serial_row(r, None if r is base else base) for r in all_rows]
    for rs, r in zip(rows_s, all_rows):
        rs["flags"] = r.get("flags") or (constraint_flags(r, base) if r is not a_row and r is not base else None)
        rs["per_show_M1"] = per_show(ctx, r)
    ro_s = [serial_row(r, base) for r in f_rows + g_rows]
    by_key = {(r["arm"], r["threshold"], r["label"]): rs for r, rs in zip(all_rows, rows_s)}
    key = lambda r: None if r is None else by_key[(r["arm"], r["threshold"], r["label"])]
    base_s, a_s, comp_s, sel_s = key(base), key(a_row), key(comp), key(sel)
    dirty = git("status", "--porcelain")
    dec = {
        "outcome": outcome, "comparator_M1_below_B": res["comparator_M1_below_B"],
        "selected": None if sel is None else {k: v for k, v in sel_s.items() if k != "per_show_M1"},
        "comparator": {k: v for k, v in comp_s.items() if k != "per_show_M1"},
        "pair_sel_vs_comp": res["pair_sel_vs_comp"], "test_plan": test_plan,
        "inputs": {
            "out_id": ctx.out_id, "scratch": ctx.scratch, "platform_note": ctx.platform_note,
            "runner_platform": sorted(ctx.platforms)[0],
            "code_commit": git("rev-parse", "HEAD"), "code_dirty": bool(dirty) if dirty is not None else None,
            "stock_int8": {"path": os.path.abspath(args.stock_int8), "sha256": PIN_INT8},
            "stock_fp32": {"path": os.path.abspath(args.stock_fp32), "sha256": PIN_FP32},
            "candidates": cands, "prescreen_top2": top2, "prescreen_sha256": prescreen_sha,
            "items_main": {"path": ctx.items_main, "sha256": ctx.sha_main},
            "items_eow": {"path": ctx.items_eow, "sha256": ctx.sha_eow},
            "train_manifest_sha256": sha256_file(args.train_manifest), "guard_n": guard_n,
            "guard_sha256": guard_shas, "vad_model_sha256": ctx.vad_sha,
            "stock_stage_reused": resume,
        },
        "run_ids": {"executed": ctx.executed, "reused": ctx.reused, "all_planned": [s["id"] for s in ctx.plan]},
        "model_calls_new": ctx.model_calls,
        "metric_table": rows_s, "report_only": ro_s, "limits": LIMITS_BY_SPEC[ARGS_SPEC], "training_spec": ARGS_SPEC,
        "rule": "training-v1 section 6; point estimates bind; CIs/p-values reported only",
    }
    json.dump(dec, open(os.path.join(out_dir, "decision.json"), "w"), indent=1)
    md = render_md(ctx, dec, rows_s, base_s, comp_s, sel_s, a_s, ro_s, None)
    with open(os.path.join(out_dir, "decision.md"), "w", encoding="utf-8") as f:
        f.write(md)
    print(f"outcome: {outcome}; wrote {out_dir}")
    print(f"new runs {len(ctx.executed)} (stock-stage new {stock_new}), reused {len(ctx.reused)}, "
          f"model_calls {ctx.model_calls}, wall {time.time() - t_start:.1f}s")


# ======================================================================== self-test (no inference)
def _mk(arm, th, epoch, pos, m1, m2=None, m3=None, m4=None, m4b=None, m5=None, n_item=100, n_guard=200):
    """Synthetic row: each metric is a count k of true events out of a fixed n, events are the first k items."""
    def evs(k, n, tag):
        return {f"{tag}{i}": i < k for i in range(n)}
    dflt = dict(m2=10, m3=80, m4=180, m4b=150, m5=190)
    k2, k3, k4, k4b, k5 = [dflt[x] if v is None else v for x, v in
                           (("m2", m2), ("m3", m3), ("m4", m4), ("m4b", m4b), ("m5", m5))]
    d = {"M1": evs(m1, 100, "a"), "M2": evs(k2, 100, "b"), "M3": evs(k3, 100, "c"), "M4": evs(k4, 200, "d"),
         "M4b": evs(k4b, 200, "e"), "M5": evs(k5, 200, "f")}
    return {"arm": arm, "label": f"x{pos}", "model_id": f"m{pos}", "threshold": th, "epoch": epoch, "top2_pos": pos,
            "ev": d}


def selftest():
    n_ok = 0

    def check(cond, msg):
        nonlocal n_ok
        if not cond:
            print("SELFTEST FAIL:", msg)
            sys.exit(1)
        n_ok += 1
        print("  ok:", msg)

    base = _mk("B", 0.5, None, 0, 50)
    cs = [_mk("C", 0.5, None, 0, 50)]
    cs[0]["threshold"] = 0.5
    for th, m1 in ((0.6, 45), (0.7, 40)):
        cs.append(_mk("C", th, None, 0, m1))
    # 1. candidate passes: M1=30 < comparator 40 with constraints met
    cand = [_mk("D1", 0.5, 1.0, 0, 30)]
    r = choose(base, cand, [dict(c) for c in cs])
    check(r["outcome"] == "dev_candidate_passes" and r["comparator"]["threshold"] == 0.7, "dev_candidate_passes")
    check(r["pair_sel_vs_comp"]["b_premature_under_comparator_not_candidate"] -
          r["pair_sel_vs_comp"]["c_premature_under_candidate_not_comparator"] == 10, "b - c = n*dM1 (=10)")
    # 2. threshold suffices: C at 0.7 (M1=40) beats the candidate (M1=45), comparator below B
    r = choose(base, [_mk("D1", 0.5, 1.0, 0, 45)], [dict(c) for c in cs])
    check(r["outcome"] == "dev_threshold_suffices", "dev_threshold_suffices (C threshold beats candidate)")
    # 3. stock suffices: comparator is B itself (no C row beats B), candidate no better than B
    r = choose(base, [_mk("D1", 0.5, 1.0, 0, 55)], [_mk("C", 0.5, None, 0, 50)])
    check(r["outcome"] == "dev_stock_suffices", "dev_stock_suffices")
    # 4. nothing passes: candidates fail dM3 (M3 77 -> -3 pt); comparator below B true / false
    bad = [_mk("D1", 0.5, 1.0, 0, 20, m3=77)]
    r = choose(base, bad, [dict(c) for c in cs])
    check(r["outcome"] == "dev_nothing_passes" and r["comparator_M1_below_B"] is True, "nothing_passes, below_B true")
    r = choose(base, bad, [_mk("C", 0.5, None, 0, 50)])
    check(r["outcome"] == "dev_nothing_passes" and r["comparator_M1_below_B"] is False, "nothing_passes, below_B false")
    # 5. exact bounds pass; just beyond fails
    for m, kw, ok in (("M2", dict(m2=11), True), ("M2", dict(m2=12), False), ("M3", dict(m3=78), True),
                      ("M3", dict(m3=77), False), ("M4", dict(m4=178), True), ("M4", dict(m4=177), False),
                      ("M4b", dict(m4b=148), True), ("M4b", dict(m4b=147), False), ("M5", dict(m5=190), True),
                      ("M5", dict(m5=189), False)):
        f = constraint_flags(_mk("D1", 0.5, 1, 0, 30, **kw), base)
        check(f[m] is ok, f"{m} {kw} -> {ok} (bound exactly passes)")
    # 6. tie-breaks
    t = [_mk("D1", 0.5, 2.0, 0, 30), _mk("D2", 0.5, 1.0, 1, 30)]  # same M1; top2 order disagrees with epoch
    r = choose(base, t, [dict(c) for c in cs])
    check(r["selected"]["arm"] == "D2", "earlier checkpoint (lower epoch) beats top2 order")
    t = [_mk("E1", 0.6, 1.0, 0, 30), _mk("E1", 0.4, 1.0, 0, 30), _mk("E1", 0.5, 1.0, 0, 30)]
    r = choose(base, t, [dict(c) for c in cs])
    check(r["selected"]["threshold"] == 0.5, "threshold closest to 0.5")
    t = [_mk("E1", 0.6, 1.0, 0, 30), _mk("E1", 0.4, 1.0, 0, 30)]
    r = choose(base, t, [dict(c) for c in cs])
    check(r["selected"]["threshold"] == 0.4, "equal distance: lower threshold")
    t = [_mk("D1", 0.5, 1.0, 1, 30), _mk("D2", 0.5, 1.0, 0, 30)]
    r = choose(base, t, [dict(c) for c in cs])
    check(r["selected"]["top2_pos"] == 0, "equal epoch: top2 order")
    cs2 = [_mk("C", 0.5, None, 0, 50), _mk("C", 0.6, None, 0, 40), _mk("C", 0.4, None, 0, 40)]
    r = choose(base, [_mk("D1", 0.5, 1.0, 0, 55)], cs2)
    check(r["comparator"]["threshold"] == 0.4, "comparator tie, equal distance -> lower threshold")
    r = choose(base, [], [_mk("C", 0.5, None, 0, 50)])
    check(r["outcome"] == "dev_nothing_passes" and r["selected"] is None, "empty candidate list -> dev_nothing_passes")
    cs3 = [_mk("C", 0.5, None, 0, 50), _mk("C", 0.55, None, 0, 40), _mk("C", 0.7, None, 0, 40)]
    r = choose(base, [_mk("D1", 0.5, 1.0, 0, 55)], cs3)
    check(r["comparator"]["threshold"] == 0.55, "comparator tie -> closest to 0.5")
    # 7. test plan note for non-0.5 threshold
    sel = _mk("E1", 0.6, 1.0, 0, 30)
    sel["model_id"] = "m0"
    cb = {"m0": {"path": "/x.onnx", "model_id": "m0", "cand_id": "R1/c", "sha256": "ab"}}
    tp = make_test_plan(sel, _mk("C", 0.7, None, 0, 40), cb, "dev_candidate_passes")
    check("section_7_1_requirement" in tp and "0.60" in tp["section_7_1_requirement"], "test_plan notes non-0.5 threshold")
    sel["threshold"] = 0.5
    check("section_7_1_requirement" not in make_test_plan(sel, _mk("C", 0.7, None, 0, 40), cb, "x"), "no note at 0.5")
    # 8. empty top2 handled by check_candidates
    # 9. guard metrics
    pr = [{"id": "p1", "label": 1, "p_full": 0.9, "p_cut": 0.6}, {"id": "p2", "label": 1, "p_full": 0.55, "p_cut": 0.3},
          {"id": "p3", "label": 1, "p_full": 0.45, "p_cut": None}, {"id": "n1", "label": 0, "p_full": 0.2, "p_cut": None},
          {"id": "n2", "label": 0, "p_full": 0.5, "p_cut": None}, {"id": "n3", "label": 0, "p_full": 0.7, "p_cut": None}]
    # by hand: th=0.4: M4 3/3, M4b 2/2 (0.6>0.4, 0.3 no -> 1/2), M5: p<=0.4: n1 -> 1/3
    exp = {0.4: (3, 3, 1, 2, 1, 3), 0.5: (2, 3, 1, 2, 2, 3), 0.6: (1, 3, 0, 2, 2, 3)}
    for th, (k4, n4, k4b, n4b, k5, n5) in exp.items():
        ev, nulls = guard_events(pr, th)
        check(counts(ev["M4"]) == (k4, n4) and counts(ev["M4b"]) == (k4b, n4b) and counts(ev["M5"]) == (k5, n5)
              and nulls == 1, f"guard metrics at {th}: M4 {k4}/{n4}, M4b {k4b}/{n4b} (1 null excluded), M5 {k5}/{n5}")
    # 10. McNemar / Wald
    check(abs(mcnemar_p(3, 3) - 1.0) < 1e-12 and abs(mcnemar_p(0, 5) - 2 / 32) < 1e-12, "McNemar exact")
    d, ci = wald_paired(2, 8, 100)
    check(abs(d - 0.06) < 1e-12 and ci[0] < 0.06 < ci[1], "Wald paired")
    # 11. test-path refusal
    for p, bad in ((os.path.join(ITEMS_DIR, "test.jsonl"), True), (os.path.join(ITEMS_DIR, "Test_end_of_window.jsonl"), True),
                   (os.path.join(BENCH, "tests", "fixtures", "selection", "dev_subset.jsonl"), False),
                   (os.path.join(ITEMS_DIR, "dev.jsonl"), False)):
        try:
            refuse_test_item_path(p)
            got = False
        except SystemExit:
            got = True
        check(got is bad, f"refuse_test_item_path({os.path.relpath(p, BENCH)}) -> {bad}")
    print(f"SELFTEST PASSED ({n_ok} checks)")


if __name__ == "__main__":
    main()
