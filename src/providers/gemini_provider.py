"""
Gemini provider: the actual "watch the video" integration.

How this differs from a normal text-prompt API call, and why that matters:
instead of sending Gemini a transcript, we send it a `file_data` Part
pointing at the YouTube URL itself. Gemini fetches and watches the video
directly — meaning it can see slides, on-screen equations, diagrams, code
shown in the video, not just what was said aloud. That visual access is
the entire reason this project exists instead of being "run Whisper +
GPT on a transcript" (see docs/DECISIONS.md #2).

The API surface for this (model names, video-duration limits, exact
request shape) has already shifted more than once across 2026 point
releases — check https://ai.google.dev/gemini-api/docs/video-understanding
if this stops working; don't assume this code is permanently correct.

Why we ask for strict JSON back instead of parsing markdown: see
docs/DECISIONS.md #5. Free-form output means writing a fragile parser for
"find the mermaid code fences, find the headings." Asking the model to
return `{title, notes_markdown, diagrams: [...]}` and running
json.loads() on it is a much smaller, more reliable surface — the
trade-off is a slightly more constrained prompt and the small chance the
model wraps the JSON in markdown fences anyway (handled below).
"""

import json
import os
import time

from google import genai
from google.genai import errors, types

from .base_provider import BaseProvider

# Retry config for transient server-side failures (503 UNAVAILABLE is
# Google's servers being overloaded, not a bug in our code or request).
# Exponential backoff: wait longer each retry so we're not hammering an
# already-overloaded server. Capped at a few attempts — if it's still
# failing after this, something else is likely wrong and we should
# surface the error rather than retry forever.
_MAX_RETRIES = 4
_BASE_DELAY_SECONDS = 5


def _call_with_retry(fn, *args, **kwargs):
    """Call fn(*args, **kwargs), retrying on transient 503s with
    exponential backoff. Re-raises immediately on anything else (e.g.
    401 auth errors, 400 bad request) since retrying those just wastes
    time — they won't fix themselves."""
    last_error = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            return fn(*args, **kwargs)
        except errors.ServerError as e:
            last_error = e
            if attempt == _MAX_RETRIES:
                break
            delay = _BASE_DELAY_SECONDS * (2 ** (attempt - 1))
            print(
                f"  [retry] Gemini server error (attempt {attempt}/{_MAX_RETRIES}), "
                f"waiting {delay}s before retrying: {e}"
            )
            time.sleep(delay)
    raise RuntimeError(
        f"Gemini API still unavailable after {_MAX_RETRIES} attempts. "
        f"This is Google's servers being overloaded, not your code — "
        f"try again in a few minutes. Last error: {last_error}"
    ) from last_error

_PROMPT_TEMPLATE = """\
Watch this lecture video and produce study notes as a set of CONCEPT
CARDS — one card per distinct concept/tool/technique actually taught.

Return ONLY valid JSON (no markdown code fences, no commentary before or
after) matching exactly this shape:

{{
  "title": "<short descriptive title for this lecture>",
  "overview": "<1-2 sentences of context for the whole lecture — what is it about, at a glance>",
  "concepts": [
    {{
      "name": "<name of this specific concept/function/technique>",
      "what_it_is": "<1-2 sentence plain definition>",
      "how_it_works": "<brief explanation of the mechanism — how it actually does what it does>",
      "syntax": "<code snippet or usage pattern shown in the video. Empty string if this concept has no code/syntax (e.g. a purely theoretical idea)>",
      "key_points": ["<2-3 short bullets — the things worth remembering, not a restatement of what_it_is>"],
      "when_to_use": "<when/where you'd actually reach for this>"
    }}
  ],
  "diagrams": [
    {{
      "title": "<what this diagram shows>",
      "mermaid": "<valid Mermaid syntax — must be SPECIFIC to concepts actually taught in this video, not a generic placeholder diagram>"
    }}
  ]
}}

STRICT rules — these exist to keep notes usable for later review, not
just a summary of the video:
- Only include a concept card for something SUBSTANTIVELY taught with
  explanation — not every word mentioned in passing.
- Do NOT create a card for: video intros/outros, the presenter's asides,
  jokes, channel promotion, "in this video we will cover..." framing,
  or anything not actually explained.
- If a concept has no real syntax/code (e.g. a conceptual idea, not a
  tool), set "syntax" to an empty string rather than inventing one.
- key_points must be genuinely distinct from what_it_is — don't just
  reword the definition three times.
- If on-screen slides, equations, or diagrams appear in the video, use
  them — don't rely only on narration.
- At least one diagram is required, based on an actual process,
  relationship, or structure taught in the video.
"""


def _strip_code_fences(text: str) -> str:
    """Models sometimes wrap JSON in ```json ... ``` despite instructions
    not to. Strip that defensively rather than failing on it."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
    return text.strip()


class GeminiProvider(BaseProvider):
    def __init__(self, model: str, api_key: str | None = None):
        self.model = model
        api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY not set. Copy .env.example to .env and fill it in."
            )
        self.client = genai.Client(api_key=api_key)

    def generate_notes_from_video(self, youtube_url: str) -> dict:
        contents = types.Content(
            parts=[
                types.Part(file_data=types.FileData(file_uri=youtube_url)),
                types.Part(text=_PROMPT_TEMPLATE),
            ]
        )

        response = _call_with_retry(
            self.client.models.generate_content,
            model=self.model,
            contents=contents,
        )

        raw_text = response.text
        cleaned = _strip_code_fences(raw_text)

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as e:
            # One retry with an explicit "fix your JSON" nudge, rather
            # than failing the whole request over a formatting slip.
            retry_prompt = (
                "Your previous response was not valid JSON. Return ONLY "
                "the corrected valid JSON object, nothing else.\n\n"
                f"Previous response:\n{raw_text}"
            )
            retry_response = _call_with_retry(
                self.client.models.generate_content,
                model=self.model,
                contents=retry_prompt,
            )
            cleaned_retry = _strip_code_fences(retry_response.text)
            try:
                data = json.loads(cleaned_retry)
            except json.JSONDecodeError:
                raise RuntimeError(
                    f"Gemini did not return valid JSON after retry. "
                    f"Last raw output:\n{retry_response.text}"
                ) from e

        # Minimal shape validation — fail loudly now rather than let a
        # malformed dict surface as a confusing bug three files away.
        for key in ("title", "overview", "concepts", "diagrams"):
            if key not in data:
                raise RuntimeError(f"Gemini response missing required key: {key!r}")

        return data