"""
Orchestrator: cache check -> provider call -> cache write.

Deliberately thin. This is the one place that should know both "how
caching works" and "how to call a provider" — everything else (cache
internals, provider internals) stays hidden behind their own modules.
That separation is why swapping providers or changing cache storage later
shouldn't require touching this file's logic, only its config.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cache.cache_manager import CacheManager
from library.library_index import LibraryIndex
from providers.gemini_provider import GeminiProvider
from utils.youtube import extract_video_id


class NotesGenerator:
    def __init__(self, config: dict):
        self.config = config
        cache_dir = config["cache"]["dir"]
        self.cache = CacheManager(cache_dir=cache_dir)
        # library.json lives alongside the cache entries it references —
        # same directory, since they're conceptually paired.
        self.library = LibraryIndex(path=f"{cache_dir}/library.json")

        gemini_cfg = config["gemini"]
        self.model = gemini_cfg["model"]
        self.prompt_version = gemini_cfg["prompt_version"]
        self.provider = GeminiProvider(model=self.model)

    def generate_from_url(self, youtube_url: str, shelf: str = "General", force: bool = False) -> dict:
        """
        `shelf` decides which library folder this video is filed under.
        Deliberate simplification worth knowing: whatever shelf is passed
        on ANY call — cache hit or miss — overwrites the entry's current
        shelf. There's no "preserve original shelf" logic the way
        `added_at` is preserved. This is a feature, not an oversight: it
        means re-adding the same URL with a different shelf typed in is
        the (low-tech, intentional) way to move a book between shelves,
        without needing separate move/edit UI.
        """
        video_id = extract_video_id(youtube_url)
        cache_key = self.cache.key_for(video_id, self.model, self.prompt_version)

        if not force:
            cached = self.cache.get(video_id, self.model, self.prompt_version)
            if cached is not None:
                print(f"[cache hit] video_id={video_id} — no API call made")
                self.library.add_or_update(cache_key, video_id, youtube_url, cached["title"], shelf)
                return cached

        print(f"[cache miss] video_id={video_id} — calling Gemini ({self.model})")
        result = self.provider.generate_notes_from_video(youtube_url)

        self.cache.set(video_id, self.model, self.prompt_version, result)
        self.library.add_or_update(cache_key, video_id, youtube_url, result["title"], shelf)
        return result