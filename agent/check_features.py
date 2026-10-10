"""Acceptance check (model/CONTRACT.md 5.2): the same saved clip through the
benchmark's predict() and through the agent's SmartTurn must give matching
features and probabilities.

usage: python agent/check_features.py [clip.wav ...]   (default: all local clips)

The benchmark functions are taken from benchmark/scripts/run_model_arm.py itself
(parsed with ast, not copied), and run with the same ONNX session as the agent.
"""
import ast
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine  # noqa: E402

SCRIPT = os.path.join(engine.ROOT, "benchmark", "scripts", "run_model_arm.py")


def benchmark_predict(session, feature_extractor):
    """Build the benchmark's predict() bound to our session and extractor."""
    tree = ast.parse(open(SCRIPT, encoding="utf-8").read())
    wanted = {"truncate_audio_to_last_n_seconds", "predict"}
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in wanted]
    if {f.name for f in funcs} != wanted:
        sys.exit(f"could not find {wanted} in {SCRIPT}")
    ns = {"np": np, "time": __import__("time"), "session": session,
          "feature_extractor": feature_extractor, "infer_times": []}
    exec(compile(ast.Module(body=funcs, type_ignores=[]), SCRIPT, "exec"), ns)
    return ns["predict"]


def main():
    clips = sys.argv[1:] or engine.list_sources()
    worst_p = worst_f = 0.0
    for model_id in ("stock-int8", "stock-fp32"):
        m = engine.resolve_model(model_id)
        st = engine.SmartTurn.load(m["path"], m["sha256"])
        ref_predict = benchmark_predict(st.sess, st.fe)
        for clip in clips:
            audio = engine.load_source(clip)
            p_agent, _ = st.predict(audio)
            p_ref = ref_predict(audio)
            n = 8 * engine.SR
            padded = np.pad(audio, (n - len(audio), 0)) if len(audio) < n else audio[-n:]
            f_ref = st.fe(padded, sampling_rate=16000, return_tensors="np", padding="max_length",
                          max_length=n, truncation=True, do_normalize=True).input_features
            f_diff = float(np.max(np.abs(st.features(audio) - f_ref.astype(np.float32))))
            p_diff = abs(p_agent - p_ref)
            worst_p, worst_f = max(worst_p, p_diff), max(worst_f, f_diff)
            print(f"{model_id}  {clip:24s} agent={p_agent:.6f} benchmark={p_ref:.6f} "
                  f"|dp|={p_diff:.2e} max|dfeat|={f_diff:.2e}")
    ok = worst_p <= 1e-6 and worst_f <= 1e-6
    print(f"{'PASS' if ok else 'FAIL'}: max |dp| {worst_p:.2e}, max |dfeat| {worst_f:.2e} "
          f"over {len(clips)} clips x 2 models (whole clip as model input)")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
