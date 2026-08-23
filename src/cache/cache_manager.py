"""
Content-addressed cache for generated notes.

Why keyed on (video_id, model, prompt_version) and not just video_id:
if we only keyed on video_id, changing the prompt or swapping models
would silently keep serving OLD output. You'd tweak a prompt, re-run,
see the same result, and wrongly conclude the tweak did nothing — when
really you were just reading yesterday's cache. Including model and
prompt_version in the key means a change to either naturally produces a
fresh cache miss, with no separate "remember to clear the cache" step.

This is deliberately simple: one JSON file per cache entry. No database.
At this project's scale (a personal tool, low volume) an actual DB would
be overengineering — a mistake worth naming honestly rather than quietly
avoiding by adding SQLite "just in case."
"""

import hashlib
import json
import os
from pathlib import Path
from typing import Optional


class CacheManager:
    def __init__(self, cache_dir: str = "./cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def key_for(self, video_id: str, model: str, prompt_version: int) -> str:
        """Public accessor for the cache key — the library index needs
        this to record which cache entry a library entry points at,
        without duplicating the hashing logic elsewhere."""
        return self._key(video_id, model, prompt_version)

    def _key(self, video_id: str, model: str, prompt_version: int) -> str:
        raw = f"{video_id}:{model}:{prompt_version}"
        # Hashing isn't for secrecy here, just to get a filesystem-safe,
        # fixed-length filename regardless of what's in the raw key.
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]

    def get(self, video_id: str, model: str, prompt_version: int) -> Optional[dict]:
        path = self.cache_dir / f"{self._key(video_id, model, prompt_version)}.json"
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def set(self, video_id: str, model: str, prompt_version: int, data: dict) -> None:
        path = self.cache_dir / f"{self._key(video_id, model, prompt_version)}.json"
        # Write to a temp file then rename — avoids a half-written cache
        # file if the process is killed mid-write.
        tmp_path = path.with_suffix(".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, path)