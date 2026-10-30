# Red-Team Arena

Red-Team Arena is an AI security assessment platform. This repository currently contains only the Phase 1 foundation: a minimal Next.js frontend, a FastAPI backend, PostgreSQL development infrastructure, and migration wiring. No assessment, agent, model-provider, or reporting features are implemented yet.

## Prerequisites

- Git
- Node.js 20 or later with npm
- Python 3.11 or later
- Docker Desktop (or Docker Engine with the Compose plugin)

## Local setup

For a new checkout, create your local environment file only if it does not exist:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

On macOS or Linux, use `test -e .env || cp .env.example .env` instead. Replace every placeholder before starting services; leave `HF_TOKEN` empty when model access is not needed. Preserve an existing `.env`. See [environment setup and snapshot review](docs/ENVIRONMENT.md) for non-sensitive defaults and remaining publication checks. Keep `DATABASE_URL` aligned with the `POSTGRES_*` values.

The database-backed API and Alembic require an explicit, non-empty `DATABASE_URL`. Compose requires a non-empty `POSTGRES_PASSWORD` from your environment or `.env` and fails if it is missing. Neither supplies a password fallback. Provider-only tools can load settings without a database URL. Removing a fallback does not rotate the password of an existing database.

### 1. Start PostgreSQL

```powershell
docker compose --env-file .env -f infra/compose.yaml up -d postgres
docker compose --env-file .env -f infra/compose.yaml ps
```

PostgreSQL data is retained in a named Docker volume. To stop it without deleting the data:

```powershell
docker compose --env-file .env -f infra/compose.yaml down
```

### 2. Start the backend

```powershell
Set-Location apps/api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m alembic upgrade head
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

On macOS or Linux, activate the virtual environment with `source .venv/bin/activate`. The API reads the repository-root `.env` file.

Run backend tests from `apps/api` with:

```powershell
python -m pytest
```

On the owner's current Windows checkout, `apps/api/.venv` references a missing Python 3.12 interpreter. The working root `.venv` uses Python 3.13; from `apps/api`, use `..\..\.venv\Scripts\python.exe -m pytest -p no:cacheprovider`. Do not rebuild either environment as part of snapshot preparation. Unit tests explicitly supply synthetic database settings and override database dependencies.

### 3. Start the frontend

In a second terminal:

```powershell
Set-Location apps/web
npm install
npm run dev
```

The frontend calls `http://localhost:8000` by default. To use another backend URL, set `NEXT_PUBLIC_API_URL` in `apps/web/.env.local` or in the frontend process environment.

## Local URLs

- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- Interactive API documentation: http://localhost:8000/docs
- API health: http://localhost:8000/api/v1/health
- Database health: http://localhost:8000/api/v1/health/database

The database health route performs a real `SELECT 1` through SQLAlchemy; it returns HTTP 503 when PostgreSQL is unavailable.

## Common development commands

Frontend, from `apps/web`:

```powershell
npm run lint
npm run build
```

Next.js regenerates the ignored `next-env.d.ts` and `.next/types` declarations during `npm run dev` or `npm run build`. Run one of these before standalone TypeScript checks on a fresh checkout; keep custom declarations in separate versioned `.d.ts` files.

Backend, from `apps/api` with the virtual environment active:

```powershell
python -m pytest
python -m alembic current
python -m uvicorn app.main:app
```

See [Architecture](docs/ARCHITECTURE.md), [AI usage policy](docs/AI_USAGE.md), [model registry concept](docs/MODEL_REGISTRY.md), and [evaluation method](docs/EVALUATION_METHOD.md) for the current design boundaries.

