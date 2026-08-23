# Roadmap (build order — do not reorder)

This mirrors the build order you set. Each step has an explicit "done"
condition. Don't start a step until the previous one's condition is met.

## Step 1 — Prove core generation (CURRENT STEP)
Input: one YouTube URL, or one PDF.
Output: structured notes (raw markdown/JSON, no styling) + at least one
Mermaid diagram that's actually accurate to the content, not generic filler.

**Done when:** you've run this on 5+ real lecture videos across different
subjects and the diagrams are consistently *specific* to the content (not
"here's a generic flowchart of steps"), without hand-editing prompts per video.

**Explicitly NOT part of this step:** any rendering, fonts, UI, book covers.
If you catch yourself styling markdown output, stop — that's Step 2.

## Step 2 — Handwriting-style rendering
Take the raw notes from Step 1 and render them in a handwritten aesthetic
(font choice, layout, ink-like diagram styling).

**Done when:** a generated note from Step 1 renders legibly and consistently
without per-note manual tweaking.

## Step 3 — Bookshelf UI
Grid of book covers → click → rendered notes from Step 2.

**Explicitly depends on Step 1+2 being solid.** A nice shelf holding weak
notes is not progress — building this early just gives you a prettier way
to notice the generation quality is bad.

## Step 4 — Editable text layer + PDF export
Let users edit rendered notes and export to PDF.

---

## Known bottleneck to plan around (not a "later" problem)
Free-tier rate limits on both providers will genuinely constrain how many
videos/PDFs you can process per day during development and real usage.
See `docs/FREE_TIER_LIMITS.md`. This is why caching is built in from day
one, not added later — without it you'll burn a meaningful chunk of your
daily quota just re-testing prompts on the same video.
