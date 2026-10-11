"""v5 preparation (D-014): short Smart Turn replay crops, their human audit gate, and a stock diagnostic.

Proposal: issue #2 comment 6104449057. Reviewable code; building crops is data preparation, not
training. No v5 training is authorized by this file.

  python model/train/v5_crops.py --work W build  --data data-v2 --out data-v5-crops
  python model/train/v5_crops.py --work W audit-export --crops data-v5-crops --out crop-audit-v1
  python model/train/v5_crops.py --work W audit-check  --worksheet crop-audit-v1/crop_audit.csv
  python model/train/v5_crops.py --work W stock-diagnostic --crops data-v5-crops [--limit N]
  python model/train/v5_crops.py --selftest

Crop rule (frozen in the proposal):
- source: Smart Turn replay rows only (`<data>/orig_replay.jsonl`); never the guard.
- a crop is a SUFFIX of the clip (the turn's ending, which carries the label, is unchanged).
- it starts at a Silero VAD speech onset that follows >= 0.15 s of non-speech, with 0.10 s of
  pre-roll (never reaching back past that pause's start); not within the first 0.5 s of the clip.
- length 1.0-4.0 s; at least 0.5 s of speech inside the crop.
- target length per row is drawn (seeded by sha256(seed:id)) from the empirical SEP training
  input-length distribution (sep_pos + stutter_neg, clipped to 1-4 s); the qualifying onset whose
  crop length is closest to the target is used (ties -> the later onset). No qualifying onset -> no crop.
Audit gate: 30 random crops per label are listened to by a named human with the full clip as
context; >= 27/30 (90%) per label must be "yes" (label still valid), else the crop family is unused.
The stock flip rate (full clip vs crop, at 0.5) is a reported diagnostic only, never a filter.
"""
import argparse
import csv
import hashlib
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

SR = C.SR
FRAME = 512                      # Silero frame at 16 kHz (32 ms)
VAD_THRESHOLD = 0.5
MIN_PAUSE_S = 0.15
PREROLL_S = 0.10
MIN_START_S = 0.50
MIN_LEN_S, MAX_LEN_S = 1.0, 4.0
MIN_SPEECH_S = 0.5
AUDIT_PER_LABEL = 30
AUDIT_PASS = 27                  # >= 90% of 30
DEFAULT_SEED = "v5-crops-1"
SILERO = os.path.join(C.ROOT, "agent", "models", "silero_vad.onnx")
SILERO_SHA256 = "2623a2953f6ff3d2c1e61740c6cdb7168133479b267dfef114a4a3cc5bdd788f"
AUDIT_FIELDS = ["audit_id", "crop_id", "claimed_label", "crop_wav", "context_wav", "crop_start_s",
                "crop_len_s", "reviewer", "reviewed_at", "label_still_valid", "notes"]


def seeded_u(seed, key):
    """Deterministic uniform [0, 1) from sha256(seed:key)."""
    return int(hashlib.sha256(f"{seed}:{key}".encode()).hexdigest()[:13], 16) / 16 ** 13


