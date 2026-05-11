# Changelog

All notable changes to this extension are documented here.

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
