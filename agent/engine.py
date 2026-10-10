"""StutterTurn agent engine: replay a real source recording through VAD + an
end-of-turn model, optionally reply with Gemini + ElevenLabs, and log timings.

Interface: agent/CONTRACT.md. Steps: agent/IMPLEMENTATION_STEPS.md.
"""
import asyncio
import datetime as dt
import hashlib
import io
import json
import os
import secrets
import subprocess
import time

import numpy as np
import onnxruntime as ort
import soundfile as sf

SR = 16000
FRAME = 512                  # Silero v5 needs 512 samples at 16 kHz -> 32 ms frames
FRAME_S = FRAME / SR         # 0.032
TRAILING_SILENCE_S = 5.0     # fed after the source ends
CONTRACT_VERSION = "0.1"
SPEECH_PROB = 0.5
PRE_ROLL_S = 0.2

AGENT = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(AGENT)
MODELS = os.path.join(AGENT, "models")
AUDIO = os.path.join(ROOT, "benchmark", "audio")
RUNS = os.path.join(AGENT, "runs")
STOCK_MODEL = os.path.join(MODELS, "smart-turn-v3.2-cpu.onnx")
SILERO_MODEL = os.path.join(MODELS, "silero_vad.onnx")

PROMPT = ("You are a helpful voice assistant on a phone line. The caller's audio is attached. "
          "Reply in one short sentence, at most 20 words. Never comment on how the caller speaks.")

CONFIGS = {
    "stock": {"label": "Stock Smart Turn v3.2", "model": "smart-turn-v3.2-cpu",
              "vad_stop_s": 0.2, "vad_start_s": 0.2, "threshold": 0.5, "fallback_s": 3.0,
              "detail": "Smart Turn v3.2 CPU ONNX; model runs after 0.2 s of silence; "
                        "3.0 s silence fallback"},
    "patient": {"label": "Patient (longer wait, same model)", "model": "smart-turn-v3.2-cpu",
                "vad_stop_s": 1.0, "vad_start_s": 0.2, "threshold": 0.5, "fallback_s": 3.0,
                "detail": "Same model and threshold; acts only after 1.0 s of silence "
                          "(stock: 0.2 s). A waiting configuration, not a trained model"},
    "candidate": {"label": "StutterTurn candidate", "model": "candidate",
                  "vad_stop_s": 0.2, "vad_start_s": 0.2, "threshold": 0.5, "fallback_s": 3.0,
                  "detail": "Niko's export from CANDIDATE_MODEL; same turn logic as stock"},
}


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _commit():
    """Short HEAD SHA, with "-dirty" if agent/ has uncommitted changes (so a log
    never names a commit that differs from the code that produced it)."""
    try:
        sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                             capture_output=True, text=True, check=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain", "--", "agent/"], cwd=ROOT,
                               capture_output=True, text=True, check=True).stdout.strip()
        return sha + ("-dirty" if dirty else "")
    except Exception:
        return "unknown"


def candidate_path():
    p = os.getenv("CANDIDATE_MODEL", "")
    return p if p and os.path.exists(p) else None


def configurations():
    out = []
    for cid, c in CONFIGS.items():
        available = cid != "candidate" or candidate_path() is not None
        out.append({"id": cid, "label": c["label"], "detail": c["detail"],
                    "available": available,
                    "note": "" if available else "No candidate export yet (CANDIDATE_MODEL unset)",
                    "model": c["model"],
                    "params": {k: c[k] for k in ("vad_stop_s", "vad_start_s", "threshold", "fallback_s")}})
    return out


class SileroVAD:
    def __init__(self, path=SILERO_MODEL):
        so = ort.SessionOptions()
        so.inter_op_num_threads = 1
        so.intra_op_num_threads = 1
        self.sess = ort.InferenceSession(path, sess_options=so, providers=["CPUExecutionProvider"])
        self.reset()

    def reset(self):
        self.state = np.zeros((2, 1, 128), dtype=np.float32)
        self.context = np.zeros((1, 64), dtype=np.float32)

    def __call__(self, frame):
        x = np.concatenate([self.context, frame[None, :]], axis=1)
        out, self.state = self.sess.run(None, {"input": x, "state": self.state,
                                               "sr": np.array(SR, dtype=np.int64)})
        self.context = x[:, -64:]
        return float(out[0][0])


