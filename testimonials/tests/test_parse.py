"""Tests for the LLM-driven parse_testimonial (US-01 internals)."""

from __future__ import annotations

import json

from src.parse import parse_testimonial


class _StubAPI:
    """Minimal stand-in for ExtensionAPI in unit tests.

    Only `llm` and `log` are exercised by parse_testimonial; we
    monkey-patch the LLM response per test.
    """

    def __init__(self, response: str | Exception):
        self._response = response
        self.logs: list[tuple[str, str, dict]] = []

    def llm(self, prompt: str, **kwargs) -> str:
        if isinstance(self._response, Exception):
            raise self._response
        return self._response

    def log(self, level: str, msg: str, **fields) -> None:
        self.logs.append((level, msg, fields))


def test_parse_with_well_formed_json():
    payload = {
        "author_name": "Maria",
        "content": "This changed my year.",
        "source": "email",
        "product": "Course",
        "highlight": "This changed my year",
        "tags": ["transformation", "course"],
        "received_at": "2026-04-20",
    }
    api = _StubAPI(json.dumps(payload))
    out = parse_testimonial(api, "Maria wrote: 'This changed my year.'")
    assert out == {
        "author_name": "Maria",
        "content": "This changed my year.",
        "source": "email",
        "product": "Course",
        "highlight": "This changed my year",
        "tags": ["transformation", "course"],
        "received_at": "2026-04-20",
    }


def test_parse_strips_code_fences():
    payload = {
        "author_name": "Pedro",
        "content": "Loved it.",
        "source": "whatsapp",
        "product": None,
        "highlight": "Loved it.",
        "tags": ["clarity"],
        "received_at": "2026-05-10",
    }
    fenced = "```json\n" + json.dumps(payload) + "\n```"
    api = _StubAPI(fenced)
    out = parse_testimonial(api, "Pedro on WhatsApp: 'Loved it.'")
    assert out["author_name"] == "Pedro"
    assert out["source"] == "whatsapp"
    assert out["highlight"] == "Loved it."


def test_parse_falls_back_when_llm_returns_garbage():
    api = _StubAPI("not json at all")
    out = parse_testimonial(api, "Some raw text from the user")
    assert out["author_name"] == "Anonymous"
    assert out["content"] == "Some raw text from the user"
    assert out["tags"] == []
    assert out["source"] is None
    # A warning was logged.
    assert any("non-JSON" in msg for _, msg, _ in api.logs)


def test_parse_falls_back_when_llm_raises():
    api = _StubAPI(RuntimeError("network down"))
    out = parse_testimonial(api, "fallback content")
    assert out["author_name"] == "Anonymous"
    assert out["content"] == "fallback content"
    assert any("LLM call failed" in msg for _, msg, _ in api.logs)


def test_parse_normalises_invalid_date():
    payload = {
        "author_name": "X",
        "content": "y",
        "received_at": "not-a-date",
    }
    api = _StubAPI(json.dumps(payload))
    out = parse_testimonial(api, "raw")
    # received_at falls back to today (a valid ISO YYYY-MM-DD), not the invalid value.
    assert out["received_at"] != "not-a-date"
    assert len(out["received_at"]) == 10
    assert out["received_at"][4] == "-" and out["received_at"][7] == "-"


def test_parse_normalises_non_list_tags():
    payload = {"author_name": "X", "content": "y", "tags": "should-be-a-list"}
    api = _StubAPI(json.dumps(payload))
    out = parse_testimonial(api, "raw")
    assert out["tags"] == []


def test_parse_normalises_empty_strings_to_none():
    payload = {
        "author_name": "X",
        "content": "y",
        "source": "  ",
        "product": "",
        "highlight": "",
    }
    api = _StubAPI(json.dumps(payload))
    out = parse_testimonial(api, "raw")
    assert out["source"] is None
    assert out["product"] is None
    assert out["highlight"] is None
