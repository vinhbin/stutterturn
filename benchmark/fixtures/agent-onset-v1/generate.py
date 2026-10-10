"""Reference onsets from Guttuu's engine (agent/engine.py, turn logic as on main 49716d0): replay each
clip, take the first speech_start event (Silero v5.1.2, p>=0.5, 7-frame start run, 512-sample frames
aligned to clip start), then the intended pre-roll start = onset frame - 6 frames. p_turn_onset is
SmartTurn.predict(x[start:cut]) with cut = round((gap_start+0.2)*16000), i.e. agent-v0.1-single's check."""
import sys, csv, asyncio, numpy as np, soundfile as sf
sys.path.insert(0, "agent"); import engine
async def nosleep(d): return None
engine.asyncio.sleep = nosleep
m = engine.SmartTurn.load(engine.STOCK_MODEL); F, SR = engine.FRAME, engine.SR
w = csv.writer(open(sys.argv[1], "w", newline=""), lineterminator="\n"); w.writerow(["clip_key","onset_s","onset_frame","input_start_sample","cut_sample","p_turn_onset_int8_macos"])
for r in csv.DictReader(open("/Users/niyakoabajebel/Documents/GitHub/stutterturn/benchmark/data/block_eval.csv")):
    evs=[]; run=engine.Run("stock", r["file"]); run.listener=evs.append; asyncio.run(run.run())
    st=[e["t"] for e in evs if e.get("name")=="speech_start"]
    x,_=sf.read(f"benchmark/audio/{r['file']}", dtype="float32")
    cut=int(round((float(r["gap_start"])+0.2)*SR))
    if not st or st[0] >= float(r["gap_start"]):
        w.writerow([r["file"][:-4], st[0] if st else "", "", 0, cut, "" ]); continue
    fr=int(round(st[0]/engine.FRAME_S)); start=max(0,(fr-6)*F)
    w.writerow([r["file"][:-4], st[0], fr, start, cut, f"{m.predict(x[start:cut]):.7f}"])
