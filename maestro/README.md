# Maestro Extension

Maestro is a Mirror-native coherence engine for project journeys.

This hello-world extension ports the original TypeScript POC into the Mirror extension system. It keeps the project-local source of truth (`maestro.yml`, `docs/coherence/rules.md`, `docs/coherence/index.md`) while using Mirror's stateful extension infrastructure for CLI commands, check history, and Mirror Mode context injection.

## Capabilities

- CLI:
  - `check`
  - `init --name`
  - `configure --locale --mode`
- Mirror Mode:
  - `coherence_status`, intended to bind to journeys
- Storage:
  - `ext_maestro_check_runs`

## Current shape

```text
journey/maestro
  -> ~/Code/mirror-extensions/maestro
  -> source-code development of this extension

journey/sandbox-pet-food
  -> ~/Code/sandbox-pet-food
  -> example online pet food store built using Maestro

~/.mirror/<user>/extensions/maestro
  -> installed runtime loaded by Pi/Mirror
```

## Install

From the Mirror Mind checkout:

```bash
uv run python -m memory extensions install maestro \
  --extensions-root ~/Code/mirror-extensions
```

## Quick setup for a journey

```bash
uv run python -m memory journey set-path sandbox-pet-food ~/Code/sandbox-pet-food
uv run python -m memory ext maestro bind coherence_status --journey sandbox-pet-food
uv run python -m memory ext maestro configure --journey sandbox-pet-food --locale pt-BR --mode technical
uv run python -m memory ext maestro init --journey sandbox-pet-food --name "Sandbox"
uv run python -m memory ext maestro check --journey sandbox-pet-food
```

## Documentation

- [Architecture](docs/architecture.md) — source/runtime/target project separation and data flow.
- [Bindings](docs/bindings.md) — journey `project_path` vs extension capability binding.
- [Commands](docs/commands.md) — operational command reference.
- [User Stories](docs/user-stories/) — implementation story trail.

## Design stance

- The canonical coherence state lives in the target project.
- Mirror's database stores history and makes context injectable.
- Bindings are journey-first; personas will be orchestrated later by Maestro itself.
- `AGENTS.md` is not touched automatically in this slice.
