"""Controlled reply timing: identical local speech for every model, no API calls."""
import asyncio
import hashlib
import inspect
import math
from pathlib import Path
import wave


class FixedServices:
    chars_used = 0
    gemini_model = 'not-used-fixed-response'

    def __init__(self, path, delay_s=1.0):
        if not math.isfinite(delay_s) or not 0 <= delay_s <= 5:
            raise ValueError('Fixed delay must be between 0 and 5 seconds')
        path = Path(path)
        with wave.open(str(path), 'rb') as audio:
            if (audio.getnchannels(), audio.getsampwidth(), audio.getframerate(), audio.getcomptype()) != (1, 2, 16000, 'NONE'):
                raise ValueError('Fixed reply must be mono 16 kHz PCM16 WAV')
            if not 0 < audio.getnframes() <= 160000:
                raise ValueError('Fixed reply must contain 0 to 10 seconds of audio')
            self.pcm = audio.readframes(audio.getnframes())
        self.delay_s = delay_s
        self.text = 'What would you like help with?'
        self.response_metadata = {
            'mode': 'fixed', 'delay_s': delay_s, 'text': self.text,
            'audio_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'duration_s': len(self.pcm) / 32000,
            'description': 'Controlled timing: live turn model, prerecorded reply; no Gemini or ElevenLabs calls. Not live API latency.'}

    async def reply_text(self, audio, on_retry=None):
        await asyncio.sleep(self.delay_s)
        return self.text

    async def stream_tts(self, text, on_chunk):
        for offset in range(0, len(self.pcm), 3200):
            result = on_chunk(self.pcm[offset:offset + 3200])
            if inspect.isawaitable(result):
                await result
            else:
                await asyncio.sleep(0)
        return len(self.pcm)
