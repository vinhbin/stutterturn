"""Build BLOCK ('still talking') and FLUENT eval sets using a simple energy VAD.

VAD: RMS on 30 ms frames with 10 ms hop. A frame is speech if its RMS (dB) is above
max(-45 dBFS, p95_frame_dB - 25 dB) for that clip. A gap is a contiguous non-speech
run >= 300 ms. Resume = start of the first run of >=5 consecutive speech frames after
the gap. BLOCK sample must have >=200 ms cumulative speech before the gap.
"""
import csv, os, json
import numpy as np
import soundfile as sf

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
AUDIO = os.path.join(BASE, "audio")

SR = 16000
FRAME = int(0.030 * SR)   # 30 ms
HOP = int(0.010 * SR)     # 10 ms
GAP_MIN_S = 0.300
ABS_FLOOR_DB = -45.0
REL_DB = 25.0
MIN_PRE_SPEECH_S = 0.200
RESUME_RUN = 5            # 5 consecutive speech frames (10ms hop) to call it a resume


def frame_rms_db(x):
    n = (len(x) - FRAME) // HOP + 1
    if n < 1:
        return np.array([]), np.array([])
    idx = np.arange(n)[:, None] * HOP + np.arange(FRAME)[None, :]
    frames = x[idx]
    rms = np.sqrt((frames ** 2).mean(axis=1) + 1e-12)
    db = 20 * np.log10(rms + 1e-12)
    t = (np.arange(n) * HOP + FRAME / 2) / SR  # frame center times
    return t, db


def analyze(path):
    x, sr = sf.read(path, dtype="float32")
    assert sr == SR, (path, sr)
    if x.ndim > 1:
        x = x.mean(axis=1)
    dur = len(x) / SR
    t, db = frame_rms_db(x)
    if len(db) == 0:
        return {"dur": dur, "error": "too_short"}
    th = max(ABS_FLOOR_DB, np.percentile(db, 95) - REL_DB)
    speech = db > th
    return {"dur": dur, "t": t, "db": db, "th": th, "speech": speech}


def runs(mask):
    """Yield (start_idx, end_idx_exclusive, value) runs."""
    out = []
    i = 0
    while i < len(mask):
        j = i
        while j < len(mask) and mask[j] == mask[i]:
            j += 1
        out.append((i, j, bool(mask[i])))
        i = j
    return out


def find_first_gap(a):
    """First non-speech run >=300ms with >=200ms cumulative speech before it and a resume after.
    Returns (gap_start_s, resume_s, pre_speech_s, reason)."""
    sp = a["speech"]
    t = a["t"]
    hop_s = HOP / SR
    rr = runs(sp)
    cum_speech = 0.0
    found_gap = False
    for k, (i, j, val) in enumerate(rr):
        seg_dur = (j - i) * hop_s
        if val:
            cum_speech += seg_dur
            continue
        if seg_dur < GAP_MIN_S:
            continue
        found_gap = True
        if cum_speech < MIN_PRE_SPEECH_S:
            continue  # gap too early (e.g. leading silence); keep looking
        # gap_start: end of previous frame run -> time of first silent frame
        gap_start = t[i] - 0.015  # frame center minus half frame
        # find resume: first run of >= RESUME_RUN consecutive speech frames after j-1
        m = j
        while m < len(sp):
            if sp[m]:
                run_len = 0
                mm = m
                while mm < len(sp) and sp[mm]:
                    run_len += 1
                    mm += 1
                if run_len >= RESUME_RUN:
                    resume = t[m] - 0.015
                    return gap_start, resume, cum_speech, "ok"
                m = mm
            else:
                m += 1
        return None, None, cum_speech, "no_resume"
    if found_gap:
        return None, None, cum_speech, "gap_but_no_pre_speech"
    return None, None, cum_speech, "no_gap"


def fluent_features(a):
    """speech_end (end of last speech run), trailing silence, and mid-utterance pauses
    (>=300ms gaps with speech >=200ms before and a resume)."""
    sp = a["speech"]
    t = a["t"]
    hop_s = HOP / SR
    rr = runs(sp)
    speech_runs = [(i, j) for i, j, v in rr if v and (j - i) >= 3]  # >=30ms cumulative
    if not speech_runs:
        return None
    last_i, last_j = speech_runs[-1]
    speech_end = t[last_j - 1] + 0.015
    trailing = a["dur"] - speech_end
    total_speech = sum((j - i) * hop_s for i, j in speech_runs)
    # mid-utterance pauses
    pauses = []
    cum = 0.0
    for i, j, v in rr:
        if v:
            cum += (j - i) * hop_s
            continue
        seg = (j - i) * hop_s
        if seg >= GAP_MIN_S and cum >= MIN_PRE_SPEECH_S and j < last_j:
            # resume check: next speech run of >=RESUME_RUN frames
            m = j
            res = None
            while m < len(sp):
                if sp[m]:
                    run_len = 0
                    mm = m
                    while mm < len(sp) and sp[mm]:
                        run_len += 1
                        mm += 1
                    if run_len >= RESUME_RUN:
                        res = t[m] - 0.015
                        break
                    m = mm
                else:
                    m += 1
            if res is not None:
                pauses.append((round(t[i] - 0.015, 3), round(res, 3)))
    return {"speech_end": speech_end, "trailing": trailing,
            "total_speech": total_speech, "pauses": pauses}


