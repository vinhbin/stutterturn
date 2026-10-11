"""Turn-input parity: the agent's real streaming loop vs the benchmark's turn_onset input policy.

Technical-execution roadmap, Package 1: "Extend parity checks with delayed speech onset, pre-roll
clipping at source start, a second turn after completion, and a pause shorter than the VAD
threshold. Compare the exact input sample range, feature array, probability and decision point
against the agent ... record the actual 32 ms schedule. Whole-clip agreement alone fails."

usage: python agent/check_turn_parity.py [--model stock-fp32|stock-int8|both] [--out PATH]

For each case the source audio is composed from local permitted clips (agent sources; HeStutters,
a TRAINING show, so this is a mechanics check, not a model result) and run through engine.Run in
real time with services off and no playback. SmartTurn.predict is wrapped to capture the exact
array the agent feeds the model. For every model check the agent makes, the benchmark input is
rebuilt with benchmark/scripts/eval_runner.py's own functions (first_onset_frame, input_start_for,
Model.predict) for an item whose silence_start_s is the agent's logged speech_stop time, at the
agent-v0.1-turn-checks schedule (single check at vad_stop_s = 0.2 s, pre_roll_s = 0.2 s).

Hard checks (exit 1 on failure):
  H1 the captured agent input equals stream[start_a:end_a] reconstructed from the decision frame
  H2 preprocessing parity: on the identical agent slice, agent features/probability equal the
     benchmark Model's within 1e-6
  H3 schedule: end_b - end_a == -384 samples (benchmark cuts at silence + 0.200 s; the agent checks
     after ceil(0.2 / 0.032) = 7 silent frames = 0.224 s)
  H4 first-turn input start: start_b == start_a (first onset - 6 frames, clipped at 0)
  H5 sub-threshold pause: no agent check starts inside the inserted short pause
Documented divergence (reported, not a failure): on a SECOND turn after a completed decision the
agent restarts its input at the new turn's onset, while turn_onset uses the clip's FIRST onset
(eval_runner.first_onset_frame docstring). The checker asserts that the divergence is exactly that.
Reported only: probability on each policy's own slice and whether the decisions agree.
"""
import argparse
import asyncio
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine  # noqa: E402

sys.path.insert(0, os.path.join(engine.ROOT, "benchmark", "scripts"))
import eval_runner as ER  # noqa: E402

SR, FRAME, FRAME_S = engine.SR, engine.FRAME, engine.FRAME_S
VAD_STOP_S, PRE_ROLL_S = 0.2, 0.2          # agent-v0.1-turn-checks
TOL = 1e-6
EXPECTED_END_DELTA = int(round(VAD_STOP_S * SR)) - int(np.ceil(VAD_STOP_S / FRAME_S - 1e-9)) * FRAME  # -384


def zeros(s):
    return np.zeros(int(round(s * SR / FRAME)) * FRAME, dtype=np.float32)


def speech_span(vad, x):
    """(first speech frame, last speech frame) by the benchmark's VAD (prob >= 0.5)."""
    p = np.array(list(vad.probs(x)))
    idx = np.where(p >= ER.VAD_THRESHOLD)[0]
    if not len(idx):
        sys.exit("a base clip has no detectable speech")
    return int(idx[0]), int(idx[-1])


def trimmed(vad, x):
    """Clip cut at its last speech frame (frame-aligned), so pauses are only the ones we insert."""
    _, last = speech_span(vad, x)
    return x[:(last + 1) * FRAME]


