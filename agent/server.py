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
                 "services": "on" if request.app["services"] else "off",
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
    ws = web.WebSocketResponse(heartbeat=20)
    await ws.prepare(request)
    queue = asyncio.Queue()
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
            if msg.get("type") == "start":
                if current["run"] is not None:
                    error("a run is already in progress on this socket", current["run"].run_id)
                    continue
                try:
                    run = engine.Run(msg.get("config", ""), msg.get("source", ""),
                                     services=request.app["services"], listener=queue.put_nowait,
                                     play=request.app["play"])
                except Exception as e:
                    error(f"cannot start: {e}")
                    continue
                current["run"] = run
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
    return ws


async def options(request):
    return web.Response(headers=CORS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--services", choices=["on", "off"], default="on")
    ap.add_argument("--play", action="store_true",
                    help="play the source and agent speech on this machine's speakers (demo)")
    ap.add_argument("--port", type=int, default=8765)
    a = ap.parse_args()
    app = web.Application()
    app["services"] = engine.Services() if a.services == "on" else None
    app["play"] = a.play
    app.router.add_get("/v0/health", health)
    app.router.add_get("/v0/configurations", configurations)
    app.router.add_get("/v0/sources", sources)
    app.router.add_get("/v0/runs/{run_id}", run_log)
    app.router.add_get("/v0/ws", ws_handler)
    app.router.add_route("OPTIONS", "/{tail:.*}", options)
    print(f"agent server: http://127.0.0.1:{a.port}  services={a.services}", flush=True)
    web.run_app(app, host="127.0.0.1", port=a.port, print=None)


if __name__ == "__main__":
    main()
