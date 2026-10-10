"""Weight-space interpolation of stock FP32 and fine-tuned checkpoints (v4; issue #2 comments
6103360382 [proposal] and Vinh's conditional go). No training:
theta = (1 - alpha) * theta_stock + alpha * theta_source (float tensors).

  python model/train/interpolate.py --haan H --work W --prescreen prescreen-v3.json --selftest
  python model/train/interpolate.py --haan H --work W --prescreen prescreen-v3.json --run-id X4 --tie-rule l2
  python model/train/interpolate.py --work W --promotion-a X4/blend-a0.50-W3e1.00.pt --threshold 0.6

Sources are the prescreen's top 2 (fixed before the selection that followed it), each verified
against the ckpt_sha256 its run logged. Grid: --alphas (default 0.25 0.50 0.75), nothing else.

Writes W/runs/<run_id>/{config.json, metrics.jsonl, blend-*.pt, run.json} in train.py's format,
so prescreen.py and export.py consume it unchanged:
- a step-0 validation record (stock; asserted equal to each source run's step 0), and one
  "checkpoint" record per blend. Top-level metrics are at threshold 0.5 (the unchanged prescreen
  rule); "by_threshold" repeats every in-loop metric at 0.4, 0.5 and 0.6 from the same probabilities.
- the "epoch" field is the tie key ("ties -> earlier" in prescreen and selector), set by the
  required --tie-rule: "l2" = relative L2 distance of the blend's weights from stock
  (||theta - theta_stock|| / ||theta_stock||, comparable across sources); "alpha_epoch" =
  alpha * source epoch. Both values are always recorded.

Preflight (before any blend is scored): clean model/train + benchmark/scripts tree; pinned haan;
stock sha256; stock PyTorch reconstruction vs ORT parity (< 5e-5, as check_parity.py); source
checkpoint, config and manifest identities pinned in config.json. Refuses an existing run dir.

--promotion-a reads metrics.jsonl only: D-010 promotion check 1 at the selected threshold
(M3s and M3-crop at that threshold >= stock at 0.5 - 2.0 pt).
--selftest checks weights only (alpha 0 == stock, alpha 1 == source, bit-exact); no dev data.
"""
import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402
import train as T  # noqa: E402

DEFAULT_ALPHAS = [0.25, 0.50, 0.75]
THRESHOLDS = [0.4, 0.5, 0.6]
PARITY_TOL = 5e-5
PROMO_TOL = 0.020
PROMO_KEYS = [("dev_stu_completed_decide", "M3s"), ("dev_eow_crop_decide", "M3-crop")]


def sources(work, prescreen_path):
    """[(cand_id, path, sha256, metrics record, step-0 record, run_dir)] for the prescreen top 2."""
    ps = json.load(open(prescreen_path))
    top2 = ps.get("top2") or []
    if len(top2) != 2 or len(set(top2)) != 2:
        sys.exit(f"REFUSING: prescreen top2 must name 2 distinct checkpoints, got {top2}")
    out = []
    for cid in top2:
        run, ckpt = cid.split("/")
        run_dir = os.path.join(work, "runs", run)
        recs = [json.loads(l) for l in open(os.path.join(run_dir, "metrics.jsonl")) if l.strip()]
        rec = next((r for r in recs if r.get("ckpt") == ckpt), None)
        if rec is None:
            sys.exit(f"REFUSING: {ckpt} not logged in {run}/metrics.jsonl")
        path = os.path.join(run_dir, ckpt)
        got = C.sha256_file(path)
        if got != rec["ckpt_sha256"]:
            sys.exit(f"REFUSING: {path} sha256 {got} != logged {rec['ckpt_sha256']}")
        out.append((cid, path, got, rec, next(r for r in recs if r["step"] == 0), run_dir))
    return out


def blend(stock_sd, src_sd, alpha):
    """Float tensors: (1 - alpha) * stock + alpha * source (exact at alpha 0 and 1).
    Non-float tensors must be identical and are copied."""
    if stock_sd.keys() != src_sd.keys():
        sys.exit(f"REFUSING: state_dict keys differ: {sorted(stock_sd.keys() ^ src_sd.keys())[:5]}")
    out = {}
    for k, a in stock_sd.items():
        b = src_sd[k]
        if a.shape != b.shape or a.dtype != b.dtype:
            sys.exit(f"REFUSING: {k}: {a.shape}/{a.dtype} vs {b.shape}/{b.dtype}")
        if a.is_floating_point():
            out[k] = a * (1.0 - alpha) + b * alpha
        else:
            if not (a == b).all():
                sys.exit(f"REFUSING: non-float tensor {k} differs between stock and source")
            out[k] = a.clone()
    return out


