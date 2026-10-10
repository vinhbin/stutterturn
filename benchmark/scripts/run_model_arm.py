"""Run stock Smart Turn v3.2 (CPU int8 ONNX) on BLOCK and FLUENT eval samples.

Uses the smart-turn repo's own preprocessing exactly (WhisperFeatureExtractor,
chunk_length=8, do_normalize=True, last-8s truncate / left zero-pad, p>0.5 = complete).

BLOCK: for each clip, construct 'still talking' samples = audio[0 : gap_start + t]
for silence checkpoints t (s) strictly inside the gap (before resume). A 'complete'
prediction during the gap = the agent would cut the speaker off mid-block.

FLUENT: latency = earliest post-speech checkpoint where the model says complete
(clips with >=0.5s trailing silence). Also: false 'complete' at mid-utterance pauses.
"""
import csv, json, os, sys, time
import numpy as np
import soundfile as sf
import onnxruntime as ort
from transformers import WhisperFeatureExtractor

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
AUDIO = os.path.join(BASE, "audio")
MODEL = os.path.join(BASE, "smart-turn", "smart-turn-v3.2-cpu.onnx")
SR = 16000

so = ort.SessionOptions()
so.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
so.inter_op_num_threads = 1
so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
session = ort.InferenceSession(MODEL, sess_options=so)
feature_extractor = WhisperFeatureExtractor(chunk_length=8)

infer_times = []

def truncate_audio_to_last_n_seconds(audio_array, n_seconds=8, sample_rate=16000):
    max_samples = n_seconds * sample_rate
    if len(audio_array) > max_samples:
        return audio_array[-max_samples:]
    elif len(audio_array) < max_samples:
        return np.pad(audio_array, (max_samples - len(audio_array), 0), mode="constant")
    return audio_array

def predict(audio_array):
    t0 = time.perf_counter()
    audio_array = truncate_audio_to_last_n_seconds(audio_array, 8)
    inputs = feature_extractor(audio_array, sampling_rate=16000, return_tensors="np",
                               padding="max_length", max_length=8 * 16000,
                               truncation=True, do_normalize=True)
    feats = np.expand_dims(inputs.input_features.squeeze(0).astype(np.float32), 0)
    prob = session.run(None, {"input_features": feats})[0][0].item()
    infer_times.append(time.perf_counter() - t0)
    return prob

BLOCK_CHECKPOINTS = [0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0, 1.2, 1.5]
FLUENT_CHECKPOINTS = [round(0.1 * i, 1) for i in range(1, 11)]  # 0.1 .. 1.0

def main():
    # ---------- BLOCK ----------
    block_rows = list(csv.DictReader(open(os.path.join(DATA, "block_eval.csv"))))
    out_rows = []
    for n, r in enumerate(block_rows):
        x, sr = sf.read(os.path.join(AUDIO, r["file"]), dtype="float32")
        gap_start, gap_dur = float(r["gap_start"]), float(r["gap_dur"])
        probs = {}
        for t in BLOCK_CHECKPOINTS:
            if t >= gap_dur - 0.01:   # person already resumed; not a valid silence checkpoint
                break
            end = int((gap_start + t) * SR)
            probs[t] = round(predict(x[:end]), 4)
        if not probs:  # gap shorter than first checkpoint margin: evaluate at 0.2 anyway if gap>=0.3
            end = int((gap_start + 0.2) * SR)
            probs[0.2] = round(predict(x[:end]), 4)
        first_t = sorted(probs)[0]
        out_rows.append({
            "file": r["file"], "gap_start": gap_start, "gap_dur": gap_dur,
            "probs": json.dumps(probs),
            "complete_at_first_check": int(probs[first_t] > 0.5),
            "complete_any_check": int(any(p > 0.5 for p in probs.values())),
            "earliest_complete_t": min((t for t, p in probs.items() if p > 0.5), default=""),
        })
        if (n + 1) % 50 == 0:
            print(f"block {n+1}/{len(block_rows)}", flush=True)
    with open(os.path.join(DATA, "model_block_results.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
        w.writeheader(); w.writerows(out_rows)
    n = len(out_rows)
    first = sum(r["complete_at_first_check"] for r in out_rows)
    anyc = sum(r["complete_any_check"] for r in out_rows)
    print(f"BLOCK N={n}: complete at first silence check (0.2s into gap): {first} ({100*first/n:.1f}%)")
    print(f"BLOCK N={n}: complete at ANY silence check before resume:      {anyc} ({100*anyc/n:.1f}%)")

    # ---------- FLUENT latency ----------
    fluent_rows = list(csv.DictReader(open(os.path.join(DATA, "fluent_eval.csv"))))
    lat_rows, latencies, censored = [], [], 0
    eligible = [r for r in fluent_rows if float(r["trailing_sil"]) >= 0.5]
    for n, r in enumerate(eligible):
        x, sr = sf.read(os.path.join(AUDIO, r["file"]), dtype="float32")
        speech_end, trailing = float(r["speech_end"]), float(r["trailing_sil"])
        lat = None
        probs = {}
        for t in FLUENT_CHECKPOINTS:
            if t > trailing:
                break
            end = int((speech_end + t) * SR)
            p = predict(x[:end])
            probs[t] = round(p, 4)
            if p > 0.5 and lat is None:
                lat = t
                break
        if lat is None:
            censored += 1
        else:
            latencies.append(lat)
        lat_rows.append({"file": r["file"], "speech_end": speech_end,
                         "trailing_sil": trailing, "latency": lat if lat else "",
                         "probs": json.dumps(probs)})
        if (n + 1) % 25 == 0:
            print(f"fluent-lat {n+1}/{len(eligible)}", flush=True)
    with open(os.path.join(DATA, "model_fluent_latency.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(lat_rows[0].keys()))
        w.writeheader(); w.writerows(lat_rows)
    la = np.array(latencies)
    print(f"FLUENT latency eligible N={len(eligible)} (trailing sil >=0.5s)")
    if len(la):
        print(f"  decided complete: {len(la)} | median={np.median(la):.2f}s mean={la.mean():.2f}s p90={np.percentile(la,90):.2f}s")
    print(f"  censored (never complete within trailing silence, max {FLUENT_CHECKPOINTS[-1]}s): {censored}")

    # ---------- FLUENT mid-utterance pause false-complete ----------
    pause_rows = []
    fp = 0; np_total = 0
    for r in fluent_rows:
        pauses = json.loads(r["pauses"])
        if not pauses:
            continue
        x, sr = sf.read(os.path.join(AUDIO, r["file"]), dtype="float32")
        for (ps, resume) in pauses:
            pd = resume - ps
            t = min(0.3, pd - 0.05)
            if t < 0.15:
                continue
            p = predict(x[:int((ps + t) * SR)])
            np_total += 1
            fp += int(p > 0.5)
            pause_rows.append({"file": r["file"], "pause_start": ps, "pause_dur": round(pd, 3),
                               "check_t": round(t, 2), "prob": round(p, 4), "complete": int(p > 0.5)})
    with open(os.path.join(DATA, "model_fluent_pause_results.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(pause_rows[0].keys()))
        w.writeheader(); w.writerows(pause_rows)
    print(f"FLUENT mid-utterance pauses tested: {np_total}, false 'complete': {fp} ({100*fp/max(np_total,1):.1f}%)")

    it = np.array(infer_times) * 1000
    print(f"Inference wall-clock (feature+onnx, CPU): n={len(it)} mean={it.mean():.0f}ms p50={np.median(it):.0f}ms p95={np.percentile(it,95):.0f}ms")

if __name__ == "__main__":
    main()
