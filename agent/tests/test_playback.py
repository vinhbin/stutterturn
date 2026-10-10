import sys
import unittest
from unittest.mock import patch

import numpy as np

from fakes import SOUNDDEVICE
from playback import Player


class PlaybackTests(unittest.TestCase):
    def setUp(self):
        self.device = patch.dict(sys.modules, {"sounddevice": SOUNDDEVICE})
        self.device.start()
        self.addCleanup(self.device.stop)

    def player(self, length=20000):
        player = Player(np.zeros(length, dtype=np.float32), extra_s=0)
        self.addCleanup(player.close)
        return player

    def test_empty_pcm_does_not_start_audio(self):
        player = self.player()
        self.assertIsNone(player.add_agent(np.empty(0, dtype=np.float32), 256))
        self.assertIsNone(player.agent_next)

    def test_timeline_exhaustion_rejects_entire_chunk(self):
        player = self.player(300)
        with self.assertRaisesRegex(BufferError, "timeline"):
            player.add_agent(np.ones(100, dtype=np.float32), 256)
        self.assertIsNone(player.agent_next)
        self.assertFalse(np.any(player.agent))

    def test_pending_capacity_rejects_without_advancing_end(self):
        player = self.player()
        player.add_agent(np.ones(8000, dtype=np.float32), 256)
        with self.assertRaisesRegex(BufferError, "pending"):
            player.add_agent(np.ones(1, dtype=np.float32))
        self.assertEqual(player.agent_next, 8256)
        player.stream.pull(512)
        self.assertEqual(player.add_agent(np.ones(256, dtype=np.float32)), 8256)

    def test_cut_reports_first_writable_sample(self):
        player = self.player()
        player.add_agent(np.ones(512, dtype=np.float32), 256)
        player.stream.pull(512)
        self.assertEqual(player.cut_agent(100), 512)
        self.assertFalse(np.any(player.stream.pull()))

    def test_cancelled_generation_cannot_block_or_contaminate_next_turn(self):
        player = self.player()
        self.assertTrue(callable(getattr(player, "begin_agent", None)),
                        "Player needs an explicit accepted-generation boundary")
        old = player.begin_agent()
        player.add_agent(np.ones(512, dtype=np.float32), 256, generation=old)
        player.cut_agent(300, generation=old)
        new = player.begin_agent()
        self.assertNotEqual(old, new)
        self.assertEqual(player.add_agent(np.full(256, .25, dtype=np.float32),
                                          512, generation=new), 512)
        self.assertIsNone(player.add_agent(np.ones(256, dtype=np.float32),
                                           512, generation=old))
        self.assertIsNone(player.cut_agent(512, generation=old))
        player.stream.pull(512)
        np.testing.assert_array_equal(player.stream.pull(), np.full(256, .25))

    def test_close_with_abort_silences_both_tracks(self):
        player = Player(np.ones(2000, dtype=np.float32), extra_s=0)
        player.add_agent(np.ones(100, dtype=np.float32), 256)
        self.assertTrue(callable(getattr(player, "abort", None)),
                        "stop needs output abort rather than normal drain")
        player.abort()
        self.assertTrue(player.stream.closed)
        self.assertTrue(player.stream.aborted)
        self.assertFalse(np.any(player.stream.pull()))
        self.assertIsNone(player.add_agent(np.ones(1, dtype=np.float32), 512))

    def test_device_abort_failure_still_closes_and_records_error(self):
        player = self.player()

        def broken_abort():
            raise RuntimeError("device removed")

        player.stream.abort = broken_abort
        player.abort()
        self.assertTrue(player.stream.closed)
        self.assertFalse(np.any(player.stream.pull()))
        self.assertEqual(player.errors, ["abort: device removed"])

    def test_late_chunk_is_relocated_without_losing_samples(self):
        player = self.player()
        player.add_agent(np.ones(256, dtype=np.float32), 256)
        np.testing.assert_array_equal(player.stream.pull(512)[256:], np.ones(256))
        self.assertEqual(player.add_agent(np.full(256, .25, dtype=np.float32)), 768)
        self.assertEqual(player.gaps, 1)
        np.testing.assert_array_equal(player.stream.pull(512)[256:], np.full(256, .25))


if __name__ == "__main__":
    unittest.main()
