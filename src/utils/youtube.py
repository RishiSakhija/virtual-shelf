"""
Extracting a stable video_id from a YouTube URL.

Why this exists as its own function: people will paste URLs in different
shapes (watch?v=, youtu.be/, with &t=123 timestamps, with playlist params).
We need ONE canonical id per video so the cache key is stable regardless
of which shape of URL was pasted — otherwise the same video with a
different timestamp param would be treated as "new" and burn a fresh
Gemini request for no reason.
"""

import re
from urllib.parse import urlparse, parse_qs

_PATTERNS = [
    r"(?:v=|/videos/|embed/|youtu\.be/|/v/|/e/|watch\?v=|&v=)([A-Za-z0-9_-]{11})",
]


def extract_video_id(url: str) -> str:
    """Return the 11-character YouTube video id, or raise ValueError."""
    parsed = urlparse(url)

    # Handle youtu.be/<id> shortlinks explicitly first — the regex below
    # also catches most of these, but this path is clearer.
    if "youtu.be" in parsed.netloc:
        candidate = parsed.path.lstrip("/")
        if len(candidate) >= 11:
            return candidate[:11]

    qs = parse_qs(parsed.query)
    if "v" in qs and qs["v"]:
        return qs["v"][0]

    for pattern in _PATTERNS:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    raise ValueError(f"Could not extract a video id from URL: {url!r}")