# ---------------------------------------------------------------- VAD and crop choice
class Silero:
    def __init__(self):
        import onnxruntime as ort
        if C.sha256_file(SILERO) != SILERO_SHA256:
            sys.exit(f"REFUSING: {SILERO} sha256 mismatch")
        so = ort.SessionOptions()
        so.inter_op_num_threads = so.intra_op_num_threads = 1
        self.sess = ort.InferenceSession(SILERO, sess_options=so, providers=["CPUExecutionProvider"])

    def mask(self, x):
        """Per-frame speech mask (prob >= 0.5), same streaming call pattern as agent/engine.py."""
        state = np.zeros((2, 1, 128), dtype=np.float32)
        ctx = np.zeros((1, 64), dtype=np.float32)
        out = []
        for i in range(len(x) // FRAME):
            f = x[i * FRAME:(i + 1) * FRAME].astype(np.float32)[None, :]
            inp = np.concatenate([ctx, f], axis=1)
            p, state = self.sess.run(None, {"input": inp, "state": state, "sr": np.array(SR, dtype=np.int64)})
            ctx = inp[:, -64:]
            out.append(float(p[0][0]) >= VAD_THRESHOLD)
        return np.array(out, dtype=bool)


def candidate_starts(mask, n_samples):
    """[(start_sample, crop_len_s, speech_s)] for every qualifying onset (pure function)."""
    out = []
    min_pause = int(np.ceil(MIN_PAUSE_S * SR / FRAME))
    run = 0
    for i, sp in enumerate(mask):
        if not sp:
            run += 1
            continue
        if i > 0 and not mask[i - 1] and run >= min_pause:
            pause_start = (i - run) * FRAME
            start = max(i * FRAME - int(PREROLL_S * SR), pause_start)
            length = (n_samples - start) / SR
            speech = float(mask[i:].sum()) * FRAME / SR
            if start >= MIN_START_S * SR and MIN_LEN_S <= length <= MAX_LEN_S and speech >= MIN_SPEECH_S:
                out.append((int(start), round(length, 4), round(speech, 4)))
        run = 0
    return out


def choose_start(cands, target_s):
    """Closest crop length to target; ties -> later start."""
    if not cands:
        return None
    return min(cands, key=lambda c: (abs(c[1] - target_s), -c[0]))


def sep_length_pool(data_dir):
    """Empirical SEP training input lengths (s), clipped to [MIN_LEN_S, MAX_LEN_S], sorted."""
    L = []
    for fn in ("sep_pos.jsonl", "stutter_neg.jsonl"):
        p = os.path.join(data_dir, fn)
        if not os.path.exists(p):
            continue
        for line in open(p):
            r = json.loads(line)
            s = min(r["keep_samples"], r["cut_samples"]) if r.get("keep_samples") else r["cut_samples"]
            L.append(min(max(s / SR, MIN_LEN_S), MAX_LEN_S))
    if not L:
        sys.exit(f"REFUSING: no SEP rows in {data_dir} to set target lengths")
    return np.sort(np.array(L))


def target_len(pool, seed, rid):
    return float(pool[min(int(seeded_u(seed, rid) * len(pool)), len(pool) - 1)])


def crop_audio(ref, work):
    """Model-input waveform for a crop reference."""
    x = C.read_audio(os.path.join(work, ref["audio"]))
    return x[ref["crop_start_samples"]:]


# ---------------------------------------------------------------- commands
def cmd_build(a):
    data = os.path.join(a.work, a.data)
    out = os.path.join(a.work, a.out)
    if os.path.exists(out):
        sys.exit(f"REFUSING: {out} exists")
    replay = [json.loads(l) for l in open(os.path.join(data, "orig_replay.jsonl"))]
    guard = [json.loads(l) for l in open(os.path.join(data, "guard.jsonl"))]
    guard_ids, guard_wavs = {r["id"] for r in guard}, {r["wav_sha256"] for r in guard}
    pool = sep_length_pool(data)
    vad = Silero()
    rows, skipped = [], 0
    for i, r in enumerate(replay):
        assert r["id"] not in guard_ids and r["wav_sha256"] not in guard_wavs, r["id"]
        x = C.read_audio(os.path.join(a.work, r["audio"]))
        tgt = target_len(pool, a.seed, r["id"])
        pick = choose_start(candidate_starts(vad.mask(x), len(x)), tgt)
        if pick is None:
            skipped += 1
            continue
        start, length, speech = pick
        pcm = (np.clip(x[start:], -1, 1) * 32767).round().astype("<i2").tobytes()
        rows.append({"id": f"crop-{r['id']}", "parent_id": r["id"], "audio": r["audio"],
                     "crop_start_samples": start, "n_samples": len(x) - start, "parent_n_samples": len(x),
                     "len_s": length, "target_len_s": round(tgt, 4), "speech_s": speech,
                     "label": r["label"], "endpoint_bool": r["endpoint_bool"], "dataset": r["dataset"],
                     "synthetic": r["synthetic"], "crop_pcm16_sha256": C.sha256_bytes(pcm)})
        if (i + 1) % 500 == 0:
            print(f"  {i + 1}/{len(replay)} replay rows, {len(rows)} crops", flush=True)
    os.makedirs(out)
    path = os.path.join(out, "replay_crops.jsonl")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(json.dumps(r, sort_keys=True) + "\n")
    lab = [r["label"] for r in rows]
    manifest = {"script": "model/train/v5_crops.py", "code_commit": C.git_commit(), "seed": a.seed,
                "source": {"data_dir": a.data, "orig_replay_sha256": C.sha256_file(os.path.join(data, "orig_replay.jsonl")),
                           "manifest_sha256": C.sha256_file(os.path.join(data, "manifest.json"))},
                "rule": {"vad": "silero (agent/models, sha pinned), frame 512, prob >= 0.5",
                         "min_pause_s": MIN_PAUSE_S, "preroll_s": PREROLL_S, "min_start_s": MIN_START_S,
                         "len_s": [MIN_LEN_S, MAX_LEN_S], "min_speech_s": MIN_SPEECH_S,
                         "target": "seeded draw from SEP input lengths clipped to [1, 4] s; closest onset, ties later"},
                "sep_target_quantiles_s": {q: round(float(np.quantile(pool, q)), 3) for q in (0.1, 0.25, 0.5, 0.75, 0.9)},
                "replay_rows": len(replay), "crops": len(rows), "skipped_no_onset": skipped,
                "crops_by_label": {"0": lab.count(0), "1": lab.count(1)},
                "len_quantiles_s": {q: round(float(np.quantile([r["len_s"] for r in rows], q)), 3)
                                    for q in (0.1, 0.25, 0.5, 0.75, 0.9)} if rows else None,
                "replay_crops_sha256": C.sha256_file(path),
                "guard_disjoint": True, "audit": "pending (audit-export, then audit-check)"}
    C.write_json(os.path.join(out, "manifest.json"), manifest)
    print(json.dumps({k: manifest[k] for k in ("crops", "skipped_no_onset", "crops_by_label", "len_quantiles_s")}))


def cmd_audit_export(a):
    import soundfile as sf
    crops = [json.loads(l) for l in open(os.path.join(a.work, a.crops, "replay_crops.jsonl"))]
    out = os.path.join(a.work, a.out)
    if os.path.exists(out):
        sys.exit(f"REFUSING: {out} exists")
    os.makedirs(os.path.join(out, "audio"))
    rows = []
    for lab, name in ((1, "complete"), (0, "incomplete")):
        pick = sorted([c for c in crops if c["label"] == lab], key=lambda c: seeded_u(a.seed + ":audit", c["id"]))
        if len(pick) < AUDIT_PER_LABEL:
            sys.exit(f"REFUSING: only {len(pick)} crops with label {lab}")
        for c in pick[:AUDIT_PER_LABEL]:
            aid = f"A{len(rows) + 1:02d}"
            full = C.read_audio(os.path.join(a.work, c["audio"]))
            sf.write(os.path.join(out, "audio", f"{aid}-crop.wav"), full[c["crop_start_samples"]:], SR, subtype="PCM_16")
            sf.write(os.path.join(out, "audio", f"{aid}-context.wav"), full, SR, subtype="PCM_16")
            rows.append({"audit_id": aid, "crop_id": c["id"], "claimed_label": name,
                         "crop_wav": f"audio/{aid}-crop.wav", "context_wav": f"audio/{aid}-context.wav",
                         "crop_start_s": round(c["crop_start_samples"] / SR, 3), "crop_len_s": c["len_s"],
                         "reviewer": "", "reviewed_at": "", "label_still_valid": "", "notes": ""})
    rows.sort(key=lambda r: seeded_u(a.seed + ":order", r["crop_id"]))  # interleave labels; ids/files unchanged
    with open(os.path.join(out, "crop_audit.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=AUDIT_FIELDS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    C.write_json(os.path.join(out, "README.json"), {
        "instructions": "For each row: listen to context_wav, then crop_wav. Does the crop alone still justify "
                        "claimed_label (complete = the speaker finished their turn; incomplete = they had more to say)? "
                        "label_still_valid: yes | no | unsure. Fill reviewer and reviewed_at (ISO date).",
        "gate": f">= {AUDIT_PASS}/{AUDIT_PER_LABEL} 'yes' per label; 'unsure' counts as not valid",
        "crops_manifest_sha256": C.sha256_file(os.path.join(a.work, a.crops, "manifest.json")),
        "seed": a.seed})
    print(f"wrote {len(rows)} audit rows to {out}")


def audit_result(rows):
    """Gate outcome from worksheet rows (pure function)."""
    res, problems = {}, []
    for name in ("complete", "incomplete"):
        rs = [r for r in rows if r["claimed_label"] == name]
        if len(rs) != AUDIT_PER_LABEL:
            problems.append(f"{name}: {len(rs)} rows, expected {AUDIT_PER_LABEL}")
        for r in rs:
            if not r["reviewer"].strip() or not r["reviewed_at"].strip():
                problems.append(f"{r['audit_id']}: reviewer/reviewed_at missing")
            if r["label_still_valid"].strip().lower() not in ("yes", "no", "unsure"):
                problems.append(f"{r['audit_id']}: label_still_valid must be yes/no/unsure")
        yes = sum(r["label_still_valid"].strip().lower() == "yes" for r in rs)
        res[name] = {"yes": yes, "n": len(rs), "passed": yes >= AUDIT_PASS}
    passed = not problems and all(v["passed"] for v in res.values())
    return {"per_label": res, "problems": problems, "rule": f">= {AUDIT_PASS}/{AUDIT_PER_LABEL} yes per label",
            "passed": passed}


def cmd_audit_check(a):
    path = os.path.join(a.work, a.worksheet)
    rows = list(csv.DictReader(open(path, newline="", encoding="utf-8")))
    out = audit_result(rows)
    out.update({"worksheet": a.worksheet, "worksheet_sha256": C.sha256_file(path),
                "reviewers": sorted({r["reviewer"] for r in rows if r["reviewer"]})})
    print(json.dumps(out, indent=1))
    sys.exit(0 if out["passed"] else 1)


def cmd_stock_diagnostic(a):
    crops = [json.loads(l) for l in open(os.path.join(a.work, a.crops, "replay_crops.jsonl"))]
    if a.limit:
        crops = sorted(crops, key=lambda c: seeded_u("diag", c["id"]))[:a.limit]
    sess = C.ort_session(C.stock_fp32_path(a.work))
    flips = {0: [0, 0], 1: [0, 0]}
    for i, c in enumerate(crops):
        full = C.read_audio(os.path.join(a.work, c["audio"]))
        p = C.ort_probs(sess, np.stack([C.features(full), C.features(full[c["crop_start_samples"]:])]))
        flips[c["label"]][0] += int((p[0] > 0.5) != (p[1] > 0.5))
        flips[c["label"]][1] += 1
        if (i + 1) % 500 == 0:
            print(f"  {i + 1}/{len(crops)}", flush=True)
    out = {"diagnostic": "stock FP32 decision flip rate, full clip vs crop, threshold 0.5 (report only; never a filter)",
           "n": len(crops), "by_label": {str(k): {"flips": v[0], "n": v[1], "rate": round(v[0] / max(v[1], 1), 4)}
                                         for k, v in flips.items()}}
    C.write_json(os.path.join(a.work, a.crops, "stock_diagnostic.json"), out)
    print(json.dumps(out, indent=1))


def selftest():
    fps = SR / FRAME  # frames per second
    def m(spans, total_s):  # speech spans in seconds -> mask
        n = int(total_s * fps)
        x = np.zeros(n, dtype=bool)
        for s, e in spans:
            x[int(s * fps):int(e * fps)] = True
        return x, int(total_s * SR)
    ok = True
    # onsets after >= 0.15 s pauses at 2.0 s and 4.0 s in a 6 s clip
    mask, n = m([(0.1, 1.8), (2.0, 3.7), (4.0, 5.8)], 6.0)
    c = candidate_starts(mask, n)
    lens = [round(x[1], 1) for x in c]
    # the 2.0 s onset would give a 4.1 s crop (> 4 s), so only the 4.0 s onset (2.1 s crop) qualifies
    ok &= check("only the in-range onset qualifies (2.1 s crop)", lens == [2.1], f"{lens}")
    ok &= check("crop length bounded to [1, 4] s", all(MIN_LEN_S <= x[1] <= MAX_LEN_S for x in c), f"{c}")
    ok &= check("choose_start closest to target", choose_start(c, 2.0)[1] == c[-1][1])
    # a pause shorter than 0.15 s does not create an onset
    mask2, n2 = m([(0.1, 2.9), (3.0, 5.0)], 5.2)
    ok &= check("pause < 0.15 s ignored", candidate_starts(mask2, n2) == [], f"{candidate_starts(mask2, n2)}")
    # onset within the first 0.5 s is not a crop
    mask3, n3 = m([(0.3, 2.0)], 2.5)
    ok &= check("no crop starting in the first 0.5 s", candidate_starts(mask3, n3) == [])
    # too little speech in the crop
    mask4, n4 = m([(0.1, 2.0), (2.5, 2.7)], 4.0)
    ok &= check("crop needs >= 0.5 s speech", candidate_starts(mask4, n4) == [])
    # pre-roll never reaches back past the pause start
    mask5, n5 = m([(0.1, 1.95), (2.12, 3.5)], 4.0)
    c5 = candidate_starts(mask5, n5)
    ok &= check("pre-roll stays inside the pause", bool(c5) and c5[0][0] >= int(1.95 * fps) * FRAME, f"{c5}")
    # audit gate
    def rows(yes_c, yes_i, unsure=0):
        out = []
        for name, yes in (("complete", yes_c), ("incomplete", yes_i)):
            for k in range(AUDIT_PER_LABEL):
                v = "yes" if k < yes else ("unsure" if k < yes + unsure else "no")
                out.append({"audit_id": f"{name[0]}{k}", "claimed_label": name, "reviewer": "r",
                            "reviewed_at": "2026-10-11", "label_still_valid": v})
        return out
    ok &= check("audit 27/30 both labels passes", audit_result(rows(27, 30))["passed"])
    ok &= check("audit 26/30 fails", not audit_result(rows(30, 26))["passed"])
    ok &= check("audit 'unsure' counts as not valid", not audit_result(rows(30, 26, unsure=4))["passed"])
    r = rows(30, 30); r[0]["reviewer"] = ""
    ok &= check("audit requires reviewer", not audit_result(r)["passed"])
    ok &= check("seeded draw is deterministic", seeded_u("s", "a") == seeded_u("s", "a") != seeded_u("t", "a"))
    print("SELFTEST " + ("PASSED" if ok else "FAILED"))
    sys.exit(0 if ok else 1)


def check(name, cond, detail=""):
    print(f"  {'ok' if cond else 'FAIL'}: {name}" + (f" ({detail})" if detail and not cond else ""))
    return bool(cond)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work")
    ap.add_argument("--selftest", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    b = sub.add_parser("build")
    b.add_argument("--data", default="data-v2")
    b.add_argument("--out", default="data-v5-crops")
    b.add_argument("--seed", default=DEFAULT_SEED)
    e = sub.add_parser("audit-export")
    e.add_argument("--crops", default="data-v5-crops")
    e.add_argument("--out", default="crop-audit-v1")
    e.add_argument("--seed", default=DEFAULT_SEED)
    k = sub.add_parser("audit-check")
    k.add_argument("--worksheet", required=True)
    d = sub.add_parser("stock-diagnostic")
    d.add_argument("--crops", default="data-v5-crops")
    d.add_argument("--limit", type=int)
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.work or not a.cmd:
        ap.error("--work and a command are required (or --selftest)")
    {"build": cmd_build, "audit-export": cmd_audit_export, "audit-check": cmd_audit_check,
     "stock-diagnostic": cmd_stock_diagnostic}[a.cmd](a)


if __name__ == "__main__":
    main()
