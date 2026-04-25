"""
Web scraping utilities.
Uses Playwright for JavaScript-heavy sites and requests+BeautifulSoup as a fast fallback.
"""

import os
import random
import time
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from config.settings import SCRAPE_DELAY_SECONDS, SCRAPE_TIMEOUT_SECONDS, USER_AGENT


class WebScraper:
    """Scrape web pages and perform web searches."""

    def __init__(self):
        self._browser = None
        self._playwright = None
        self._pw_available = True
        self._init_playwright()

    def _init_playwright(self) -> None:
        """Lazily initialise Playwright browser (headless Chromium)."""
        try:
            from playwright.sync_api import sync_playwright

            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(headless=True)
        except Exception:
            self._pw_available = False
            self._browser = None
            self._playwright = None

    # ------------------------------------------------------------------
    # Full page scrape (Playwright)
    # ------------------------------------------------------------------
    def scrape_url(self, url: str, wait_for_selector: str | None = None) -> dict:
        """Scrape a URL using Playwright. Falls back to simple scrape on failure."""
        if not self._pw_available or self._browser is None:
            return self.scrape_simple(url)

        try:
            context = self._browser.new_context(user_agent=USER_AGENT)
            page = context.new_page()
            page.set_default_timeout(SCRAPE_TIMEOUT_SECONDS * 1000)

            page.goto(url, wait_until="domcontentloaded")
            if wait_for_selector:
                try:
                    page.wait_for_selector(wait_for_selector, timeout=10000)
                except Exception:
                    pass  # Selector not found – proceed with what we have

            # Give JS time to render
            page.wait_for_timeout(2000)

            title = page.title()
            meta_desc = ""
            try:
                meta_desc = page.locator('meta[name="description"]').get_attribute("content") or ""
            except Exception:
                pass

            text = page.inner_text("body")
            links = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")

            context.close()
            self._polite_delay()

            return {
                "url": url,
                "title": title,
                "meta_description": meta_desc,
                "text": self._clean_text(text),
                "links": links[:50],  # cap to avoid noise
                "success": True,
            }

        except Exception as exc:
            err = str(exc).lower()
            if "timeout" in err:
                print(f"  \033[93m⚠ Page timed out: {url}\033[0m")
            elif "404" in err or "not found" in err:
                print(f"  \033[93m⚠ Page not found: {url}\033[0m")
            elif "403" in err or "forbidden" in err:
                print(f"  \033[93m⚠ Access blocked: {url}. Trying fallback…\033[0m")
                return self.scrape_simple(url)
            else:
                pass  # Silent fallback
            return self.scrape_simple(url)

    # ------------------------------------------------------------------
    # Simple scrape (requests + BeautifulSoup)
    # ------------------------------------------------------------------
    def scrape_simple(self, url: str) -> dict:
        """Fast scrape using requests + BeautifulSoup (no JS rendering)."""
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        try:
            resp = requests.get(url, headers=headers, timeout=SCRAPE_TIMEOUT_SECONDS)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")

            title = soup.title.string.strip() if soup.title and soup.title.string else ""
            meta_tag = soup.find("meta", attrs={"name": "description"})
            meta_desc = meta_tag.get("content", "") if meta_tag else ""

            # Remove scripts and styles
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()

            text = soup.get_text(separator="\n", strip=True)

            links = []
            for a in soup.find_all("a", href=True)[:50]:
                href = a["href"]
                if href.startswith("/"):
                    href = urljoin(url, href)
                links.append(href)

            self._polite_delay()

            return {
                "url": url,
                "title": title,
                "meta_description": meta_desc,
                "text": self._clean_text(text),
                "links": links,
                "success": True,
            }

        except requests.exceptions.HTTPError as exc:
            code = exc.response.status_code if exc.response is not None else 0
            if code == 404:
                print(f"  \033[93m⚠ Page not found: {url}\033[0m")
            elif code == 403:
                print(f"  \033[93m⚠ Access blocked: {url}\033[0m")
            elif code == 401:
                print(f"  \033[93m⚠ Login required: {url}. Paste the job text instead.\033[0m")
            return {"url": url, "text": "", "success": False}

        except requests.exceptions.Timeout:
            print(f"  \033[93m⚠ Page timed out: {url}\033[0m")
            return {"url": url, "text": "", "success": False}

        except requests.exceptions.ConnectionError:
            print(f"  \033[93m⚠ Connection refused: {url}\033[0m")
            return {"url": url, "text": "", "success": False}

        except Exception:
            return {"url": url, "text": "", "success": False}

    # ------------------------------------------------------------------
    # Web search
    # ------------------------------------------------------------------
    def search_google(self, query: str, num_results: int = 5) -> list[dict]:
        """Search the web. Tries SerpAPI → DuckDuckGo HTML fallback."""
        serp_key = os.getenv("SERPAPI_KEY", "").strip()
        if serp_key:
            return self._search_serpapi(query, serp_key, num_results)
        return self._search_duckduckgo(query, num_results)

    def _search_serpapi(self, query: str, api_key: str, num: int) -> list[dict]:
        """Use SerpAPI for Google search results."""
        try:
            from serpapi import GoogleSearch

            params = {
                "q": query,
                "api_key": api_key,
                "num": num,
                "engine": "google",
            }
            search = GoogleSearch(params)
            results = search.get_dict()
            organic = results.get("organic_results", [])
            return [
                {
                    "title": r.get("title", ""),
                    "url": r.get("link", ""),
                    "snippet": r.get("snippet", ""),
                }
                for r in organic[:num]
            ]
        except Exception:
            return self._search_duckduckgo(query, num)

    def _search_duckduckgo(self, query: str, num: int) -> list[dict]:
        """DuckDuckGo HTML search – no API key required."""
        headers = {"User-Agent": USER_AGENT}
        try:
            resp = requests.get(
                "https://html.duckduckgo.com/html/",
                params={"q": query},
                headers=headers,
                timeout=15,
            )
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            results = []
            for result in soup.select(".result")[:num]:
                title_tag = result.select_one(".result__title a")
                snippet_tag = result.select_one(".result__snippet")
                if title_tag:
                    href = title_tag.get("href", "")
                    # DuckDuckGo wraps URLs in a redirect
                    if "uddg=" in href:
                        from urllib.parse import parse_qs, urlparse as _urlparse

                        parsed = _urlparse(href)
                        qs = parse_qs(parsed.query)
                        href = qs.get("uddg", [href])[0]
                    results.append(
                        {
                            "title": title_tag.get_text(strip=True),
                            "url": href,
                            "snippet": snippet_tag.get_text(strip=True) if snippet_tag else "",
                        }
                    )
            self._polite_delay()
            return results

        except Exception:
            return []

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------
    def close(self) -> None:
        """Release Playwright resources."""
        try:
            if self._browser:
                self._browser.close()
            if self._playwright:
                self._playwright.stop()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _polite_delay() -> None:
        """Random delay to be polite to servers."""
        time.sleep(SCRAPE_DELAY_SECONDS + random.uniform(0, 0.5))

    @staticmethod
    def _clean_text(text: str) -> str:
        """Collapse whitespace and limit length."""
        import re

        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]+", " ", text)
        return text.strip()
