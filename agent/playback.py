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
        self.gaps = 0              # late chunks pushed past their slot
        self.lock = threading.Lock()
        self.stream = sd.OutputStream(samplerate=SR, channels=1, dtype="float32", blocksize=GUARD,
                                      latency="low", device=device, callback=self._cb)
        self.device_name = sd.query_devices(self.stream.device)["name"]

    def _cb(self, outdata, frames, _time, _status):
        with self.lock:
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
                "note": "event t is the timeline position; device latency applies equally to "
                        "source and agent audio and is not measured acoustically"}

    def add_agent(self, pcm, want_index=None):
        """Mix agent PCM (float32) into the timeline. The first call (want_index set)
        starts agent speech at max(want_index, read + GUARD); later calls continue
        contiguously, or at read + GUARD if their slot already played. Returns the
        start index used for this piece, or None if silenced by a barge-in."""
        with self.lock:
            floor = self.read + GUARD
            if want_index is not None:
                start = max(want_index, floor)
            else:
                start = self.agent_next
                if start < floor:
                    self.gaps += 1
                    start = floor
            if self.agent_cut is not None and start >= self.agent_cut:
                return None
            end = min(start + len(pcm), len(self.agent))
            if self.agent_cut is not None:
                end = min(end, self.agent_cut)
            self.agent[start:end] += pcm[:end - start]
            self.agent_next = start + len(pcm)
            return start

    def cut_agent(self, index):
        """Silence agent audio from timeline index onward (barge-in)."""
        with self.lock:
            index = max(index, self.read)
            self.agent_cut = index
            self.agent[index:] = 0.0

    def position(self):
        with self.lock:
            return self.read

    def close(self):
        try:
            self.stream.stop()
            self.stream.close()
        except Exception:
            pass
