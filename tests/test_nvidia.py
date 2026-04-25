"""
Tests for NVIDIA API connectivity.
Requires a valid NVIDIA_API_KEY in .env to run.
"""

import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()


@unittest.skipUnless(
    os.getenv("NVIDIA_API_KEY", "").startswith("nvapi-"),
    "NVIDIA_API_KEY not set — skipping API tests",
)
class TestNvidiaConnectivity(unittest.TestCase):
    """Test that the NVIDIA NIM API is reachable and functional."""

    @classmethod
    def setUpClass(cls):
        from utils.nvidia_client import NvidiaLLM
        cls.llm = NvidiaLLM()

    def test_api_connectivity(self):
        """Verify API key works with a simple prompt."""
        response = self.llm.generate(
            "Say 'hello' and nothing else.",
            temperature=0.1,
            max_tokens=16,
        )
        self.assertIsInstance(response, str)
        self.assertTrue(len(response) > 0, "Expected non-empty response")

    def test_json_extraction(self):
        """Verify JSON mode returns parseable JSON."""
        result = self.llm.extract_json(
            'Extract the fruit from this sentence: "I like apples." '
            'Return JSON: {"fruit": "apple"}'
        )
        self.assertIsInstance(result, dict)
        self.assertIn("fruit", result)


if __name__ == "__main__":
    unittest.main()
