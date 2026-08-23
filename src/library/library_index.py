"""
Library index: a catalog of every video whose notes have been generated.

Why this exists separately from CacheManager: cache/*.json files are
addressed by an opaque hash of (video_id, model, prompt_version) — great
for answering "have I generated this exact thing before," useless for
answering "what's in my library, and what should the bookshelf display."
The library index is that second, human-facing list: video url, title,
which cache entry holds the actual content, and when it was first added.

Kept as ONE JSON file (a list of entries), not one-file-per-entry, because
the whole point is reading it as a list in a single shot when building the
shelf — scanning a directory of many tiny files every time the shelf loads
would be slower and messier for no benefit at this project's scale.

Upsert semantics, not append-only: calling add_or_update() is always safe
to call, cache hit or miss, first time or the hundredth. If the entry
already exists (same cache_key), its original "added" timestamp is
preserved and only the rest is refreshed — so re-running the same video
never creates a duplicate shelf entry or loses the original add date.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List


class LibraryIndex:
    def __init__(self, path: str = "./cache/library.json"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write([])

    def _read(self) -> List[dict]:
        with open(self.path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write(self, entries: List[dict]) -> None:
        # Temp-file-then-rename, same pattern as CacheManager — avoids a
        # half-written library.json if the process dies mid-write.
        tmp_path = self.path.with_suffix(".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2)
        os.replace(tmp_path, self.path)

    def add_or_update(self, cache_key: str, video_id: str, url: str, title: str) -> None:
        entries = self._read()
        existing = next((e for e in entries if e["cache_key"] == cache_key), None)
        added_at = existing["added_at"] if existing else datetime.now(timezone.utc).isoformat()

        entries = [e for e in entries if e["cache_key"] != cache_key]
        entries.append({
            "cache_key": cache_key,
            "video_id": video_id,
            "url": url,
            "title": title,
            "added_at": added_at,
        })
        self._write(entries)

    def list_all(self) -> List[dict]:
        return self._read()