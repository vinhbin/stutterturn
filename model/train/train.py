"""Fine-tune stock Smart Turn v3.2 (model/specs/training-v1.md sections 2d, 3, 4).

  python model/train/train.py --haan H --work W --run-id R1 --lr 3e-5 --p-stutter 0.40
  python model/train/train.py --haan H --work W --run-id R4 --lr 3e-5 --p-stutter 0.40 --freeze-but-last2
  python model/train/train.py --haan H --work W --sanity       # check 4
  python model/train/train.py --haan H --work W --throughput   # check 5

Writes W/runs/<run_id>/{config.json, metrics.jsonl, ckpt-e<epoch>.pt, run.json}; refuses an
existing run directory. Features are computed once per sample (eval_runner preprocessing)
and cached in W/features/.
"""
import argparse
import json
import math
import os
import platform
import sys
import time
from datetime import datetime, timezone

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

FEAT_SHAPE = (80, 800)


# ---------------------------------------------------------------- feature cache
def _load_refs(path):
    return [json.loads(l) for l in open(path) if l.strip()]


def _audio_for(ref, work):
    """Returns the model input waveform for a reference row."""
    if "cut_samples" in ref:  # SEP-28k cut (stutter negative, 2e positive or dev item)
        x = C.read_audio(os.path.join(C.BENCH, ref["audio"]))
        cut = min(ref["cut_samples"], len(x))
        keep = ref.get("keep_samples")  # v2 length matching / M3-crop: last `keep` samples only
        return x[max(0, cut - keep):cut] if keep else x[:cut]
    import soundfile as sf  # Smart Turn replay/guard row: full audio
    x, sr = sf.read(os.path.join(work, ref["audio"]), dtype="float32")
    assert sr == C.SR
    return x


def dev_refs(group):
    """Dev unfinished items of one group, cut at silence start + 0.20 s (single schedule)."""
    out = []
    for line in open(os.path.join(C.BENCH, "items", "v1", "dev.jsonl")):
        it = json.loads(line)
        if it["group"] == group and it["kind"] == "unfinished":
            out.append({"id": it["item_id"], "audio": it["audio"], "label": 0,
                        "cut_samples": int(round((it["silence_start_s"] + 0.20) * C.SR))})
    return out


def eow_refs():
    """In-loop M3 (spec rev 265ab02): dev end-of-window completed proxies, cut at
    round((silence_start_s + 0.20) * 16000) from the clip start."""
    out = []
    for line in open(os.path.join(C.BENCH, "items", "v1", "dev_end_of_window.jsonl")):
        it = json.loads(line)
        out.append({"id": it["item_id"], "audio": it["audio"], "label": 1,
                    "cut_samples": int(round((it["silence_start_s"] + 0.20) * C.SR))})
    return out


def m3crop_refs():
    """M3-crop (training-v2): M3 items with only the last 1.25 s before the cut kept."""
    return [dict(r, id=r["id"] + "-crop1.25", keep_samples=int(1.25 * C.SR)) for r in eow_refs()]


def m3s_refs(work):
    """In-loop M3s (training-v2): dev stuttered completed proxies (eval-items cand_stu_cmp,
    538 clips) cut at te + 0.20 from the clip start. Keys come from the shared 2e rule
    (proxies.py) and are cached by dev.csv hash."""
    dev_csv = os.path.join(C.BENCH, "splits", "v1", "dev.csv")
    cache = os.path.join(work, "features", "m3s_refs.json")
    sha = C.sha256_file(dev_csv)
    if os.path.exists(cache):
        d = json.load(open(cache))
        if d.get("dev_csv_sha256") == sha:
            return d["refs"]
    import proxies as P
    rows = [r for r in P.split_rows("dev") if r["category"] in ("block", "other_disfluent")]
    got, _ = P.completed_proxies(rows)
    refs = [{"id": f"dev-m3s-{g['clip_key']}", "audio": f"audio/{g['clip_key']}.wav", "label": 1,
             "cut_samples": int(round((g["te"] + 0.20) * C.SR))}
            for g in sorted(got, key=lambda g: g["clip_key"]) if g["group"] == "stuttered"]
    os.makedirs(os.path.dirname(cache), exist_ok=True)
    C.write_json(cache, {"dev_csv_sha256": sha, "refs": refs})
    return refs


