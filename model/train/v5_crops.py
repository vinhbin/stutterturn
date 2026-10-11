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
FALLBACK_RULE = "shortest_onset_for_short_targets"  # Niko, #2 02:56Z: one fallback, then report and stop
SEP_SHARES = {"stutter_neg.jsonl": 0.5, "sep_pos.jsonl": 0.5}  # W3: p_neg = p_pos = 0.10 -> equal SEP shares
SHORT_S, SHORT_MIN_FRAC = 2.0, 0.25   # gate: >= 25% of built crops under 2.0 s, per label
PREROLL_S = 0.10
MIN_START_S = 0.50
MIN_LEN_S, MAX_LEN_S = 1.0, 4.0
MIN_SPEECH_S = 0.5
AUDIT_PER_LABEL = 30
AUDIT_PASS = 27                  # >= 90% of 30
DEFAULT_SEED = "v5-crops-1"
HELDOUT_SHOW = "IStutterSoWhat"   # dev2 (build_dev2_items.py); never shapes training inputs
HELDOUT_KEYS = os.path.join(C.BENCH, "items", "dev2-v1", "heldout_keys.txt")
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


def candidate_starts(mask, n_samples, min_pause_s=MIN_PAUSE_S):
    """[(start_sample, crop_len_s, speech_s)] for every qualifying onset (pure function)."""
    out = []
    min_pause = int(np.ceil(min_pause_s * SR / FRAME))
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


def effective_pause_s(pause_s):
    """The pause actually required after rounding up to whole 32 ms frames (0.15 -> 0.16 s)."""
    return round(int(np.ceil(pause_s * SR / FRAME)) * FRAME / SR, 4)


def choose_start(cands, target_s, shortest_for_short=False):
    """Closest crop length to target; ties -> later start. Fallback rule: when the target is under
    SHORT_S, take the shortest qualifying onset (all candidates are already >= MIN_LEN_S)."""
    if not cands:
        return None
    if shortest_for_short and target_s < SHORT_S:
        return min(cands, key=lambda c: (c[1], -c[0]))
    return min(cands, key=lambda c: (abs(c[1] - target_s), -c[0]))


def heldout_keys():
    """dev2 held-out clip keys: heldout_keys.txt when built, else every train-split clip of the show."""
    if os.path.exists(HELDOUT_KEYS):
        return {l.strip() for l in open(HELDOUT_KEYS) if l.strip()}
    import csv as _csv
    return {r["clip_key"] for r in _csv.DictReader(open(os.path.join(C.BENCH, "splits", "v1", "train.csv"), newline=""))
            if r["show"] == HELDOUT_SHOW}


def sep_length_pool(data_dir, exclude=frozenset(), info=None, shares=SEP_SHARES):
    """SEP training input-length distribution as the W3 mixture draws it: each source gets its share,
    rows within a source by their weight; held-out clips excluded; lengths clipped to [1, 4] s.
    Returns (sorted lengths, cumulative probabilities)."""
    L, W, dropped = [], [], 0
    for fn, share in shares.items():
        p = os.path.join(data_dir, fn)
        if not os.path.exists(p):
            sys.exit(f"REFUSING: {fn} missing in {data_dir}")
        ls, ws = [], []
        for line in open(p):
            r = json.loads(line)
            if r["clip_key"] in exclude:
                dropped += 1
                continue
            s = min(r["keep_samples"], r["cut_samples"]) if r.get("keep_samples") else r["cut_samples"]
            ls.append(min(max(s / SR, MIN_LEN_S), MAX_LEN_S))
            ws.append(float(r.get("weight", 1.0)))
        if not ls:
            sys.exit(f"REFUSING: no usable rows in {fn}")
        tot = sum(ws)
        L += ls
        W += [share * w / tot for w in ws]
    order = np.argsort(L, kind="stable")
    lens, cdf = np.array(L)[order], np.cumsum(np.array(W)[order])
    cdf /= cdf[-1]
    if info is not None:
        info.update({"rows_used": len(L), "heldout_rows_excluded": dropped, "source_shares": shares,
                     "within_source": "row weight (as the W3 mixture draws)"})
    return lens, cdf


def pool_quantile(pool, q):
    lens, cdf = pool
    return float(lens[min(int(np.searchsorted(cdf, q, side="left")), len(lens) - 1)])


def target_len(pool, seed, rid):
    return pool_quantile(pool, seeded_u(seed, rid))


