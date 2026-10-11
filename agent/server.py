"""HTTP + WebSocket server for the agent (agent/CONTRACT.md v0.1).

usage: python agent/server.py [--services on|off] [--port 8765]
"""
import argparse
import asyncio
import csv
import json
import os
import sys

from aiohttp import WSMsgType, web

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine  # noqa: E402

CORS = {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "*"}
RIGHTS = "SEP-28k podcast audio; rights remain with owners; not redistributed"


def _categories():
    cats = {}
    for name, cat in (("block_eval.csv", "block"), ("fluent_eval.csv", "fluent")):
        path = os.path.join(engine.ROOT, "benchmark", "data", name)
        if os.path.exists(path):
            with open(path, newline="") as f:
                for row in csv.DictReader(f):
                    cats[row["file"]] = cat
    return cats


def jres(data, status=200):
    return web.json_response(data, status=status, headers=CORS)


async def health(request):
    return jres({"ok": True, "contract": engine.CONTRACT_VERSION, "commit": engine._commit(),
                 "services": "fixed" if getattr(request.app["services"], "response_metadata", {}).get("mode") == "fixed" else "on" if request.app["services"] else "off",
                 "response": getattr(request.app["services"], "response_metadata", {"mode": "live_api" if request.app["services"] else "off"}),
                 "browser_audio": "pcm16-v1" if request.app["browser_audio"] else None,
                 "playback": "on" if request.app["play"] else "off"})


async def configurations(request):
    return jres(engine.configurations())


async def sources(request):
    cats = _categories()
    out = []
    for f in engine.list_sources():
        info = engine.sf.info(os.path.join(engine.AUDIO, f))
        # `file` is the bare name the client sends back in `start` (lives in benchmark/audio/).
        out.append({"source_id": f, "file": f,
                    "duration_s": round(info.frames / info.samplerate, 3),
                    "category": cats.get(f, "unknown"), "rights_note": RIGHTS})
    return jres(out)


async def run_log(request):
    run_id = os.path.basename(request.match_info["run_id"])
    path = os.path.join(engine.RUNS, f"{run_id}.jsonl")
    if not os.path.exists(path):
        return jres({"error": f"no run {run_id}"}, status=404)
    with open(path, encoding="utf-8") as f:
        return web.Response(text=f.read(), content_type="application/x-ndjson", headers=CORS)


