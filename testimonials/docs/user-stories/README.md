[< testimonials](../../README.md)

# User stories

The user stories that drove the construction of the testimonials
extension.

## Order

US-04 (migrate) shipped first so the schema was validated against
production-shape data with real embeddings before any other feature.
Then the read paths (US-02, US-03), then the write path (US-01) which
depends on the LLM.

| # | Story | Status |
|---|-------|--------|
| US-01 | [Register testimonial from free text](US-01-register-testimonial-from-free-text.md) | ✅ Done |
| US-02 | [List testimonials with filters](US-02-list-testimonials-with-filters.md) | ✅ Done |
| US-03 | [Search testimonials by similarity](US-03-search-testimonials-by-similarity.md) | ✅ Done |
| US-04 | [Migrate legacy testimonials](US-04-migrate-legacy-testimonials.md) | ✅ Done |
| US-05 | [Mirror Mode capability `recent_testimonials`](US-05-mirror-mode-capability.md) | ✅ Done |
