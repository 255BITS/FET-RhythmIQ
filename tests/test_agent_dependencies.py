"""Offline compatibility checks for the deployed agent's dependency graph."""

import asyncio
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch

from uagents.config import ALMANAC_CONTRACT_VERSION
from uagents.network import AlmanacContract


class AgentDependenciesTest(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        directory = Path(__file__).resolve().parents[1] / "agent"
        sys.path.insert(0, str(directory))
        sys.path.insert(0, str(directory.parent / "common"))
        spec = importlib.util.spec_from_file_location("rhythmiq_agent", directory / "agent.py")
        module = importlib.util.module_from_spec(spec)

        def contract_state(_contract, query):
            assert query == {"query_contract_state": {}}, query
            return {"contract_version": ALMANAC_CONTRACT_VERSION}

        with patch.object(AlmanacContract, "query_contract", contract_state):
            spec.loader.exec_module(module)
        cls.agent = module

    async def test_write_song_rest_and_message_models(self):
        module = self.agent
        request = module.WriteSongRequest(
            instruction="Offline song", artist_name="Test", model_name="test", station="test"
        )
        song = dict(title="Test song", lyrics="Test lyrics", style="pop", negative_style="none")
        context = SimpleNamespace(logger=Mock(), send=AsyncMock())
        with patch.object(module, "generate_song", return_value=song):
            response = await module.handle_post(context, request)
            self.assertEqual(response.model_dump(), song)
            await module.handle_song_request(context, "test-recipient", request)
        context.send.assert_awaited_once()
        self.assertEqual(context.send.call_args.args[1].model_dump(), song)

    async def test_audio_result_model_without_api_calls(self):
        module = self.agent
        song = dict(title="Test song", lyrics="Test lyrics", style="pop", negative_style="none")
        records = [
            {key: f"https://example.com/{i}/{key}" for key in
             ("audio_url", "image_url", "video_url", "image_large_url")}
            for i in (1, 2)
        ]
        context = SimpleNamespace(logger=Mock())
        with patch.object(module, "generate_audio", return_value=["one", "two"]), patch.object(
            module, "poll_until_complete", return_value=records
        ):
            response = await module.generate_audio_response(context, song)
        self.assertEqual(response.status, "complete")
        self.assertEqual(response.audio_url_1, records[0]["audio_url"])
        self.assertEqual(response.audio_url_2, records[1]["audio_url"])


if __name__ == "__main__":
    unittest.main()
