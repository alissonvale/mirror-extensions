[< User Stories](README.md)

# US-10 — Inject financial context into Mirror Mode

**Status:** ⚪ Planned

## Story

**As a** user talking to the mirror through a financially-aware
persona (e.g. `tesoureira`),
**I want** the live state of my finances injected into the prompt
automatically,
**so that** the persona answers grounded in current numbers without
the agent having to remember to call a CLI subcommand.

The extension already declares the `financial_summary` capability in
its manifest. This story makes the provider return real text and
documents the binding workflow end to end.

### Acceptance value

- `python -m memory ext finances bind financial_summary --persona tesoureira`
- A Mirror Mode turn with `tesoureira` active includes
  `=== extension/finances/financial_summary ===` followed by the live
  summary: liquid / semi-liquid totals, monthly cash flow rows, burn,
  runway.
- The provider returns `None` when the database is empty so the prompt
  is not polluted by an empty section.
- The summary respects the persona briefing's voice and concision —
  short tables, no prose.

## Plan

- `src/reports.py`: `financial_context_text() -> str | None`
  composes the same numbers as `runway` + monthly summary, formatted
  as a tight markdown block.
- `extension.py`: `_provide_financial_summary` calls
  `financial_context_text()`.
- `docs/persona-recipes.md`: documents the recommended briefing for a
  `tesoureira` persona and the bind command.

## Test Guide

- With seeded fixture data, the provider returns a non-empty string
  containing each section header (liquid, semi-liquid, monthly flow,
  burn, runway).
- With an empty database, the provider returns `None`.
- Binding to a persona makes the section appear in
  `IdentityService.load_mirror_context(persona=...)` output.
- Unbinding removes the section.
- A broken downstream (e.g. inconsistent snapshot) does not raise; the
  provider catches and returns `None` with a logged warning, per the
  extension contract.
