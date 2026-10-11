"""HTTP/WS boundaries for a single-CPU hosted agent; no models or paid calls."""
import asyncio
import importlib.util
import pathlib
import sys
import types
import unittest
from unittest.mock import patch

from aiohttp.test_utils import AioHTTPTestCase


class FakeRun:
    def __init__(self, config, source, services=None, listener=None, play=False, playback_factory=None):
        self.run_id = "test-run"
        self.listener = listener
        self.done = asyncio.Event()
        self.playback_factory = playback_factory

    async def run(self):
        self.listener({"type": "run_started", "run_id": self.run_id})
        if self.playback_factory:
            import numpy as np
            player = self.playback_factory(np.zeros(16, dtype=np.float32))
            player.start()
            player.send_source()
            player.close()
        await self.done.wait()

    def stop(self):
        self.done.set()


class HostedServerTests(AioHTTPTestCase):
    async def get_application(self):
        fake = types.SimpleNamespace(
            CONTRACT_VERSION="0.1", Run=FakeRun,
            list_sources=lambda: ["allowed.wav"],
            _commit=lambda: "test", configurations=lambda: [],
        )
        path = pathlib.Path(__file__).parents[1] / "server.py"
        spec = importlib.util.spec_from_file_location("hosted_server_under_test", path)
        module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"engine": fake}):
            spec.loader.exec_module(module)
        self.assertTrue(callable(getattr(module, "create_app", None)),
                        "server needs a configurable hosted application factory")
        return module.create_app(services=None, play=False, max_runs=1,
                                 allowed_origin="https://demo.example",
                                 browser_audio=getattr(self, "enable_audio", False))

    async def test_rejects_cross_origin_websocket(self):
        response = await self.client.get("/v0/ws", headers={"Origin": "https://evil.example"})
        self.assertEqual(response.status, 403)

    async def test_invalid_message_and_unlisted_source_do_not_start_runs(self):
        async with self.client.ws_connect("/v0/ws", origin="https://demo.example") as ws:
            for payload in ([], None, {"type": "start", "config": "stock", "source": "../allowed.wav"},
                            {"type": "start", "config": "stock", "source": "missing.wav"}):
                await ws.send_json(payload)
                self.assertEqual((await ws.receive_json())["type"], "error")
            self.assertEqual(self.app["runtime"]["active_runs"], 0)

    async def test_global_slot_is_released_after_disconnect(self):
        first = await self.client.ws_connect("/v0/ws")
        second = await self.client.ws_connect("/v0/ws")
        start = {"type": "start", "config": "stock", "source": "allowed.wav"}
        try:
            await first.send_json(start)
            self.assertEqual((await first.receive_json())["type"], "run_started")
            await second.send_json(start)
            busy = await second.receive_json()
            self.assertEqual(busy["type"], "error")
            self.assertIn("busy", busy["message"])
            await first.close()
            for _ in range(100):
                if self.app["runtime"]["active_runs"] == 0:
                    break
                await asyncio.sleep(0.01)
            self.assertEqual(self.app["runtime"]["active_runs"], 0)
            await second.send_json(start)
            self.assertEqual((await second.receive_json())["type"], "run_started")
        finally:
            await first.close()
            await second.close()


class BrowserAudioServerTests(HostedServerTests):
    enable_audio = True

    async def test_audio_is_opt_in_and_separately_sequenced(self):
        response = await self.client.get('/v0/health')
        self.assertEqual((await response.json())['browser_audio'], 'pcm16-v1')
        async with self.client.ws_connect('/v0/ws') as ws:
            await ws.send_json({'type': 'start', 'config': 'stock', 'source': 'allowed.wav',
                                'browser_audio': True})
            self.assertEqual((await ws.receive_json())['type'], 'run_started')
            source = await ws.receive_json()
            self.assertEqual((source['type'], source['action'], source['audio_seq']),
                             ('browser_audio', 'source', 0))
            self.assertEqual(source['run_id'], 'test-run')
            self.assertNotIn('seq', source)
            finish = await ws.receive_json()
            self.assertEqual((finish['action'], finish['audio_seq']), ('finish', 1))

    async def test_legacy_client_receives_no_audio(self):
        async with self.client.ws_connect('/v0/ws') as ws:
            await ws.send_json({'type': 'start', 'config': 'stock', 'source': 'allowed.wav'})
            self.assertEqual((await ws.receive_json())['type'], 'run_started')
            with self.assertRaises(asyncio.TimeoutError):
                await asyncio.wait_for(ws.receive_json(), .05)


if __name__ == "__main__":
    unittest.main()
