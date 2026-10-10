"""Reply-policy routing without credentials, model weights or provider calls."""
import sys
import types
import unittest
from unittest.mock import AsyncMock, patch

import numpy as np

from fakes import import_engine

engine = import_engine()


class ReplyRequestTests(unittest.IsolatedAsyncioTestCase):
    async def test_policy_is_system_instruction_and_caller_audio_is_user_content(self):
        generate = AsyncMock(return_value=types.SimpleNamespace(text="Hello."))
        service = engine.Services.__new__(engine.Services)
        service.gemini_model = "configured-test-model"
        service.genai_client = types.SimpleNamespace(aio=types.SimpleNamespace(
            models=types.SimpleNamespace(generate_content=generate)))
        audio_part = object()
        sdk_types = types.SimpleNamespace(
            Part=types.SimpleNamespace(from_bytes=lambda **kwargs: audio_part),
            GenerateContentConfig=lambda **kwargs: kwargs,
            ThinkingConfig=lambda **kwargs: kwargs,
        )
        with patch.dict(sys.modules, {
            "google": types.ModuleType("google"),
            "google.genai": types.SimpleNamespace(types=sdk_types),
        }), patch.object(engine.sf, "write", create=True):
            await service.reply_text(np.zeros(512, dtype=np.float32))

        request = generate.call_args.kwargs
        self.assertEqual(request["config"].get("system_instruction"), engine.PROMPT)
        self.assertEqual(request["contents"], [audio_part])
        self.assertEqual(request["model"], service.gemini_model)
