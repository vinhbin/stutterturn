"""Local contract fixture. Synthetic events only: no audio, models, or services.

Run: python web/demo-ui/dev/mock-agent-server.py
This deliberately small HTTP/WebSocket server is for UI development only.
"""

import argparse
import base64
import hashlib
import json
import math
import select
import struct
import time
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit


NOTICE = "MOCK — synthetic fixture; no audio, no model output, not evidence"
SCENARIOS = ("overlap", "held", "cancelled", "timeout", "no-response")
LOGS = {}


def tagged(**fields):
    return {"mock": True, "model": "mock", "detail": NOTICE, **fields}


def event(t, kind, name, **fields):
    return tagged(type="event", t=t, kind=kind, name=name, **fields)


def scenario(name):
    events = [event(0, "state", "state", state="speaking"),
              event(0, "info", "speech_start"),
              event(0.8, "info", "speech_stop"),
              event(0.8, "state", "state", state="silence"),
              event(1, "decision", "turn_incomplete", prob=0.2, threshold=0.5),
              event(1, "state", "state", state="holding")]
    summary = dict(first_turn_complete_t=None, first_agent_audio_t=None,
                   llm_latency_s=None, tts_first_audio_s=None,
                   audible_interruption=False, overlap_s=0, cancelled=False,
                   no_response=False, timeouts=[], speaker_resumed_after_decision=False)
    if name == "no-response":
        events.append(event(3.5, "info", "no_response"))
        summary["no_response"] = True
        return events, summary, 3.8
    complete = 3.3 if name == "held" else 1.5
    if name == "held":
        events += [event(2, "info", "speech_start"),
                   event(2, "state", "state", state="speaking"),
                   event(3, "info", "speech_stop"),
                   event(3, "state", "state", state="silence")]
    trigger = "fallback_timeout" if name == "timeout" else "smart_turn"
    events += [event(complete, "decision", "turn_complete", prob=0.81,
                     threshold=0.5, trigger=trigger),
               event(complete, "info", "response_requested")]
    summary.update(first_turn_complete_t=complete, trigger=trigger)
    if name == "cancelled":
        events += [event(1.9, "info", "speaker_resumed"),
                   event(1.9, "state", "state", state="speaking"),
                   event(1.9, "info", "cancelled", before_audible=True)]
        summary.update(cancelled=True, speaker_resumed_after_decision=True)
        return events, summary, 2.5
    if name == "timeout":
        events += [event(2.2, "info", "timeout", service="mock-reply"),
                   event(2.3, "info", "no_response")]
        summary.update(no_response=True, timeouts=["mock-reply"])
        return events, summary, 2.8
    audio_start = 4 if name == "held" else 2.1
    audio_end = 4.7 if name == "held" else 3
    events += [event(audio_start, "audible", "agent_audio_start"),
               event(audio_start, "state", "state", state="agent")]
    summary.update(first_agent_audio_t=audio_start, llm_latency_s=0.35,
                   tts_first_audio_s=audio_start - complete - 0.35)
    if name == "overlap":
        events += [event(2.4, "info", "speaker_resumed"),
                   event(2.4, "state", "state", state="speaking"),
                   event(2.4, "audible", "overlap")]
        summary.update(audible_interruption=True, overlap_s=0.6,
                       speaker_resumed_after_decision=True)
    events += [event(audio_end, "audible", "agent_audio_end", overlap_s=summary["overlap_s"]),
               event(audio_end, "info", "speech_stop"),
               event(audio_end, "state", "state", state="silence")]
    return events, summary, audio_end + 0.4


def frame(payload, opcode=1):
    if not isinstance(payload, bytes):
        payload = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    length = len(payload)
    header = bytes([0x80 | opcode])
    header += bytes([length]) if length < 126 else bytes([126]) + struct.pack("!H", length)
    return header + payload