def select_crops(replay, masks, pool, seed, min_pause_s, shortest_for_short=False):
    """Crop rows for one rule (pure given VAD masks)."""
    rows = []
    for r, (mask, n) in zip(replay, masks):
        tgt = target_len(pool, seed, r["id"])
        pick = choose_start(candidate_starts(mask, n, min_pause_s), tgt, shortest_for_short)
        if pick is None:
            continue
        start, length, speech = pick
        rows.append({"id": f"crop-{r['id']}", "parent_id": r["id"], "audio": r["audio"],
                     "crop_start_samples": start, "n_samples": n - start, "parent_n_samples": n,
                     "len_s": length, "target_len_s": round(tgt, 4), "speech_s": speech, "min_pause_s": min_pause_s,
                     "choice_rule": FALLBACK_RULE if shortest_for_short else "closest_to_target",
                     "label": r["label"], "endpoint_bool": r["endpoint_bool"], "dataset": r["dataset"],
                     "synthetic": r["synthetic"]})
    return rows


def length_gate(rows):
    """Niko's build gate: >= SHORT_MIN_FRAC of crops under SHORT_S, for each label (pure)."""
    out = {}
    for lab in (0, 1):
        L = [r["len_s"] for r in rows if r["label"] == lab]
        frac = sum(x < SHORT_S for x in L) / len(L) if L else 0.0
        out[str(lab)] = {"n": len(L), "frac_under_2s": round(frac, 4), "passed": bool(L) and frac >= SHORT_MIN_FRAC}
    return {**out, "passed": all(v["passed"] for v in out.values())}


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
    held = heldout_keys()
    pool_info = {"heldout_show": HELDOUT_SHOW, "heldout_keys": len(held),
                 "heldout_source": HELDOUT_KEYS if os.path.exists(HELDOUT_KEYS) else "splits/v1/train.csv (show filter)"}
    pool = sep_length_pool(data, held, pool_info)
    vad = Silero()
    masks = []  # one VAD pass per clip; both rules reuse it
    for i, r in enumerate(replay):
        assert r["id"] not in guard_ids and r["wav_sha256"] not in guard_wavs, r["id"]
        x = C.read_audio(os.path.join(a.work, r["audio"]))
        masks.append((vad.mask(x), len(x)))
        if (i + 1) % 500 == 0:
            print(f"  VAD {i + 1}/{len(replay)}", flush=True)
    attempts = []
    for rule, shortest in (("closest_to_target", False), (FALLBACK_RULE, True)):  # one fallback, then stop
        rows = select_crops(replay, masks, pool, a.seed, MIN_PAUSE_S, shortest)
        skipped = len(replay) - len(rows)
        gate = length_gate(rows)
        attempts.append({"choice_rule": rule, "min_pause_s": MIN_PAUSE_S,
                         "effective_min_pause_s": effective_pause_s(MIN_PAUSE_S), "crops": len(rows),
                         "skipped_no_onset": skipped, "length_gate": gate})
        print(json.dumps(attempts[-1]), flush=True)
        if gate["passed"]:
            break
    os.makedirs(out)
    if not attempts[-1]["length_gate"]["passed"]:
        C.write_json(os.path.join(out, "manifest.json"), {
            "script": "model/train/v5_crops.py", "code_commit": C.git_commit(), "seed": a.seed,
            "status": "FAILED length gate with closest-to-target and with the shortest-onset fallback: "
                      "report and stop (no crops written)",
            "attempts": attempts})
        sys.exit("length gate failed with both rules: crops not written; report and stop (pre-registered)")
    for r in rows:  # hash the chosen crops' audio
        x = C.read_audio(os.path.join(a.work, r["audio"]))[r["crop_start_samples"]:]
        r["crop_pcm16_sha256"] = C.sha256_bytes((np.clip(x, -1, 1) * 32767).round().astype("<i2").tobytes())
    path = os.path.join(out, "replay_crops.jsonl")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(json.dumps(r, sort_keys=True) + "\n")
    lab = [r["label"] for r in rows]
    manifest = {"script": "model/train/v5_crops.py", "code_commit": C.git_commit(), "seed": a.seed,
                "source": {"data_dir": a.data, "orig_replay_sha256": C.sha256_file(os.path.join(data, "orig_replay.jsonl")),
                           "manifest_sha256": C.sha256_file(os.path.join(data, "manifest.json"))},
                "rule": {"vad": "silero (agent/models, sha pinned), frame 512, prob >= 0.5",
                         "min_pause_s": MIN_PAUSE_S, "effective_min_pause_s": effective_pause_s(MIN_PAUSE_S),
                         "choice_rule_used": attempts[-1]["choice_rule"], "preroll_s": PREROLL_S, "min_start_s": MIN_START_S,
                         "len_s": [MIN_LEN_S, MAX_LEN_S], "min_speech_s": MIN_SPEECH_S,
                         "target": "seeded draw from the weighted SEP input-length distribution (held-out show "
                                   "excluded), clipped to [1, 4] s; closest onset, ties later"},
                "sep_length_pool": pool_info,
                "sep_target_quantiles_s": {q: round(pool_quantile(pool, q), 3) for q in (0.1, 0.25, 0.5, 0.75, 0.9)},
                "replay_rows": len(replay), "crops": len(rows), "skipped_no_onset": skipped,
                "crops_by_label": {"0": lab.count(0), "1": lab.count(1)},
                "len_quantiles_s": {q: round(float(np.quantile([r["len_s"] for r in rows], q)), 3)
                                    for q in (0.1, 0.25, 0.5, 0.75, 0.9)} if rows else None,
                "replay_crops_sha256": C.sha256_file(path),
                "length_gate_rule": f">= {SHORT_MIN_FRAC:.0%} of crops under {SHORT_S} s per label; one fallback: "
                                    f"shortest qualifying onset for rows with target < {SHORT_S} s, then report and stop "
                                    f"(Niko, #2 2026-10-11T02:56Z)",
                "attempts": attempts,
                "guard_disjoint": True, "audit": "pending (audit-export, then audit-check)"}
    C.write_json(os.path.join(out, "manifest.json"), manifest)
    print(json.dumps({k: manifest[k] for k in ("crops", "skipped_no_onset", "crops_by_label", "len_quantiles_s", "attempts")}))


