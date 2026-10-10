"""ElevenLabs Agents live arm: stream real SEP-28k BLOCK clips into a ConvAI websocket
session and record when the agent takes its turn, under turn_eagerness=normal vs patient.

Cut-off classification per clip (speaker blocks at gap_start, resumes at resume):
  - strict: agent audio/response event arrives BEFORE resume (agent began its turn in the gap)
  - likely: agent audio/response arrives before resume+0.5s (decision was in the gap; LLM+TTS
    latency delays the first event), OR server sends an 'interruption' event right after
    resume (agent was already speaking when the user resumed).
Usage: python elevenlabs_arm.py <eagerness> <n_clips>
"""
import asyncio, base64, csv, json, os, sys, time
import numpy as np
import soundfile as sf
import urllib.request
import websockets

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
AUDIO = os.path.join(BASE, "audio")
KEY = os.environ["ELEVENLABS_API_KEY"]
AGENT_ID = "agent_9901m4k3jsfyehcry084sqnk3vyv"
SR = 16000
CHUNK_S = 0.1
TRAIL_SIL_S = 5.0

def api(method, path, body=None):
    req = urllib.request.Request("https://api.elevenlabs.io" + path,
                                 data=json.dumps(body).encode() if body else None,
                                 method=method)
    req.add_header("xi-api-key", KEY)
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())

def set_eagerness(eagerness):
    api("PATCH", f"/v1/convai/agents/{AGENT_ID}",
        {"conversation_config": {"turn": {"turn_eagerness": eagerness, "turn_timeout": 7}}})
    got = api("GET", f"/v1/convai/agents/{AGENT_ID}")["conversation_config"]["turn"]["turn_eagerness"]
    assert got == eagerness, got
    print(f"agent turn_eagerness set to {got}")

async def run_clip(signed_url, path, gap_start, resume):
    x, sr = sf.read(os.path.join(AUDIO, path), dtype="float32")
    assert sr == SR
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2").tobytes()
    sil = b"\x00\x00" * int(SR * CHUNK_S)
    chunk_b = int(SR * CHUNK_S) * 2
    events = []
    t0 = None
    async with websockets.connect(signed_url, max_size=16 * 1024 * 1024) as ws:
        async def reader():
            nonlocal t0
            try:
                async for msg in ws:
                    d = json.loads(msg)
                    ts = (time.perf_counter() - t0) if t0 else -1
                    typ = d.get("type")
                    if typ == "ping":
                        await ws.send(json.dumps({"type": "pong",
                                                  "event_id": d["ping_event"]["event_id"]}))
                        continue
                    if typ == "vad_score":
                        continue
                    info = ""
                    if typ == "user_transcript":
                        info = d["user_transcription_event"]["user_transcript"][:60]
                    elif typ == "agent_response":
                        info = d["agent_response_event"]["agent_response"][:60]
                    elif typ == "audio":
                        info = "agent-audio"
                    events.append((round(ts, 3), typ, info))
            except websockets.ConnectionClosed:
                pass
        rt = asyncio.create_task(reader())
        await asyncio.sleep(0.5)  # let initiation metadata arrive
        t0 = time.perf_counter()
        total = pcm + b"\x00\x00" * int(SR * TRAIL_SIL_S)
        n = len(total) // chunk_b
        for i in range(n):
            await ws.send(json.dumps({"user_audio_chunk":
                base64.b64encode(total[i * chunk_b:(i + 1) * chunk_b]).decode()}))
            # real-time pacing
            target = (i + 1) * CHUNK_S
            now = time.perf_counter() - t0
            if target > now:
                await asyncio.sleep(target - now)
            # stop early if agent already responded and user already resumed long ago
            if time.perf_counter() - t0 > len(pcm) / 2 / SR + TRAIL_SIL_S:
                break
        await asyncio.sleep(1.0)
        rt.cancel()
    first_agent = next((ts for ts, typ, _ in events if typ in ("audio", "agent_response")), None)
    interrupted = any(typ == "interruption" for _, typ, _ in events)
    return events, first_agent, interrupted

async def main():
    eagerness = sys.argv[1] if len(sys.argv) > 1 else "normal"
    n_clips = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    set_eagerness(eagerness)
    rows = list(csv.DictReader(open(os.path.join(DATA, "block_eval.csv"))))
    picks = [r for r in rows if float(r["gap_dur"]) >= 0.5][:n_clips]
    out = []
    for i, r in enumerate(picks):
        signed = api("GET", f"/v1/convai/conversation/get-signed-url?agent_id={AGENT_ID}")["signed_url"]
        gap_start, resume = float(r["gap_start"]), float(r["resume"])
        try:
            events, first_agent, interrupted = await run_clip(signed, r["file"], gap_start, resume)
        except Exception as e:
            print(f"{r['file']}: ERROR {e}")
            out.append({"file": r["file"], "eagerness": eagerness, "error": str(e)[:100],
                        "gap_start": gap_start, "resume": resume, "first_agent_evt": "",
                        "cutoff_strict": "", "cutoff_likely": "", "events": ""})
            continue
        strict = int(first_agent is not None and first_agent < resume)
        likely = int(strict or (first_agent is not None and first_agent < resume + 0.5) or interrupted)
        out.append({"file": r["file"], "eagerness": eagerness, "error": "",
                    "gap_start": gap_start, "resume": resume,
                    "first_agent_evt": first_agent if first_agent is not None else "",
                    "cutoff_strict": strict, "cutoff_likely": likely,
                    "events": json.dumps(events[:12])})
        print(f"[{i+1}/{len(picks)}] {r['file']} gap={gap_start}-{resume} "
              f"first_agent={first_agent} strict={strict} likely={likely} intr={interrupted}")
        await asyncio.sleep(0.3)
    fn = os.path.join(DATA, f"elevenlabs_{eagerness}_results.csv")
    with open(fn, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader(); w.writerows(out)
    ok = [r for r in out if r["error"] == ""]
    if ok:
        s = sum(r["cutoff_strict"] for r in ok); l = sum(r["cutoff_likely"] for r in ok)
        print(f"\n{eagerness}: N={len(ok)} cutoff_strict={s} ({100*s/len(ok):.0f}%) "
              f"cutoff_likely={l} ({100*l/len(ok):.0f}%) errors={len(out)-len(ok)}")

if __name__ == "__main__":
    asyncio.run(main())
