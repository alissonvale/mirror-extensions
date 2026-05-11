[< User Stories](README.md)

# US-01 — Register testimonial from free text

**Status:** ✅ Done · 2026-05-11

## Story

**As a** user who receives praise (or feedback) from customers
through informal channels (WhatsApp, email, social media),
**I want** to add a testimonial by pasting whatever I wrote in my
notes about it,
**so that** the structured fields (author, source, product,
highlight, tags) are extracted automatically and the testimonial is
indexed for semantic search later.

### Acceptance value

- `python -m memory ext testimonials add "Pedro on WhatsApp: 'Loved
  the workshop, learned a lot.'"` produces a single row with the
  author (`Pedro`), the verbatim content (`Loved the workshop,
  learned a lot.`), the source (`whatsapp`), an inferred highlight,
  2–5 tags, and an embedding ready for search.

## Plan

- `src/parse.py` calls `api.llm()` with a strict JSON-only prompt;
  any failure (network, garbage output, parse error) yields a
  minimal but coherent fallback record (author = "Anonymous",
  content = raw input, no tags, today as the received date).
- `src/cli/add.py` calls `parse_testimonial`, then `api.embed()` on
  the verbatim content, then `insert_testimonial`. Embedding failure
  is non-fatal: the record is saved without an embedding and a
  warning prints.
- The CLI prints the parsed fields back so the user can spot a bad
  extraction immediately.

## Test Guide

- LLM returns well-formed JSON → fields land exactly.
- LLM wraps the JSON in ``` fences → fences stripped.
- LLM returns garbage → fallback record built from raw text.
- LLM raises → same fallback path, warning logged.
- `received_at` invalid → falls back to today.
- `tags` not a list → empty list.
- Empty string fields normalised to `None`.
