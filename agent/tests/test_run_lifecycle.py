import asyncio
import inspect
import io
import sys
import tempfile
import threading
import time
import types
import unittest
from unittest.mock import patch

import numpy as np

from fakes import SOUNDDEVICE, import_engine
from playback import Player

engine = import_engine()


class FakeServices:
    gemini_model = "offline-fake"
    chars_used = 0

    def __init__(self, chunks=()):
        self.chunks = chunks
        self.callbacks = []
        self.hold = None

    async def reply_text(self, _audio, on_retry=None):
        return "A deterministic reply."

    async def stream_tts(self, _text, on_chunk):
        self.callbacks.append(on_chunk)
        for chunk in self.chunks:
            await self.deliver(on_chunk, chunk)
        if self.hold:
            await self.hold.wait()
        return sum(map(len, self.chunks))

    @staticmethod
    async def deliver(callback, chunk):
        result = callback(chunk)
        if inspect.isawaitable(result):
            await result


class RunLifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def test_genuine_gemini_deadline_stays_a_timeout(self):
        services = FakeServices()
        async def timeout(_audio, on_retry=None):
            raise asyncio.TimeoutError()
        services.reply_text = timeout
        run, messages = self.make_run(services, playback=False)
        run._start_reply(0, [np.zeros(512)])
        await run.reply_task
        self.assertEqual(run.s['timeouts'], ['gemini'])
        self.assertEqual(run.s['errors'], [])
        self.assertFalse(services.callbacks)

    async def test_empty_gemini_reply_records_error_without_audio_or_timeout(self):
        services = FakeServices()
        async def empty(_audio, on_retry=None):
            raise engine.GeminiReplyError('empty_reply', 'STOP')
        services.reply_text = empty
        run, messages = self.make_run(services, playback=False)
        run._start_reply(0, [np.zeros(512)])
        await run.reply_task
        self.assertEqual(run.s['timeouts'], [])
        self.assertEqual(run.s['errors'], ['gemini:empty_reply'])
        self.assertFalse(services.callbacks)
        self.assertTrue(any(m.get('name') == 'provider_error' and m.get('service') == 'gemini' for m in messages))

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        for patcher in (
            patch.dict(sys.modules, {"sounddevice": SOUNDDEVICE}),
            patch.object(engine, "RUNS", self.tmp.name),
            patch.object(engine, "resolve_model", return_value={
                "path": "unused", "sha256": "fake", "model_id": "stock-int8", "threshold": .5}),
            patch.object(engine, "load_source", return_value=np.zeros(2048, dtype=np.float32)),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def make_run(self, services=None, playback=True):
        messages = []
        run = engine.Run("stock", "fake.wav", services=services, listener=messages.append,
                         play=playback)
        run.t0 = time.monotonic()
        run._log = io.StringIO()
        if playback:
            run.player = Player(np.zeros(100000, dtype=np.float32), extra_s=0)
            self.addCleanup(run.player.close)
        return run, messages

    async def start_reply(self, run):
        run._start_reply(0, [np.zeros(512, dtype=np.float32)])
        for _ in range(20):
            if run.services.callbacks:
                return
            await asyncio.sleep(0)
        self.fail("fake service never received the chunk callback")

    async def test_one_byte_chunk_has_no_false_audio_start(self):
        services = FakeServices()
        services.hold = asyncio.Event()
        run, messages = self.make_run(services)
        await self.start_reply(run)
        try:
            await services.deliver(services.callbacks[0], b"\x00")
            self.assertFalse(any(m.get("name") == "agent_audio_start" for m in messages))
            await services.deliver(services.callbacks[0], b"\x40")
            self.assertEqual(sum(m.get("name") == "agent_audio_start" for m in messages), 1)
        finally:
            run.reply_task.cancel()
            await asyncio.gather(run.reply_task, return_exceptions=True)

    async def test_malformed_final_fragment_is_reported(self):
        run, messages = self.make_run(FakeServices([b"\x00\x40\x00"]))
        run._start_reply(0, [np.zeros(512, dtype=np.float32)])
        await run.reply_task
        self.assertTrue(any(m.get("name") == "playback_error"
                            and m.get("code") == "malformed_pcm" for m in messages))

    async def test_timeline_exhaustion_is_visible_and_keeps_accepted_end(self):
        run, messages = self.make_run(FakeServices([b"\x00\x40" * 256] * 2))
        run.player.close()
        run.player = Player(np.zeros(600, dtype=np.float32), extra_s=0)
        self.addCleanup(run.player.close)
        run._start_reply(0, [np.zeros(512, dtype=np.float32)])
        await run.reply_task
        self.assertEqual(run.agent_audio_end, .032)
        self.assertTrue(any(m.get("name") == "playback_error"
                            and m.get("code") == "timeline_capacity" for m in messages))

    async def test_stop_before_scheduled_start_has_zero_output_interval(self):
        services = FakeServices([b"\x00\x40" * 256])
        run, messages = self.make_run(services)
        run._start_reply(0, [np.zeros(512, dtype=np.float32)])
        await run.reply_task
        run._barge_in(0, 0)
        end = next(m for m in messages if m.get("name") == "agent_audio_end")
        cancel = next(m for m in messages if m.get("name") == "cancelled")
        self.assertEqual(end["t"], .016)
        self.assertEqual(end["overlap_s"], 0)
        self.assertTrue(cancel["before_audible"])
        self.assertEqual(end["timing"]["accepted_cut_sample"], 0)
        self.assertFalse(np.any(run.player.stream.pull(512)))

    async def test_provider_timeout_closes_partial_accepted_interval(self):
        services = FakeServices([b"\x00\x40" * 256])
        services.hold = asyncio.Event()
        run, messages = self.make_run(services)
        # The expected sample interval assumes the first chunk arrives at t=0.
        run.now = lambda: 0.0
        real_wait_for = asyncio.wait_for

        async def fast_timeout(awaitable, timeout):
            return await real_wait_for(awaitable, .02)

        with patch.object(engine.asyncio, "wait_for", side_effect=fast_timeout):
            run._start_reply(0, [np.zeros(512, dtype=np.float32)])
            await run.reply_task
        self.assertEqual(run.agent_audio_end, .032)
        self.assertEqual(run.s["timeouts"], ["elevenlabs"])
        run._maybe_end_agent_audio(.1)
        self.assertEqual(sum(m.get("name") == "agent_audio_end" for m in messages), 1)

    async def test_real_service_awaits_async_chunk_callback_without_network(self):
        class Response:
            status = 200

            def __init__(self):
                self.content = self

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def iter_chunked(self, size):
                yield b"first"
                yield b"second"

        class Session(Response):
            def __init__(self, **kwargs):
                super().__init__()

            def post(self, *args, **kwargs):
                return Response()

        service = engine.Services.__new__(engine.Services)
        service.chars_used = 0
        service.max_chars = 100
        service.voice_id = "fake"
        service.el_key = "not-a-credential"
        received = []

        async def callback(chunk):
            await asyncio.sleep(0)
            received.append(chunk)

        with patch.dict(sys.modules, {"aiohttp": types.SimpleNamespace(
                ClientSession=Session, ClientTimeout=lambda **kwargs: None)}):
            total = await service.stream_tts("test", callback)
        self.assertEqual(total, 11)
        self.assertEqual(received, [b"first", b"second"])

    async def test_late_retired_callback_cannot_write_new_turn(self):
        services = FakeServices()
        services.hold = asyncio.Event()
        run, messages = self.make_run(services)
        await self.start_reply(run)
        old_task = run.reply_task
        old_callback = services.callbacks[0]
        run._barge_in(0, .2)
        run._start_reply(0, [np.zeros(512, dtype=np.float32)])
        for _ in range(20):
            if len(services.callbacks) == 2:
                break
            await asyncio.sleep(0)
        try:
            await services.deliver(old_callback, b"\x00\x40" * 256)
            self.assertFalse(np.any(run.player.agent))
            await services.deliver(services.callbacks[1], b"\x00\x20" * 256)
            self.assertTrue(np.any(run.player.agent))
            self.assertEqual(sum(m.get("name") == "agent_audio_start" for m in messages), 1)
        finally:
            run.reply_task.cancel()
            await asyncio.gather(old_task, run.reply_task, return_exceptions=True)

    async def test_barge_in_records_actual_clamped_cut(self):
        run, messages = self.make_run()
        run.player.add_agent(np.ones(8000, dtype=np.float32), 256)
        run.agent_audio_start = .016
        run.agent_audible = True
        run.player.stream.pull(8000)
        run._barge_in(.1, .2)
        end = next(m for m in messages if m.get("name") == "agent_audio_end")
        self.assertEqual(end["t"], .5)
        self.assertEqual(end["overlap_s"], .4)

    async def test_pending_provider_does_not_extend_audio_through_silence(self):
        for action in ("barge_in", "stop"):
            with self.subTest(action=action):
                services = FakeServices([b"\x00\x40" * 256])
                services.hold = asyncio.Event()
                run, messages = self.make_run(services)
                run.now = lambda: 0.0  # Fixed arrival; fake device time advances below.
                await self.start_reply(run)
                task = run.reply_task
                run.player.stream.pull(8000)
                try:
                    if action == "stop":
                        run.stop()
                    else:
                        run._barge_in(.1, .2)
                    end = next(m for m in messages if m.get("name") == "agent_audio_end")
                    self.assertEqual(end["t"], .032)
                    self.assertFalse(any(m.get("name") == "overlap" for m in messages))
                    if action == "barge_in":
                        cancelled = next(m for m in messages if m.get("name") == "cancelled")
                        self.assertFalse(cancelled["before_audible"])
                finally:
                    task.cancel()
                    await asyncio.gather(task, return_exceptions=True)

    async def test_stop_silences_source_and_rejects_late_pcm_immediately(self):
        services = FakeServices()
        services.hold = asyncio.Event()
        run, messages = self.make_run(services)
        run.player.src[:] = .25
        await self.start_reply(run)
        task = run.reply_task
        try:
            run.stop()
            self.assertTrue(run.player.stream.closed)
            self.assertFalse(np.any(run.player.stream.pull()))
            count = len(messages)
            await services.deliver(services.callbacks[0], b"\x00\x40" * 256)
            self.assertEqual(len(messages), count)
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    async def test_provider_burst_is_paced_and_fully_preserved(self):
        run, messages = self.make_run(FakeServices([b"\x00\x40" * 16000]))
        run._start_reply(0, [np.zeros(512, dtype=np.float32)])
        heard = []
        for _ in range(160):
            await asyncio.sleep(.002)
            self.assertLessEqual(np.count_nonzero(run.player.agent[run.player.position():]), 8000)
            heard.extend(run.player.stream.pull())
            if run.reply_task.done() and run.player.position() >= (run.player.agent_next or 0):
                break
        await asyncio.wait_for(run.reply_task, 1)
        self.assertEqual(np.count_nonzero(heard), 16000)
        self.assertFalse(any(m.get("name") == "playback_error" for m in messages))

    async def test_stop_during_backpressure_discards_pending_samples(self):
        run, messages = self.make_run(FakeServices([b"\x00\x40" * 16000]))
        await self.start_reply(run)
        task = run.reply_task
        self.assertFalse(task.done())
        run.stop()
        await asyncio.wait_for(asyncio.gather(task, return_exceptions=True), .2)
        self.assertFalse(np.any(run.player.stream.pull(20000)))
        self.assertFalse(np.any(run.player.agent))

    async def test_finally_closes_partial_audio_after_provider_failure(self):
        class Broken(FakeServices):
            async def stream_tts(self, text, on_chunk):
                await self.deliver(on_chunk, b"\x00\x40" * 256)
                raise RuntimeError("fake transport lost")

        run, messages = self.make_run(Broken())
        run._start_reply(0, [np.zeros(512, dtype=np.float32)])
        await run.reply_task
        self.assertEqual(run.agent_audio_end, .032)
        run._maybe_end_agent_audio(.1)
        ends = [m for m in messages if m.get("name") == "agent_audio_end"]
        self.assertEqual(len(ends), 1)
        self.assertEqual(ends[0]["t"], .032)
        self.assertEqual(ends[0]["timing"]["basis"], "scheduled_output_samples")

    async def test_finished_stream_rejects_late_callbacks(self):
        services = FakeServices([b"\x00\x40" * 256])
        run, _ = self.make_run(services)
        run._start_reply(0, [np.zeros(512, dtype=np.float32)])
        await run.reply_task
        original_end = run.player.agent_next
        await services.deliver(services.callbacks[0], b"\x00\x40" * 256)
        self.assertEqual(run.player.agent_next, original_end)

    async def test_shared_model_serializes_features_during_restart(self):
        model = engine.SmartTurn.__new__(engine.SmartTurn)
        model._predict_lock = threading.Lock()
        entered = threading.Event()
        release = threading.Event()
        second_entered = threading.Event()
        counter = iter(range(2))

        def features(_audio):
            if next(counter) == 0:
                entered.set()
                release.wait(2)
            else:
                second_entered.set()
            return np.zeros(1)

        model.features = features
        model.sess = types.SimpleNamespace(run=lambda *args: [np.array([.5])])
        first = asyncio.create_task(asyncio.to_thread(model.predict, np.zeros(1)))
        second = None
        try:
            for _ in range(100):
                if entered.is_set():
                    break
                await asyncio.sleep(.002)
            self.assertTrue(entered.is_set())
            second = asyncio.create_task(asyncio.to_thread(model.predict, np.zeros(1)))
            await asyncio.sleep(.02)
            self.assertFalse(second_entered.is_set(), "a restart reused model state concurrently")
        finally:
            release.set()
            await asyncio.gather(*([first, second] if second else [first]))

    async def test_stop_during_inference_releases_output_and_drops_result(self):
        entered = threading.Event()
        release = threading.Event()

        def predict(_audio):
            entered.set()
            release.wait(2)
            return .9, 1

        model = types.SimpleNamespace(sha256="fake", predict=predict)
        run, messages = self.make_run(playback=True)
        run.player.close()
        run.player = None
        run.cfg = {**run.cfg, "vad_start_s": .032, "vad_stop_s": .032}
        with patch.object(engine.SmartTurn, "load", return_value=model), \
                patch.object(engine, "_commit", return_value="test-only"):
            # The fake VAD must accept frames, while its sequence controls inference entry.
            probs = iter([1., 0.])
            with patch.object(engine, "SileroVAD", return_value=lambda _: next(probs)):
                task = asyncio.create_task(run.run())
                try:
                    for _ in range(100):
                        if entered.is_set():
                            break
                        await asyncio.sleep(.005)
                    self.assertTrue(entered.is_set())
                    run.stop()
                    self.assertTrue(run.player.stream.closed)
                    await asyncio.wait_for(asyncio.shield(task), .2)
                    self.assertEqual(messages[-1]["reason"], "stopped")
                    self.assertFalse(any(m.get("name") == "turn_complete" for m in messages))
                finally:
                    release.set()
                    await asyncio.gather(task, return_exceptions=True)

    async def test_normal_completion_waits_for_source_tail_before_closing(self):
        model = types.SimpleNamespace(sha256="fake")
        run, messages = self.make_run()
        run.player.close()
        run.player = None
        run.audio = np.zeros(1024, dtype=np.float32)
        processed = asyncio.Event()

        def listener(message):
            messages.append(message)
            if message.get("name") == "no_response":
                processed.set()

        run.listener = listener
        with patch.object(engine.SmartTurn, "load", return_value=model), \
                patch.object(engine, "SileroVAD", return_value=lambda _: 0.), \
                patch.object(engine, "TRAILING_SILENCE_S", 0), \
                patch.object(engine, "_commit", return_value="test-only"):
            task = asyncio.create_task(run.run())
            try:
                for _ in range(100):
                    if run.player:
                        break
                    await asyncio.sleep(.002)
                run.player.stream.pull(512)
                await asyncio.wait_for(processed.wait(), 1)
                await asyncio.sleep(0)
                self.assertFalse(task.done(), "normal drain dropped the caller's last frame")
                run.player.stream.pull(512)
                await asyncio.wait_for(task, .2)
                self.assertTrue(run.player.stream.closed)
                self.assertEqual(messages[-1]["reason"], "completed")
            finally:
                if not task.done():
                    run.stop()
                await asyncio.gather(task, return_exceptions=True)

    async def test_outer_reply_deadline_reports_timeout_and_closes_run(self):
        services = FakeServices([b"\x00\x40" * 256])
        services.hold = asyncio.Event()
        model = types.SimpleNamespace(sha256="fake", predict=lambda _: (.9, 1))
        run, messages = self.make_run(services, playback=False)
        run.audio = np.zeros(1024, dtype=np.float32)
        run.cfg = {**run.cfg, "vad_start_s": .032, "vad_stop_s": .032}
        probabilities = iter([1., 0.])
        real_wait_for = asyncio.wait_for

        async def shorten_outer_deadline(awaitable, timeout):
            return await real_wait_for(awaitable, .02 if timeout == 15 else timeout)

        with patch.object(engine.SmartTurn, "load", return_value=model), \
                patch.object(engine, "SileroVAD", return_value=lambda _: next(probabilities)), \
                patch.object(engine, "TRAILING_SILENCE_S", 0), \
                patch.object(engine, "_commit", return_value="test-only"), \
                patch.object(engine.asyncio, "wait_for", side_effect=shorten_outer_deadline):
            summary = await run.run()
        self.assertEqual(summary["timeouts"], ["reply"])
        self.assertEqual(sum(m.get("name") == "agent_audio_end" for m in messages), 1)
        self.assertEqual(sum(m["type"] == "run_ended" for m in messages), 1)
        self.assertTrue(run._log.closed)
        count = len(messages)
        await services.deliver(services.callbacks[0], b"\x00\x40" * 256)
        self.assertEqual(len(messages), count)
        self.assertFalse([task for task in asyncio.all_tasks()
                          if task is not asyncio.current_task() and not task.done()])


if __name__ == "__main__":
    unittest.main()
