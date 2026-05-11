# Changelog

All notable changes to this extension are documented here.

## [0.2.0] — 2026-05-11

Fifth user story shipped.

### Added
- `recent_testimonials` Mirror Mode capability. Query-driven: only
  injects a block when the user query semantically matches at least
  one stored testimonial above a relevance floor (default 0.30),
  capped at 3 hits. Bind with
  `python -m memory ext testimonials bind recent_testimonials --persona <id>`.
- `docs/bindings.md` documents recommended bindings and tuning.

## [0.1.0] — 2026-05-11

First versioned release. Four user stories shipped.

### Added
- `ext_testimonials_records` schema.
- `add` subcommand: free-text input, LLM-extracted fields, embedded
  for search.
- `list` subcommand: filter by product / author / source.
- `search` subcommand: cosine similarity over embeddings.
- `migrate-legacy` subcommand: copy from a legacy mirror SQLite
  database with embeddings preserved.