def feature_cache(work, name, refs):
    """float32 memmap [N, 80, 800] in W/features/<name>.f32, keyed by the refs' content hash."""
    d = os.path.join(work, "features")
    os.makedirs(d, exist_ok=True)
    key = C.sha256_bytes(json.dumps([r["id"] for r in refs]).encode() +
                         json.dumps([r.get("cut_samples") for r in refs]).encode() +
                         (json.dumps([r.get("keep_samples") for r in refs]).encode()
                          if any("keep_samples" in r for r in refs) else b""))
    data_p, meta_p = os.path.join(d, name + ".f32"), os.path.join(d, name + ".json")
    if os.path.exists(meta_p) and json.load(open(meta_p)).get("key") == key:
        return np.memmap(data_p, dtype=np.float32, mode="r", shape=(len(refs), *FEAT_SHAPE))
    t0 = time.time()
    mm = np.memmap(data_p + ".part", dtype=np.float32, mode="w+", shape=(len(refs), *FEAT_SHAPE))
    for i, r in enumerate(refs):
        mm[i] = C.features(_audio_for(r, work))
        if (i + 1) % 1000 == 0:
            print(f"  features {name}: {i + 1}/{len(refs)}", flush=True)
    mm.flush()
    del mm
    os.replace(data_p + ".part", data_p)
    C.write_json(meta_p, {"key": key, "n": len(refs), "secs": round(time.time() - t0, 1)})
    print(f"features {name}: {len(refs)} in {time.time() - t0:.0f}s", flush=True)
    return np.memmap(data_p, dtype=np.float32, mode="r", shape=(len(refs), *FEAT_SHAPE))


def load_data(work, data="data"):
    dd = os.path.join(work, data)
    man = json.load(open(os.path.join(dd, "manifest.json")))
    stu = _load_refs(os.path.join(dd, "stutter_neg.jsonl"))
    rep = _load_refs(os.path.join(dd, "orig_replay.jsonl"))
    grd = _load_refs(os.path.join(dd, "guard.jsonl"))
    pos_p = os.path.join(dd, "sep_pos.jsonl")
    pos = _load_refs(pos_p) if os.path.exists(pos_p) else None
    dstu, dflu, deow = dev_refs("stuttered"), dev_refs("fluent"), eow_refs()
    dm3s, dcrop = m3s_refs(work), m3crop_refs()
    D = {"manifest": man, "manifest_sha256": C.sha256_file(os.path.join(dd, "manifest.json")), "data_dir": data,
         "stu": stu, "rep": rep, "grd": grd, "pos": pos, "dstu": dstu, "dflu": dflu, "deow": deow,
         "dm3s": dm3s, "dcrop": dcrop,
         "F_deow": feature_cache(work, "dev_eow_t020", deow),
         "F_dm3s": feature_cache(work, "dev_m3s_te020", dm3s),
         "F_dcrop": feature_cache(work, "dev_eow_t020_crop1.25", dcrop),
         "F_stu": feature_cache(work, "stutter_neg", stu), "F_rep": feature_cache(work, "orig_replay", rep),
         "F_grd": feature_cache(work, "guard", grd), "F_dstu": feature_cache(work, "dev_stu_t020", dstu),
         "F_dflu": feature_cache(work, "dev_flu_t020", dflu)}
    if pos is not None:
        D["F_pos"] = feature_cache(work, "sep_pos_v2", pos)
    return D


# ---------------------------------------------------------------- model helpers
def pick_device():
    import torch
    if torch.cuda.is_available():
        return "cuda"
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def probs(model, F, device, bs=64):
    import torch
    model.eval()
    out = []
    with torch.no_grad():
        for i in range(0, len(F), bs):
            x = torch.from_numpy(np.ascontiguousarray(F[i:i + bs])).to(device)
            out.append(torch.sigmoid(model(x)).float().cpu().numpy())
    model.train()
    return np.concatenate(out)