def audit_sample(crops, seed):
    """The seeded audit sample: {label: [crop rows]} (first AUDIT_PER_LABEL by sha256(seed:audit:id))."""
    out = {}
    for lab in (1, 0):
        pick = sorted([c for c in crops if c["label"] == lab], key=lambda c: seeded_u(seed + ":audit", c["id"]))
        if len(pick) < AUDIT_PER_LABEL:
            sys.exit(f"REFUSING: only {len(pick)} crops with label {lab}")
        out[lab] = pick[:AUDIT_PER_LABEL]
    return out


def cmd_audit_export(a):
    import soundfile as sf
    crops = [json.loads(l) for l in open(os.path.join(a.work, a.crops, "replay_crops.jsonl"))]
    out = os.path.join(a.work, a.out)
    if os.path.exists(out):
        sys.exit(f"REFUSING: {out} exists")
    os.makedirs(os.path.join(out, "audio"))
    rows = []
    sample = audit_sample(crops, a.seed)
    for lab, name in ((1, "complete"), (0, "incomplete")):
        for c in sample[lab]:
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
    crops_dir = os.path.join(a.work, a.crops)
    res_path = os.path.join(crops_dir, "audit_result.json")
    if os.path.exists(res_path):
        sys.exit(f"REFUSING: {res_path} exists (one audit result per crop build)")
    rows = list(csv.DictReader(open(path, newline="", encoding="utf-8")))
    readme = json.load(open(os.path.join(os.path.dirname(path), "README.json")))
    crops_manifest_sha = C.sha256_file(os.path.join(crops_dir, "manifest.json"))
    built = {json.loads(l)["id"]: json.loads(l) for l in open(os.path.join(crops_dir, "replay_crops.jsonl"))}
    binding = {
        "worksheet_exported_from_this_build": readme.get("crops_manifest_sha256") == crops_manifest_sha,
        "all_crop_ids_in_build": all(r["crop_id"] in built for r in rows),
        "claimed_labels_match_build": all(r["crop_id"] in built and
                                          {"complete": 1, "incomplete": 0}[r["claimed_label"]] == built[r["crop_id"]]["label"]
                                          for r in rows),
        "no_duplicate_crops": len({r["crop_id"] for r in rows}) == len(rows),
        "no_duplicate_audit_ids": len({r["audit_id"] for r in rows}) == len(rows),
        "matches_seeded_export_sample": {(r["crop_id"], r["claimed_label"]) for r in rows} == {
            (c["id"], "complete" if lab == 1 else "incomplete")
            for lab, cs in audit_sample(list(built.values()), readme.get("seed", "")).items() for c in cs}}
    out = audit_result(rows)
    out.update({"binding": binding, "passed": out["passed"] and all(binding.values()),
                "worksheet": a.worksheet, "worksheet_sha256": C.sha256_file(path),
                "crops_manifest_sha256": crops_manifest_sha,
                "reviewers": sorted({r["reviewer"] for r in rows if r["reviewer"]}),
                "code_commit": C.git_commit()})
    C.write_json(res_path, out)
    print(json.dumps(out, indent=1))
    sys.exit(0 if out["passed"] else 1)


