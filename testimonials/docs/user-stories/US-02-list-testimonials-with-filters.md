[< User Stories](README.md)

# US-02 — List testimonials with filters

**Status:** ✅ Done · 2026-05-11

## Story

**As a** user reviewing what people have said about my work,
**I want** to list the testimonials I have on file, optionally
filtered by product, author, or source channel,
**so that** I can pull up all the testimonials about a launch, or
everything Maria has ever sent me, without writing SQL.

### Acceptance value

- `python -m memory ext testimonials list` lists every testimonial
  ordered by `received_at DESC`.
- `--product <name>` narrows to one product (case-insensitive).
- `--author <substring>` partial-matches the author name.
- `--source <channel>` narrows to one channel.

## Plan

- `src/store.py:list_testimonials` builds the SQL with optional
  WHERE clauses joined by AND.
- `src/cli/list.py` formats each row: id, author + source +
  received date, product, highlight (or a 120-char content
  preview when no highlight exists), tags.

## Test Guide

- Empty store → "(no testimonials matched)".
- Product / author / source filters narrow correctly.
- Ordering by `received_at DESC` then `created_at DESC`.
- Unknown flag → clear error.
