-- Initial schema for the Maestro extension.
--
-- Source of truth for project coherence remains in the project itself
-- (`maestro.yml`, `docs/coherence/rules.md`, `docs/coherence/index.md`).
-- The extension database records check history and summary counts.
--
-- Every CREATE/ALTER/DROP must target tables matching ext_maestro_*.

CREATE TABLE ext_maestro_check_runs (
    id              TEXT PRIMARY KEY,
    journey_id      TEXT,
    project_root    TEXT NOT NULL,
    locale          TEXT NOT NULL,
    mode            TEXT NOT NULL,
    source          TEXT NOT NULL DEFAULT 'cli', -- 'cli' | 'mirror_mode'
    open_count      INTEGER NOT NULL DEFAULT 0,
    resolved_count  INTEGER NOT NULL DEFAULT 0,
    blocking_count  INTEGER NOT NULL DEFAULT 0,
    important_count INTEGER NOT NULL DEFAULT 0,
    optional_count  INTEGER NOT NULL DEFAULT 0,
    summary         TEXT,
    created_at      TEXT NOT NULL
);

CREATE INDEX idx_ext_maestro_check_runs_journey
    ON ext_maestro_check_runs(journey_id);

CREATE INDEX idx_ext_maestro_check_runs_project_root
    ON ext_maestro_check_runs(project_root);

CREATE INDEX idx_ext_maestro_check_runs_created_at
    ON ext_maestro_check_runs(created_at);
