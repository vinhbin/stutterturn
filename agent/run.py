"""Run one or more replays from the command line.

usage:
  python agent/run.py --config stock --source HeStutters_2_57.wav --services off
  python agent/run.py --config patient --all --services off
"""
import argparse
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine  # noqa: E402


def print_msg(msg):
    if msg["type"] == "event":
        extra = msg.get("state") or msg.get("name", "")
        prob = msg.get("prob")
        bits = [f"{msg['t']:7.3f}", f"{msg['kind']:9s}", extra]
        if prob is not None:
            bits.append(f"p={prob}")
        for k in ("trigger", "service", "before_audible", "overlap_s", "detail"):
            if k in msg:
                bits.append(f"{k}={msg[k]}")
        print("  ".join(str(b) for b in bits))
    elif msg["type"] == "run_started":
        print(f"== {msg['run_id']}  {msg['config']}  {msg['source']['source_id']}  "
              f"services={msg['services']}  commit={msg['commit']}")
    elif msg["type"] == "run_ended":
        print(f"== ended ({msg['reason']}) summary: {json.dumps(msg['summary'])}")
        print(f"   log: {msg['log']}")


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="stock", choices=list(engine.CONFIGS))
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--source")
    g.add_argument("--all", action="store_true")
    ap.add_argument("--services", choices=["on", "off"], default="off")
    ap.add_argument("--play", action="store_true",
                    help="play the source and agent speech on the laptop speakers")
    a = ap.parse_args()

    services = engine.Services() if a.services == "on" else None
    sources = engine.list_sources() if a.all else [a.source]
    if not sources:
        sys.exit("no sources in benchmark/audio/; run agent/fetch_assets.py")
    for src in sources:
        run = engine.Run(a.config, src, services=services, listener=print_msg, play=a.play)
        await run.run()


if __name__ == "__main__":
    asyncio.run(main())