def l2_from_stock(stock_sd, sd):
    """(absolute, relative) L2 distance over float tensors, accumulated in float64."""
    num = sum(float(((sd[k].double() - a.double()) ** 2).sum()) for k, a in stock_sd.items() if a.is_floating_point())
    den = sum(float((a.double() ** 2).sum()) for a in stock_sd.values() if a.is_floating_point())
    return num ** 0.5, (num / den) ** 0.5


def validate_multi(model, D, device):
    """train.validate's metrics at each threshold in THRESHOLDS from one set of probabilities.
    Returns (metrics at 0.5, {"0.4": {...}, "0.5": {...}, "0.6": {...}})."""
    P = {k: T.probs(model, D[f], device) for k, f in
         (("stu", "F_dstu"), ("flu", "F_dflu"), ("grd", "F_grd"), ("eow", "F_deow"), ("m3s", "F_dm3s"),
          ("crop", "F_dcrop"))}
    y = np.array([r["label"] for r in D["grd"]])
    by = {}
    for th in THRESHOLDS:
        r = lambda p: round(float((p > th).mean()), 4)  # noqa: E731
        by[f"{th:.1f}"] = {
            "dev_stutter_premature": r(P["stu"]), "n_dev_stutter": len(P["stu"]),
            "dev_eow_first_check_decide": r(P["eow"]), "n_dev_eow": len(P["eow"]),
            "dev_stu_completed_decide": r(P["m3s"]), "n_dev_m3s": len(P["m3s"]),
            "dev_eow_crop_decide": r(P["crop"]), "n_dev_eow_crop": len(P["crop"]),
            "dev_fluent_premature": r(P["flu"]), "n_dev_fluent": len(P["flu"]),
            "guard_recall": r(P["grd"][y == 1]), "n_guard_pos": int((y == 1).sum()),
            "guard_specificity": round(float((P["grd"][y == 0] <= th).mean()), 4),
            "n_guard_neg": int((y == 0).sum())}
    return by["0.5"], by


def clean_tree():
    st = subprocess.run(["git", "status", "--porcelain", "--", "model/train/", "benchmark/scripts/"],
                        cwd=C.ROOT, capture_output=True, text=True, check=True).stdout.strip()
    if st:
        sys.exit(f"REFUSING: uncommitted changes under model/train or benchmark/scripts:\n{st}")
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=C.ROOT, capture_output=True, text=True,
                          check=True).stdout.strip()


def stock_parity(load_from_onnx, onnx_path):
    from export import check_features
    model = load_from_onnx(onnx_path).eval()
    feats = check_features(os.path.join(C.BENCH, "items", "v1", "dev.jsonl"), 3)
    p_torch = C.torch_probs(model, feats)
    p_ort = C.ort_probs(C.ort_session(onnx_path), feats)
    err = float(np.max(np.abs(p_torch - p_ort)))
    if not err < PARITY_TOL:
        sys.exit(f"REFUSING: stock reconstruction parity {err} >= {PARITY_TOL}")
    return {"n": len(feats), "max_abs_error": err, "tol": PARITY_TOL}


def selftest(stock_sd, srcs, torch):
    for cid, path, *_ in srcs:
        src_sd = torch.load(path, map_location="cpu", weights_only=False)["state_dict"]
        b0, b1 = blend(stock_sd, src_sd, 0.0), blend(stock_sd, src_sd, 1.0)
        ok0 = all(torch.equal(b0[k], stock_sd[k]) for k in stock_sd)
        ok1 = all(torch.equal(b1[k], src_sd[k]) for k in src_sd)
        moved = sum(int(not torch.equal(stock_sd[k], src_sd[k])) for k in stock_sd)
        d_abs, d_rel = l2_from_stock(stock_sd, src_sd)
        print(json.dumps({"selftest": cid, "alpha0_equals_stock": ok0, "alpha1_equals_source": ok1,
                          "tensors_differing_stock_vs_source": moved, "tensors": len(stock_sd),
                          "source_l2_from_stock": round(d_abs, 6), "source_rel_l2_from_stock": round(d_rel, 8)}))
        if not (ok0 and ok1):
            sys.exit(1)
    print("SELFTEST PASS")


