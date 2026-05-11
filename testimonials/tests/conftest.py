"""Shared fixtures for the testimonials extension test suite."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import numpy as np
import pytest

_EXTENSION_ROOT = Path(__file__).resolve().parents[1]
if str(_EXTENSION_ROOT) not in sys.path:
    sys.path.insert(0, str(_EXTENSION_ROOT))

from memory.db.schema import SCHEMA  # noqa: E402
from memory.extensions.api import ExtensionAPI  # noqa: E402
from memory.extensions.migrations import run_migrations  # noqa: E402

MIGRATIONS_DIR = _EXTENSION_ROOT / "migrations"
FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def testimonials_api():
    """Real ExtensionAPI on an in-memory mirror database.

    The framework's core schema is bootstrapped (so _ext_migrations and
    _ext_bindings exist), then this extension's migrations apply.
    """
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA)
    run_migrations(conn, extension_id="testimonials", migrations_dir=MIGRATIONS_DIR)
    yield ExtensionAPI(extension_id="testimonials", connection=conn)
    conn.close()


@pytest.fixture
def deterministic_embedder(monkeypatch):
    """Make api.embed() return a deterministic vector based on text hash.

    Used by every test that exercises the embedding path. We patch
    the underlying generate_embedding so callers do not need to inject
    embed_fn at construction time.
    """

    def fake_generate(text: str):
        # 1536 float32, derived from text bytes so two equal strings
        # round-trip to the same vector. Normalised so cosine values
        # land in a predictable range.
        seed = abs(hash(text)) % (2**31)
        rng = np.random.default_rng(seed)
        vec = rng.standard_normal(1536, dtype=np.float32)
        norm = np.linalg.norm(vec)
        return vec / norm if norm > 0 else vec

    monkeypatch.setattr("memory.intelligence.embeddings.generate_embedding", fake_generate)
    return fake_generate


@pytest.fixture
def legacy_db(tmp_path):
    """Build a small legacy mirror database with five sample testimonials,
    each with a real-shaped 6144-byte float32 embedding."""
    target = tmp_path / "legacy.sqlite3"
    conn = sqlite3.connect(str(target))
    try:
        conn.executescript(
            """
            CREATE TABLE testimonials (
                id TEXT PRIMARY KEY,
                author_name TEXT NOT NULL,
                content TEXT NOT NULL,
                source TEXT,
                product TEXT,
                highlight TEXT,
                tags TEXT,
                received_at TEXT,
                created_at TEXT NOT NULL,
                embedding BLOB
            );
            """
        )
        rng = np.random.default_rng(42)
        for idx, (author, content, source, product, highlight, tags) in enumerate(
            [
                (
                    "Alice",
                    "Loved the workshop, learned a lot.",
                    "email",
                    "Workshop",
                    "Loved the workshop",
                    '["workshop","clarity"]',
                ),
                (
                    "Bob",
                    "Best book I read this year.",
                    "whatsapp",
                    "Book",
                    "Best book I read this year",
                    '["book","recommendation"]',
                ),
                (
                    "Cara",
                    "Your course changed my career.",
                    "linkedin",
                    "Course",
                    "changed my career",
                    '["course","transformation"]',
                ),
                (
                    "Dani",
                    "The youtube videos are great.",
                    "youtube",
                    "YouTube",
                    None,
                    '["youtube","content"]',
                ),
                (
                    "Eric",
                    "Thanks for the mentorship session.",
                    "email",
                    "Mentorship",
                    "Thanks for the mentorship",
                    '["mentorship"]',
                ),
            ],
            start=1,
        ):
            vec = rng.standard_normal(1536, dtype=np.float32)
            blob = vec.tobytes()
            conn.execute(
                "INSERT INTO testimonials VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    f"leg0000{idx}",
                    author,
                    content,
                    source,
                    product,
                    highlight,
                    tags,
                    "2026-01-15",
                    "2026-01-15T00:00:00Z",
                    blob,
                ),
            )
        conn.commit()
    finally:
        conn.close()
    return target
