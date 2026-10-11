import base64
import importlib
import pathlib
import sys
import unittest

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parents[1]))


class BrowserPlaybackTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.find_spec("browser_playback")
        self.assertIsNotNone(spec, "browser playback transport must exist")
        self.Player = importlib.import_module("browser_playback").BrowserPlayer
        self.time = 0.0
        self.messages = []
        self.player = self.Player(np.ones(1600, dtype=np.float32) * .25,
                                  self.messages.append, clock=lambda: self.time)
        self.player.start()

    def test_source_is_pcm16_and_never_emitted_before_run_ack(self):
        self.assertEqual(self.messages, [])
        self.player.send_source()
        source = self.messages[0]
        self.assertEqual(source["action"], "source")
        pcm = np.frombuffer(base64.b64decode(source["pcm"]), dtype="<i2")
        self.assertEqual(len(pcm), 1600)
        self.assertGreater(pcm.min(), 8000)

    def test_barge_in_retires_generation_but_preserves_next_reply(self):
        old = self.player.begin_agent()
        self.player.add_agent(np.ones(256), 0, generation=old)
        self.player.cut_agent(100, generation=old)
        count = len(self.messages)
        self.assertIsNone(self.player.add_agent(np.ones(256), generation=old))
        self.assertEqual(len(self.messages), count)
        new = self.player.begin_agent()
        self.assertIsNotNone(self.player.add_agent(np.ones(256), generation=new))
        self.assertEqual(self.messages[-1]["generation"], new)

    def test_queue_is_bounded_and_released_by_timeline_progress(self):
        from playback import PendingAudioFull
        gen = self.player.begin_agent()
        self.player.add_agent(np.ones(8000), 0, generation=gen)
        with self.assertRaises(PendingAudioFull):
            self.player.add_agent(np.ones(256), generation=gen)
        self.time = .1
        self.assertIsNotNone(self.player.add_agent(np.ones(256), generation=gen))

    def test_stop_clears_both_tracks_and_rejects_late_chunks(self):
        gen = self.player.begin_agent()
        self.player.abort()
        self.assertEqual(self.messages[-1]["action"], "stop")
        self.assertIsNone(self.player.add_agent(np.ones(256), generation=gen))

    def test_normal_close_does_not_abort_queued_audio(self):
        self.player.close()
        self.player.abort()
        self.assertEqual([m["action"] for m in self.messages], ["finish"])
