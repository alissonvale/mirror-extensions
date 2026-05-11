[< User Stories](README.md)

# US-04 — Migrate legacy testimonials

**Status:** ✅ Done · 2026-05-11

## Story

**As a** user who collected testimonials in an earlier mirror
implementation,
**I want** a single command to copy every legacy testimonial,
including its precomputed embedding, into this extension's schema,
**so that** my archive is available for search the moment I
install the extension.

### Acceptance value

- `python -m memory ext testimonials migrate-legacy --source <path>`
- `--dry-run` reports counts without writing.
- Idempotent: re-running imports zero rows.
- Embeddings copied verbatim (the legacy mirror used the same
  embedding model the framework's `api.embed()` uses today).

## Plan

- `src/migrate_legacy.py` opens the source database read-only via
  the SQLite URI form, validates that the `testimonials` table
  exists, then copies every row whose id is missing from
  `ext_testimonials_records` inside a single `api.transaction()`
  savepoint.
- Column-for-column copy: `id, author_name, content, source,
  product, highlight, tags, received_at, created_at, embedding`.
  No transformation, no LLM call.

## Test Guide

- Synthetic legacy fixture (5 rows, each with a 6144-byte embedding).
- Happy path: dry-run reports 5; real run imports 5; verbatim
  values; embeddings preserved (length 6144).
- Idempotent: second run imports 0, skips 5.
- Partial state: delete one row, re-run, imports 1, skips 4.
- Missing source / non-SQLite source / missing `testimonials`
  table → `LegacyMigrationError` with a clear message.
