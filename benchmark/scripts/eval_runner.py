"""Matched evaluation runner v1 (see specs/eval-runner-v1.md).

Usage:
  python benchmark/scripts/eval_runner.py --model M.onnx --model-id stock-int8 \
      --expected-sha256 HEX --items items.jsonl --config cfg.json [--scratch] [--no-cache]
  python benchmark/scripts/eval_runner.py --rescore RUN_DIR --config other.json [--scratch]

Probabilities are computed on the full grid (or only the schedule's check points under
grid_scope "checks") and stored; decisions are derived from the
grid by the configured schedule, so thresholds/schedules can be re-scored offline.
"""
import argparse, hashlib, json, math, os, platform, sqlite3, subprocess, sys, time
from datetime import datetime, timezone
from importlib import metadata

import numpy as np

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNS = os.path.join(BASE, "runs")
CACHE_PATH = os.path.join(BASE, "cache", "probs.sqlite")
SR = 16000
PREPROC_VERSION = "smartturn-v3-upstream-1"
EPS = 1e-9

GROUPS = {"stuttered", "fluent"}
KINDS = {"unfinished", "completed"}
LABEL_SOURCES = {"human", "sep28k_annotator", "energy_vad"}
SCHEDULES = {"single", "interval", "legacy"}
GRID_SCOPES = {"full", "checks"}
ITEM_FIELDS = ["item_id", "clip_key", "audio", "split", "group", "kind", "silence_start_s",
               "resume_s", "turn_end_s", "observe_until_s", "label_source"]
OUTCOME_KEYS = ["grid", "infer_ms", "outcome", "premature", "decision_t", "trigger", "margin_s",
                "delay_s", "censored_at_s", "first_check_complete", "first_check_t",
                "input_policy", "input_start_s", "onset_s", "input_start_fallback"]
INPUT_POLICIES = {"clip_start", "turn_onset"}
# Silero onset detector constants (specs/input-policy-v1.md). Must match agent/engine.py.
VAD_FRAME = 512
VAD_CTX = 64
VAD_THRESHOLD = 0.5
VAD_START_S = 0.2
VAD_FRAME_S = 0.032


# ---------------------------------------------------------------- helpers
def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def key3(t):
    return f"{t:.3f}"


def wilson(k, n, z=1.96):
    if n == 0:
        return [None, None]
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(max(0.0, c - h), 4), round(min(1.0, c + h), 4)]


def git(*args):
    try:
        return subprocess.run(["git", *args], cwd=BASE, capture_output=True, text=True,
                              check=True).stdout.strip()
    except Exception:
        return None


def env_versions():
    v = {"python": sys.version.split()[0], "platform": platform.platform()}
    for p in ["onnxruntime", "transformers", "numpy", "soundfile"]:
        try:
            v[p] = metadata.version(p)
        except Exception:
            v[p] = None
    return v


def resolve_audio(p):
    return p if os.path.isabs(p) else os.path.join(BASE, p)