def main():
    tallies = {"block": {}, "fluent": {}}
    # ---- BLOCK ----
    block_out = []
    with open(os.path.join(DATA, "block_candidates.csv")) as f:
        cands = list(csv.DictReader(f))
    for row in cands:
        p = os.path.join(AUDIO, os.path.basename(row["file"]))
        if not os.path.exists(p):
            tallies["block"]["missing_file"] = tallies["block"].get("missing_file", 0) + 1
            continue
        a = analyze(p)
        if a["dur"] < 2.9:
            tallies["block"]["empty_or_short_wav"] = tallies["block"].get("empty_or_short_wav", 0) + 1
            continue
        gap_start, resume, pre, reason = find_first_gap(a)
        if reason != "ok":
            tallies["block"][reason] = tallies["block"].get(reason, 0) + 1
            continue
        block_out.append({
            "file": os.path.basename(row["file"]), "Show": row["Show"],
            "Block": row["Block"], "gap_start": round(gap_start, 3),
            "resume": round(resume, 3), "gap_dur": round(resume - gap_start, 3),
            "pre_speech": round(pre, 3), "vad_th_db": round(a["th"], 1),
        })
        tallies["block"]["ok"] = tallies["block"].get("ok", 0) + 1

    # ---- FLUENT ----
    fluent_out = []
    with open(os.path.join(DATA, "fluent_candidates.csv")) as f:
        cands = list(csv.DictReader(f))
    for row in cands:
        p = os.path.join(AUDIO, os.path.basename(row["file"]))
        if not os.path.exists(p):
            tallies["fluent"]["missing_file"] = tallies["fluent"].get("missing_file", 0) + 1
            continue
        a = analyze(p)
        if a["dur"] < 2.9:
            tallies["fluent"]["empty_or_short_wav"] = tallies["fluent"].get("empty_or_short_wav", 0) + 1
            continue
        ff = fluent_features(a)
        if ff is None or ff["total_speech"] < 0.5:
            tallies["fluent"]["no_speech_detected"] = tallies["fluent"].get("no_speech_detected", 0) + 1
            continue
        fluent_out.append({
            "file": os.path.basename(row["file"]), "Show": row["Show"],
            "NoStutteredWords": row["NoStutteredWords"],
            "speech_end": round(ff["speech_end"], 3),
            "trailing_sil": round(ff["trailing"], 3),
            "total_speech": round(ff["total_speech"], 3),
            "pauses": json.dumps(ff["pauses"]),
            "vad_th_db": round(a["th"], 1),
        })
        tallies["fluent"]["ok"] = tallies["fluent"].get("ok", 0) + 1

    block_out = block_out[:200]
    fluent_out = fluent_out[:200]

    for name, out in [("block_eval.csv", block_out), ("fluent_eval.csv", fluent_out)]:
        with open(os.path.join(DATA, name), "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
            w.writeheader()
            w.writerows(out)

    gaps = np.array([r["gap_dur"] for r in block_out])
    print("TALLIES:", json.dumps(tallies, indent=1))
    print(f"BLOCK eval N={len(block_out)} (capped at 200)")
    print(f"FLUENT eval N={len(fluent_out)} (capped at 200)")
    print(f"BLOCK gap durations: median={np.median(gaps):.3f} p75={np.percentile(gaps,75):.3f} "
          f"p90={np.percentile(gaps,90):.3f} max={gaps.max():.3f} min={gaps.min():.3f}")
    for to in [0.5, 0.8, 1.5, 3.0]:
        print(f"  gaps > {to}s: {(gaps > to).sum()} ({100*(gaps> to).mean():.1f}%)")
    tr = np.array([r["trailing_sil"] for r in fluent_out])
    print(f"FLUENT trailing silence: median={np.median(tr):.3f}, >=0.5s: {(tr>=0.5).sum()}, >=1.0s: {(tr>=1.0).sum()}")
    npauses = sum(1 for r in fluent_out if json.loads(r["pauses"]))
    print(f"FLUENT clips with >=1 mid-utterance pause >=300ms: {npauses}")
    with open(os.path.join(DATA, "eval_tallies.json"), "w") as f:
        json.dump(tallies, f, indent=1)


if __name__ == "__main__":
    main()
