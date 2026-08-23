# Virtual Shelf

YouTube lectures + PDFs → structured notes with auto-generated Mermaid diagrams,
in a bookshelf UI with a handwritten-note aesthetic.

## Current stage
See `docs/ROADMAP.md`. **We are on Step 1: prove core generation.** No UI work
happens until Step 1 output is consistently good — that's a hard rule, not
a suggestion (see `docs/DECISIONS.md` #1).

## Why this structure exists
This project has a known failure mode for solo builders: you get 70% through
Step 1, get excited, jump to UI, and six weeks later you have a beautiful
bookshelf displaying mediocre notes with no clean way to fix the core
pipeline without breaking the UI. The structure below exists specifically
to prevent that. Read `docs/ROADMAP.md` before writing new code — if what
you're about to build isn't in the current step, stop.

## Quick start
```bash
cp .env.example .env        # fill in GEMINI_API_KEY and GROQ_API_KEY
pip install -r requirements.txt
python src/main.py --url "https://youtube.com/watch?v=XXXX"
```

## Directory guide
- `docs/` — read these before coding. They exist so the project doesn't stall
  when you come back to it after a few days and forget why something is
  built the way it is.
- `config/` — model/provider selection lives here, NOT hardcoded in source.
  Free-tier models get deprecated or rate-limited without notice; you should
  be able to swap `gemini-2.5-flash` → `gemini-3-flash` by editing one line.
- `src/providers/` — one class per AI backend, same interface. This is the
  part of the code most likely to need to change without notice (see
  `docs/FREE_TIER_LIMITS.md`), so it's isolated.
- `src/cache/` — content-addressed cache. Same video/PDF + same prompt
  version = never pay for generation twice.
- `cache/` — actual cached output (gitignored). Delete this folder to force
  regeneration.
