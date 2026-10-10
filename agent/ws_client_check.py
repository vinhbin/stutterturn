"""Tiny WebSocket client to check agent/server.py.

usage: python agent/ws_client_check.py [config] [source] [--port 8765]
Exits non-zero if the server sends an error or the run does not end.
"""
import asyncio
import json
import sys

import aiohttp


async def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    config = args[0] if args else "stock"
    source = args[1] if len(args) > 1 else "HeStutters_4_32.wav"
    port = int(sys.argv[sys.argv.index("--port") + 1]) if "--port" in sys.argv else 8765
    async with aiohttp.ClientSession() as s:
        async with s.ws_connect(f"ws://127.0.0.1:{port}/v0/ws") as ws:
            await ws.send_json({"type": "start", "config": config, "source": source})
            async for m in ws:
                msg = json.loads(m.data)
                if msg["type"] == "event":
                    print(msg["seq"], msg["t"], msg["kind"], msg.get("name") or msg.get("state"),
                          msg.get("prob", ""))
                else:
                    print(json.dumps(msg)[:300])
                if msg["type"] == "error":
                    sys.exit(1)
                if msg["type"] == "run_ended":
                    return
    sys.exit("socket closed before run_ended")


if __name__ == "__main__":
    asyncio.run(asyncio.wait_for(main(), timeout=60))
