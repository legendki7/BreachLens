# Environment setup and snapshot review

`.env.example` is a template containing placeholders only. It is not runnable until every placeholder is replaced. Never overwrite an existing `.env` when preparing a snapshot. The API settings loader reads the repository-root `.env`; Alembic obtains its URL from the database settings loader in `apps/api/migrations/env.py`. The INI file intentionally contains no connection URL.

The database-backed API and migrations use `DatabaseSettings`, which requires a non-empty `DATABASE_URL` and raises a validation error if it is missing or blank. General `Settings` permits an absent URL for provider-only tools that do not access the database. Explicit constructor arguments take precedence over process environment variables, which take precedence over the root `.env`. Settings validation messages hide input values.

Compose requires a non-empty externally supplied `POSTGRES_PASSWORD`, via process environment or the documented `--env-file .env` command. Missing or empty passwords produce a required-variable error. Non-sensitive database name, user and port defaults remain; no password or credential-bearing URL fallback remains.

## Non-sensitive local defaults

| Variable | Suggested local value or instruction |
| --- | --- |
| APP_ENV | `development` |
| API_HOST | `127.0.0.1` |
| API_PORT | `8000` |
| FRONTEND_URL | `http://localhost:3000`; explicit origins only |
| HF_TOKEN | Empty for mock/local work; otherwise use your own authorized token |
| POSTGRES_DB | `red_team_arena` |
| POSTGRES_USER | `red_team_arena` |
| POSTGRES_PASSWORD | Choose a private password; no password default is documented here |
| POSTGRES_PORT | `5432` |
| DATABASE_URL | Construct a `postgresql+asyncpg` URL for your chosen database/user/password, host and port; percent-encode URL credentials as needed |
| NEXT_PUBLIC_API_URL | `http://localhost:8000` |
| NEXT_PUBLIC_SITE_URL | Public origin of the deployed website (for example `https://<your-domain>`). Set it before a production or static build so Open Graph and Twitter image URLs are absolute; when unset, the image tags are omitted. See [InfinityFree deployment](DEPLOY_INFINITYFREE.md). |

The root environment file is used by the API and the documented Compose command. Supply `NEXT_PUBLIC_API_URL` and `NEXT_PUBLIC_SITE_URL` separately to the frontend process or in `apps/web/.env.local`. Browser-exposed variables must never contain secrets.

## Publication review

This is a work-in-progress MVP handoff snapshot, not a fully validated release or an end-to-end readiness claim. The latest focused backend configuration, native guardrail and migration checks passed: **15 tests passed**. Offline Alembic SQL generation through the latest migration passed; actual database connectivity remains unverified. Native Compose validation is unavailable because Docker CLI is missing. Full backend suite collection is blocked by missing `huggingface_hub` and `nemoguardrails`. See the existing Windows environment limitations below. These results record prior checks; creating a snapshot commit does not imply a fresh full-suite run.

The application and Compose password fallbacks have been removed. This changes configuration requirements, not the credentials of an existing database. The owner's `.env` was preserved. No database connection, online migration, password rotation or database-user change was performed. If an existing database uses a previously shared development password, coordinate its replacement with the database role, local `.env` and dependent processes separately; changing an environment variable alone does not update an existing database role.

`apps/api/tests/test_config.py` uses synthetic connection-string parsing fixtures without connecting to a database. The token-shaped string in `apps/api/tests/test_native_guardrails.py` is an explicit synthetic alphabet/number fixture used to test detection, not authentication. Retain both fixtures and their coverage.

`apps/api/tests/conftest.py` supplies an explicit synthetic `DATABASE_URL` before importing the API, then restores the process environment after pytest. Database endpoint tests override database dependencies. This keeps unit tests independent of real local database credentials.

## Existing Windows Python environments

The API-local `apps/api/.venv` references a missing Python 3.12 interpreter. The existing root `.venv` uses the working Python 3.13 interpreter. Run backend checks with the root environment (from `apps/api`, `..\..\.venv\Scripts\python.exe -m pytest -p no:cacheprovider`). Neither environment was deleted, rebuilt or modified during this preparation. Offline Alembic checks use an explicit synthetic URL supplied only to the check process; they do not connect to the database.

The root environment runs the focused configuration/guardrail/migration checks, but currently lacks `huggingface_hub` and `nemoguardrails`, preventing full-suite collection. Docker CLI is unavailable in this session, so native `docker compose config --quiet` validation remains pending. Do not run plain `docker compose config` in shared output because it can expose expanded credentials. No packages or tools were installed to work around these limitations.

Database backup patterns ignore `.dump`, `.sql.gz` and `.sqlite3` files (including SQLite sidecars). Plain `.sql` files remain eligible so migrations, seeds and fixtures cannot be silently lost. Review any newly added plain SQL files before staging; put raw backup files outside the source tree or approve a specific ignore path.

Next.js regenerates `apps/web/next-env.d.ts` and `.next/types` during development/build. They are ignored, while `tsconfig.json` retains the required declaration references. Do not delete local declarations to prepare a snapshot.

The ignored `apps/api/.pytest_cache/` directory could not be inspected because access was denied. Its ignore rule excludes it from the ordinary publishable set; do not force-add ignored paths. No permissions were changed and nothing was deleted.
