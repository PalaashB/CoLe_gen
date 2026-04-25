"""
Simple disk-based JSON cache with TTL (time-to-live).
Used for company research, API responses, and scraped pages.
"""

import hashlib
import json
import time
from pathlib import Path

from config.settings import CACHE_DIR, RESEARCH_CACHE_TTL


class DiskCache:
    """Persistent JSON cache stored on disk with configurable TTL."""

    def __init__(
        self,
        cache_dir: str | Path | None = None,
        default_ttl: int = RESEARCH_CACHE_TTL,
    ):
        self.cache_dir = Path(cache_dir) if cache_dir else CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.default_ttl = default_ttl

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def get(self, key: str) -> dict | list | None:
        """Return cached data for *key*, or None if missing / expired."""
        path = self._key_path(key)
        if not path.exists():
            return None

        try:
            with open(path, "r") as f:
                entry = json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

        ttl = entry.get("ttl", self.default_ttl)
        created = entry.get("created", 0)
        if time.time() - created > ttl:
            # Expired – remove stale file
            try:
                path.unlink()
            except OSError:
                pass
            return None

        return entry.get("data")

    def set(self, key: str, data, ttl: int | None = None) -> None:
        """Persist *data* under *key* with an optional custom TTL."""
        path = self._key_path(key)
        entry = {
            "key": key,
            "created": time.time(),
            "ttl": ttl if ttl is not None else self.default_ttl,
            "data": data,
        }
        try:
            with open(path, "w") as f:
                json.dump(entry, f, indent=2, default=str)
        except OSError as exc:
            print(f"\033[93m⚠ Cache write failed: {exc}\033[0m")

    def clear(self) -> int:
        """Delete all cache files. Returns number of files removed."""
        count = 0
        for p in self.cache_dir.glob("*.json"):
            try:
                p.unlink()
                count += 1
            except OSError:
                pass
        return count

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _key_path(self, key: str) -> Path:
        """Hash the key to a stable filename."""
        digest = hashlib.sha256(key.encode()).hexdigest()[:16]
        return self.cache_dir / f"{digest}.json"
