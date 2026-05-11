-- Initial schema for the testimonials extension.
--
-- The shape is copied from the legacy `testimonials` table so a
-- legacy migration can be a pure column-for-column copy. The only
-- thing that changes is the prefix: the table moves from
-- `testimonials` to `ext_testimonials_records`.
--
-- `tags` is stored as a JSON-encoded array (text) to stay portable.
-- `embedding` is a float32 BLOB (1536 * 4 = 6144 bytes for OpenAI
-- text-embedding-3-small, the model the framework's api.embed() uses).
--
-- Every CREATE/ALTER/DROP must target tables matching
-- ext_testimonials_*.

CREATE TABLE ext_testimonials_records (
    id           TEXT PRIMARY KEY,
    author_name  TEXT NOT NULL,
    content      TEXT NOT NULL,
    source       TEXT,                -- 'whatsapp' | 'email' | 'linkedin' | 'live' | 'instagram' | 'youtube' | 'form' | 'other' | etc.
    product      TEXT,                -- free-form: the product/service the testimonial refers to
    highlight    TEXT,                -- one-sentence quotable extract
    tags         TEXT,                -- JSON array of strings
    received_at  TEXT,                -- ISO date
    created_at   TEXT NOT NULL,       -- ISO datetime
    embedding    BLOB                 -- float32 vector matching api.embed() output
);

CREATE INDEX idx_ext_testimonials_records_product
    ON ext_testimonials_records(product);

CREATE INDEX idx_ext_testimonials_records_received
    ON ext_testimonials_records(received_at);
