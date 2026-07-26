# Contributing to ShadowForge

Thanks for your interest in ShadowForge. This document explains how to set up a
development environment, run the test suite, and how the project is organized.

## Development setup

```bash
git clone https://github.com/shadowforge/shadowforge.git
cd shadowforge
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Running tests

```bash
pytest
```

All pull requests must pass the full test suite. New features require tests.

## Code style

- Python 3.12+, fully typed public APIs.
- `ruff` for linting, `mypy --strict` for type checking:

```bash
ruff check src tests
mypy src/shadowforge
```

- Keep modules small and focused. One responsibility per module (SOLID).
- No placeholder implementations, no TODO comments in `main`.

## Project phases

ShadowForge is developed in phases. Each phase ships complete and tested.

| Phase | Scope | Status |
|-------|-------|--------|
| 1 | Core: app, routing, request/response, middleware, DI, config, CLI (`new`, `run`) | ✅ shipped |
| 2 | ORM layer (SQLAlchemy), migrations, `generate model/crud/api`, `migrate` | planned |
| 3 | Authentication (JWT, refresh, RBAC, API keys, sessions) | planned |
| 4 | AI module (OpenAI / Claude / Gemini, RAG, agents, prompt templates) | planned |
| 5 | Document AI (OCR, PDF extraction, classification) | planned |
| 6 | Workflow engine (jobs, queues, retries, scheduling) | planned |
| 7 | Admin dashboard, monitoring, metrics | planned |

## Commit conventions

- One logical change per commit.
- Reference the phase/module in the subject, e.g. `routing: support custom converters`.

## Reporting issues

Open a GitHub issue with a minimal reproduction. Include Python version and
the output of `shadowforge version`.
