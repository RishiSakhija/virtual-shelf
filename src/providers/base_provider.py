"""
Common interface every AI provider implements.

Why this exists even with only one provider wired up right now: the whole
point of "config-swappable, not hardcoded" (see docs/DECISIONS.md #7) is
that notes_generator.py should never need to know whether it's talking to
Gemini or Groq or whatever replaces either of them next year. It just
calls .generate_notes_from_video() on whatever provider config handed it.

Groq's class will implement this same interface later (docs/DECISIONS.md
#4) via a transcript-based path — same method signature, different
insides. That's the payoff of defining the interface now even though only
one class implements it today.
"""

from abc import ABC, abstractmethod


class BaseProvider(ABC):
    @abstractmethod
    def generate_notes_from_video(self, youtube_url: str) -> dict:
        """
        Returns a dict shaped like:
        {
            "title": str,
            "notes_markdown": str,
            "diagrams": [ { "title": str, "mermaid": str }, ... ]
        }
        Raises on failure — caller (notes_generator.py) decides what to do
        about it (currently: nothing, since there's no fallback wired up
        yet — see docs/DECISIONS.md #4).
        """
        raise NotImplementedError
