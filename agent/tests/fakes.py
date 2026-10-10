"""Offline boundaries: no models, devices, credentials or service calls."""
import importlib
from pathlib import Path
import sys
import types
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class FakeStream:
    device = 0
    latency = 0.01

    def __init__(self, **kwargs):
        self.callback = kwargs["callback"]
        self.closed = False
        self.aborted = False
        self.started = False

    def start(self):
        self.started = True

    def pull(self, frames=256, status=None):
        out = np.zeros((frames, 1), dtype=np.float32)
        self.callback(out, frames, types.SimpleNamespace(
            currentTime=0.0, outputBufferDacTime=0.01), status)
        return out[:, 0]

    def stop(self):
        pass

    def abort(self):
        self.aborted = True

    def close(self):
        self.closed = True


SOUNDDEVICE = types.SimpleNamespace(
    OutputStream=FakeStream, query_devices=lambda _: {"name": "deterministic fake"})


def import_engine():
    # engine imports dotenv at module load; suppress it even on configured machines.
    with patch.dict(sys.modules, {
        "dotenv": types.SimpleNamespace(load_dotenv=lambda *a, **k: None),
        "onnxruntime": types.ModuleType("onnxruntime"),
        "soundfile": types.ModuleType("soundfile"),
    }):
        return importlib.import_module("engine")
