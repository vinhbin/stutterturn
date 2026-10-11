"""Fixed responses use local PCM, never providers, and remain cancellable."""
import asyncio
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
import wave
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fixed_response import FixedServices


class FixedResponseTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'reply.wav'
        self.pcm = b'\x00\x20' * 8000
        with wave.open(str(self.path), 'wb') as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(16000)
            f.writeframes(self.pcm)

    def tearDown(self):
        self.temp.cleanup()

    async def test_local_reply_and_identical_pcm_without_credentials(self):
        with patch.dict('os.environ', {}, clear=True):
            service = FixedServices(self.path, delay_s=1.0)
        with patch('fixed_response.asyncio.sleep', new_callable=unittest.mock.AsyncMock) as sleep:
            text = await service.reply_text(object())
            sleep.assert_awaited_once_with(1.0)
        self.assertEqual(text, 'What would you like help with?')
        for _ in range(2):
            chunks = []
            async def collect(chunk):
                chunks.append(chunk)
            self.assertEqual(await service.stream_tts(text, collect), len(self.pcm))
            self.assertEqual(b''.join(chunks), self.pcm)
        self.assertEqual(service.chars_used, 0)
        self.assertEqual(service.response_metadata['mode'], 'fixed')
        self.assertEqual(service.response_metadata['audio_sha256'], hashlib.sha256(self.path.read_bytes()).hexdigest())

    async def test_cancellation_during_wait_prevents_audio(self):
        service = FixedServices(self.path, delay_s=1.0)
        chunks = []
        async def respond():
            text = await service.reply_text(None)
            await service.stream_tts(text, chunks.append)
        task = asyncio.create_task(respond())
        await asyncio.sleep(0)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual(chunks, [])

    async def test_rejects_incompatible_audio_and_invalid_delay(self):
        with wave.open(str(self.path), 'wb') as f:
            f.setnchannels(2)
            f.setsampwidth(2)
            f.setframerate(16000)
            f.writeframes(self.pcm)
        with self.assertRaises(ValueError):
            FixedServices(self.path)
        for delay in (-1, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                FixedServices(self.path, delay_s=delay)


if __name__ == '__main__':
    unittest.main()