def promotion_a(work, cand, th):
    run, ckpt = cand.split("/")
    recs = [json.loads(l) for l in open(os.path.join(work, "runs", run, "metrics.jsonl")) if l.strip()]
    base = next(r for r in recs if r["step"] == 0)["by_threshold"]["0.5"]
    rec = next(r for r in recs if r.get("ckpt") == ckpt)["by_threshold"][f"{th:.1f}"]
    res = {k: {"label": lab, "candidate_at_threshold": rec[k], "stock_at_0.5": base[k],
               "delta": round(rec[k] - base[k], 4), "passed": rec[k] >= base[k] - PROMO_TOL - 1e-9}
           for k, lab in PROMO_KEYS}
    out = {"check": "D-010 promotion 1", "candidate": cand, "threshold": th, "rule": ">= stock@0.5 - 0.020",
           **res, "passed": all(v["passed"] for v in res.values())}
    print(json.dumps(out, indent=1))
    sys.exit(0 if out["passed"] else 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--haan")
    ap.add_argument("--work", required=True)
    ap.add_argument("--prescreen", help="prescreen JSON under --work whose top2 are the sources")
    ap.add_argument("--run-id")
    ap.add_argument("--alphas", type=float, nargs="+", default=DEFAULT_ALPHAS)
    ap.add_argument("--tie-rule", choices=["l2", "alpha_epoch"],
                    help="what the 'epoch' tie key holds (required for a run; frozen by review)")
    ap.add_argument("--data", default="data-v2", help="data dir under --work (validation sets only)")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--promotion-a", metavar="RUN/CKPT")
    ap.add_argument("--threshold", type=float, choices=THRESHOLDS)
    a = ap.parse_args()
    if a.promotion_a:
        if a.threshold is None:
            sys.exit("--promotion-a needs --threshold")
        return promotion_a(a.work, a.promotion_a, a.threshold)
    if not (a.haan and a.prescreen):
        sys.exit("--haan and --prescreen are required")
    if any(not 0.0 < x < 1.0 for x in a.alphas) or len(set(a.alphas)) != len(a.alphas):
        sys.exit("--alphas must be distinct values strictly between 0 and 1")

    import torch
    prescreen_path = os.path.join(a.work, a.prescreen)
    srcs = sources(a.work, prescreen_path)
    load_from_onnx, _ = C.import_haan(a.haan)
    stock_path = C.stock_fp32_path(a.work)  # verifies the pinned stock sha256
    stock = load_from_onnx(stock_path)
    # clone: on CPU .cpu() aliases the live parameters, which later load_state_dict calls overwrite
    stock_sd = {k: v.detach().cpu().clone() for k, v in stock.state_dict().items()}
    if a.selftest:
        return selftest(stock_sd, srcs, torch)

    if not a.run_id or not a.tie_rule:
        sys.exit("--run-id and --tie-rule are required for a run")
    head = clean_tree()
    parity = stock_parity(load_from_onnx, stock_path)
    run_dir = os.path.join(a.work, "runs", a.run_id)
    try:
        os.mkdir(run_dir)
    except FileExistsError:
        sys.exit(f"REFUSING: run directory exists: {run_dir}")

    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    device = T.pick_device()
    D = T.load_data(a.work, a.data)
    src_info = []
    for cid, path, sha, rec, _, sdir in srcs:
        rj = json.load(open(os.path.join(sdir, "run.json")))
        ck = torch.load(path, map_location="cpu", weights_only=False)
        src_info.append({"cand_id": cid, "sha256": sha, "epoch": rec["epoch"], "step": rec["step"],
                         "config_json_sha256": C.sha256_file(os.path.join(sdir, "config.json")),
                         "config_sha256": rj.get("config_sha256"), "run_code_commit": rj.get("code_commit"),
                         "train_manifest_sha256": ck.get("train_manifest_sha256"),
                         "init_sha256": json.load(open(os.path.join(sdir, "config.json"))).get("init_sha256")})
    if any(s["init_sha256"] != C.STOCK_FP32_SHA256 for s in src_info):
        sys.exit("REFUSING: a source run was not initialised from the pinned stock FP32")
    cfg = {"run_id": a.run_id, "method": "weight-space interpolation (WiSE-FT); no training",
           "formula": "theta = (1 - alpha) * theta_stock + alpha * theta_source (float tensors)",
           "alphas": a.alphas, "thresholds_recorded": THRESHOLDS, "tie_rule": a.tie_rule,
           "init": "stock-fp32 via haan", "init_sha256": C.STOCK_FP32_SHA256, "haan_commit": C.HAAN_COMMIT,
           "stock_reconstruction_parity": parity, "code_commit": head,
           "prescreen": a.prescreen, "prescreen_sha256": C.sha256_file(prescreen_path), "sources": src_info,
           "validation_data_dir": D["data_dir"], "validation_manifest_sha256": D["manifest_sha256"]}
    cfg_sha = C.sha256_bytes(json.dumps(cfg, sort_keys=True).encode())
    C.write_json(os.path.join(run_dir, "config.json"), cfg)
    metrics_f = open(os.path.join(run_dir, "metrics.jsonl"), "w")

    def log(rec):
        metrics_f.write(json.dumps(rec) + "\n")
        metrics_f.flush()
        print(json.dumps(rec), flush=True)

    t0 = time.time()
    model = stock.to(device)
    step0, by0 = validate_multi(model, D, device)
    if step0 != T.validate(model, D, device):
        sys.exit("REFUSING: multi-threshold validation at 0.5 differs from train.validate")
    for cid, _, _, _, s0, _ in srcs:  # same stock + sets -> identical step 0
        diff = {k: (v, s0.get(k)) for k, v in step0.items() if s0.get(k) != v}
        if diff:
            sys.exit(f"REFUSING: stock validation differs from {cid}'s step 0: {diff}")
    log({"step": 0, "epoch": 0.0, "kind": "validation", **step0, "by_threshold": by0})

    ckpts = []
    for (cid, path, sha, rec, _, _), info in zip(srcs, src_info):
        ck = torch.load(path, map_location="cpu", weights_only=False)
        src_tag = cid.replace("/ckpt-", "e").replace(".pt", "").replace("/", "")  # W3/ckpt-e1.00.pt -> W3e1.00
        for alpha in a.alphas:
            sd = blend(stock_sd, ck["state_dict"], alpha)
            d_abs, d_rel = l2_from_stock(stock_sd, sd)
            alpha_epoch = round(alpha * rec["epoch"], 3)
            epoch = round(d_rel, 8) if a.tie_rule == "l2" else alpha_epoch
            name = f"blend-a{alpha:.2f}-{src_tag}.pt"
            out = os.path.join(run_dir, name)
            interp = {"alpha": alpha, "source": cid, "source_sha256": sha, "stock_sha256": C.STOCK_FP32_SHA256,
                      "l2_from_stock": round(d_abs, 6), "rel_l2_from_stock": round(d_rel, 8),
                      "alpha_x_source_epoch": alpha_epoch, "tie_rule": a.tie_rule}
            torch.save({"state_dict": sd, "run_id": a.run_id, "step": None, "epoch": epoch,
                        "config_sha256": cfg_sha, "train_manifest_sha256": info["train_manifest_sha256"],
                        "interpolation": interp}, out)
            model.load_state_dict(sd)
            m05, by = validate_multi(model, D, device)
            r = {"step": None, "epoch": epoch, "kind": "checkpoint", "ckpt": name, "ckpt_sha256": C.sha256_file(out),
                 **interp, **m05, "by_threshold": by}
            ckpts.append(r)
            log(r)
    metrics_f.close()
    C.write_json(os.path.join(run_dir, "run.json"), {
        "run_id": a.run_id, "finished_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "wall_min": round((time.time() - t0) / 60, 2), "code_commit": C.git_commit(),
        "config_sha256": cfg_sha, "env": T.env_info(device), "checkpoints": [c["ckpt"] for c in ckpts]})
    print(f"RUN {a.run_id} done: {len(ckpts)} blends", flush=True)


if __name__ == "__main__":
    main()
