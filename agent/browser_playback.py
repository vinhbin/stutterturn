"""Bounded PCM transport on the server timeline; browser/device latency is separate.

Implements the laptop Player interface without opening a server sound device.
PCM goes only to the requesting authenticated socket, never into the event log.
"""
import base64
import time

import numpy as np

from playback import GUARD, MAX_PENDING, PendingAudioFull, SR


class BrowserPlayer:
    transport = "pcm16-v1"

    def __init__(self, source, send, clock=time.monotonic):
        if len(source) > 90 * SR:
            raise ValueError("Browser replay source exceeds 90 seconds")
        self.source = source
        self.send = send
        self.clock = clock
        self.t0 = None
        self.agent_start = self.agent_next = None
        self.generation = 0
        self.accepting = True
        self.closed = False
        self.errors = []
        self.gaps = 0

    def start(self):
        self.t0 = self.clock()

    def info(self):
        return {"transport": self.transport, "samplerate": SR,
                "timing_version": "browser-schedule-v1", "max_pending_samples": MAX_PENDING,
                "note": "Server sample schedule; browser buffers 250 ms plus network delay. "
                        "Not measured acoustic playback."}

    def _emit(self, action, **fields):
        self.send({"action": action, "sample_rate": SR, **fields})

    @staticmethod
    def _pcm(samples):
        pcm = (np.clip(samples, -1, 1) * 32767).astype("<i2")
        return base64.b64encode(pcm.tobytes()).decode("ascii")

    def send_source(self):
        self._emit("source", sample=0, pcm=self._pcm(self.source))

    def position(self):
        return max(0, int((self.clock() - self.t0) * SR)) if self.t0 is not None else 0

    def begin_agent(self):
        if self.closed:
            return None
        if self.generation:
            self._emit("cancel", generation=self.generation, sample=self.position())
        self.generation += 1
        self.accepting = True
        self.agent_start = self.agent_next = None
        return self.generation

    def add_agent(self, pcm, want_index=None, *, generation=None):
        if self.closed or not self.accepting or not len(pcm) or generation != self.generation:
            return None
        position = self.position()
        floor = position + GUARD
        start = max(floor, want_index if want_index is not None else (self.agent_next or floor))
        end = start + len(pcm)
        pending_start = max(position, self.agent_start if self.agent_start is not None else start)
        if end - pending_start > MAX_PENDING:
            raise PendingAudioFull("Browser audio pending capacity exhausted")
        if self.agent_next is not None and self.agent_next < floor:
            self.gaps += 1
        self._emit("agent", sample=start, generation=generation, pcm=self._pcm(pcm))
        if self.agent_start is None:
            self.agent_start = start
        self.agent_next = end
        return start

    def cut_agent(self, index, *, generation=None):
        if generation != self.generation or self.closed:
            return None
        index = max(index, self.position())
        self.accepting = False
        self._emit("cancel", sample=index, generation=generation)
        if self.agent_next is not None:
            self.agent_next = min(index, self.agent_next)
        return index

    def abort(self):
        index = self.position()
        if not self.closed:
            self.closed = True
            self.accepting = False
            self._emit("stop")
        return index

    def close(self):
        if not self.closed:
            self.closed = True
            self.accepting = False
            self._emit("finish")
