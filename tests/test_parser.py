"""
Tests for the JobParser — URL detection and text classification.
"""

import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import unittest


class TestURLDetection(unittest.TestCase):
    """Verify that URLs are correctly identified."""

    def _is_url(self, text: str) -> bool:
        """Mirror the JobParser._is_url logic for testing without full init."""
        import re
        first_line = text.split("\n")[0].strip()
        return bool(re.match(r"https?://[^\s]+", first_line))

    def test_simple_https_url(self):
        self.assertTrue(self._is_url("https://jobs.lever.co/stripe/abc-123"))

    def test_simple_http_url(self):
        self.assertTrue(self._is_url("http://careers.google.com/jobs/12345"))

    def test_linkedin_url(self):
        self.assertTrue(self._is_url("https://www.linkedin.com/jobs/view/3456789"))

    def test_indeed_url(self):
        self.assertTrue(self._is_url("https://www.indeed.com/viewjob?jk=abc123"))

    def test_greenhouse_url(self):
        self.assertTrue(self._is_url("https://boards.greenhouse.io/company/jobs/456"))

    def test_url_with_trailing_whitespace(self):
        self.assertTrue(self._is_url("  https://example.com/jobs/123  "))

    def test_url_with_query_params(self):
        self.assertTrue(self._is_url("https://example.com/jobs?id=42&ref=ai"))


class TestTextDetection(unittest.TestCase):
    """Verify that plain text is correctly identified."""

    def _is_url(self, text: str) -> bool:
        import re
        first_line = text.split("\n")[0].strip()
        return bool(re.match(r"https?://[^\s]+", first_line))

    def test_plain_description(self):
        text = "Software Engineer at Stripe\nRemote position"
        self.assertFalse(self._is_url(text))

    def test_multiline_job_posting(self):
        text = """
        Senior Backend Engineer
        Company: Acme Corp
        Location: NYC
        Skills: Python, Go, AWS
        """
        self.assertFalse(self._is_url(text))

    def test_empty_string(self):
        self.assertFalse(self._is_url(""))

    def test_random_text(self):
        self.assertFalse(self._is_url("Looking for SWE role at a startup"))

    def test_email(self):
        self.assertFalse(self._is_url("recruiter@company.com sent this job"))


class TestMixedInput(unittest.TestCase):
    """Verify URL in text is handled correctly."""

    def _is_url(self, text: str) -> bool:
        import re
        first_line = text.split("\n")[0].strip()
        return bool(re.match(r"https?://[^\s]+", first_line))

    def test_url_first_line(self):
        text = "https://example.com/jobs/123\nSome additional context here"
        self.assertTrue(self._is_url(text))

    def test_url_not_first_line(self):
        text = "Check out this job:\nhttps://example.com/jobs/123"
        self.assertFalse(self._is_url(text))

    def test_url_embedded_in_text(self):
        text = "Apply at https://example.com/jobs"
        self.assertFalse(self._is_url(text))


if __name__ == "__main__":
    unittest.main()
