"""Free-text -> structured testimonial via LLM.

Takes whatever the user types (a paraphrase, a quoted message, a
description of where the testimonial came from) and asks the
framework's LLM router to extract the structured fields: author,
verbatim content, source channel, product/service, a quotable
highlight, tags, and a received date.

Failure modes are silent and friendly: a malformed JSON response, a
network error, or any other surprise yields a minimal but coherent
record (author = ``Anonymous``, content = the raw input, no tags).
The user can edit the record afterwards if needed.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from src.store_writes import today_iso

if TYPE_CHECKING:
    from memory.extensions.api import ExtensionAPI


PARSE_PROMPT_TEMPLATE = """You are a testimonial-extraction assistant.

Analyse the text below — it is an informal description of a testimonial
the user received from a customer, student, or reader. Extract
structured fields.

## Reference date
Today is {today}.

## Rules

- **author_name**: name of the person who wrote the testimonial. Use
  "Anonymous" when not mentioned.
- **content**: the testimonial itself (the customer's voice, not the
  user's description of it). Preserve the original wording.
- **source**: where the message came from (one of: whatsapp, email,
  linkedin, live, instagram, youtube, telegram, form, sms, in-person,
  other). Infer from context.
- **product**: the product or service the testimonial refers to. Free
  text from the content; use null if it cannot be inferred.
- **highlight**: the most impactful sentence from the testimonial
  (one short sentence, quotable). Extract verbatim from content; do
  not invent.
- **tags**: 2 to 5 thematic tags useful for later search (e.g.
  "clarity", "transformation", "practical", "course", "book").
- **received_at**: the date the testimonial was received in YYYY-MM-DD
  format. If the text says "today" or does not say, use {today}.

## Response format

Return ONLY a JSON object, no markdown fences, no commentary:

{{
  "author_name": "...",
  "content": "...",
  "source": "...",
  "product": "..." or null,
  "highlight": "...",
  "tags": ["...", "..."],
  "received_at": "YYYY-MM-DD"
}}

## Text

"""


def parse_testimonial(api: ExtensionAPI, text: str) -> dict:
    """Run the LLM extraction and return a dict with normalised fields.

    The dict always contains the seven documented keys; missing or
    invalid values fall back to sensible defaults. Never raises on
    LLM or JSON failures — returns a minimal record built from the
    raw text instead.
    """
    today = today_iso()
    prompt = PARSE_PROMPT_TEMPLATE.format(today=today) + text

    try:
        raw = api.llm(prompt, family="gemini", tier="flash")
    except Exception as exc:
        api.log("warning", "LLM call failed; using fallback record", error=str(exc))
        return _fallback(text, today)

    cleaned = _strip_code_fences(raw or "").strip()
    if not cleaned:
        return _fallback(text, today)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        api.log("warning", "LLM returned non-JSON; using fallback record")
        return _fallback(text, today)

    return _normalise(data, fallback_text=text, today=today)


# --- helpers --------------------------------------------------------------


def _strip_code_fences(raw: str) -> str:
    """Some models wrap JSON in ```...```; strip that politely."""
    stripped = raw.strip()
    if not stripped.startswith("```"):
        return stripped
    parts = stripped.split("\n", 1)
    body = parts[1] if len(parts) > 1 else ""
    if body.endswith("```"):
        body = body[:-3]
    return body.strip()


def _fallback(text: str, today: str) -> dict:
    return {
        "author_name": "Anonymous",
        "content": text.strip(),
        "source": None,
        "product": None,
        "highlight": None,
        "tags": [],
        "received_at": today,
    }


def _normalise(data: dict, *, fallback_text: str, today: str) -> dict:
    tags_raw = data.get("tags") or []
    if not isinstance(tags_raw, list):
        tags_raw = []
    tags = [str(t) for t in tags_raw if t]

    received = data.get("received_at") or today
    # Light validation: must look like YYYY-MM-DD.
    try:
        datetime.strptime(received, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        received = today

    return {
        "author_name": (data.get("author_name") or "Anonymous").strip(),
        "content": (data.get("content") or fallback_text).strip(),
        "source": _opt(data.get("source")),
        "product": _opt(data.get("product")),
        "highlight": _opt(data.get("highlight")),
        "tags": tags,
        "received_at": received,
    }


def _opt(value) -> str | None:
    if value is None:
        return None
    stripped = str(value).strip()
    return stripped or None