class SmartTurn:
    _cache = {}

    def __init__(self, path):
        from transformers import WhisperFeatureExtractor
        so = ort.SessionOptions()
        so.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        so.inter_op_num_threads = 1
        so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        self.sess = ort.InferenceSession(path, sess_options=so, providers=["CPUExecutionProvider"])
        self.fe = WhisperFeatureExtractor(chunk_length=8)
        self.sha256 = _sha256(path)

    @classmethod
    def load(cls, path):
        if path not in cls._cache:
            cls._cache[path] = cls(path)
        return cls._cache[path]

    def predict(self, audio):
        n = 8 * SR
        audio = audio[-n:] if len(audio) > n else np.pad(audio, (n - len(audio), 0))
        inputs = self.fe(audio, sampling_rate=SR, return_tensors="np", padding="max_length",
                         max_length=n, truncation=True, do_normalize=True)
        feats = np.expand_dims(inputs.input_features.squeeze(0).astype(np.float32), 0)
        return float(self.sess.run(None, {"input_features": feats})[0][0].item())


def list_sources():
    if not os.path.isdir(AUDIO):
        return []
    return sorted(f for f in os.listdir(AUDIO) if f.lower().endswith(".wav"))


def load_source(name):
    path = os.path.join(AUDIO, os.path.basename(name))
    x, sr = sf.read(path, dtype="float32")
    if x.ndim > 1:
        x = x.mean(axis=1)
    if sr != SR:
        raise ValueError(f"{name}: expected {SR} Hz, got {sr}")
    return x


# ---------------------------------------------------------------- services

class Services:
    """Gemini reply + ElevenLabs streaming TTS. One instance per process."""

    def __init__(self):
        from dotenv import load_dotenv
        load_dotenv(os.path.join(AGENT, ".env"))
        missing = [k for k in ("GEMINI_API_KEY", "ELEVENLABS_API_KEY") if not os.getenv(k)]
        if missing:
            raise RuntimeError("Missing in agent/.env: " + ", ".join(missing))
        from google import genai
        self.genai_client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        self.gemini_model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
        self.el_key = os.environ["ELEVENLABS_API_KEY"]
        self.voice_id = os.getenv("ELEVENLABS_VOICE_ID", "")
        self.max_chars = int(os.getenv("ELEVENLABS_MAX_CHARS", "3000"))
        self.chars_used = 0

    async def reply_text(self, audio):
        from google.genai import types
        wav = io.BytesIO()
        sf.write(wav, audio, SR, format="WAV", subtype="PCM_16")
        resp = await self.genai_client.aio.models.generate_content(
            model=self.gemini_model,
            contents=[types.Part.from_bytes(data=wav.getvalue(), mime_type="audio/wav"), PROMPT],
            config=types.GenerateContentConfig(
                max_output_tokens=60, temperature=0.4,
                thinking_config=types.ThinkingConfig(thinking_budget=0)))
        return (resp.text or "").strip()[:120]

    async def _voice(self, session):
        if not self.voice_id:
            async with session.get("https://api.elevenlabs.io/v1/voices",
                                   headers={"xi-api-key": self.el_key}) as r:
                r.raise_for_status()
                self.voice_id = (await r.json())["voices"][0]["voice_id"]
        return self.voice_id

    async def stream_tts(self, text, on_chunk):
        """Calls on_chunk(bytes) per PCM chunk; returns total bytes."""
        import aiohttp
        if self.chars_used + len(text) > self.max_chars:
            raise CreditCapReached()
        self.chars_used += len(text)
        total = 0
        timeout = aiohttp.ClientTimeout(total=20)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            voice = await self._voice(session)
            url = (f"https://api.elevenlabs.io/v1/text-to-speech/{voice}/stream"
                   "?output_format=pcm_16000")
            async with session.post(url, headers={"xi-api-key": self.el_key},
                                    json={"text": text, "model_id": "eleven_flash_v2_5"}) as r:
                if r.status != 200:
                    raise RuntimeError(f"ElevenLabs HTTP {r.status}: {(await r.text())[:200]}")
                async for chunk in r.content.iter_chunked(3200):
                    total += len(chunk)
                    on_chunk(chunk)
        return total