async def ws_handler(request):
    origin = request.headers.get("Origin")
    allowed_origin = request.app["allowed_origin"]
    if allowed_origin and origin and origin != allowed_origin:
        raise web.HTTPForbidden(text="Origin not allowed")
    ws = web.WebSocketResponse(heartbeat=20, max_msg_size=4096)
    await ws.prepare(request)
    queue = asyncio.Queue(maxsize=128)
    current = {"run": None, "task": None}

    async def pump():
        while True:
            msg = await queue.get()
            if ws.closed:
                return
            await ws.send_str(json.dumps(msg, separators=(",", ":")))

    pump_task = asyncio.create_task(pump())

    def error(message, run_id=None):
        queue.put_nowait({"v": engine.CONTRACT_VERSION, "type": "error", "run_id": run_id,
                          "seq": -1, "message": message})

    async def do_run(run):
        try:
            await run.run()
        except Exception as e:
            error(f"run failed: {e}", run.run_id)
        finally:
            request.app["runtime"]["active_runs"] -= 1
            current["run"] = current["task"] = None

    try:
        async for m in ws:
            if m.type != WSMsgType.TEXT:
                continue
            try:
                msg = json.loads(m.data)
            except ValueError:
                error("invalid JSON")
                continue
            if not isinstance(msg, dict):
                error("message must be a JSON object")
                continue
            if msg.get("type") == "start":
                if current["run"] is not None:
                    error("a run is already in progress on this socket", current["run"].run_id)
                    continue
                if request.app["runtime"]["active_runs"] >= request.app["max_runs"]:
                    error("server busy; another replay is in progress")
                    continue
                if msg.get("source") not in engine.list_sources():
                    error("source must be one of the advertised recordings")
                    continue
                try:
                    extra = {}
                    if msg.get("browser_audio") is True:
                        if not request.app["browser_audio"]:
                            raise ValueError("Browser audio is not enabled on this backend")
                        from browser_playback import BrowserPlayer
                        audio_seq = 0

                        def send_audio(packet):
                            nonlocal audio_seq
                            queue.put_nowait({"v": engine.CONTRACT_VERSION, "type": "browser_audio",
                                              "run_id": current["run"].run_id,
                                              "audio_seq": audio_seq, **packet})
                            audio_seq += 1

                        extra["playback_factory"] = lambda source: BrowserPlayer(source, send_audio)
                    run = engine.Run(msg.get("config", ""), msg.get("source", ""),
                                     services=request.app["services"], listener=queue.put_nowait,
                                     play=request.app["play"], **extra)
                except Exception as e:
                    error(f"cannot start: {e}")
                    continue
                current["run"] = run
                request.app["runtime"]["active_runs"] += 1
                current["task"] = asyncio.create_task(do_run(run))
            elif msg.get("type") == "stop":
                run = current["run"]
                if run is None or msg.get("run_id") not in (None, run.run_id):
                    error("no such active run", msg.get("run_id"))
                else:
                    run.stop()
            else:
                error(f"unknown message type {msg.get('type')!r}")
    finally:
        if current["run"] is not None:
            current["run"].stop()
            if current["task"]:
                await asyncio.gather(current["task"], return_exceptions=True)
        await asyncio.sleep(0.05)
        pump_task.cancel()
        await asyncio.gather(pump_task, return_exceptions=True)
    return ws


async def options(request):
    return web.Response(headers=CORS)


def create_app(services=None, play=False, max_runs=1, allowed_origin=None, browser_audio=False):
    if max_runs < 1:
        raise ValueError("max_runs must be positive")
    app = web.Application()
    app["services"] = services
    app["play"] = play
    app["max_runs"] = max_runs
    app["runtime"] = {"active_runs": 0}
    app["allowed_origin"] = allowed_origin
    app["browser_audio"] = browser_audio
    app.router.add_get("/v0/health", health)
    app.router.add_get("/v0/configurations", configurations)
    app.router.add_get("/v0/sources", sources)
    app.router.add_get("/v0/runs/{run_id}", run_log)
    app.router.add_get("/v0/ws", ws_handler)
    app.router.add_route("OPTIONS", "/{tail:.*}", options)
    return app


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--services", choices=["on", "off", "fixed"], default="on")
    ap.add_argument("--fixed-response", help="Local mono 16 kHz PCM16 reply WAV for controlled comparisons")
    ap.add_argument("--fixed-delay", type=float, default=1.0, help="Identical simulated response delay in seconds")
    ap.add_argument("--play", action="store_true",
                    help="play the source and agent speech on this machine's speakers (demo)")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--max-runs", type=int, default=1, help="global concurrent replay limit")
    ap.add_argument("--allowed-origin", help="reject browser WebSockets from other origins")
    ap.add_argument("--browser-audio", action="store_true", help="offer authenticated PCM browser playback")
    a = ap.parse_args()
    if a.services == "fixed":
        if not a.fixed_response:
            ap.error('--fixed-response is required with --services fixed')
        from fixed_response import FixedServices
        services = FixedServices(a.fixed_response, a.fixed_delay)
    else:
        services = engine.Services() if a.services == "on" else None
    app = create_app(services,
                     a.play, a.max_runs, a.allowed_origin, a.browser_audio)
    print(f"agent server: http://127.0.0.1:{a.port}  services={a.services}", flush=True)
    web.run_app(app, host="127.0.0.1", port=a.port, print=None)


if __name__ == "__main__":
    main()
