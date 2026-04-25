"""
NVIDIA NIM API wrapper.
All LLM calls in the entire project go through this module.
No other file imports the openai library directly.
"""

import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from config.settings import (
    API_LOG_PATH,
    EXTRACTION_TEMPERATURE,
    MAX_RETRIES,
    MAX_TOKENS_EXTRACTION,
    NVIDIA_BASE_URL,
    NVIDIA_MODEL,
    RETRY_BACKOFF,
)

load_dotenv()


class NvidiaLLM:
    """Central LLM client wrapping the NVIDIA NIM (OpenAI-compatible) API."""

    def __init__(self):
        self.api_key = os.getenv("NVIDIA_API_KEY", "").strip()
        if not self.api_key:
            print(
                "\n\033[91m✗ NVIDIA API key not found.\033[0m\n"
                "  Add NVIDIA_API_KEY=nvapi-your-key to your .env file.\n"
                "  Get a key at: https://build.nvidia.com\n"
            )
            sys.exit(1)

        self.client = OpenAI(base_url=NVIDIA_BASE_URL, api_key=self.api_key)
        self.model = NVIDIA_MODEL
        self.session_tokens = 0

        # Ensure log directory exists
        API_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Core generation
    # ------------------------------------------------------------------
    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = False,
        json_mode: bool = False,
    ) -> str:
        """Send a prompt to the NVIDIA API and return the full response text.

        If *stream* is True a generator yielding text chunks is returned instead.
        If *json_mode* is True the response is parsed as JSON (retries up to 3×).
        """
        if json_mode:
            temperature = EXTRACTION_TEMPERATURE
            max_tokens = min(max_tokens, MAX_TOKENS_EXTRACTION)

        messages = self._build_messages(prompt, system_prompt)

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                start = time.time()
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    top_p=0.95,
                    max_tokens=max_tokens,
                    stream=stream,
                )

                if stream:
                    return self._stream_chunks(response, start)

                text = response.choices[0].message.content or ""
                latency = time.time() - start
                tokens = getattr(response.usage, "total_tokens", 0) if response.usage else 0
                self.session_tokens += tokens
                self._log_call(prompt[:80], tokens, latency)

                if json_mode:
                    return self._parse_json_response(text, prompt, system_prompt, attempt)

                return text.strip()

            except Exception as exc:
                if not self._handle_error(exc, attempt):
                    raise

        return ""

    # ------------------------------------------------------------------
    # Streaming helper
    # ------------------------------------------------------------------
    def generate_streaming(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """Stream response chunks, print each to the terminal, and return the full text."""
        messages = self._build_messages(prompt, system_prompt)

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                start = time.time()
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    top_p=0.95,
                    max_tokens=max_tokens,
                    stream=True,
                )

                full_text = ""
                for chunk in response:
                    if chunk.choices and chunk.choices[0].delta.content:
                        piece = chunk.choices[0].delta.content
                        print(piece, end="", flush=True)
                        full_text += piece

                print()  # newline after stream ends
                latency = time.time() - start
                self._log_call(prompt[:80], len(full_text.split()), latency)
                return full_text.strip()

            except Exception as exc:
                if not self._handle_error(exc, attempt):
                    raise

        return ""

    # ------------------------------------------------------------------
    # JSON extraction helper
    # ------------------------------------------------------------------
    def extract_json(self, prompt: str, system_prompt: str | None = None) -> dict | list:
        """Generate a response in JSON mode and return the parsed object."""
        suffix = "\n\nReturn ONLY valid JSON. No markdown, no explanation, no code blocks."
        full_prompt = prompt + suffix

        for attempt in range(1, MAX_RETRIES + 1):
            raw = self.generate(
                full_prompt,
                system_prompt=system_prompt,
                temperature=EXTRACTION_TEMPERATURE,
                max_tokens=MAX_TOKENS_EXTRACTION,
                json_mode=False,  # we handle parsing ourselves
            )
            try:
                return self._clean_and_parse_json(raw)
            except json.JSONDecodeError:
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_BACKOFF * attempt)
                    continue
                # Last attempt – return empty dict and warn
                print("\033[93m⚠ Could not parse JSON from model response.\033[0m")
                return {}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _build_messages(prompt: str, system_prompt: str | None) -> list[dict]:
        msgs: list[dict] = []
        if system_prompt:
            msgs.append({"role": "system", "content": system_prompt})
        msgs.append({"role": "user", "content": prompt})
        return msgs

    def _stream_chunks(self, response, start: float):
        """Return a generator that yields text chunks."""
        full_text = ""
        for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                piece = chunk.choices[0].delta.content
                full_text += piece
                yield piece
        latency = time.time() - start
        self._log_call("streaming", len(full_text.split()), latency)

    @staticmethod
    def _clean_and_parse_json(text: str) -> dict | list:
        """Strip markdown fences and parse JSON."""
        cleaned = text.strip()
        # Remove ```json ... ``` wrappers
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        return json.loads(cleaned)

    def _parse_json_response(
        self, text: str, prompt: str, system_prompt: str | None, attempt: int
    ) -> str:
        """Try to parse JSON; retry with stricter prompt on failure."""
        try:
            parsed = self._clean_and_parse_json(text)
            return json.dumps(parsed)
        except json.JSONDecodeError:
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF * attempt)
                return self.generate(
                    prompt + "\n\nYou MUST return valid JSON only.",
                    system_prompt=system_prompt,
                    json_mode=True,
                )
            return text.strip()

    def _handle_error(self, exc: Exception, attempt: int) -> bool:
        """Handle API errors with retries. Returns True if a retry should be attempted."""
        exc_str = str(exc)
        status = getattr(exc, "status_code", None) or getattr(exc, "code", None)

        if status == 401:
            print(
                "\n\033[91m✗ Invalid NVIDIA API key.\033[0m\n"
                "  Generate a new one at https://build.nvidia.com\n"
            )
            sys.exit(1)

        if status == 429:
            wait = RETRY_BACKOFF * (2 ** (attempt - 1))
            print(f"\033[93m⚠ Rate limited. Retrying in {wait:.0f}s…\033[0m")
            time.sleep(wait)
            return attempt < MAX_RETRIES

        if isinstance(status, int) and status >= 500:
            wait = RETRY_BACKOFF * attempt
            if attempt < MAX_RETRIES:
                print(f"\033[93m⚠ Server error. Retrying ({attempt}/{MAX_RETRIES})…\033[0m")
                time.sleep(wait)
                return True
            print("\033[91m✗ NVIDIA API temporarily unavailable. Try again in a few minutes.\033[0m")
            return False

        if "timeout" in exc_str.lower() or "timed out" in exc_str.lower():
            if attempt < MAX_RETRIES:
                print(f"\033[93m⚠ Request timed out. Retrying…\033[0m")
                time.sleep(RETRY_BACKOFF)
                return True
            print("\033[91m✗ Request timed out. Check your internet connection.\033[0m")
            return False

        if "connection" in exc_str.lower() or "network" in exc_str.lower():
            print("\033[91m✗ Network error. Check your internet connection.\033[0m")
            return False

        # Unknown error – propagate after retries exhausted
        if attempt < MAX_RETRIES:
            time.sleep(RETRY_BACKOFF * attempt)
            return True

        print(f"\033[91m✗ API error: {exc_str}\033[0m")
        return False

    def _log_call(self, prompt_preview: str, tokens: int, latency: float) -> None:
        """Append a one-line log entry."""
        try:
            with open(API_LOG_PATH, "a") as f:
                ts = datetime.now().isoformat(timespec="seconds")
                f.write(f"{ts} | tokens={tokens} | latency={latency:.1f}s | {prompt_preview}\n")
        except OSError:
            pass  # Non-critical
