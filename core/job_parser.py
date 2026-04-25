"""
Job posting parser.
Detects URL vs raw text input and extracts structured job data via the NVIDIA API.
"""

import re

from utils.nvidia_client import NvidiaLLM
from utils.scraper import WebScraper
from utils.helpers import info, warn, error, success

from config.settings import EXTRACTION_TEMPERATURE, MAX_TOKENS_EXTRACTION


class JobParser:
    """Parse job postings from URLs or raw text into structured data."""

    def __init__(self, llm: NvidiaLLM, scraper: WebScraper):
        self.llm = llm
        self.scraper = scraper

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def parse_input(self, user_input: str) -> dict:
        """Accept raw user input (URL or text) and return structured job data."""
        if not user_input.strip():
            error("No input provided. Please paste a job URL or description.")
            return {}

        if self._is_url(user_input.strip()):
            info("URL detected")
            raw_text = self._scrape_job_url(user_input.strip())
            if not raw_text:
                error("Could not scrape the page. Paste the job description text instead.")
                return {}
        else:
            info("Text input detected")
            raw_text = user_input.strip()

        info("Parsing job details with AI…")
        job_data = self._extract_structured_data(raw_text)

        # Validate minimum fields
        if not job_data.get("company_name"):
            warn("Could not identify the company name.")
            try:
                name = input("  Enter company name manually: ").strip()
                if name:
                    job_data["company_name"] = name
            except (EOFError, KeyboardInterrupt):
                pass

        if not job_data.get("position_title"):
            warn("Could not identify the position title.")
            try:
                title = input("  Enter position title manually: ").strip()
                if title:
                    job_data["position_title"] = title
            except (EOFError, KeyboardInterrupt):
                pass

        if job_data.get("company_name") and job_data.get("position_title"):
            success("Job details extracted successfully")
        else:
            error("Missing company name or position. Cannot continue.")
            return {}

        return job_data

    # ------------------------------------------------------------------
    # Input detection
    # ------------------------------------------------------------------
    @staticmethod
    def _is_url(text: str) -> bool:
        """Check if the entirety of the input (first non-empty line) looks like a URL."""
        first_line = text.split("\n")[0].strip()
        return bool(re.match(r"https?://[^\s]+", first_line))

    # ------------------------------------------------------------------
    # Scrape a job posting URL
    # ------------------------------------------------------------------
    def _scrape_job_url(self, url: str) -> str:
        """Scrape the job posting page and return its text content."""
        info("Scraping job page…")
        result = self.scraper.scrape_url(url)
        if result.get("success") and result.get("text"):
            success("Page scraped")
            return result["text"]

        # Playwright may have failed – try simple scraper
        result = self.scraper.scrape_simple(url)
        if result.get("success") and result.get("text"):
            success("Page scraped (fallback)")
            return result["text"]

        return ""

    # ------------------------------------------------------------------
    # LLM-based structured extraction
    # ------------------------------------------------------------------
    def _extract_structured_data(self, raw_text: str) -> dict:
        """Send raw text to the NVIDIA API and extract structured job data."""
        # Truncate very long postings to save tokens
        truncated = raw_text[:6000] if len(raw_text) > 6000 else raw_text

        system_prompt = (
            "You are a precise data extraction assistant. "
            "Extract structured job posting data from the text provided. "
            "Return ONLY a valid JSON object with the specified fields. "
            "If a field cannot be determined from the text, use null."
        )

        prompt = f"""Extract the following fields from this job posting text.
Return ONLY a valid JSON object. No markdown code blocks. No explanations.

Required JSON schema:
{{
    "company_name": "exact company name",
    "position_title": "exact job title",
    "location": "location or Remote",
    "employment_type": "Full-time/Part-time/Contract/Internship",
    "salary_range": "if mentioned, else null",
    "key_requirements": ["requirement 1", "requirement 2"],
    "required_skills": ["skill1", "skill2"],
    "nice_to_have_skills": ["skill1", "skill2"],
    "experience_years": "X-Y years or null",
    "education": "degree requirement or null",
    "company_description": "brief from posting",
    "role_description": "what the job entails",
    "tech_stack": ["technology1", "technology2"],
    "benefits": ["benefit1", "benefit2"],
    "application_deadline": "if mentioned, else null",
    "remote_policy": "Remote/Hybrid/On-site"
}}

--- JOB POSTING TEXT ---
{truncated}
"""

        result = self.llm.extract_json(prompt, system_prompt=system_prompt)

        if isinstance(result, dict):
            return self._normalise(result)
        return {}

    # ------------------------------------------------------------------
    # Normalisation
    # ------------------------------------------------------------------
    @staticmethod
    def _normalise(data: dict) -> dict:
        """Ensure all expected keys exist and lists are actually lists."""
        list_fields = [
            "key_requirements",
            "required_skills",
            "nice_to_have_skills",
            "tech_stack",
            "benefits",
        ]
        for field in list_fields:
            val = data.get(field)
            if val is None:
                data[field] = []
            elif isinstance(val, str):
                data[field] = [v.strip() for v in val.split(",") if v.strip()]

        string_fields = [
            "company_name",
            "position_title",
            "location",
            "employment_type",
            "salary_range",
            "experience_years",
            "education",
            "company_description",
            "role_description",
            "application_deadline",
            "remote_policy",
        ]
        for field in string_fields:
            if field not in data:
                data[field] = None

        return data
