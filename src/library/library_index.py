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

Storage format: {"entries": [...], "shelves": [...]}. Originally shelves
were NOT their own record — a shelf existed only when an entry
referenced it, which kept things simple but made it impossible to
represent an empty shelf (e.g., created in advance to move existing
books into later, before any book is filed under it — decided [this
session] this needs to be a real, supportable case). The "shelves" list
holds names of explicitly-created shelves with zero books; shelves that
already have books are still derived from entries as before. A shelf's
full membership is the UNION of both — never double-counted, since
list_shelves() dedupes by name.

Backward compatibility: earlier versions of this file were a bare JSON
list of entries (no wrapping object, no explicit-shelves list). _read()
detects that shape and migrates it in memory automatically — no manual
migration step, no data loss, existing entries keep every field they had.

Kept as ONE JSON file, not one-file-per-entry, because the whole point is
reading it as a list in a single shot when building the shelf — scanning
a directory of many tiny files every time the shelf loads would be
slower and messier for no benefit at this project's scale.

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
            self._write_data({"entries": [], "shelves": []})

    def _read_data(self) -> dict:
        with open(self.path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        if isinstance(raw, list):
            # Old format: a bare list of entries. Migrate in memory —
            # written back in the new shape on the next write, not
            # forced immediately, so a pure read never has side effects.
            return {"entries": raw, "shelves": []}
        raw.setdefault("entries", [])
        raw.setdefault("shelves", [])
        return raw

    def _write_data(self, data: dict) -> None:
        # Temp-file-then-rename, same pattern as CacheManager — avoids a
        # half-written library.json if the process dies mid-write.
        tmp_path = self.path.with_suffix(".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, self.path)

    def add_or_update(
        self, cache_key: str, video_id: str, url: str, title: str, shelf: str = _DEFAULT_SHELF
    ) -> None:
        shelf = (shelf or "").strip() or _DEFAULT_SHELF

        data = self._read_data()
        entries = data["entries"]
        existing = next((e for e in entries if e["cache_key"] == cache_key), None)
        added_at = existing["added_at"] if existing else datetime.now(timezone.utc).isoformat()

        data["entries"] = [e for e in entries if e["cache_key"] != cache_key]
        data["entries"].append({
            "cache_key": cache_key,
            "video_id": video_id,
            "url": url,
            "title": title,
            "shelf": shelf,
            "added_at": added_at,
        })
        self._write_data(data)

    def list_all(self) -> List[dict]:
        return self._read_data()["entries"]

    def list_shelves(self) -> List[dict]:
        """Distinct shelf names with a book count for each, sorted
        alphabetically — what the library home page renders as folders
        (and branches, in the tree view). Includes shelves with zero
        books (explicitly created via create_shelf()), not just ones
        derived from existing entries. Entries from before shelves
        existed (no "shelf" key) count under the default shelf rather
        than being silently dropped."""
        data = self._read_data()
        counts: dict[str, int] = {}
        for entry in data["entries"]:
            shelf = entry.get("shelf") or _DEFAULT_SHELF
            counts[shelf] = counts.get(shelf, 0) + 1
        for name in data["shelves"]:
            counts.setdefault(name, 0)
        return [
            {"name": name, "count": count}
            for name, count in sorted(counts.items())
        ]

    def list_by_shelf(self, shelf: str) -> List[dict]:
        """Entries belonging to one specific shelf — what a shelf's own
        page renders. Same default-shelf fallback as list_shelves(), so
        an entry's shelf membership is judged consistently everywhere."""
        return [
            e for e in self._read_data()["entries"]
            if (e.get("shelf") or _DEFAULT_SHELF) == shelf
        ]

    def create_shelf(self, name: str) -> bool:
        """Explicitly creates a shelf with zero books — the case that
        motivated the storage format change: setting up a shelf in
        advance so existing books (from other shelves) can be moved into
        it, without needing to generate a new video just to create the
        name. Returns False if the name is blank or a shelf by that name
        (empty or not) already exists — creating is a no-op then, not an
        error, since the desired end state (a shelf with this name
        exists) is already true."""
        name = (name or "").strip()
        if not name:
            return False
        data = self._read_data()
        already_exists = name in data["shelves"] or any(
            (e.get("shelf") or _DEFAULT_SHELF) == name for e in data["entries"]
        )
        if already_exists:
            return False
        data["shelves"].append(name)
        self._write_data(data)
        return True

    def rename_shelf(self, old_name: str, new_name: str) -> int:
        """Renames a shelf by relabeling every entry currently under
        old_name, AND updating the explicit-shelves list if old_name was
        an empty shelf created via create_shelf(). Returns how many
        ENTRIES were moved (an empty shelf being renamed returns 0, which
        is correct — no entries moved — even though the rename itself
        succeeded). If new_name happens to match an already-existing
        shelf, this doubles as a merge — not a special case, just a
        natural consequence of shelf membership being nothing more than
        a matching string."""
        new_name = (new_name or "").strip() or _DEFAULT_SHELF
        data = self._read_data()

        if old_name in data["shelves"]:
            data["shelves"].remove(old_name)
            if new_name not in data["shelves"]:
                data["shelves"].append(new_name)

        count = 0
        for e in data["entries"]:
            current = e.get("shelf") or _DEFAULT_SHELF
            if current == old_name:
                e["shelf"] = new_name
                count += 1

        self._write_data(data)
        return count

    def delete_shelf(self, name: str) -> int:
        """Deletes a shelf WITHOUT deleting the underlying generated
        notes — those cost a real API call to create, so a shelf being
        an organizational mistake shouldn't destroy them. Entries are
        moved back to the default shelf instead. Implemented as a rename
        to the default shelf, since that's exactly the semantics wanted
        — this also correctly handles removing an empty explicitly-
        created shelf via rename_shelf's own list cleanup."""
        return self.rename_shelf(name, _DEFAULT_SHELF)

    def move_entry(self, video_id: str, new_shelf: str) -> bool:
        """Moves a single book to a different shelf by video_id. Returns
        True if a matching entry was found and moved, False otherwise —
        the caller (API route) turns a False into a 404."""
        new_shelf = (new_shelf or "").strip() or _DEFAULT_SHELF
        data = self._read_data()
        found = False
        for e in data["entries"]:
            if e["video_id"] == video_id:
                e["shelf"] = new_shelf
                found = True
        self._write_data(data)
        return found