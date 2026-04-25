"""
Deep company research engine.
Scrapes the web, searches news, and uses the NVIDIA API to synthesise actionable insights.
"""

import time
from datetime import datetime

from utils.nvidia_client import NvidiaLLM
from utils.scraper import WebScraper
from utils.cache import DiskCache
from utils.helpers import info, success, warn, cyan, dim, green

from config.settings import (
    COMPANY_PAGE_PATHS,
    MAX_PAGE_CONTENT_LENGTH,
    SYNTHESIS_TEMPERATURE,
    MAX_TOKENS_SYNTHESIS,
)


class CompanyResearchAgent:
    """Perform deep internet research on a company to personalise cover letters."""

    def __init__(self, llm: NvidiaLLM, scraper: WebScraper, cache: DiskCache):
        self.llm = llm
        self.scraper = scraper
        self.cache = cache

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def research_company(self, job_data: dict) -> dict:
        """Run the full research pipeline. Returns synthesised insights dict."""
        company = job_data.get("company_name", "Unknown")
        cache_key = f"research::{company.lower().strip()}"

        # Check cache first
        cached = self.cache.get(cache_key)
        if cached:
            info(f"Using cached research for {company} (less than 24h old)")
            return cached

        print(f"\n  {cyan(f'Researching {company}…')}")
        start = time.time()
        raw: dict = {}

        # Step 1 – Company website
        self._step("1/6", "Finding company website…")
        website = self._find_company_website(company)
        raw["website"] = website
        self._done()

        # Step 2 – Scrape pages
        self._step("2/6", "Scraping company pages…")
        pages = {}
        if website:
            pages = self._scrape_company_pages(website)
        raw["pages"] = pages
        self._done()

        # Step 3 – News
        self._step("3/6", "Searching recent news…")
        news = self._search_recent_news(company)
        raw["news"] = news
        self._done()

        # Step 4 – Tech stack
        self._step("4/6", "Analysing tech stack…")
        homepage_text = pages.get("homepage", "")
        tech = self._identify_tech_stack(company, homepage_text)
        raw["tech_stack"] = tech
        self._done()

        # Step 5 – Culture
        self._step("5/6", "Studying company culture…")
        about_text = pages.get("about", pages.get("about-us", ""))
        culture = self._analyse_culture(company, about_text)
        raw["culture"] = culture
        self._done()

        # Step 6 – Synthesise
        self._step("6/6", "Synthesising insights…")
        insights = self._synthesise_insights(job_data, raw)
        self._done()

        elapsed = time.time() - start
        print(f"\n  {green(f'Research complete')} {dim(f'(took {elapsed:.0f}s)')}\n")

        # Cache results
        self.cache.set(cache_key, insights)

    def research_company_stream(self, job_data: dict):
        """Streaming version of research pipeline that yields progress items for a Web UI."""
        company = job_data.get("company_name", "Unknown")
        cache_key = f"research::{company.lower().strip()}"

        cached = self.cache.get(cache_key)
        if cached:
            yield {"type": "progress", "step": "Cache", "message": f"Using cached research for {company}"}
            yield {"type": "research_done", "insights": cached}
            return

        yield {"type": "progress", "step": "1/6", "message": f"Finding company website for {company}..."}
        start = time.time()
        raw: dict = {}

        website = self._find_company_website(company)
        raw["website"] = website

        yield {"type": "progress", "step": "2/6", "message": "Scraping company pages..."}
        pages = {}
        if website:
            pages = self._scrape_company_pages(website)
        raw["pages"] = pages

        yield {"type": "progress", "step": "3/6", "message": "Searching recent news..."}
        news = self._search_recent_news(company)
        raw["news"] = news

        yield {"type": "progress", "step": "4/6", "message": "Analysing tech stack..."}
        homepage_text = pages.get("homepage", "")
        tech = self._identify_tech_stack(company, homepage_text)
        raw["tech_stack"] = tech

        yield {"type": "progress", "step": "5/6", "message": "Studying company culture..."}
        about_text = pages.get("about", pages.get("about-us", ""))
        culture = self._analyse_culture(company, about_text)
        raw["culture"] = culture

        yield {"type": "progress", "step": "6/6", "message": "Synthesising insights..."}
        insights = self._synthesise_insights(job_data, raw)

        elapsed = time.time() - start
        self.cache.set(cache_key, insights)
        
        yield {"type": "progress", "step": "Done", "message": f"Research complete ({elapsed:.0f}s)"}
        yield {"type": "research_done", "insights": insights}

    # ------------------------------------------------------------------
    # Research steps
    # ------------------------------------------------------------------
    def _find_company_website(self, company_name: str) -> str | None:
        results = self.scraper.search_google(f"{company_name} official website", num_results=3)
        if not results:
            return None

        # Pick the most likely official domain
        for r in results:
            url = r.get("url", "")
            if url and not any(x in url for x in ["wikipedia", "linkedin", "glassdoor", "crunchbase", "indeed"]):
                return url

        return results[0].get("url") if results else None

    def _scrape_company_pages(self, base_url: str) -> dict:
        """Scrape homepage + standard sub-pages."""
        from urllib.parse import urljoin

        pages = {}

        # Homepage
        result = self.scraper.scrape_simple(base_url)
        if result.get("success") and result.get("text"):
            pages["homepage"] = result["text"][:MAX_PAGE_CONTENT_LENGTH]

        # Standard paths
        for path in COMPANY_PAGE_PATHS:
            full_url = urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
            result = self.scraper.scrape_simple(full_url)
            if result.get("success") and result.get("text"):
                key = path.strip("/").replace("-", "_") or "root"
                pages[key] = result["text"][:MAX_PAGE_CONTENT_LENGTH]

        return pages

    def _search_recent_news(self, company_name: str) -> list[dict]:
        year = datetime.now().year
        results: list[dict] = []

        q1 = f"{company_name} news {year}"
        q2 = f"{company_name} announcement funding launch"

        for q in (q1, q2):
            hits = self.scraper.search_google(q, num_results=4)
            results.extend(hits)

        # Deduplicate by URL
        seen = set()
        unique = []
        for r in results:
            url = r.get("url", "")
            if url not in seen:
                seen.add(url)
                unique.append(r)

        return unique[:8]

    def _identify_tech_stack(self, company_name: str, website_content: str) -> list[str]:
        hits = self.scraper.search_google(f"{company_name} tech stack engineering blog", num_results=3)
        snippets = " ".join(h.get("snippet", "") for h in hits)
        combined = f"Website content:\n{website_content[:1500]}\n\nSearch results:\n{snippets}"

        prompt = f"""Based on the following information about {company_name}, list the programming languages, frameworks,
cloud providers, databases, and infrastructure tools they are known to use.
Return ONLY a JSON array of technology name strings. Example: ["Python", "Go", "AWS", "Kubernetes"]

{combined}
"""
        result = self.llm.extract_json(prompt)
        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            return result.get("tech_stack", result.get("technologies", []))
        return []

    def _analyse_culture(self, company_name: str, about_content: str) -> dict:
        hits = self.scraper.search_google(f"{company_name} culture values glassdoor", num_results=3)
        snippets = " ".join(h.get("snippet", "") for h in hits)

        combined = f"About page:\n{about_content[:1500]}\n\nSearch results:\n{snippets}"

        prompt = f"""Analyse the culture of {company_name} from the following information.
Return a JSON object with:
{{
    "values": ["value1", "value2", "value3"],
    "work_style": "description of work environment",
    "key_traits": ["trait1", "trait2", "trait3", "trait4", "trait5"]
}}

{combined}
"""
        result = self.llm.extract_json(prompt)
        if isinstance(result, dict):
            return result
        return {"values": [], "work_style": "", "key_traits": []}

    def _get_funding_info(self, company_name: str) -> dict | None:
        hits = self.scraper.search_google(f"{company_name} funding series valuation", num_results=3)
        if not hits:
            return None
        snippets = " ".join(h.get("snippet", "") for h in hits)
        prompt = f"""Extract funding information for {company_name} from:
{snippets}

Return JSON: {{"stage": "Series X or Public", "last_round": "$XM", "valuation": "$XB or null", "investors": ["investor1"]}}
If it's a public company, set stage to "Public" and include market cap if known.
"""
        result = self.llm.extract_json(prompt)
        return result if isinstance(result, dict) else None

    # ------------------------------------------------------------------
    # Synthesis
    # ------------------------------------------------------------------
    def _synthesise_insights(self, job_data: dict, raw_research: dict) -> dict:
        """Use the LLM to distil raw research into actionable cover-letter insights."""
        company = job_data.get("company_name", "Unknown")

        # Build a text summary of all raw research
        parts = [f"Company: {company}"]

        if raw_research.get("website"):
            parts.append(f"Website: {raw_research['website']}")

        pages = raw_research.get("pages", {})
        for page_name, content in pages.items():
            parts.append(f"\n--- {page_name.upper()} PAGE ---\n{content[:800]}")

        news = raw_research.get("news", [])
        if news:
            parts.append("\n--- RECENT NEWS ---")
            for n in news[:5]:
                parts.append(f"• {n.get('title', '')} – {n.get('snippet', '')}")

        tech = raw_research.get("tech_stack", [])
        if tech:
            parts.append(f"\nKnown tech stack: {', '.join(tech)}")

        culture = raw_research.get("culture", {})
        if culture:
            parts.append(f"\nCulture values: {', '.join(culture.get('values', []))}")
            parts.append(f"Work style: {culture.get('work_style', '')}")
            parts.append(f"Key traits: {', '.join(culture.get('key_traits', []))}")

        # Job context
        parts.append(f"\nPosition: {job_data.get('position_title', '')}")
        skills = job_data.get("required_skills", [])
        if skills:
            parts.append(f"Required skills: {', '.join(skills)}")

        combined = "\n".join(parts)

        system_prompt = (
            "You are a career research analyst. Synthesise raw company research "
            "into actionable insights for writing a personalised cover letter. "
            "Return ONLY valid JSON."
        )

        prompt = f"""Based on the following research about {company}, produce actionable insights for a cover letter.

{combined}

Return this exact JSON structure:
{{
    "company_momentum": "One sentence about their most recent notable achievement or direction",
    "cultural_keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"],
    "pain_points": ["pain_point1", "pain_point2", "pain_point3"],
    "connection_angles": ["angle1", "angle2", "angle3"],
    "recent_initiatives": ["initiative1", "initiative2"],
    "interview_questions": ["question1", "question2", "question3"],
    "talking_points": ["point1", "point2", "point3"],
    "red_flags": ["any concerns from research, or empty list"]
}}
"""

        result = self.llm.extract_json(prompt, system_prompt=system_prompt)

        if isinstance(result, dict):
            # Merge in raw tech stack and culture info for downstream use
            result.setdefault("tech_stack_found", tech)
            result.setdefault("culture_details", culture)
            return result

        return {
            "company_momentum": f"Research on {company} produced limited results.",
            "cultural_keywords": [],
            "pain_points": [],
            "connection_angles": [],
            "recent_initiatives": [],
            "interview_questions": [],
            "talking_points": [],
            "red_flags": ["Limited research data available"],
            "tech_stack_found": tech,
            "culture_details": culture,
        }

    # ------------------------------------------------------------------
    # Display helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _step(number: str, description: str) -> None:
        print(f"  [{number}] {description:<40}", end="", flush=True)

    @staticmethod
    def _done() -> None:
        print(f" {green('done')}")