class CreditCapReached(Exception):
    pass


# ---------------------------------------------------------------- run

class Run:
    def __init__(self, config, source, services=None, listener=None):
        if config not in CONFIGS:
            raise ValueError(f"unknown config {config!r}")
        self.config = config
        self.cfg = CONFIGS[config]
        if config == "candidate":
            path = candidate_path()
            if not path:
                raise ValueError("candidate unavailable: CANDIDATE_MODEL unset or missing")
        else:
            path = STOCK_MODEL
        self.model_path = path
        self.model_name = os.path.basename(path).rsplit(".", 1)[0]
        self.source_name = os.path.basename(source)
        self.audio = load_source(source)
        self.services = services
        self.listener = listener
        self.run_id = (f"{dt.datetime.now(dt.timezone.utc):%Y%m%dT%H%M%SZ}-{config}-"
                       f"{secrets.token_hex(2)}")
        self.seq = 0
        self.stopped = False
        os.makedirs(RUNS, exist_ok=True)
        self.log_path = os.path.join(RUNS, f"{self.run_id}.jsonl")
        self._log = None
        self.t0 = None
        # summary state
        self.s = {"first_turn_complete_t": None, "trigger": None, "first_agent_audio_t": None,
                  "llm_latency_s": None, "tts_first_audio_s": None,
                  "speaker_resumed_after_decision": False, "cancelled": False,
                  "audible_interruption": False, "overlap_s": None, "no_response": False,
                  "timeouts": [], "reply_text": None}
        self.turns = 0
        self.reply_task = None
        self.agent_audio_start = None   # t
        self.agent_audio_end = None     # t (scheduled)
        self.agent_audible = False

    # -- emit
    def now(self):
        return round(time.monotonic() - self.t0, 3)

    def _send(self, msg):
        self._log.write(json.dumps(msg, separators=(",", ":")) + "\n")
        self._log.flush()
        if self.listener:
            self.listener(msg)
        self.seq += 1

    def event(self, t, kind, name=None, **fields):
        msg = {"v": CONTRACT_VERSION, "type": "event", "run_id": self.run_id, "seq": self.seq,
               "t": round(t, 3), "kind": kind}
        if name:
            msg["name"] = name
        msg.update(fields)
        self._send(msg)

    def state(self, t, state, **fields):
        self.event(t, "state", state=state, **fields)

    def stop(self):
        self.stopped = True

    # -- reply
    def _start_reply(self, t, turn_audio):
        if self.services is None:
            self.event(t, "info", "response_requested", detail="services off")
            return
        self.event(t, "info", "response_requested", detail=f"gemini {self.services.gemini_model}")
        self.reply_task = asyncio.create_task(self._reply(np.concatenate(turn_audio)))

    async def _reply(self, audio):
        try:
            t_req = time.monotonic()
            try:
                text = await asyncio.wait_for(self.services.reply_text(audio), timeout=10)
            except asyncio.TimeoutError:
                self.event(self.now(), "info", "timeout", service="gemini")
                self.s["timeouts"].append("gemini")
                return
            self.s["llm_latency_s"] = round(time.monotonic() - t_req, 3)
            self.s["reply_text"] = text
            if not text:
                self.event(self.now(), "info", "timeout", service="gemini", detail="empty reply")
                self.s["timeouts"].append("gemini")
                return
            t_tts = time.monotonic()

            def on_chunk(chunk):
                if self.agent_audio_start is None:
                    t = self.now()
                    self.agent_audio_start = t
                    self.agent_audible = True
                    self.s["first_agent_audio_t"] = self.s["first_agent_audio_t"] or t
                    self.s["tts_first_audio_s"] = round(time.monotonic() - t_tts, 3)
                    self.event(t, "audible", "agent_audio_start", detail=text)
                    self.state(t, "agent")

            try:
                total = await asyncio.wait_for(self.services.stream_tts(text, on_chunk), timeout=10)
            except asyncio.TimeoutError:
                self.event(self.now(), "info", "timeout", service="elevenlabs")
                self.s["timeouts"].append("elevenlabs")
                return
            except CreditCapReached:
                self.event(self.now(), "info", "timeout", service="elevenlabs",
                           detail="local character cap reached")
                self.s["timeouts"].append("elevenlabs")
                return
            if self.agent_audio_start is not None:
                self.agent_audio_end = self.agent_audio_start + total / 2 / SR
        except asyncio.CancelledError:
            raise
        except Exception as e:
            self.event(self.now(), "info", "timeout", service="reply", detail=str(e)[:200])
            self.s["timeouts"].append("reply")

    def _maybe_end_agent_audio(self, t):
        if self.agent_audible and self.agent_audio_end is not None and t >= self.agent_audio_end:
            self.agent_audible = False
            self.event(self.agent_audio_end, "audible", "agent_audio_end")
            self.state(self.agent_audio_end, "silence")

    def _barge_in(self, t_resume, vad_start_s):
        task = self.reply_task
        if self.agent_audible:
            t_stop = t_resume + vad_start_s
            self.event(t_resume, "audible", "overlap")
            self.agent_audible = False
            overlap = round(t_stop - t_resume, 3)
            self.event(t_stop, "audible", "agent_audio_end", overlap_s=overlap)
            self.event(t_stop, "info", "cancelled", before_audible=False)
            self.s["audible_interruption"] = True
            self.s["overlap_s"] = overlap
            self.s["cancelled"] = True
            if task and not task.done():
                task.cancel()
        elif task and not task.done():
            task.cancel()
            self.event(t_resume, "info", "cancelled", before_audible=True)
            self.s["cancelled"] = True
        self.reply_task = None
        self.agent_audio_start = None
        self.agent_audio_end = None

    # -- main loop
    async def run(self):
        cfg = self.cfg
        model = await asyncio.to_thread(SmartTurn.load, self.model_path)
        vad = SileroVAD()
        self._log = open(self.log_path, "w", encoding="utf-8", newline="\n")
        trailing = np.zeros(int(TRAILING_SILENCE_S * SR), dtype=np.float32)
        stream = np.concatenate([self.audio, trailing])
        n_frames = len(stream) // FRAME
        pre_roll_n = int(round(PRE_ROLL_S / FRAME_S))
        start_n = int(np.ceil(cfg["vad_start_s"] / FRAME_S - 1e-9))
        stop_n = int(np.ceil(cfg["vad_stop_s"] / FRAME_S - 1e-9))
        fallback_n = int(np.ceil(cfg["fallback_s"] / FRAME_S - 1e-9))

        self.t0 = time.monotonic()
        self._send({"v": CONTRACT_VERSION, "type": "run_started", "run_id": self.run_id,
                    "seq": self.seq, "config": self.config,
                    "params": {k: cfg[k] for k in ("vad_stop_s", "vad_start_s", "threshold",
                                                   "fallback_s")}
                              | {"frame_s": FRAME_S, "trailing_silence_s": TRAILING_SILENCE_S},
                    "model": self.model_name, "model_sha256": model.sha256,
                    "source": {"source_id": self.source_name,
                               "duration_s": round(len(self.audio) / SR, 3),
                               "source_offset_s": 0},
                    "commit": _commit(),
                    "t0_wall": dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds")
                               .replace("+00:00", "Z"),
                    "services": "on" if self.services else "off"})

        in_speech = False
        speech_run = silence_run = 0
        first_speech_i = first_silence_i = None
        pre_roll = []
        turn_audio = None          # list of frames, None = no open turn
        decided = False
        checked = False
        reason = "completed"

        for i in range(n_frames):
            if self.stopped:
                reason = "stopped"
                break
            target = self.t0 + i * FRAME_S
            delay = target - time.monotonic()
            if delay > 0:
                await asyncio.sleep(delay)
            ft = i * FRAME_S
            self._maybe_end_agent_audio(ft)
            frame = stream[i * FRAME:(i + 1) * FRAME]
            p = vad(frame)
            pre_roll.append(frame)
            if len(pre_roll) > pre_roll_n:
                pre_roll.pop(0)
            if turn_audio is not None:
                turn_audio.append(frame)

            if p >= SPEECH_PROB:
                if speech_run == 0:
                    first_speech_i = i
                speech_run += 1
                silence_run = 0
                if not in_speech and speech_run >= start_n:
                    in_speech = True
                    st = first_speech_i * FRAME_S
                    self.event(st, "info", "speech_start", prob=round(p, 3))
                    self.state(st, "speaking")
                    checked = False
                    if turn_audio is not None and decided:
                        self.event(st, "info", "speaker_resumed")
                        self.s["speaker_resumed_after_decision"] = True
                        self._barge_in(st, cfg["vad_start_s"])
                        turn_audio = None
                    if turn_audio is None:
                        turn_audio = list(pre_roll)
                        decided = False
                        self.turns += 1
            else:
                if silence_run == 0:
                    first_silence_i = i
                silence_run += 1
                speech_run = 0
                if in_speech and silence_run >= stop_n:
                    in_speech = False
                    stt = first_silence_i * FRAME_S
                    self.event(stt, "info", "speech_stop")
                    self.state(stt, "silence")
                    if turn_audio is not None and not decided and not checked:
                        checked = True
                        prob = await asyncio.to_thread(model.predict, np.concatenate(turn_audio))
                        if prob > cfg["threshold"]:
                            decided = True
                            self.event(ft, "decision", "turn_complete", model=self.model_name,
                                       prob=round(prob, 4), threshold=cfg["threshold"],
                                       trigger="smart_turn")
                            self._first_decision(ft, "smart_turn")
                            self._start_reply(ft, turn_audio)
                        else:
                            self.event(ft, "decision", "turn_incomplete", model=self.model_name,
                                       prob=round(prob, 4), threshold=cfg["threshold"])
                            self.state(ft, "holding", prob=round(prob, 4), model=self.model_name)
                if (turn_audio is not None and not decided and not in_speech
                        and silence_run >= fallback_n):
                    decided = True
                    self.event(ft, "decision", "turn_complete", model=self.model_name, prob=None,
                               threshold=cfg["threshold"], trigger="fallback_timeout")
                    self._first_decision(ft, "fallback_timeout")
                    self._start_reply(ft, turn_audio)

        if self.s["first_turn_complete_t"] is None and reason == "completed":
            self.event(n_frames * FRAME_S, "info", "no_response")
            self.s["no_response"] = True

        if self.reply_task and not self.reply_task.done():
            if reason == "stopped":
                self.reply_task.cancel()
            try:
                await asyncio.wait_for(asyncio.shield(self.reply_task), timeout=15)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                pass
        if self.agent_audible and self.agent_audio_end is not None:
            await asyncio.sleep(max(0.0, self.t0 + self.agent_audio_end - time.monotonic()))
            self._maybe_end_agent_audio(self.agent_audio_end)

        summary = dict(self.s)
        summary["services"] = "on" if self.services else "off"
        summary["chars_used"] = self.services.chars_used if self.services else 0
        summary["turns"] = self.turns
        self._send({"v": CONTRACT_VERSION, "type": "run_ended", "run_id": self.run_id,
                    "seq": self.seq, "t": self.now(), "reason": reason, "summary": summary,
                    "log": os.path.relpath(self.log_path, ROOT).replace("\\", "/")})
        self._log.close()
        return summary

    def _first_decision(self, t, trigger):
        if self.s["first_turn_complete_t"] is None:
            self.s["first_turn_complete_t"] = round(t, 3)
            self.s["trigger"] = trigger
