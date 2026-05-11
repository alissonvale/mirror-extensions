[< User Stories](README.md)

# US-03 — Search testimonials by similarity

**Status:** ✅ Done · 2026-05-11

## Story

**As a** user looking for what someone said about a specific topic,
**I want** to search across my testimonials with natural language,
**so that** paraphrase and language drift do not hide a relevant
testimonial behind an unhelpful substring match.

### Acceptance value

- `python -m memory ext testimonials search "loved the workshop"`
  ranks every testimonial that has an embedding by cosine similarity
  to the query and returns the top 5 by default.
- `--limit <N>` adjusts the cutoff.
- Empty store → friendly hint pointing at `add` or `migrate-legacy`.

## Plan

- `src/search.py:search_testimonials` calls `api.embed(query)`,
  reads every row with a non-null embedding, computes cosine
  similarity, sorts descending, returns top N.
- `cosine_similarity(a, b)` defensively returns 0.0 on empty bytes,
  zero norm, or dimensionality mismatch.

## Test Guide

- Identical vectors → 1.0.
- Orthogonal high-dim vectors → near zero.
- Empty / mismatched bytes → 0.0.
- Ranking order: higher-similarity rows come first.
- `--limit` respected.
- Rows without embedding are skipped.
- Empty store → friendly message.

## Notes on embedding compatibility

The framework's `api.embed()` uses OpenAI `text-embedding-3-small`,
the same model the legacy mirror used. Embeddings migrated under
US-04 are directly searchable with no re-computation.