def build_cases(vad):
    srcs = engine.list_sources()
    if len(srcs) < 2:
        sys.exit("need >= 2 local agent sources (run agent/fetch_assets.py)")
    a, b = engine.load_source(srcs[0]), engine.load_source(srcs[1])
    at, bt = trimmed(vad, a), trimmed(vad, b)
    first_a, _ = speech_span(vad, a)
    clip_start = max(0, first_a - 2) * FRAME          # speech begins 2 frames in: pre-roll must clip
    pause_frames = 2                                  # 0.064 s < 7 frames needed for a check
    cases = {
        "delayed_onset": {"audio": np.concatenate([zeros(1.5), at, zeros(1.2)]),
                          "desc": f"1.5 s silence, then {srcs[0]} (speech-trimmed), 1.2 s silence"},
        "preroll_clipped": {"audio": np.concatenate([a[clip_start:clip_start + len(at) - clip_start], zeros(1.2)]),
                            "desc": f"{srcs[0]} starting 2 frames before its first speech frame"},
        "sub_threshold_pause": {"audio": np.concatenate([at, zeros(pause_frames * FRAME_S), bt, zeros(1.2)]),
                                "pause": (len(at) / SR, (len(at) + pause_frames * FRAME) / SR),
                                "desc": f"{srcs[0]} + {pause_frames * FRAME_S:.3f} s pause + {srcs[1]}"},
        "second_turn": {"audio": np.concatenate([at, zeros(3.6), bt, zeros(1.2)]),
                        "second_turn_from": (len(at) + len(zeros(3.6))) / SR,
                        "desc": f"{srcs[0]} + 3.6 s silence (fallback completes turn 1) + {srcs[1]}"},
    }
    return cases, srcs[:2]


async def agent_run(config, audio, name):
    captured, events = [], []
    orig = engine.SmartTurn.predict

    def wrapped(self, x):
        captured.append(np.array(x, dtype=np.float32, copy=True))
        return orig(self, x)
    engine.SmartTurn.predict = wrapped
    try:
        run = engine.Run(config, engine.list_sources()[0], services=None,
                         listener=lambda m: events.append(m), play=False)
        run.audio, run.source_name = audio.astype(np.float32), f"parity-{name}"
        await run.run()
    finally:
        engine.SmartTurn.predict = orig
    return run, captured, [e for e in events if e.get("type") == "event"]