def read_frames(buffer):
    """Consume complete masked browser frames; retain a partial frame in buffer."""
    messages = []
    while len(buffer) >= 2:
        first, second = buffer[:2]
        if not first & 0x80 or first & 0x70 or not second & 0x80:
            raise ValueError("Only complete, masked WebSocket frames are supported by this dev mock")
        length, offset = second & 127, 2
        if length == 127:
            raise ValueError("Message exceeds mock limit")
        if length == 126:
            if len(buffer) < 4:
                break
            length, offset = struct.unpack("!H", buffer[2:4])[0], 4
        if length > 16384:
            raise ValueError("Message exceeds mock limit")
        if len(buffer) < offset + 4 + length:
            break
        mask = buffer[offset:offset + 4]
        start = offset + 4
        payload = bytes(value ^ mask[i % 4] for i, value in enumerate(buffer[start:start + length]))
        del buffer[:start + length]
        messages.append((first & 15, payload))
    return messages


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format, *args):
        pass

    def send_json(self, data, status=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/v0/health":
            self.send_json(tagged(ok=True, contract="0.1", commit="development-mock", services="off"))
        elif path == "/v0/configurations":
            self.send_json([tagged(id=arm, label=label, available=arm != "candidate",
                                  note=NOTICE, model_sha256="mock-not-a-model",
                                  params={"fixture": "identical across arms", "services": "off"})
                            for arm, label in (("stock", "STOCK"), ("patient", "PATIENT"),
                                               ("candidate", "STUTTERTURN"))])
        elif path == "/v0/sources":
            self.send_json([tagged(source_id="mock-" + name, file=name + ".fixture",
                                  duration_s=5, category="synthetic-" + name, rights_note=NOTICE)
                            for name in SCENARIOS])
        elif path.startswith("/v0/runs/"):
            rows = LOGS.get(path.rsplit("/", 1)[-1])
            if rows is None:
                self.send_json(tagged(error="Unknown mock run"), 404)
            else:
                body = "".join(json.dumps(row) + "\n" for row in rows).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/x-ndjson")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(body)
        elif path == "/v0/ws" and self.headers.get("Upgrade", "").lower() == "websocket":
            self.websocket()
        else:
            self.send_json(tagged(error="Unknown development endpoint"), 404)

    def websocket(self):
        key = self.headers.get("Sec-WebSocket-Key", "")
        if not key or self.headers.get("Sec-WebSocket-Version") != "13":
            self.send_json(tagged(error="WebSocket version 13 required"), 400)
            return
        accept = base64.b64encode(hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()).digest()).decode()
        self.send_response(101)
        self.send_header("Upgrade", "websocket")
        self.send_header("Connection", "Upgrade")
        self.send_header("Sec-WebSocket-Accept", accept)
        self.end_headers()
        self.wfile.flush()
        self.close_connection = True
        buffer, queue = bytearray(), []
        run_id, seq, started = None, 0, 0

        def emit(message):
            nonlocal seq
            payload = tagged(v="0.1", run_id=run_id, seq=seq, **message)
            self.connection.sendall(frame(payload))
            if run_id:
                LOGS[run_id].append(payload)
            seq += 1

        try:
            while True:
                if select.select([self.connection], [], [], 0.02)[0]:
                    chunk = self.connection.recv(16384)
                    if not chunk:
                        return
                    buffer.extend(chunk)
                    for opcode, payload in read_frames(buffer):
                        if opcode == 8:
                            self.connection.sendall(frame(b"", 8))
                            return
                        if opcode == 9:
                            self.connection.sendall(frame(payload, 10))
                            continue
                        if opcode != 1:
                            raise ValueError("This mock accepts text commands only")
                        command = json.loads(payload.decode("utf-8"))
                        if not isinstance(command, dict):
                            raise ValueError("Expected an object command")
                        if command.get("type") == "stop":
                            if run_id and command.get("run_id") == run_id:
                                queue = []
                                emit(dict(type="run_ended", t=(time.monotonic() - started) * self.server.speed,
                                          reason="stopped", summary={}))
                                run_id = None
                        elif command.get("type") == "start":
                            name = str(command.get("source", "")).removesuffix(".fixture")
                            if run_id or name not in SCENARIOS or command.get("config") not in ("stock", "patient"):
                                raise ValueError("Choose an available mock arm and fixture; one run at a time")
                            run_id = "mock-" + uuid.uuid4().hex[:12]
                            seq, started = 0, time.monotonic()
                            if len(LOGS) >= 20:
                                LOGS.pop(next(iter(LOGS)))
                            LOGS[run_id] = []
                            emit(dict(type="run_started", config=command["config"],
                                      client_ref=command.get("client_ref"), services="off",
                                      model_sha256="mock-not-a-model", commit="development-mock",
                                      params={"fixture": name, "identical_across_arms": True},
                                      source={"source_id": "mock-" + name, "file": name + ".fixture",
                                              "duration_s": 5, "source_offset_s": 0, "mock": True},
                                      t0_wall=datetime.now(timezone.utc).isoformat()))
                            events, summary, end = scenario(name)
                            queue = events + [tagged(type="run_ended", t=end, reason="completed",
                                                     summary=summary, log="/v0/runs/" + run_id)]
                        else:
                            raise ValueError("Unknown mock command")
                while queue and queue[0]["t"] <= (time.monotonic() - started) * self.server.speed:
                    message = queue.pop(0)
                    emit(message)
                    if message["type"] == "run_ended":
                        run_id = None
        except (ValueError, UnicodeError) as error:
            try:
                self.connection.sendall(frame(tagged(v="0.1", type="error", run_id=run_id,
                                                    seq=-1, message="MOCK: " + str(error))))
            except OSError:
                pass
        except OSError:
            pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--speed", type=float, default=1, help="Fixture playback speed; event timestamps stay synthetic")
    args = parser.parse_args()
    if not math.isfinite(args.speed) or args.speed <= 0:
        parser.error("--speed must be finite and positive")
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    server.speed = args.speed
    print(f"DEVELOPMENT MOCK at http://127.0.0.1:{args.port} — NO AUDIO / NOT EVIDENCE", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