def validate(model, D, device, threshold=0.5):
    """In-loop fast validation (section 4): rates at t = 0.20 and on the guard set."""
    p_stu, p_flu, p_grd = probs(model, D["F_dstu"], device), probs(model, D["F_dflu"], device), \
        probs(model, D["F_grd"], device)
    p_eow = probs(model, D["F_deow"], device)
    p_m3s, p_crop = probs(model, D["F_dm3s"], device), probs(model, D["F_dcrop"], device)
    y = np.array([r["label"] for r in D["grd"]])
    return {"dev_stutter_premature": round(float((p_stu > threshold).mean()), 4), "n_dev_stutter": len(p_stu),
            "dev_eow_first_check_decide": round(float((p_eow > threshold).mean()), 4), "n_dev_eow": len(p_eow),
            "dev_stu_completed_decide": round(float((p_m3s > threshold).mean()), 4), "n_dev_m3s": len(p_m3s),
            "dev_eow_crop_decide": round(float((p_crop > threshold).mean()), 4), "n_dev_eow_crop": len(p_crop),
            "dev_fluent_premature": round(float((p_flu > threshold).mean()), 4), "n_dev_fluent": len(p_flu),
            "guard_recall": round(float((p_grd[y == 1] > threshold).mean()), 4), "n_guard_pos": int((y == 1).sum()),
            "guard_specificity": round(float((p_grd[y == 0] <= threshold).mean()), 4),
            "n_guard_neg": int((y == 0).sum())}


def freeze_but_last2(model):
    """R4: freeze the encoder except its last 2 layers (+ final norm); head stays trainable."""
    for p in model.encoder.parameters():
        p.requires_grad = False
    n = len(model.encoder.layers)
    for layer in list(model.encoder.layers)[n - 2:]:
        for p in layer.parameters():
            p.requires_grad = True
    for p in model.encoder.layer_norm.parameters():
        p.requires_grad = True