# ---------------------------------------------------------------- config / items
def load_config(path):
    cfg = json.load(open(path))
    errs = []
    for k in ["config_id", "threshold", "vad_stop_s", "schedule", "fallback_timeout_s", "grid_step_s"]:
        if k not in cfg:
            errs.append(f"missing {k}")
    if errs:
        sys.exit(f"bad config {path}: {errs}")
    cfg.setdefault("recheck_interval_s", None)
    if cfg["schedule"] not in SCHEDULES:
        sys.exit(f"bad schedule {cfg['schedule']}")
    if cfg["grid_step_s"] < 0.001:
        sys.exit("grid_step_s must be >= 0.001 (grid keys have 3 decimals)")
    def on_grid(x):
        r = x / cfg["grid_step_s"]
        return abs(r - round(r)) < 1e-6
    if not on_grid(cfg["vad_stop_s"]):
        sys.exit("vad_stop_s must be a multiple of grid_step_s")
    if cfg["schedule"] == "interval":
        ri = cfg["recheck_interval_s"]
        if not ri or ri <= 0 or not on_grid(ri):
            sys.exit("interval schedule needs recheck_interval_s > 0, a multiple of grid_step_s")
    if cfg["schedule"] == "legacy" and not cfg.get("checkpoints_s"):
        sys.exit("legacy schedule needs checkpoints_s")
    # NOTE: input_policy / pre_roll_s are deliberately NOT setdefault'ed: the resolved config is hashed
    # into run.json and existing configs must keep their config_sha256. Read with cfg.get(...).
    pol = cfg.get("input_policy", "clip_start")
    if pol not in INPUT_POLICIES:
        sys.exit(f"bad input_policy {pol!r}")
    if pol == "turn_onset":
        pr = cfg.get("pre_roll_s")
        if not isinstance(pr, (int, float)) or isinstance(pr, bool) or pr < 0:
            sys.exit("input_policy turn_onset needs numeric pre_roll_s >= 0")
        if cfg["schedule"] == "legacy":
            sys.exit("schedule legacy is not allowed with input_policy turn_onset")
    elif "pre_roll_s" in cfg:
        sys.exit("pre_roll_s is only allowed with input_policy turn_onset")
    # grid_scope: not setdefault'ed either (specs/checks-only-grid-v1.md); read with cfg.get(..., "full").
    gs = cfg.get("grid_scope", "full")
    if gs not in GRID_SCOPES:
        sys.exit(f"bad grid_scope {gs!r} (expected 'full' or 'checks')")
    if gs == "checks" and cfg["schedule"] == "legacy":
        sys.exit("grid_scope checks is not allowed with schedule legacy (legacy already evaluates only its checkpoints)")
    return cfg


def load_items(path):
    import soundfile as sf
    items, errs, seen = [], [], set()
    for ln, line in enumerate(open(path), 1):
        if not line.strip():
            continue
        try:
            it = json.loads(line)
        except Exception as e:
            errs.append(f"line {ln}: invalid JSON ({e})")
            continue
        e0 = len(errs)
        miss = [k for k in ITEM_FIELDS if k not in it]
        if miss:
            errs.append(f"line {ln}: missing fields {miss}")
            continue
        if it["item_id"] in seen:
            errs.append(f"line {ln}: duplicate item_id {it['item_id']}")
        seen.add(it["item_id"])
        if it["group"] not in GROUPS: errs.append(f"line {ln}: bad group {it['group']!r}")
        if it["kind"] not in KINDS: errs.append(f"line {ln}: bad kind {it['kind']!r}")
        if it["label_source"] not in LABEL_SOURCES: errs.append(f"line {ln}: bad label_source {it['label_source']!r}")
        num = lambda v: isinstance(v, (int, float)) and not isinstance(v, bool)
        if not num(it["silence_start_s"]): errs.append(f"line {ln}: silence_start_s not numeric")
        if not num(it["observe_until_s"]): errs.append(f"line {ln}: observe_until_s not numeric")
        if len(errs) == e0:
            if it["observe_until_s"] <= it["silence_start_s"]:
                errs.append(f"line {ln}: observe_until_s <= silence_start_s")
            if it["kind"] == "unfinished":
                if not num(it["resume_s"]): errs.append(f"line {ln}: unfinished needs numeric resume_s")
                elif it["resume_s"] <= it["silence_start_s"]: errs.append(f"line {ln}: resume_s <= silence_start_s")
                if it["turn_end_s"] is not None: errs.append(f"line {ln}: unfinished must have turn_end_s null")
            elif it["kind"] == "completed":
                if not num(it["turn_end_s"]): errs.append(f"line {ln}: completed needs numeric turn_end_s")
                if it["resume_s"] is not None: errs.append(f"line {ln}: completed must have resume_s null")
        ap = resolve_audio(str(it["audio"]))
        if not os.path.isfile(ap):
            errs.append(f"line {ln}: missing audio file {it['audio']}")
        elif len(errs) == e0:
            try:
                info = sf.info(ap)
                if info.samplerate != SR: errs.append(f"line {ln}: audio sample rate {info.samplerate} != {SR}")
                elif info.frames / SR + 0.002 < it["observe_until_s"]:
                    errs.append(f"line {ln}: audio shorter ({info.frames / SR:.3f}s) than observe_until_s")
            except Exception as e:
                errs.append(f"line {ln}: unreadable audio ({e})")
        items.append(it)
    if errs:
        print("BAD ITEMS:\n  " + "\n  ".join(errs), file=sys.stderr)
        sys.exit(1)
    if not items:
        sys.exit("no items")
    return items


