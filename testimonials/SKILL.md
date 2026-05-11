---
name: "ext-testimonials"
description: Customer testimonials with LLM-assisted structuring and semantic search.
user-invocable: true
---

# Testimonials

Stores customer testimonials with structured fields (author, source,
product, highlight, tags) and an embedding so the user can search
their archive semantically. Adding a testimonial accepts free text —
an LLM extracts the structured fields automatically.

## Commands

- `python -m memory ext testimonials add "<free text>"` — register a new
  testimonial. The text can be informal ("Pedro wrote on WhatsApp:
  '...'"); the extension calls the LLM to extract author, source,
  product, highlight, and tags.
- `python -m memory ext testimonials list [--product <p>]` — list
  registered testimonials.
- `python -m memory ext testimonials search "<query>"` — semantic
  search across the archive.
- `python -m memory ext testimonials migrate-legacy --source <path>` —
  import testimonials from a legacy mirror SQLite database that
  carries a `testimonials` table.

## When the agent should use this

User mentions a quote, a customer note, a kind message, social-media
feedback — any external positive (or negative) word about something
they made. The agent should call `add` with the user's description as
the free-text payload; the LLM extraction figures out the rest.

For lookups ("what did Maria say?", "do I have testimonials about my
course?"), prefer `search` over `list`: the embedding match handles
paraphrase and language drift better than substring filters.

## What the agent should not do

- Do not invent testimonials. If the database returns no results, say
  so; suggest the user run `add` with the source text.
- Do not paraphrase a testimonial when quoting it back to the user.
  The `highlight` field is meant to be quoted verbatim.