# ---------------------------------------------------------------- mixture
class Mixture:
    """Per-sample draw: 2a stutter negatives (prob p_neg, by weight), 2e SEP-28k positives
    (prob p_pos, by weight; training-v2), else 2b replay (uniform). With p_pos = 0 this is
    exactly the v1 two-source mixture (same RNG sequence)."""

    def __init__(self, D, p_neg, seed, p_pos=0.0):
        if p_pos > 0 and D.get("pos") is None:
            sys.exit("--p-pos > 0 needs sep_pos.jsonl (build_train_set.py --v2, then --data data-v2)")
        self.D, self.p, self.p_pos = D, p_neg, p_pos
        self.p_rep = 1.0 - p_neg - p_pos
        self.rng = np.random.default_rng(seed)
        w = np.array([r["weight"] for r in D["stu"]], dtype=np.float64)
        self.w = w / w.sum()
        self.weight_total = float(w.sum())
        if p_pos > 0:
            wp = np.array([r["weight"] for r in D["pos"]], dtype=np.float64)
            self.wp = wp / wp.sum()
            self.pos_stuttered = np.array([r["group"] == "stuttered" for r in D["pos"]])
        self.y_rep = np.array([r["label"] for r in D["rep"]], dtype=np.float32)
        fp = float(self.y_rep.mean())
        # fixed pos_weight = expected negatives / positives over the whole mixture (v2 2d;
        # equals the v1 two-source formula when p_pos = 0)
        self.pos_weight = (p_neg + self.p_rep * (1 - fp)) / (p_pos + self.p_rep * fp)
        self.replay_pos_frac = fp

    def samples_per_epoch(self):
        return int(round(self.weight_total / self.p))

    @staticmethod
    def _rows(F, idx):
        return F[np.sort(idx)][np.argsort(np.argsort(idx))]

    def batch(self, n):
        if self.p_pos == 0:
            is_stu = self.rng.random(n) < self.p
            x = np.empty((n, *FEAT_SHAPE), dtype=np.float32)
            y = np.empty(n, dtype=np.float32)
            si = self.rng.choice(len(self.w), size=int(is_stu.sum()), p=self.w)
            ri = self.rng.integers(0, len(self.y_rep), size=int((~is_stu).sum()))
            x[is_stu], y[is_stu] = self._rows(self.D["F_stu"], si), 0.0
            x[~is_stu], y[~is_stu] = self._rows(self.D["F_rep"], ri), self.y_rep[ri]
            return x, y
        u = self.rng.random(n)
        src = np.where(u < self.p, 0, np.where(u < self.p + self.p_pos, 1, 2))
        x = np.empty((n, *FEAT_SHAPE), dtype=np.float32)
        y = np.empty(n, dtype=np.float32)
        si = self.rng.choice(len(self.w), size=int((src == 0).sum()), p=self.w)
        pi = self.rng.choice(len(self.wp), size=int((src == 1).sum()), p=self.wp)
        ri = self.rng.integers(0, len(self.y_rep), size=int((src == 2).sum()))
        x[src == 0], y[src == 0] = self._rows(self.D["F_stu"], si), 0.0
        x[src == 1], y[src == 1] = self._rows(self.D["F_pos"], pi), 1.0
        x[src == 2], y[src == 2] = self._rows(self.D["F_rep"], ri), self.y_rep[ri]
        return x, y

    def check(self, draws=10000):
        """training-v2 check 3: empirical source fractions and stuttered share within 2e."""
        u = np.random.default_rng(12345).random(draws)
        src = np.where(u < self.p, 0, np.where(u < self.p + self.p_pos, 1, 2))
        stu_share = None
        if self.p_pos > 0:
            pi = np.random.default_rng(54321).choice(len(self.wp), size=int((src == 1).sum()), p=self.wp)
            stu_share = float(self.pos_stuttered[pi].mean())
        return {"draws": draws, "frac_neg": round(float((src == 0).mean()), 4),
                "frac_pos": round(float((src == 1).mean()), 4),
                "frac_replay": round(float((src == 2).mean()), 4),
                "target": [self.p, self.p_pos, round(self.p_rep, 4)],
                "stuttered_share_within_2e": None if stu_share is None else round(stu_share, 4)}


