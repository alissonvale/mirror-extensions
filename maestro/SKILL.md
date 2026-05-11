---
name: "ext-maestro"
description: Coherence engine for Mirror-native project journeys.
user-invocable: true
---

# /mm-maestro

Operate the Maestro coherence layer for the active journey project.

## Purpose

Maestro keeps project coherence visible before implementation work. The hello-world lens checks two base Units of Coherence (UoCs):

- `project.working_name` — every Maestro project has a provisional working name (blocking)
- `project.git_repository` — every Maestro project should be tracked in git (important)

The source of truth lives in the project:

- `maestro.yml`
- `docs/coherence/rules.md`
- `docs/coherence/index.md`

The extension records check summaries in `ext_maestro_check_runs`.

## Journey/project mapping

Maestro uses two independent links:

1. `journey -> project_path`: which folder represents the journey.
2. `maestro/coherence_status -> journey/<id>`: which journey receives automatic coherence context in Mirror Mode.

Current mappings:

```text
journey/maestro          -> ~/Code/mirror-extensions/maestro
journey/sandbox-pet-food -> ~/Code/sandbox-pet-food
```

The installed runtime is separate:

```text
~/.mirror/<user>/extensions/maestro
```

Do not confuse runtime copy with source code or target project.

## Commands

```bash
uv run python -m memory ext maestro check --journey maestro
uv run python -m memory ext maestro configure --journey maestro --locale pt-BR --mode technical
uv run python -m memory ext maestro init --journey maestro --name "Maestro"
```

If working outside a journey, pass `--root`:

```bash
uv run python -m memory ext maestro check --root /path/to/project
```

## Mirror Mode binding

Bind the capability to any journey that should receive automatic coherence status:

```bash
uv run python -m memory ext maestro bind coherence_status --journey maestro
uv run python -m memory ext maestro bind coherence_status --journey sandbox-pet-food
```

The provider always injects when the active journey is bound and the project path is configured. It never raises into Mirror Mode; failures return no block and are logged.

## Docs

Detailed docs live in:

- `docs/architecture.md`
- `docs/bindings.md`
- `docs/commands.md`

## Operating protocol

When the user asks for Maestro work:

1. Run `check` for the active journey.
2. If a blocking UoC is open, surface it before implementation work.
3. Treat gaps as requests for judgment, not automatic errors.
4. Do not edit `AGENTS.md` yet. That contract is intentionally left open.
5. When a UoC changes, let the command update `docs/coherence/index.md`.
