"""
Library index: a catalog of every video whose notes have been generated,
organized into named shelves (subjects/folders) — a "personal library"
model rather than one flat list of every book.

Why this exists separately from CacheManager: cache/*.json files are
addressed by an opaque hash of (video_id, model, prompt_version) — great
for answering "have I generated this exact thing before," useless for
answering "what's in my library, and what should the bookshelf display."
The library index is that second, human-facing list: video url, title,
which shelf it belongs to, which cache entry holds the actual content,
and when it was first added.

Kept as ONE JSON file (a list of entries), not one-file-per-entry, because
the whole point is reading it as a list in a single shot when building the
shelf — scanning a directory of many tiny files every time the shelf loads
would be slower and messier for no benefit at this project's scale.

Shelves are NOT their own separate record — a shelf is just whatever
distinct `shelf` string appears on one or more entries. This keeps the
data model simple (one file, one list) for now; if shelves ever need
their own metadata (an icon, a description, a sort order), that's the
point to introduce a real second collection — not before it's needed.

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

_DEFAULT_SHELF = "General"


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

    def add_or_update(
        self, cache_key: str, video_id: str, url: str, title: str, shelf: str = _DEFAULT_SHELF
    ) -> None:
        shelf = (shelf or "").strip() or _DEFAULT_SHELF

        entries = self._read()
        existing = next((e for e in entries if e["cache_key"] == cache_key), None)
        added_at = existing["added_at"] if existing else datetime.now(timezone.utc).isoformat()

        entries = [e for e in entries if e["cache_key"] != cache_key]
        entries.append({
            "cache_key": cache_key,
            "video_id": video_id,
            "url": url,
            "title": title,
            "shelf": shelf,
            "added_at": added_at,
        })
        self._write(entries)

    def list_all(self) -> List[dict]:
        return self._read()

    def list_shelves(self) -> List[dict]:
        """Distinct shelf names with a book count for each, sorted
        alphabetically — what the library home page renders as folders.
        Entries from before shelves existed (no "shelf" key) count under
        the default shelf rather than being silently dropped."""
        counts: dict[str, int] = {}
        for entry in self._read():
            shelf = entry.get("shelf") or _DEFAULT_SHELF
            counts[shelf] = counts.get(shelf, 0) + 1
        return [
            {"name": name, "count": count}
            for name, count in sorted(counts.items())
        ]

    def list_by_shelf(self, shelf: str) -> List[dict]:
        """Entries belonging to one specific shelf — what a shelf's own
        page renders. Same default-shelf fallback as list_shelves(), so
        an entry's shelf membership is judged consistently everywhere."""
        return [
            e for e in self._read()
            if (e.get("shelf") or _DEFAULT_SHELF) == shelf
        ]

    def rename_shelf(self, old_name: str, new_name: str) -> int:
        """Renames a shelf by relabeling every entry currently under
        old_name. Returns how many entries were moved. If new_name
        happens to match an already-existing shelf, this doubles as a
        merge — not a special case, just a natural consequence of shelf
        membership being nothing more than a matching string."""
        new_name = (new_name or "").strip() or _DEFAULT_SHELF
        entries = self._read()
        count = 0
        for e in entries:
            current = e.get("shelf") or _DEFAULT_SHELF
            if current == old_name:
                e["shelf"] = new_name
                count += 1
        self._write(entries)
        return count

    def delete_shelf(self, name: str) -> int:
        """Deletes a shelf WITHOUT deleting the underlying generated
        notes — those cost a real API call to create, so a shelf being
        an organizational mistake shouldn't destroy them. Entries are
        moved back to the default shelf instead. Implemented as a rename
        to the default shelf, since that's exactly the semantics wanted."""
        return self.rename_shelf(name, _DEFAULT_SHELF)

    def move_entry(self, video_id: str, new_shelf: str) -> bool:
        """Moves a single book to a different shelf by video_id. Returns
        True if a matching entry was found and moved, False otherwise —
        the caller (API route) turns a False into a 404."""
        new_shelf = (new_shelf or "").strip() or _DEFAULT_SHELF
        entries = self._read()
        found = False
        for e in entries:
            if e["video_id"] == video_id:
                e["shelf"] = new_shelf
                found = True
        self._write(entries)
        return found