def require_audit(work, crops):
    """For the (future) v5 mixture builder: refuse crops without a passing, build-bound audit."""
    d = os.path.join(work, crops)
    p = os.path.join(d, "audit_result.json")
    if not os.path.exists(p):
        sys.exit(f"REFUSING: {crops} has no audit_result.json (run audit-export, human review, audit-check)")
    r = json.load(open(p))
    if not r.get("passed") or r.get("crops_manifest_sha256") != C.sha256_file(os.path.join(d, "manifest.json")):
        sys.exit(f"REFUSING: {crops} audit failed or is bound to a different build")
    return r


def cmd_stock_diagnostic(a):
    res_path = os.path.join(a.work, a.crops, "stock_diagnostic.json")
    if os.path.exists(res_path):
        sys.exit(f"REFUSING: {res_path} exists")
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
    C.write_json(res_path, out)
    print(json.dumps(out, indent=1))


def assert_outside_repo(work):
    w, root = os.path.realpath(work), os.path.realpath(C.ROOT)
    if os.path.commonpath([w, root]) == root:
        sys.exit(f"REFUSING: --work {work} is inside the repo; audio/feature caches must stay outside git")


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
    # pause parameter and frame rounding (0.15 s requires 0.16 s after rounding)
    mask6, n6 = m([(0.1, 2.0), (2.13, 4.0)], 4.5)
    ok &= check("0.12 s pause: rejected at 0.15 s", candidate_starts(mask6, n6, 0.15) == [])
    ok &= check("0.12 s pause: accepted at 0.10 s", len(candidate_starts(mask6, n6, 0.10)) == 1)
    g_rows = [{"label": l, "len_s": x} for l in (0, 1) for x in (1.5, 2.5, 3.0, 3.5)]
    ok &= check("effective pause 0.15 -> 0.16 s", effective_pause_s(0.15) == 0.16)
    cands = [(48000, 1.2, 1.0), (32000, 2.2, 1.5), (16000, 3.2, 2.0)]
    ok &= check("closest rule picks 2.2 s for a 1.8 s target", choose_start(cands, 1.8)[1] == 2.2)
    ok &= check("fallback picks the shortest (1.2 s) for a 1.8 s target", choose_start(cands, 1.8, True)[1] == 1.2)
    ok &= check("fallback leaves targets >= 2 s on the closest rule", choose_start(cands, 3.0, True)[1] == 3.2)
    ok &= check("length gate passes at 25% under 2 s", length_gate(g_rows)["passed"])
    g_rows[0]["len_s"] = 2.2
    ok &= check("length gate fails if one label < 25%", not length_gate(g_rows)["passed"])
    # held-out show never shapes target lengths
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        with open(os.path.join(td, "sep_pos.jsonl"), "w") as f:
            f.write(json.dumps({"clip_key": "Keep_1_1", "cut_samples": 32000, "weight": 1.0}) + "\n")
            f.write(json.dumps({"clip_key": "IStutterSoWhat_1_1", "cut_samples": 16000, "weight": 1.0}) + "\n")
        with open(os.path.join(td, "stutter_neg.jsonl"), "w") as f:
            f.write(json.dumps({"clip_key": "Keep_2_1", "cut_samples": 48000, "weight": 3.0}) + "\n")
            f.write(json.dumps({"clip_key": "Keep_2_2", "cut_samples": 64000, "weight": 1.0}) + "\n")
        info = {}
        pl = sep_length_pool(td, {"IStutterSoWhat_1_1"}, info)
        ok &= check("held-out rows excluded from the length pool", 1.0 not in list(pl[0]) and info["heldout_rows_excluded"] == 1)
        # shares 0.5/0.5; within stutter_neg weights 3:1 -> P(2.0)=0.5, P(3.0)=0.375, P(4.0)=0.125
        ok &= check("pool weighted by source share and row weight",
                    np.allclose(pl[1], [0.5, 0.875, 1.0]) and pool_quantile(pl, 0.6) == 3.0, f"{pl}")
        # audit result is bound to the build
        cd = os.path.join(td, "crops"); wd = os.path.join(td, "audit"); os.makedirs(cd); os.makedirs(wd)
        C.write_json(os.path.join(cd, "manifest.json"), {"x": 1})
        built = [{"id": f"crop-{l}{k}", "label": l} for l in (0, 1) for k in range(AUDIT_PER_LABEL + 5)]
        with open(os.path.join(cd, "replay_crops.jsonl"), "w") as f:
            f.writelines(json.dumps(r) + "\n" for r in built)
        def run_check(rows, readme_sha):
            C.write_json(os.path.join(wd, "README.json"), {"crops_manifest_sha256": readme_sha, "seed": "s"})
            with open(os.path.join(wd, "crop_audit.csv"), "w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=AUDIT_FIELDS, lineterminator="\n"); w.writeheader()
                w.writerows({**{k: "" for k in AUDIT_FIELDS}, **r} for r in rows)
            rp = os.path.join(cd, "audit_result.json")
            if os.path.exists(rp):
                os.remove(rp)
            ns = argparse.Namespace(work=td, worksheet="audit/crop_audit.csv", crops="crops")
            try:
                cmd_audit_check(ns)
            except SystemExit as e:
                return e.code == 0, json.load(open(rp)) if os.path.exists(rp) else None
        smp = audit_sample(built, "s")
        good = [{"audit_id": f"A{i}", "crop_id": c["id"], "claimed_label": "complete" if c["label"] else "incomplete",
                 "reviewer": "r", "reviewed_at": "2026-10-11", "label_still_valid": "yes"}
                for i, c in enumerate(smp[1] + smp[0])]
        msha = C.sha256_file(os.path.join(cd, "manifest.json"))
        import contextlib, io as _io
        with contextlib.redirect_stdout(_io.StringIO()):
            p1, r1 = run_check(good, msha)
            p2, _ = run_check(good, "0" * 64)
            bad = [dict(r) for r in good]; bad[0]["crop_id"] = "crop-not-built"
            p3, _ = run_check(bad, msha)
            notseeded = [dict(r) for r in good]
            notseeded[0]["crop_id"] = next(c["id"] for c in built if c["label"] == 1 and c not in smp[1])
            p4, _ = run_check(notseeded, msha)
            dup = [dict(r) for r in good]; dup[1]["audit_id"] = dup[0]["audit_id"]
            p5, _ = run_check(dup, msha)
        ok &= check("audit bound to this build passes and is written", p1 and r1 and r1["passed"])
        ok &= check("audit from another build refused", not p2)
        ok &= check("audit naming an unbuilt crop refused", not p3)
        ok &= check("audit with a built but non-sampled crop refused", not p4)
        ok &= check("audit with duplicate audit_ids refused", not p5)
        ok &= check("require_audit refuses a failed audit", _refuses(lambda: require_audit(td, "crops")))
        with contextlib.redirect_stdout(_io.StringIO()):
            run_check(good, msha)
        ok &= check("require_audit accepts a passing, build-bound audit", require_audit(td, "crops")["passed"])
        C.write_json(os.path.join(cd, "manifest.json"), {"x": 2})  # the build changed after the audit
        ok &= check("require_audit refuses after the build changes", _refuses(lambda: require_audit(td, "crops")))
    ok &= check("--work inside the repo refused", _refuses(lambda: assert_outside_repo(C.ROOT)))
    ok &= check("seeded draw is deterministic", seeded_u("s", "a") == seeded_u("s", "a") != seeded_u("t", "a"))
    print("SELFTEST " + ("PASSED" if ok else "FAILED"))
    sys.exit(0 if ok else 1)


def _refuses(fn):
    try:
        fn()
    except SystemExit:
        return True
    return False


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
    k.add_argument("--crops", default="data-v5-crops")
    d = sub.add_parser("stock-diagnostic")
    d.add_argument("--crops", default="data-v5-crops")
    d.add_argument("--limit", type=int)
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.work or not a.cmd:
        ap.error("--work and a command are required (or --selftest)")
    assert_outside_repo(a.work)
    {"build": cmd_build, "audit-export": cmd_audit_export, "audit-check": cmd_audit_check,
     "stock-diagnostic": cmd_stock_diagnostic}[a.cmd](a)


if __name__ == "__main__":
    main()