def check_case(name, case, config, st, bmodel, vad):
    audio = case["audio"]
    stream = np.concatenate([audio, np.zeros(int(engine.TRAILING_SILENCE_S * SR), dtype=np.float32)])
    run, captured, events = asyncio.run(agent_run(config, audio, name))
    checks = [e for e in events if e.get("kind") == "decision" and e.get("prob") is not None]
    stops = [e["t"] for e in events if e.get("name") == "speech_stop"]
    if len(checks) != len(captured):
        return {"case": name, "error": f"{len(checks)} model decisions vs {len(captured)} captured inputs"}
    onset_frame = ER.first_onset_frame(vad, audio)
    out, hard = [], []
    for k, (ev, xa) in enumerate(zip(checks, captured)):
        i_dec = int(round(ev["t"] / FRAME_S))
        end_a = (i_dec + 1) * FRAME
        start_a = end_a - len(xa)
        stt = max(t for t in stops if t <= ev["t"] + 1e-9)
        item = {"silence_start_s": stt}
        start_b, onset_s, fb = ER.input_start_for(item, onset_frame, PRE_ROLL_S)
        end_b = min(int(round((stt + VAD_STOP_S) * SR)), len(audio))
        xb = audio[start_b:end_b]
        h1 = bool(np.array_equal(stream[start_a:end_a], xa))
        f_agent = st.features(xa)
        n = 8 * SR
        padded = np.pad(xa, (n - len(xa), 0)) if len(xa) < n else xa[-n:]
        f_bench = bmodel.fe(padded, sampling_rate=SR, return_tensors="np", padding="max_length",
                            max_length=n, truncation=True, do_normalize=True).input_features.astype(np.float32)
        p_agent_slice, _ = st.predict(xa)
        p_bench_same = bmodel.predict(xa)
        dfeat, dp = float(np.max(np.abs(f_agent - f_bench))), abs(p_agent_slice - p_bench_same)
        p_bench_own = bmodel.predict(xb)
        # a later turn: the agent completed an earlier turn (smart_turn or fallback) before this check,
        # so it restarted its input at the resumed speech (any case, not only the designed one)
        second = any(e.get("kind") == "decision" and e.get("name") == "turn_complete" and e["t"] < ev["t"]
                     for e in events)
        rec = {"check": k, "decision_t": ev["t"], "decision": ev["name"], "silence_start_s": stt,
               "agent_range": [start_a, end_a], "bench_range": [start_b, end_b],
               "start_delta": start_b - start_a, "end_delta": end_b - end_a,
               "h1_slice_reconstructed": h1, "h2_max_dfeat": dfeat, "h2_dp": dp,
               "p_agent_logged": ev["prob"], "p_bench_own_slice": round(p_bench_own, 6),
               "decisions_agree": (ev["prob"] > run.threshold) == (p_bench_own > run.threshold),
               "bench_input_fallback": fb, "second_turn": second}
        hard += [("H1", h1), ("H2", dfeat <= TOL and dp <= TOL), ("H3", rec["end_delta"] == EXPECTED_END_DELTA)]
        if second:
            rec["divergence"] = "documented: agent restarts at the turn's onset; turn_onset uses the clip's first onset"
            first_start = max(0, (onset_frame - int(round(PRE_ROLL_S / ER.VAD_FRAME_S))) * FRAME)
            hard.append(("H4-divergence-is-first-onset", start_b == first_start and start_a > start_b))
        else:
            hard.append(("H4", rec["start_delta"] == 0))
        out.append(rec)
    if "second_turn_from" in case and not any(r["second_turn"] for r in out):
        hard.append(("designed-second-turn-reached", False))
    if "pause" in case:
        p0, p1 = case["pause"]
        bad = [e["t"] for e in checks if p0 - 1e-9 <= e["t"] <= p1 + 7 * FRAME_S]
        hard.append(("H5", not bad))
    failed = [h for h, ok in hard if not ok]
    return {"case": name, "desc": case["desc"], "run_id": run.run_id, "checks": out,
            "hard_failed": failed, "passed": not failed and bool(out)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", choices=["stock-fp32", "stock-int8", "both"], default="both")
    ap.add_argument("--out", help="write the JSON report here")
    a = ap.parse_args()
    vad = ER.SileroVAD(engine.SILERO_MODEL)
    cases, srcs = build_cases(vad)
    report = {"tool": "agent/check_turn_parity.py", "commit": engine._commit(), "sources": srcs,
              "schedule": {"frame_s": FRAME_S, "agent_check_after_s": round(7 * FRAME_S, 3),
                           "bench_check_after_s": VAD_STOP_S, "expected_end_delta_samples": EXPECTED_END_DELTA,
                           "pre_roll_frames": int(round(PRE_ROLL_S / FRAME_S))},
              "results": []}
    models = ["stock-fp32", "stock-int8"] if a.model == "both" else [a.model]
    configs = {"stock-fp32": "stock_fp32", "stock-int8": "stock"}
    for mid in models:
        m = engine.resolve_model(mid)
        st = engine.SmartTurn.load(m["path"], m["sha256"])
        bmodel = ER.Model(m["path"])
        for name, case in cases.items():
            r = check_case(name, case, configs[mid], st, bmodel, vad)
            r["model"] = mid
            report["results"].append(r)
            for c in r.get("checks", []):
                print(f"{mid:10s} {name:20s} chk{c['check']} t={c['decision_t']:.3f} agent[{c['agent_range'][0]},"
                      f"{c['agent_range'][1]}) bench[{c['bench_range'][0]},{c['bench_range'][1]}) "
                      f"dstart={c['start_delta']} dend={c['end_delta']} dfeat={c['h2_max_dfeat']:.1e} "
                      f"dp={c['h2_dp']:.1e} p_agent={c['p_agent_logged']} p_bench={c['p_bench_own_slice']:.4f}"
                      + (" [2nd turn: documented divergence]" if c["second_turn"] else ""))
            print(f"  -> {name}: {'PASS' if r['passed'] else 'FAIL ' + str(r.get('hard_failed') or r.get('error'))}")
    ok = all(r["passed"] for r in report["results"])
    report["passed"] = ok
    if a.out:
        with open(a.out, "w", encoding="utf-8", newline="\n") as f:
            json.dump(report, f, indent=1)
    print(f"{'PASS' if ok else 'FAIL'}: {len(report['results'])} case runs")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
