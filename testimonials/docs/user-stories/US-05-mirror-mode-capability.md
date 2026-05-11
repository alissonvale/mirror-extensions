[< User Stories](README.md)

# US-05 — Mirror Mode capability `recent_testimonials`

**Status:** ✅ Done · 2026-05-11

## Story

**As a** user reflecting on copy, a launch, or how to talk about my
work in a piece of writing,
**I want** the mirror to automatically surface a few testimonials
that match what I am currently discussing,
**so that** I can speak with the customer's voice in mind without
having to pause and run a search myself.

### Acceptance value

- Binding the `recent_testimonials` capability to a persona (e.g.
  `escritora`, `divulgadora`, `editor`) causes the persona to receive
  a compact testimonials block in every Mirror Mode turn where the
  user query matches at least one stored testimonial above a
  relevance floor.
- Without a query, or with no relevant matches, the block does not
  appear — Mirror Mode stays clean.
- Any internal failure is isolated; Mirror Mode never breaks because
  of a testimonials hiccup.

## Plan

- `src/context.py:provide_recent_testimonials(api, ctx)` is the
  context provider. It calls `search_testimonials` with `ctx.query`
  and filters by a `RELEVANCE_FLOOR` (default 0.30). The block lists
  at most `MAX_HITS` (default 3) testimonials, formatted as a tiny
  markdown bullet list with author, product (if known), score, and
  the verbatim highlight (falling back to a trimmed content preview).
- `extension.py` registers the provider via
  `api.register_mirror_context("recent_testimonials", ...)`.
- All exceptions inside the composer are caught and logged; the
  provider returns `None` rather than letting the exception
  propagate, so the framework's context dispatcher records a clean
  skip.

## Test Guide

- **Happy path:** seed two testimonials, ask the most relevant query
  → block contains the matching author and the section title.
- **Cap:** seeding more than `MAX_HITS` testimonials all matching the
  query produces a block with exactly `MAX_HITS` bullets.
- **No query:** empty, missing, or whitespace-only `ctx.query` →
  `None`.
- **Empty archive:** with no testimonials in the DB → `None`.
- **Below floor:** queries with no semantic overlap to any stored
  content → `None`.
- **Robustness:** when `search_testimonials` raises, the provider
  returns `None` and logs a warning; Mirror Mode is not affected.
- **Highlight vs content:** the block prefers `highlight`; falls
  back to a trimmed content preview when no highlight exists.
- **Floor sanity:** the configured `RELEVANCE_FLOOR` stays within a
  conservative range (0.2–0.5).

## Notes

The provider is **query-driven**, not time-driven. A "show recent
testimonials always" variant was considered and rejected: with a
small archive (5 testimonials in production at the time of writing)
that approach would inject the same block on every turn of the
bound persona, regardless of topic, which is exactly the noise the
framework's binding model is meant to avoid.

If a user later decides the always-on variant is useful in a
specific persona (e.g. a dedicated "social-proof" lens), it can be
added as a second capability without changing this one.
