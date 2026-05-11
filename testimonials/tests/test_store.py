"""CRUD-level tests for testimonials store + store_writes."""

from __future__ import annotations

from src.models import encode_tags, parse_tags
from src.store import (
    all_with_embeddings,
    get_testimonial,
    list_testimonials,
)
from src.store_writes import insert_testimonial


def _insert(api, **kwargs):
    defaults = dict(
        author_name="Alice",
        content="Loved it.",
        source="email",
        product="Workshop",
        highlight="Loved it.",
        tags=["clarity", "workshop"],
        received_at="2026-05-01",
    )
    defaults.update(kwargs)
    return insert_testimonial(api, **defaults)


# --- store_writes -------------------------------------------------------


def test_insert_persists_all_columns(testimonials_api):
    tid = _insert(testimonials_api)
    row = get_testimonial(testimonials_api, tid)
    assert row is not None
    assert row.author_name == "Alice"
    assert row.content == "Loved it."
    assert row.source == "email"
    assert row.product == "Workshop"
    assert row.highlight == "Loved it."
    assert row.tags == ("clarity", "workshop")
    assert row.received_at == "2026-05-01"


def test_insert_accepts_explicit_id(testimonials_api):
    tid = _insert(testimonials_api, id="customid")
    assert tid == "customid"
    assert get_testimonial(testimonials_api, "customid") is not None


def test_insert_handles_empty_tags(testimonials_api):
    tid = _insert(testimonials_api, tags=None)
    row = get_testimonial(testimonials_api, tid)
    assert row.tags == ()


# --- list with filters --------------------------------------------------


def test_list_empty(testimonials_api):
    assert list_testimonials(testimonials_api) == []


def test_list_filters_by_product(testimonials_api):
    _insert(testimonials_api, author_name="A1", product="Book")
    _insert(testimonials_api, author_name="A2", product="Workshop")
    out = list_testimonials(testimonials_api, product="book")  # case-insensitive
    assert [t.author_name for t in out] == ["A1"]


def test_list_filters_by_author_substring(testimonials_api):
    _insert(testimonials_api, author_name="Pedro Moreira")
    _insert(testimonials_api, author_name="Henrique Bastos")
    out = list_testimonials(testimonials_api, author_like="moreira")
    assert [t.author_name for t in out] == ["Pedro Moreira"]


def test_list_filters_by_source(testimonials_api):
    _insert(testimonials_api, author_name="X", source="whatsapp")
    _insert(testimonials_api, author_name="Y", source="email")
    out = list_testimonials(testimonials_api, source="WhatsApp")
    assert [t.author_name for t in out] == ["X"]


def test_list_orders_by_received_then_created(testimonials_api):
    _insert(testimonials_api, author_name="older", received_at="2026-01-01")
    _insert(testimonials_api, author_name="newer", received_at="2026-05-01")
    out = list_testimonials(testimonials_api)
    assert [t.author_name for t in out] == ["newer", "older"]


# --- embeddings ---------------------------------------------------------


def test_all_with_embeddings_returns_only_rows_with_embedding(testimonials_api):
    _insert(testimonials_api, author_name="With", embedding=b"\x00" * 6144)
    _insert(testimonials_api, author_name="Without", embedding=None)
    out = all_with_embeddings(testimonials_api)
    assert [t.author_name for t in out] == ["With"]


# --- tags codec --------------------------------------------------------


def test_parse_tags_handles_none_and_empty():
    assert parse_tags(None) == ()
    assert parse_tags("") == ()


def test_parse_tags_decodes_json():
    assert parse_tags('["a","b"]') == ("a", "b")


def test_parse_tags_tolerates_malformed_json():
    assert parse_tags("[not, json}") == ()


def test_parse_tags_tolerates_non_list_json():
    assert parse_tags('"a string"') == ()


def test_encode_tags_round_trip():
    encoded = encode_tags(["x", "y"])
    assert parse_tags(encoded) == ("x", "y")


def test_encode_tags_empty_returns_none():
    assert encode_tags([]) is None
    assert encode_tags(None) is None