# ---------------------------------------------------------------- main
def env_info(device):
    import torch
    from importlib import metadata
    v = {"python": sys.version.split()[0], "platform": platform.platform(), "device": device,
         "torch": torch.__version__}
    if device == "cuda":
        v["gpu"] = torch.cuda.get_device_name(0)
    for p in ("transformers", "onnx", "onnxruntime", "numpy"):
        v[p] = metadata.version(p)
    return v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--haan", required=True)
    ap.add_argument("--work", required=True)
    ap.add_argument("--run-id")
    ap.add_argument("--lr", type=float, default=3e-5)
    ap.add_argument("--p-stutter", "--p-neg", dest="p_stutter", type=float, default=0.40,
                    help="probability of a 2a stutter negative (v2: p_neg)")
    ap.add_argument("--p-pos", type=float, default=0.0, help="training-v2: probability of a 2e positive")
    ap.add_argument("--data", default="data", help="data dir under --work (v2: data-v2)")
    ap.add_argument("--mixture-check", action="store_true", help="training-v2 check 3")
    ap.add_argument("--step0", action="store_true", help="training-v2 check 4: print step-0 validation")
    ap.add_argument("--epochs", type=float, default=2.0)
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--max-minutes", type=float, default=60.0)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--freeze-but-last2", action="store_true")
    ap.add_argument("--sanity", action="store_true", help="check 4")
    ap.add_argument("--throughput", action="store_true", help="check 5")
    a = ap.parse_args()

    import torch
    torch.manual_seed(a.seed)
    np.random.seed(a.seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    device = pick_device()
    load_from_onnx, _ = C.import_haan(a.haan)
    D = load_data(a.work, a.data)
    mix = Mixture(D, a.p_stutter, a.seed, a.p_pos)
    if a.mixture_check:
        print(json.dumps({"check": "v2-3", **mix.check(), "pos_weight": round(mix.pos_weight, 6),
                          "replay_pos_frac": round(mix.replay_pos_frac, 6)}))
        return
    model = load_from_onnx(C.stock_fp32_path(a.work)).to(device)
    model.train()
    if a.freeze_but_last2:
        freeze_but_last2(model)
    params = [p for p in model.parameters() if p.requires_grad]
    lossf = torch.nn.BCEWithLogitsLoss(pos_weight=torch.tensor(mix.pos_weight, device=device))

    if a.step0:
        print(json.dumps({"check": "v2-4", "step": 0, **validate(model, D, device)}))
        return

    if a.sanity:  # check 4: memorize a fixed 64-sample subset
        x64, y64 = mix.batch(64)
        opt = torch.optim.AdamW(params, lr=a.lr, weight_decay=0.01)
        losses = []
        for step in range(200):
            idx = slice((step % 2) * 32, (step % 2) * 32 + 32)
            xb, yb = torch.from_numpy(x64[idx]).to(device), torch.from_numpy(y64[idx]).to(device)
            loss = lossf(model(xb), yb)
            opt.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(params, 1.0)
            opt.step()
            losses.append(float(loss))
        start, end = float(np.mean(losses[:2])), float(np.mean(losses[-2:]))
        ok = end < 0.2 * start
        print(json.dumps({"check": 4, "device": device, "lr": a.lr, "steps": 200, "subset": 64,
                          "loss_start": round(start, 4), "loss_end": round(end, 5),
                          "ratio": round(end / start, 4), "passed": ok}))
        sys.exit(0 if ok else 1)

    if a.throughput:  # check 5
        opt = torch.optim.AdamW(params, lr=a.lr, weight_decay=0.01)
        n_warm, n_meas = 5, 30
        for i in range(n_warm + n_meas):
            if i == n_warm:
                if device == "cuda":
                    torch.cuda.synchronize()
                t0 = time.perf_counter()
            xb, yb = mix.batch(a.batch)
            xb, yb = torch.from_numpy(xb).to(device), torch.from_numpy(yb).to(device)
            loss = lossf(model(xb), yb)
            opt.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(params, 1.0)
            opt.step()
        if device == "cuda":
            torch.cuda.synchronize()
        sps = n_meas * a.batch / (time.perf_counter() - t0)
        spe = mix.samples_per_epoch()
        tv = time.perf_counter()
        validate(model, D, device)
        val_s = time.perf_counter() - tv
        n_ckpt = int(2 * a.epochs) + 1
        proj = 2 * spe / sps + n_ckpt * val_s
        print(json.dumps({"check": 5, "device": device, **({"gpu": torch.cuda.get_device_name(0)} if device == "cuda" else {}),
                          "batch": a.batch, "samples_per_s_fwd_bwd": round(sps, 1),
                          "samples_per_epoch": spe, "epoch_s": round(spe / sps, 1),
                          "validation_s": round(val_s, 1), "checkpoints_per_run": n_ckpt,
                          "projected_run_min_2_epochs": round(proj / 60, 1),
                          "pos_weight": round(mix.pos_weight, 4),
                          "max_gpu_mem_gb": round(torch.cuda.max_memory_allocated() / 1e9, 2) if device == "cuda" else None}))
        return

    if not a.run_id:
        sys.exit("--run-id required")
    run_dir = os.path.join(a.work, "runs", a.run_id)
    os.makedirs(os.path.dirname(run_dir), exist_ok=True)
    try:
        os.mkdir(run_dir)
    except FileExistsError:
        sys.exit(f"REFUSING: run directory exists: {run_dir}")

    spe = mix.samples_per_epoch()
    steps_per_epoch = math.ceil(spe / a.batch)
    total_steps = int(round(steps_per_epoch * a.epochs))
    warm = max(1, int(round(0.10 * total_steps)))
    ckpt_steps = sorted({int(round(k * steps_per_epoch / 2)) for k in range(1, int(2 * a.epochs) + 1)} | {total_steps})
    cfg = {"run_id": a.run_id, "lr": a.lr, "p_stutter": a.p_stutter, "p_neg": a.p_stutter, "p_pos": a.p_pos,
           "p_replay": round(1 - a.p_stutter - a.p_pos, 6), "data_dir": D["data_dir"],
           "epochs": a.epochs, "batch": a.batch,
           "optimizer": "AdamW", "weight_decay": 0.01, "grad_clip": 1.0, "warmup_frac": 0.10,
           "schedule": "linear warmup then linear decay", "seed": a.seed,
           "freeze_but_last2": a.freeze_but_last2, "pos_weight": round(mix.pos_weight, 6),
           "replay_pos_frac": round(mix.replay_pos_frac, 6), "samples_per_epoch": spe,
           "steps_per_epoch": steps_per_epoch, "total_steps": total_steps, "warmup_steps": warm,
           "checkpoint_steps": ckpt_steps, "max_minutes": a.max_minutes,
           "train_manifest_sha256": D["manifest_sha256"], "init": "stock-fp32 via haan",
           "init_sha256": C.STOCK_FP32_SHA256, "determinism": {"cudnn.deterministic": True,
           "cudnn.benchmark": False, "note": "CUDA/MPS are not bit-deterministic"}}
    cfg_sha = C.sha256_bytes(json.dumps(cfg, sort_keys=True).encode())
    C.write_json(os.path.join(run_dir, "config.json"), cfg)

    opt = torch.optim.AdamW(params, lr=a.lr, weight_decay=0.01)
    sched = torch.optim.lr_scheduler.LambdaLR(
        opt, lambda s: (s + 1) / warm if s < warm else max(0.0, (total_steps - s) / max(1, total_steps - warm)))
    metrics_f = open(os.path.join(run_dir, "metrics.jsonl"), "w")

    def log(rec):
        metrics_f.write(json.dumps(rec) + "\n")
        metrics_f.flush()
        print(json.dumps(rec), flush=True)

    log({"step": 0, "epoch": 0.0, "kind": "validation", **validate(model, D, device)})
    t_start, ckpts, stopped_early, step = time.time(), [], False, 0
    running = []
    for step in range(1, total_steps + 1):
        xb, yb = mix.batch(a.batch)
        xb, yb = torch.from_numpy(xb).to(device), torch.from_numpy(yb).to(device)
        loss = lossf(model(xb), yb)
        opt.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(params, 1.0)
        opt.step()
        sched.step()
        running.append(float(loss))
        out_of_time = (time.time() - t_start) / 60 > a.max_minutes
        if step in ckpt_steps or out_of_time:
            epoch = round(step / steps_per_epoch, 3)
            path = os.path.join(run_dir, f"ckpt-e{epoch:.2f}.pt")
            torch.save({"state_dict": {k: v.detach().cpu() for k, v in model.state_dict().items()},
                        "run_id": a.run_id, "step": step, "epoch": epoch, "config_sha256": cfg_sha,
                        "train_manifest_sha256": D["manifest_sha256"]}, path)
            rec = {"step": step, "epoch": epoch, "kind": "checkpoint", "ckpt": os.path.basename(path),
                   "ckpt_sha256": C.sha256_file(path), "train_loss_mean": round(float(np.mean(running)), 5),
                   "lr": sched.get_last_lr()[0], "elapsed_min": round((time.time() - t_start) / 60, 2),
                   **validate(model, D, device)}
            running = []
            ckpts.append(rec)
            log(rec)
            if out_of_time:
                stopped_early = True
                break
    metrics_f.close()
    C.write_json(os.path.join(run_dir, "run.json"), {
        "run_id": a.run_id, "finished_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "steps_done": step, "total_steps": total_steps, "stopped_at_time_cap": stopped_early,
        "wall_min": round((time.time() - t_start) / 60, 2), "code_commit": C.git_commit(),
        "config_sha256": cfg_sha, "env": env_info(device), "checkpoints": [c["ckpt"] for c in ckpts]})
    print(f"RUN {a.run_id} done: {step}/{total_steps} steps, {len(ckpts)} checkpoints", flush=True)


if __name__ == "__main__":
    main()
