"""Laptop-speaker playback for live demos (`--play`).

One 16 kHz mono timeline: the source recording (plus trailing silence) is laid down up
front, and agent speech is mixed in when it arrives. Timeline sample i plays i/16000 s
after the stream starts, so in play mode event times for agent audio are positions on
this timeline, directly comparable with source times. Both tracks share the output
device's latency (reported, not measured acoustically).
"""
import threading

import numpy as np

SR = 16000
GUARD = 256  # samples of headroom ahead of the read pointer when scheduling agent audio
MAX_PENDING = 8000  # 500 ms; reject whole chunks rather than silently truncate


class PendingAudioFull(BufferError):
    """Retry after the device consumes queued samples."""


class Player:
    def __init__(self, source, extra_s=30.0, device=None):
        import sounddevice as sd
        n = len(source) + int(extra_s * SR)
        self.src = np.zeros(n, dtype=np.float32)
        self.src[:len(source)] = source
        self.agent = np.zeros(n, dtype=np.float32)
        self.read = 0              # next timeline sample the device will pull
        self.agent_next = None     # next free agent sample index
        self.agent_cut = None      # agent audio silenced from this index (barge-in)
        self.agent_start = None
        self.generation = 0
        self.accepting = True
        self.closed = False
        self.errors = []
        self.gaps = 0              # late chunks pushed past their slot
        self.lock = threading.Lock()
        self.stream = sd.OutputStream(samplerate=SR, channels=1, dtype="float32", blocksize=GUARD,
                                      latency="low", device=device, callback=self._cb)
        self.device_name = sd.query_devices(self.stream.device)["name"]

    def _cb(self, outdata, frames, _time, _status):
        with self.lock:
            if self.closed:
                outdata.fill(0)
                return
            i, j = self.read, self.read + frames
            if j <= len(self.src):
                mix = self.src[i:j] + self.agent[i:j]
            else:
                mix = np.zeros(frames, dtype=np.float32)
                k = max(0, len(self.src) - i)
                mix[:k] = self.src[i:i + k] + self.agent[i:i + k]
            self.read = j
        outdata[:, 0] = np.clip(mix, -1.0, 1.0)

    def start(self):
        self.stream.start()

    def info(self):
        return {"device": self.device_name, "samplerate": SR, "blocksize": GUARD,
                "reported_output_latency_s": round(float(self.stream.latency), 4),
                "timing_version": "playback-v1", "max_pending_samples": MAX_PENDING,
                "capacity_policy": "reject_whole_chunk",
                "note": "event t is the timeline position; device latency applies equally to "
                        "source and agent audio and is not measured acoustically"}

    def begin_agent(self):
        """Accept one new reply; its token fences late callbacks from older replies."""
        with self.lock:
            if self.closed:
                return None
            self.agent[self.read:] = 0.0
            self.generation += 1
            self.accepting = True
            self.agent_start = self.agent_next = self.agent_cut = None
            return self.generation

    def add_agent(self, pcm, want_index=None, *, generation=None):
        """Mix agent PCM (float32) into the timeline. The first call (want_index set)
        starts agent speech at max(want_index, read + GUARD); later calls continue
        contiguously, or at read + GUARD if their slot already played. Returns the
        start index used for this piece, or None for empty/retired/closed input.
        Capacity exhaustion raises BufferError without accepting any samples.
        Engine callers must carry the token returned by begin_agent()."""
        with self.lock:
            if (self.closed or not self.accepting or not len(pcm)
                    or (generation is not None and generation != self.generation)):
                return None
            floor = self.read + GUARD
            if want_index is not None:
                start = max(want_index, floor)
            else:
                start = self.agent_next if self.agent_next is not None else floor
                if start < floor:
                    start = floor
            end = start + len(pcm)
            if end > len(self.agent):
                raise BufferError("playback timeline capacity exhausted")
            pending_start = max(self.read, self.agent_start if self.agent_start is not None
                                else start)
            if end - pending_start > MAX_PENDING:
                raise PendingAudioFull("playback pending capacity exhausted (8000 samples)")
            if want_index is None and self.agent_next is not None and self.agent_next < floor:
                self.gaps += 1
            self.agent[start:end] += pcm
            if self.agent_start is None:
                self.agent_start = start
            self.agent_next = end
            return start

    def cut_agent(self, index, *, generation=None):
        """Retire this generation and return the first sample we could silence.

        Already submitted device buffers cannot be retracted by this index.
        """
        with self.lock:
            if generation is not None and generation != self.generation:
                return None
            index = max(index, self.read)
            self.accepting = False
            self.agent_cut = index
            self.agent[index:] = 0.0
            if self.agent_next is not None:
                self.agent_next = min(index, self.agent_next)
            return index

    def position(self):
        with self.lock:
            return self.read

    def abort(self):
        """Invalidate both tracks immediately, then ask the device to discard buffers."""
        with self.lock:
            if self.closed:
                return self.read
            self.closed = True
            self.accepting = False
            self.src.fill(0)
            self.agent.fill(0)
            index = self.read
        try:
            self.stream.abort()
        except Exception as exc:
            self.errors.append(f"abort: {exc}")
        try:
            self.stream.close()
        except Exception as exc:
            self.errors.append(f"close: {exc}")
        return index

    def close(self):
        if self.closed:
            return
        try:
            self.stream.stop()
        except Exception as exc:
            self.errors.append(f"stop: {exc}")
        with self.lock:
            self.closed = True
            self.accepting = False
        try:
            self.stream.close()
        except Exception as exc:
            self.errors.append(f"close: {exc}")
