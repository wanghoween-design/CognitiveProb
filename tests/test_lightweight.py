import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.setdefault("SKIP_MODEL_PRELOAD", "1")
os.environ.setdefault("COGNITIVEPROBE_MOCK_LLM", "1")
os.environ.setdefault("SKIP_DB_INIT", "1")


class LightweightTests(unittest.TestCase):
    def test_coordinator_parses_json_route(self):
        from src.agents import graph

        with patch.object(graph, "call_llm", return_value='{"type": 2}'):
            self.assertEqual(
                graph.coordinator({"question": "What is Python?"}),
                {"question_type": "simple_factual"},
            )

    def test_coordinator_falls_back_to_last_route_number(self):
        from src.agents import graph

        with patch.object(graph, "call_llm", return_value="analysis result type is 3"):
            self.assertEqual(
                graph.coordinator({"question": "What are the effects of a four-day work week?"}),
                {"question_type": "complex_reasoning"},
            )

    def test_mock_generation_does_not_load_model(self):
        from src.agents.lora_inference import generate_base, generate_lora

        self.assertTrue(generate_base("hello").startswith("[mock:base]"))
        self.assertTrue(generate_lora("hello", "critical").startswith("[mock:critical]"))

    def test_app_import_skips_preload(self):
        from src.main import app

        self.assertEqual(app.title, "CognitiveProbe")


if __name__ == "__main__":
    unittest.main()