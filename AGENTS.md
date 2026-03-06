# AGENTS.md

## Cursor Cloud specific instructions

### Overview

Knowledge Gains AI is a single-service FastAPI web application that generates personalized hypertrophy training programs using OpenAI GPT-4.1. It uses Jinja2 templates with HTMX/Alpine.js on the frontend and Supabase (hosted PostgreSQL + pgvector) as the database.

### Prerequisites

- **Python**: >=3.13 (`.python-version` specifies 3.13.5; install via `deadsnakes` PPA on Ubuntu)
- **Package manager**: `uv` (lockfile: `uv.lock`)

### Running the app

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The app serves at `http://localhost:8000`.

### Lint / Test / Build

See `README.md` "Development" section. Key commands:

- **Lint**: `uv run ruff check .`
- **Tests**: `uv run pytest` (test directory `tests/` is configured but currently empty)
- **Install dev deps**: `uv sync --extra dev --group dev` (the `dev` optional-dependency group has pytest/black/mypy/etc.; the `dev` dependency-group has `types-requests`)

### External service dependencies

The full wizard flow (form submission, program generation) requires working connections to:

1. **Supabase** — cloud-hosted PostgreSQL database for storing wizard answers, routines, progress logs, and file vectors. Configured via `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` in `.env`.
2. **OpenAI API** — for GPT-4.1 program generation and text embeddings. Configured via `OPENAI_API_KEY` in `.env`.

Both are external SaaS services and require internet access. In sandboxed/offline environments, the homepage and static assets load fine, but form submissions will fail with DNS resolution errors.

### Non-obvious gotchas

- The `pyproject.toml` has `dev` defined in *both* `[project.optional-dependencies]` and `[dependency-groups]`. To get the full dev toolchain (pytest, black, mypy, etc.), run `uv sync --extra dev --group dev`.
- The `.env` file is committed to the repo with real-looking API keys. These may be revoked; replace with valid keys if needed.
- No `tests/` directory exists yet; `uv run pytest` exits with code 5 (no tests collected), which is expected.
- The app uses `SessionMiddleware` with `itsdangerous`; sessions are cookie-based with a random UUID per visitor (no authentication system).
