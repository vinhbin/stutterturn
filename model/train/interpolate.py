"""Weight-space interpolation of stock FP32 and fine-tuned checkpoints (proposed v4; issue #2
comment 6103360382). No training: theta = (1 - alpha) * theta_stock + alpha * theta_source.

  python model/train/interpolate.py --haan H --work W --prescreen prescreen-v3.json --run-id X4
  python model/train/interpolate.py --haan H --work W --prescreen prescreen-v3.json --selftest

Sources are the prescreen's top 2 (fixed before the selection that followed it), each verified
against the ckpt_sha256 its run logged. Grid: --alphas (default 0.25 0.50 0.75), nothing else.

Writes W/runs/<run_id>/{config.json, metrics.jsonl, blend-*.pt, run.json} in train.py's format,
so prescreen.py and export.py consume it unchanged: a step-0 validation record (stock; asserted
equal to the source run's step 0) and one "checkpoint" record per blend. The "epoch" field of a
blend is alpha * source epoch ("effective epochs from stock"): the selector's and prescreen's
"ties -> earlier" then prefer the blend closer to stock. Refuses an existing run directory.
--selftest checks weights only (alpha 0 == stock, alpha 1 == source, bit-exact); no dev data.
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402
import train as T  # noqa: E402

DEFAULT_ALPHAS = [0.25, 0.50, 0.75]


def sources(work, prescreen_path):
    """[(cand_id, path, sha256, metrics record, step-0 record)] for the prescreen top 2."""
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
        out.append((cid, path, got, rec, next(r for r in recs if r["step"] == 0)))
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


def selftest(stock_sd, srcs, torch):
    for cid, path, _, _, _ in srcs:
        src_sd = torch.load(path, map_location="cpu", weights_only=False)["state_dict"]
        b0, b1 = blend(stock_sd, src_sd, 0.0), blend(stock_sd, src_sd, 1.0)
        ok0 = all(torch.equal(b0[k], stock_sd[k]) for k in stock_sd)
        ok1 = all(torch.equal(b1[k], src_sd[k]) for k in src_sd)
        moved = sum(int(not torch.equal(stock_sd[k], src_sd[k])) for k in stock_sd)
        print(json.dumps({"selftest": cid, "alpha0_equals_stock": ok0, "alpha1_equals_source": ok1,
                          "tensors_differing_stock_vs_source": moved, "tensors": len(stock_sd)}))
        if not (ok0 and ok1):
            sys.exit(1)
    print("SELFTEST PASS")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--haan", required=True)
    ap.add_argument("--work", required=True)
    ap.add_argument("--prescreen", required=True, help="prescreen JSON under --work whose top2 are the sources")
    ap.add_argument("--run-id")
    ap.add_argument("--alphas", type=float, nargs="+", default=DEFAULT_ALPHAS)
    ap.add_argument("--data", default="data-v2", help="data dir under --work (validation sets only)")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if any(not 0.0 < x < 1.0 for x in a.alphas) or len(set(a.alphas)) != len(a.alphas):
        sys.exit("--alphas must be distinct values strictly between 0 and 1")

    import torch
    prescreen_path = os.path.join(a.work, a.prescreen)
    srcs = sources(a.work, prescreen_path)
    load_from_onnx, _ = C.import_haan(a.haan)
    stock = load_from_onnx(C.stock_fp32_path(a.work))  # verifies the pinned stock sha256
    stock_sd = {k: v.detach().cpu() for k, v in stock.state_dict().items()}
    if a.selftest:
        return selftest(stock_sd, srcs, torch)

    if not a.run_id:
        sys.exit("--run-id required")
    run_dir = os.path.join(a.work, "runs", a.run_id)
    try:
        os.mkdir(run_dir)
    except FileExistsError:
        sys.exit(f"REFUSING: run directory exists: {run_dir}")

    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    device = T.pick_device()
    D = T.load_data(a.work, a.data)
    cfg = {"run_id": a.run_id, "method": "weight-space interpolation (WiSE-FT); no training",
           "formula": "theta = (1 - alpha) * theta_stock + alpha * theta_source (float tensors)",
           "alphas": a.alphas, "init": "stock-fp32 via haan", "init_sha256": C.STOCK_FP32_SHA256,
           "prescreen": a.prescreen, "prescreen_sha256": C.sha256_file(prescreen_path),
           "sources": [{"cand_id": cid, "sha256": sha, "epoch": rec["epoch"]} for cid, _, sha, rec, _ in srcs],
           "epoch_field": "alpha * source epoch (ties -> closer to stock)",
           "validation_data_dir": D["data_dir"], "validation_manifest_sha256": D["manifest_sha256"]}
    cfg_sha = C.sha256_bytes(json.dumps(cfg, sort_keys=True).encode())
    C.write_json(os.path.join(run_dir, "config.json"), cfg)
    metrics_f = open(os.path.join(run_dir, "metrics.jsonl"), "w")

    def log(rec):
        metrics_f.write(json.dumps(rec) + "\n")
        metrics_f.flush()
        print(json.dumps(rec), flush=True)

    t0 = time.time()
    model = load_from_onnx(C.stock_fp32_path(a.work)).to(device)
    step0 = T.validate(model, D, device)
    for cid, _, _, _, s0 in srcs:  # same stock, same validation sets -> identical step 0
        diff = {k: (v, s0.get(k)) for k, v in step0.items() if s0.get(k) != v}
        if diff:
            sys.exit(f"REFUSING: stock validation differs from {cid}'s step 0: {diff}")
    log({"step": 0, "epoch": 0.0, "kind": "validation", **step0})

    ckpts = []
    for cid, path, sha, rec, _ in srcs:
        ck = torch.load(path, map_location="cpu", weights_only=False)
        src_tag = cid.replace("/ckpt-", "e").replace(".pt", "").replace("/", "")  # W3/ckpt-e1.00.pt -> W3e1.00
        for alpha in a.alphas:
            sd = blend(stock_sd, ck["state_dict"], alpha)
            name = f"blend-a{alpha:.2f}-{src_tag}.pt"
            out = os.path.join(run_dir, name)
            epoch = round(alpha * rec["epoch"], 3)
            torch.save({"state_dict": sd, "run_id": a.run_id, "step": None, "epoch": epoch,
                        "config_sha256": cfg_sha, "train_manifest_sha256": ck.get("train_manifest_sha256"),
                        "interpolation": {"alpha": alpha, "source": cid, "source_sha256": sha,
                                          "stock_sha256": C.STOCK_FP32_SHA256}}, out)
            model.load_state_dict(sd)
            r = {"step": None, "epoch": epoch, "kind": "checkpoint", "ckpt": name, "ckpt_sha256": C.sha256_file(out),
                 "alpha": alpha, "source": cid, "source_sha256": sha, **T.validate(model, D, device)}
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
