# Free tier limits — read this before assuming quota

Checked: August 2026. **These numbers move often on both providers — sources
disagreed with each other even within the same month searching this.
Treat everything here as "last known," not gospel. Before relying on a
number for real planning, check:**
- Gemini: https://ai.google.dev/gemini-api/docs/rate-limits (your actual
  project limits are also visible in Google AI Studio)
- Groq: https://console.groq.com/docs/rate-limits (limits shown in your
  console dashboard are authoritative, docs pages lag)

## Gemini API (Flash / Flash-Lite, free tier)
As of mid-2026, published free-tier limits for Flash-class models cluster
around **~10-15 requests/minute and ~1,000-1,500 requests/day**, shared
per Google *project* (not per API key — multiple keys don't multiply this).
Flash-Lite generally gets a somewhat higher RPM than Flash.

**Real-world translation for this project:** at 1 lecture video = 1 request,
you can realistically process on the order of low hundreds of videos/day
before hitting RPD — assuming zero retries. The RPM cap (10-15/min) matters
more during *development*, when you're re-running the same prompt in a
tight loop: this is the actual reason caching had to be load-bearing from
day one, not the daily cap.

**Known trade-off:** free-tier Gemini usage may be used by Google to
improve their products (unlike paid tier). Worth knowing if you ever
process anything sensitive.

## Groq API (llama-3.1-8b-instant, free tier)
Published limits cluster around **~30 requests/minute, and daily limits
reported anywhere from ~1,000 to ~14,400/day depending on source and
date** — this model in particular is described as the most generous on
Groq's free tier. Not currently wired into this project (see DECISIONS.md
#4), so not yet a live constraint — revisit these numbers when it is.

## Bottleneck to actually plan around
For v1 (video-only, Gemini-only), the binding constraint during
**development** is Gemini's RPM, not RPD — you will hit it if you
loop-test prompt changes without caching. During any real usage with
more than a handful of users, RPD becomes the ceiling first. Neither
requires a credit card to observe directly — check your Google AI Studio
dashboard for your project's actual current numbers rather than trusting
this file once it's more than a month or two old.