# ---------------------------------------------------------------- grid + decision
def grid_times(it, cfg):
    """Times (s after silence start) at which probabilities are computed."""
    ss, obs = it["silence_start_s"], it["observe_until_s"]
    if cfg["schedule"] == "legacy":
        if it["kind"] != "unfinished":
            sys.exit("legacy schedule supports unfinished items only")
        gap = it.get("legacy_gap_dur_s", it["resume_s"] - ss)
        ts = []
        for t in cfg["checkpoints_s"]:
            if t >= gap - 0.01:
                break
            ts.append(t)
        return ts or [0.2]
    ts, k = [], 0
    while True:
        t = round(cfg["vad_stop_s"] + k * cfg["grid_step_s"], 6)
        k += 1
        if t > obs - ss + EPS or t > cfg["fallback_timeout_s"] + EPS:
            break
        if it["kind"] == "unfinished" and ss + t >= it["resume_s"] - EPS:
            break
        ts.append(t)
    return ts


def check_times(grid_ts, cfg):
    """Subset of grid times the schedule actually evaluates."""
    if cfg["schedule"] == "legacy":
        return list(grid_ts)
    if cfg["schedule"] == "single":
        return [t for t in grid_ts if abs(t - cfg["vad_stop_s"]) < 1e-6][:1]
    ri, v = cfg["recheck_interval_s"], cfg["vad_stop_s"]
    out = []
    for t in grid_ts:
        r = (t - v) / ri
        if abs(r - round(r)) < 1e-6:
            out.append(t)
    return out


def decide(it, cfg, grid):
    """grid: {key3: prob}. Returns outcome fields."""
    th, ss, obs = cfg["threshold"], it["silence_start_s"], it["observe_until_s"]
    legacy = cfg["schedule"] == "legacy"
    ts = sorted(float(k) for k in grid)
    checks = check_times(ts, cfg)
    prob = lambda t: grid[key3(t)]
    cond = (lambda p: round(p, 4) > th) if legacy else (lambda p: p > th)
    fired = next((t for t in checks if cond(prob(t))), None)
    fb_t = ss + cfg["fallback_timeout_s"]
    out = {}
    if legacy and checks:
        out["first_check_t"] = checks[0]
        out["first_check_complete"] = bool(cond(prob(checks[0])))
    if it["kind"] == "unfinished":
        resume = it["resume_s"]
        if fired is not None:
            dt, trig = ss + fired, "model"
        elif not legacy and fb_t < resume - EPS and fb_t <= obs + EPS:
            dt, trig = fb_t, "fallback"
        else:
            dt, trig = None, None
        prem = dt is not None and dt < resume - EPS
        out.update(outcome="premature" if prem else "not_premature", premature=prem,
                   decision_t=None if dt is None else round(dt, 6), trigger=trig,
                   margin_s=None if dt is None else round(resume - dt, 6))
    else:
        te = it["turn_end_s"]
        if fired is not None:
            dt, trig = ss + fired, "model"
        elif fb_t <= obs + EPS and te + cfg["fallback_timeout_s"] <= obs + EPS:
            dt, trig = fb_t, "fallback"
        else:
            dt, trig = None, None
        if dt is None:
            out.update(outcome="censored", decision_t=None, trigger=None, delay_s=None,
                       censored_at_s=obs)
        else:
            out.update(outcome="decided", decision_t=round(dt, 6), trigger=trig,
                       delay_s=round(dt - te, 6), censored_at_s=None)
    return out


