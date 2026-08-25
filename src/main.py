"""
Step 1 CLI: YouTube URL -> structured notes + Mermaid diagrams.

Deliberately raw output at this stage (docs/ROADMAP.md — no styling until
Step 2). This script's only job is proving generation quality: run it on
real lecture videos and actually read the output critically before
writing any more code.
"""

import argparse
import json
import sys
import textwrap
from pathlib import Path

import yaml
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generation.notes_generator import NotesGenerator
from render.notes_renderer import render_notes_html
from utils.youtube import extract_video_id

_WRAP_WIDTH = 78


def _wrap(text: str, indent: str = "    ") -> str:
    """Wrap long lines to _WRAP_WIDTH so terminal output stays readable
    instead of one giant unbroken line per field."""
    return textwrap.fill(
        text, width=_WRAP_WIDTH, initial_indent=indent, subsequent_indent=indent
    )


def print_notes(result: dict) -> None:
    """Render the concept-card JSON as readable console text.

    This is presentation-only — it doesn't touch the underlying data
    shape (still concept cards + diagrams). Per docs/ROADMAP.md this is
    as far as "styling" goes at Step 1: readable terminal output, not a
    rendered UI. Step 2 is where actual visual/handwriting rendering
    happens.
    """
    title = result["title"]
    print("\n" + "=" * _WRAP_WIDTH)
    print(title.center(_WRAP_WIDTH))
    print("=" * _WRAP_WIDTH)
    print("\n" + _wrap(result["overview"], indent="") + "\n")

    for i, c in enumerate(result["concepts"], 1):
        print("-" * _WRAP_WIDTH)
        print(f"{i}. {c['name']}")
        print("-" * _WRAP_WIDTH)

        print("\nWhat it is:")
        print(_wrap(c["what_it_is"]))

        print("\nHow it works:")
        print(_wrap(c["how_it_works"]))

        if c.get("syntax"):
            print("\nSyntax / usage:")
            for line in c["syntax"].splitlines():
                print(f"    {line}")

        print("\nKey points:")
        for kp in c["key_points"]:
            print(_wrap(f"- {kp}"))

        print("\nWhen to use:")
        print(_wrap(c["when_to_use"]))
        print()

    print("=" * _WRAP_WIDTH)
    print("DIAGRAMS".center(_WRAP_WIDTH))
    print("=" * _WRAP_WIDTH)
    for i, diagram in enumerate(result["diagrams"], 1):
        print(f"\n[{i}] {diagram['title']}")
        print("```mermaid")
        print(diagram["mermaid"])
        print("```")


def load_config(path: str = "config/config.yaml") -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="Virtual Shelf — Step 1: video to notes")
    parser.add_argument("--url", required=True, help="YouTube lecture URL")
    parser.add_argument(
        "--force", action="store_true", help="Bypass cache, force regeneration"
    )
    args = parser.parse_args()

    config = load_config()
    generator = NotesGenerator(config)

    result = generator.generate_from_url(args.url, force=args.force)

    print_notes(result)

    # Also dump raw JSON to a file so you can inspect exact structure —
    # useful when judging "is this diagram actually specific to the
    # content" per the Step 1 done-condition in docs/ROADMAP.md.
    out_path = Path("cache") / "last_run.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(f"\n(full JSON also written to {out_path})")

    # Render to a PREDICTABLE path keyed by video_id, not the ad-hoc
    # filename notes_renderer.py takes when run standalone. This is what
    # lets Step 3's bookshelf link to a book without guessing a filename —
    # every video's rendered page always lives at the same place.
    video_id = extract_video_id(args.url)
    notes_dir = Path("output") / "notes"
    notes_dir.mkdir(parents=True, exist_ok=True)
    note_path = notes_dir / f"{video_id}.html"
    with open(note_path, "w", encoding="utf-8") as f:
        f.write(render_notes_html(result))
    print(f"(rendered note -> {note_path})")


if __name__ == "__main__":
    main()