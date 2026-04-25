"""
Tests for the quality scoring logic in CoverLetterGenerator.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.letter_generator import CoverLetterGenerator


class _FakeLLM:
    """Minimal stub so we can instantiate the generator without an API key."""
    pass


class TestQualityScoring(unittest.TestCase):
    """Verify quality scoring produces correct results."""

    @classmethod
    def setUpClass(cls):
        cls.gen = CoverLetterGenerator(_FakeLLM())

        cls.job_data = {
            "company_name": "Stripe",
            "position_title": "Senior Backend Engineer",
            "required_skills": ["Python", "Go", "AWS"],
            "tech_stack": ["Kubernetes", "Kafka", "Ruby"],
        }

        cls.research = {
            "company_momentum": "Stripe launched embedded finance platform in Q3 2024",
            "cultural_keywords": ["rigorous", "user-obsessed", "long-term", "transparent", "writing-heavy"],
            "recent_initiatives": ["embedded finance platform", "Stripe Tax AI launch"],
            "pain_points": ["scaling infrastructure", "international expansion"],
        }

    def test_scoring_perfect(self):
        """A letter with all elements should score 80+."""
        letter = """Dear Hiring Team at Stripe,

When Stripe launched its embedded finance platform last quarter, I immediately saw
the distributed systems challenges behind making financial infrastructure invisible.
Having built a real-time data pipeline processing 2M events per day at TechCorp
using Python and Kafka, I understand what rigorous infrastructure engineering demands.

At TechCorp I led the migration from monolith to microservices serving 500K daily active
users, leveraging AWS and Kubernetes. I reduced API latency by 40% — exactly the kind of
scaling infrastructure work Stripe needs as it expands internationally. My experience
with Go, Python, and distributed message queues maps directly to your tech stack.

Stripe's user-obsessed, writing-heavy culture aligns with how I work. In my first 90 days
I would audit the payment processing pipeline for bottleneck elimination and propose a
roadmap for scaling throughput 3x. I'd welcome the chance to discuss this further.

Sincerely,
Alex Chen"""

        quality = self.gen._evaluate_quality(letter, self.job_data, self.research)
        self.assertGreaterEqual(quality["score"], 80, f"Expected 80+, got {quality['score']}")
        self.assertTrue(quality["checks"]["no_generic_openers"])

    def test_scoring_generic(self):
        """A generic letter should score below 50."""
        letter = """Dear Sir/Madam,

I am writing to express my interest in the position at your company.
I believe I would be a great fit because I am passionate about technology
and have experience in software development.

I have worked with various programming languages and frameworks.
I am a team player and I enjoy solving problems.

Thank you for your consideration.

Sincerely,
Alex Chen"""

        quality = self.gen._evaluate_quality(letter, self.job_data, self.research)
        self.assertLess(quality["score"], 50, f"Expected <50, got {quality['score']}")
        self.assertFalse(quality["checks"]["no_generic_openers"])

    def test_length_check_short(self):
        """Letter under 200 words should fail the length check."""
        letter = "Dear Hiring Team at Stripe,\n\nShort letter.\n\nSincerely,\nAlex"
        quality = self.gen._evaluate_quality(letter, self.job_data, self.research)
        self.assertFalse(quality["checks"]["appropriate_length"])

    def test_length_check_good(self):
        """Letter between 200-400 words should pass the length check."""
        # Build a ~280 word letter
        words = "word " * 280
        letter = f"Dear Hiring Team at Stripe,\n\n{words}\n\nSincerely,\nAlex"
        quality = self.gen._evaluate_quality(letter, self.job_data, self.research)
        self.assertTrue(quality["checks"]["appropriate_length"])

    def test_metrics_detection(self):
        """Check that numeric metrics are picked up."""
        letter = "I processed 2M events/day and reduced latency by 40%. Revenue grew $5M."
        quality = self.gen._evaluate_quality(letter, self.job_data, self.research)
        self.assertTrue(quality["checks"]["includes_metrics"])

    def test_no_metrics(self):
        """Check that lack of metrics is detected."""
        letter = "I have experience with many things and am very skilled at programming."
        quality = self.gen._evaluate_quality(letter, self.job_data, self.research)
        self.assertFalse(quality["checks"]["includes_metrics"])


if __name__ == "__main__":
    unittest.main()