# ---------------------------------------------------------------- model + cache
class Model:
    def __init__(self, path):
        import onnxruntime as ort
        from transformers import WhisperFeatureExtractor
        so = ort.SessionOptions()
        so.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        so.inter_op_num_threads = 1
        so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        self.session = ort.InferenceSession(path, sess_options=so, providers=["CPUExecutionProvider"])
        self.fe = WhisperFeatureExtractor(chunk_length=8)

    def predict(self, audio):
        n = 8 * SR
        if len(audio) > n:
            audio = audio[-n:]
        elif len(audio) < n:
            audio = np.pad(audio, (n - len(audio), 0), mode="constant")
        inp = self.fe(audio, sampling_rate=SR, return_tensors="np", padding="max_length",
                      max_length=n, truncation=True, do_normalize=True)
        feats = np.expand_dims(inp.input_features.squeeze(0).astype(np.float32), 0)
        return self.session.run(None, {"input_features": feats})[0][0].item()  # already a probability


class SileroVAD:
    """Silero VAD v5.1.2 over 512-sample frames (spec text, independent of agent/engine.py)."""

    def __init__(self, path):
        import onnxruntime as ort
        so = ort.SessionOptions()
        so.inter_op_num_threads = 1
        so.intra_op_num_threads = 1
        self.sess = ort.InferenceSession(path, sess_options=so, providers=["CPUExecutionProvider"])

    def probs(self, x, stop_after_run=None):
        """Yield speech probability per consecutive 512-sample frame aligned to sample 0."""
        state = np.zeros((2, 1, 128), dtype=np.float32)
        ctx = np.zeros((1, VAD_CTX), dtype=np.float32)
        sr = np.array(SR, dtype=np.int64)
        for i in range(len(x) // VAD_FRAME):
            frame = x[i * VAD_FRAME:(i + 1) * VAD_FRAME].astype(np.float32)
            inp = np.concatenate([ctx, frame[None, :]], axis=1)
            out, state = self.sess.run(None, {"input": inp, "state": state, "sr": sr})
            ctx = inp[:, -VAD_CTX:]
            yield float(out[0][0])


def first_onset_frame(vad, x):
    """Index of the first frame of the first run of start_n consecutive speech frames, else None.
    Deliberately the FIRST onset in the clip: each item is scored as if no earlier decision had reset
    the turn. The agent resets its turn only after a decision, so this matches the agent whenever the
    item's check is its first decision."""
    start_n = math.ceil(VAD_START_S / VAD_FRAME_S - 1e-9)
    run = 0
    for i, p in enumerate(vad.probs(x)):
        run = run + 1 if p >= VAD_THRESHOLD else 0
        if run >= start_n:
            return i - start_n + 1
    return None


def input_start_for(it, onset_frame, pre_roll_s):
    """Returns (input_start_sample, onset_s, fallback)."""
    if onset_frame is None:
        return 0, None, True
    onset_s = onset_frame * VAD_FRAME / SR
    if onset_s >= it["silence_start_s"]:
        return 0, onset_s, True
    pre = int(round(pre_roll_s / VAD_FRAME_S))
    return max(0, (onset_frame - pre) * VAD_FRAME), onset_s, False


class Cache:
    def __init__(self, path, enabled):
        self.enabled = enabled
        self.hits = self.misses = 0
        if enabled:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            self.db = sqlite3.connect(path)
            self.db.execute("CREATE TABLE IF NOT EXISTS probs (model_sha256 TEXT, preproc_version TEXT,"
                            " audio_sha256 TEXT, cut_sample_index INTEGER, prob REAL,"
                            " PRIMARY KEY (model_sha256, preproc_version, audio_sha256, cut_sample_index))")
            self.db.commit()

    def get(self, key):
        if not self.enabled:
            return None
        r = self.db.execute("SELECT prob FROM probs WHERE model_sha256=? AND preproc_version=? AND"
                            " audio_sha256=? AND cut_sample_index=?", key).fetchone()
        return None if r is None else r[0]

    def put(self, key, p):
        if self.enabled:
            self.db.execute("INSERT OR REPLACE INTO probs VALUES (?,?,?,?,?)", (*key, p))

    def commit(self):
        if self.enabled:
            self.db.commit()


# ---------------------------------------------------------------- summary
def pct(a, q):
    return round(float(np.percentile(a, q)), 4) if len(a) else None


def summarize(rows, cfg):
    groups = {}
    for r in rows:
        groups.setdefault((r["split"], r["group"], r["kind"], r["label_source"]), []).append(r)
    out = []
    for (split, group, kind, ls), rs in sorted(groups.items()):
        g = {"split": split, "group": group, "kind": kind, "label_source": ls, "n": len(rs)}
        if kind == "unfinished":
            k = sum(1 for r in rs if r["premature"])
            g.update(premature_n=k, premature_rate=round(k / len(rs), 4), premature_ci95=wilson(k, len(rs)))
            if cfg["schedule"] == "legacy":
                k1 = sum(1 for r in rs if r.get("first_check_complete"))
                g.update(first_check_premature_n=k1, first_check_premature_rate=round(k1 / len(rs), 4),
                         first_check_premature_ci95=wilson(k1, len(rs)))
        else:
            dec = [r for r in rs if r["outcome"] == "decided"]
            d = np.array([r["delay_s"] for r in dec])
            g.update(decided_by_model_n=sum(1 for r in dec if r["trigger"] == "model"),
                     decided_by_fallback_n=sum(1 for r in dec if r["trigger"] == "fallback"),
                     censored_n=len(rs) - len(dec),
                     delay_s_median=pct(d, 50), delay_s_p90=pct(d, 90),
                     delay_s_max=round(float(d.max()), 4) if len(d) else None)
        if cfg.get("input_policy", "clip_start") == "turn_onset":
            nf = [r for r in rs if not r.get("input_start_fallback")]
            g.update(input_start_fallback_n=len(rs) - len(nf), n_nonfallback=len(nf))
            if kind == "unfinished":
                kn = sum(1 for r in nf if r["premature"])
                g.update(premature_n_nonfallback=kn,
                         premature_rate_nonfallback=round(kn / len(nf), 4) if nf else None,
                         premature_ci95_nonfallback=wilson(kn, len(nf)))
        ms = np.array([v for r in rs for v in r["infer_ms"].values() if v is not None])
        g["infer_ms"] = {"n": len(ms), "mean": round(float(ms.mean()), 2) if len(ms) else None,
                         "p95": pct(ms, 95)}
        out.append(g)
    return out


# ---------------------------------------------------------------- main
def make_run_id(args, model_id, config_id, items_sha):
    if args.run_id:
        return args.run_id
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    rid = f"{ts}-{model_id}-{config_id}-{items_sha[:8]}"
    return ("scratch-" if args.scratch else "") + rid


def claim_dir(run_id):
    os.makedirs(RUNS, exist_ok=True)
    d = os.path.join(RUNS, run_id)
    try:
        os.mkdir(d)
    except FileExistsError:
        sys.exit(f"run directory already exists, refusing to overwrite: {d}")
    return d


def write_run(d, run, rows, summary):
    with open(os.path.join(d, "results.jsonl"), "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    json.dump(summary, open(os.path.join(d, "summary.json"), "w"), indent=1)
    json.dump(run, open(os.path.join(d, "run.json"), "w"), indent=1)


def base_run(run_id, cfg, extra):
    dirty = git("status", "--porcelain")
    run = {"run_id": run_id, "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "code_commit": git("rev-parse", "HEAD"), "code_dirty": bool(dirty) if dirty is not None else None,
           "runner_sha256": sha256_file(os.path.abspath(__file__)), "preproc_version": PREPROC_VERSION,
           "config": cfg, "config_sha256": hashlib.sha256(canon(cfg).encode()).hexdigest(),
           "env": env_versions()}
    run.update(extra)
    return run


def do_infer(args):
    t_start = time.time()
    cfg = load_config(args.config)
    model_sha = sha256_file(args.model)
    if model_sha != args.expected_sha256.lower():
        sys.exit(f"model hash mismatch: got {model_sha}, expected {args.expected_sha256}")
    turn = cfg.get("input_policy", "clip_start") == "turn_onset"
    vad_sha = None
    if turn:
        if not (args.vad_model and args.vad_sha256):
            sys.exit("input_policy turn_onset requires --vad-model and --vad-sha256")
        vad_sha = sha256_file(args.vad_model)
        if vad_sha != args.vad_sha256.lower():
            sys.exit(f"vad model hash mismatch: got {vad_sha}, expected {args.vad_sha256}")
    items = load_items(args.items)
    items_sha = sha256_file(args.items)
    run_id = make_run_id(args, args.model_id, cfg["config_id"], items_sha)
    d = claim_dir(run_id)
    try:
        import soundfile as sf
        model = Model(args.model)
        vad = SileroVAD(args.vad_model) if turn else None
        cache = Cache(CACHE_PATH, not args.no_cache)
        audio_cache = {}
        rows = []
        for n, it in enumerate(items):
            ap = resolve_audio(it["audio"])
            if ap not in audio_cache:
                audio_cache.clear()  # keep one clip in memory
                x, sr = sf.read(ap, dtype="float32")
                if x.ndim > 1:
                    x = x.mean(axis=1).astype(np.float32)
                audio_cache[ap] = (x, sha256_file(ap),
                                   first_onset_frame(vad, x) if turn else None)
            x, asha, onset_frame = audio_cache[ap]
            if turn:
                start, onset_s, fb = input_start_for(it, onset_frame, cfg["pre_roll_s"])
                pre_v = f"{PREPROC_VERSION}|start={start}|vad={vad_sha[:16]}"
            else:
                start, onset_s, fb, pre_v = 0, None, False, PREPROC_VERSION
            grid, ims = {}, {}
            ts_all = grid_times(it, cfg)
            if cfg.get("grid_scope", "full") == "checks":
                ts_all = check_times(ts_all, cfg)
            for t in ts_all:
                if cfg["schedule"] == "legacy":
                    cut = int((it["silence_start_s"] + t) * SR)  # run_model_arm.py: int(), not round()
                else:
                    cut = int(round((it["silence_start_s"] + t) * SR))
                cut = min(cut, len(x))
                key = (model_sha, pre_v, asha, cut)
                p = cache.get(key)
                if p is None:
                    t0 = time.perf_counter()
                    p = model.predict(x[start:cut] if turn else x[:cut])
                    ims[key3(t)] = round((time.perf_counter() - t0) * 1000, 2)
                    cache.put(key, p)
                    cache.misses += 1
                else:
                    ims[key3(t)] = None
                    cache.hits += 1
                grid[key3(t)] = round(p, 6)
            cache.commit()
            row = {k: it[k] for k in it}
            row["grid"], row["infer_ms"] = grid, ims
            row.update(decide(it, cfg, grid))
            row["input_policy"] = cfg.get("input_policy", "clip_start")
            row["input_start_s"] = round(start / SR, 6)
            if turn:
                row["onset_s"] = None if onset_s is None else round(onset_s, 6)
                row["input_start_fallback"] = fb
            rows.append(row)
            if (n + 1) % 25 == 0:
                print(f"{n + 1}/{len(items)}", flush=True)
        summary = summarize(rows, cfg)
        run = base_run(run_id, cfg, {"model_id": args.model_id, "model_sha256": model_sha,
                                     "items_path": os.path.relpath(os.path.abspath(args.items), BASE),
                                     "items_sha256": items_sha, "vad_model_sha256": vad_sha, "cache_hits": cache.hits,
                                     "cache_misses": cache.misses, "model_calls": cache.misses,
                                     "grid_points": cache.hits + cache.misses, "wall_s": round(time.time() - t_start, 2)})
        write_run(d, run, rows, summary)
    except BaseException:
        import shutil
        shutil.rmtree(d, ignore_errors=True)
        raise
    print_summary(run_id, summary, run)


def do_rescore(args):
    t_start = time.time()
    src = args.rescore
    srun = json.load(open(os.path.join(src, "run.json")))
    scfg = srun["config"]
    cfg = load_config(args.config)
    if args.threshold is not None:
        cfg["threshold"] = args.threshold
    for k in ["grid_step_s", "vad_stop_s"]:
        if cfg[k] != scfg[k]:
            sys.exit(f"refusing rescore: {k} differs ({scfg[k]} -> {cfg[k]})")
    for k in ["input_policy", "pre_roll_s"]:
        dflt = "clip_start" if k == "input_policy" else None
        if cfg.get(k, dflt) != scfg.get(k, dflt):
            sys.exit(f"refusing rescore: {k} differs ({scfg.get(k, dflt)} -> {cfg.get(k, dflt)}); "
                     "stored grids are for a different input")
    if (cfg["schedule"] == "legacy") != (scfg["schedule"] == "legacy") or (
            cfg["schedule"] == "legacy" and cfg["checkpoints_s"] != scfg["checkpoints_s"]):
        sys.exit("refusing rescore: legacy schedules can only be rescored with identical checkpoints_s")
    src_rows = [json.loads(l) for l in open(os.path.join(src, "results.jsonl")) if l.strip()]
    rows = []
    for r in src_rows:
        it = {k: v for k, v in r.items() if k not in OUTCOME_KEYS}
        need_ts = grid_times(it, cfg)
        if cfg.get("grid_scope", "full") == "checks":
            need_ts = check_times(need_ts, cfg)
        need = [key3(t) for t in need_ts]
        if cfg["schedule"] == "legacy":
            need = sorted(r["grid"])  # identical checkpoints and items => identical grid
        missing = [k for k in need if k not in r["grid"]]
        if missing:
            sys.exit(f"refusing rescore: stored grid for {it['item_id']} lacks {len(missing)} required points"
                     f" (e.g. {missing[:3]}); re-run inference")
        grid = {k: r["grid"][k] for k in need}
        row = dict(it)
        row["grid"] = grid
        row["infer_ms"] = {k: r["infer_ms"].get(k) for k in grid}
        row.update(decide(it, cfg, grid))
        # input fields are carried from the stored run (policy is guaranteed identical above)
        row["input_policy"] = r.get("input_policy", scfg.get("input_policy", "clip_start"))
        row["input_start_s"] = r.get("input_start_s", 0.0)
        if row["input_policy"] == "turn_onset":
            row["onset_s"] = r.get("onset_s")
            row["input_start_fallback"] = r.get("input_start_fallback")
        rows.append(row)
    run_id = make_run_id(args, srun["model_id"], cfg["config_id"], srun["items_sha256"])
    if args.threshold is not None and not args.run_id:
        run_id += f"-th{args.threshold:.2f}"
    d = claim_dir(run_id)
    try:
        summary = summarize(rows, cfg)
        run = base_run(run_id, cfg, {"model_id": srun["model_id"], "model_sha256": srun["model_sha256"],
                                     "items_path": srun["items_path"], "items_sha256": srun["items_sha256"],
                                     "vad_model_sha256": srun.get("vad_model_sha256"),
                                     "rescored_from": srun["run_id"], "model_calls": 0,
                                     "cache_hits": 0, "cache_misses": 0,
                                     "wall_s": round(time.time() - t_start, 2)})
        write_run(d, run, rows, summary)
    except BaseException:
        import shutil
        shutil.rmtree(d, ignore_errors=True)
        raise
    print_summary(run_id, summary, run)


def print_summary(run_id, summary, run):
    print(f"RUN {run_id}  (cache hits={run['cache_hits']} misses={run['cache_misses']} wall={run['wall_s']}s)")
    for g in summary:
        print(json.dumps(g))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model"); ap.add_argument("--model-id"); ap.add_argument("--expected-sha256")
    ap.add_argument("--items"); ap.add_argument("--config", required=True)
    ap.add_argument("--vad-model", help="Silero VAD onnx (required for input_policy turn_onset)")
    ap.add_argument("--vad-sha256", help="expected sha256 of --vad-model")
    ap.add_argument("--rescore", help="existing run dir to re-score from stored grids")
    ap.add_argument("--scratch", action="store_true"); ap.add_argument("--no-cache", action="store_true")
    ap.add_argument("--threshold", type=float,
                    help="with --rescore: override the config's threshold; appends -thX.XX to the run id")
    ap.add_argument("--run-id", help="override the derived run id (used to test immutability)")
    args = ap.parse_args()
    if args.threshold is not None and not args.rescore:
        ap.error("--threshold is only valid with --rescore")
    if args.rescore:
        do_rescore(args)
    else:
        if not (args.model and args.model_id and args.expected_sha256 and args.items):
            ap.error("--model, --model-id, --expected-sha256 and --items are required")
        do_infer(args)


if __name__ == "__main__":
    main()
