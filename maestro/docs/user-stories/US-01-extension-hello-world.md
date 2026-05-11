# US-01 — Maestro extension hello world

## Goal

Port the original standalone Maestro POC into a Mirror-native extension while preserving the essential experience: before building, the Mirror can inspect the active journey project and surface its coherence status.

## Scope

- Use journey `maestro` as the first dogfood target.
- Resolve project root from `identity(layer='journey', key='maestro').metadata.project_path`.
- Keep canonical coherence state in the target project:
  - `maestro.yml`
  - `docs/coherence/rules.md`
  - `docs/coherence/index.md`
- Store check history in `ext_maestro_check_runs`.
- Provide one Mirror Mode capability: `coherence_status`, bound to a journey.
- Do not edit `AGENTS.md` automatically.

## UoCs in the hello-world lens

| ID | Semantic ID | Severity | Expected state |
|---|---|---|---|
| UoC-001 | `project.working_name` | blocking | Every Maestro project has a provisional working name. |
| UoC-002 | `project.git_repository` | important | Every Maestro project should be tracked in git. |

## Commands

```bash
uv run python -m memory ext maestro configure --journey maestro --locale pt-BR --mode technical
uv run python -m memory ext maestro init --journey maestro --name "Maestro"
uv run python -m memory ext maestro check --journey maestro
```

## Mirror Mode binding

```bash
uv run python -m memory ext maestro bind coherence_status --journey maestro
```

## Acceptance criteria

- Empty project reports UoC-001 as open/blocking and UoC-002 as open/important.
- `init --name` resolves UoC-001 and writes project-local docs.
- Creating `.git/` resolves UoC-002.
- `configure --locale pt-BR --mode non-technical` changes the human surface without changing semantic IDs.
- `check` records one row in `ext_maestro_check_runs`.
- `coherence_status` always injects a block for a configured journey and returns `None` on internal errors.
