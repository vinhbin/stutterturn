"""Reply-policy routing without credentials, model weights or provider calls."""
import asyncio
import sys
import types
import unittest
from unittest.mock import AsyncMock, patch

import numpy as np

from fakes import import_engine

engine = import_engine()


class ReplyRequestTests(unittest.IsolatedAsyncioTestCase):
    async def request(self, responses, on_retry=None):
        self.generate = AsyncMock(side_effect=responses)
        service = engine.Services.__new__(engine.Services)
        service.gemini_model = 'configured-test-model'
        service.genai_client = types.SimpleNamespace(aio=types.SimpleNamespace(
            models=types.SimpleNamespace(generate_content=self.generate)))
        sdk_types = types.SimpleNamespace(
            Part=types.SimpleNamespace(from_bytes=lambda **kw: object()),
            GenerateContentConfig=lambda **kw: kw, ThinkingConfig=lambda **kw: kw)
        with patch.dict(sys.modules, {'google': types.ModuleType('google'),
                                      'google.genai': types.SimpleNamespace(types=sdk_types)}), \
                patch.object(engine.sf, 'write', create=True):
            return await service.reply_text(np.zeros(512), on_retry=on_retry)

    async def test_empty_reply_retries_once_with_more_output_room(self):
        retries = []
        result = await self.request([types.SimpleNamespace(text=''), types.SimpleNamespace(text='Hello.')], retries.append)
        self.assertEqual(result, 'Hello.')
        self.assertEqual(self.generate.await_count, 2)
        self.assertEqual(len(retries), 1)
        self.assertGreater(self.generate.call_args_list[1].kwargs['config']['max_output_tokens'],
                           self.generate.call_args_list[0].kwargs['config']['max_output_tokens'])

    async def test_two_empty_responses_are_an_error_not_a_timeout(self):
        with self.assertRaises(engine.GeminiReplyError) as raised:
            await self.request([types.SimpleNamespace(text=''), types.SimpleNamespace(text='')])
        self.assertEqual(raised.exception.code, 'empty_reply')
        self.assertEqual(self.generate.await_count, 2)

    async def test_blocked_candidate_does_not_retry(self):
        response = types.SimpleNamespace(text='', candidates=[types.SimpleNamespace(finish_reason='SAFETY')])
        with self.assertRaises(engine.GeminiReplyError) as raised:
            await self.request([response])
        self.assertEqual(raised.exception.code, 'blocked_reply')
        self.assertEqual(self.generate.await_count, 1)

    async def test_prompt_block_does_not_retry(self):
        response = types.SimpleNamespace(text='', prompt_feedback=types.SimpleNamespace(block_reason='SAFETY'))
        with self.assertRaises(engine.GeminiReplyError):
            await self.request([response])
        self.assertEqual(self.generate.await_count, 1)

    async def test_cancellation_does_not_retry(self):
        with self.assertRaises(asyncio.CancelledError):
            await self.request([asyncio.CancelledError()])
        self.assertEqual(self.generate.await_count, 1)

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
