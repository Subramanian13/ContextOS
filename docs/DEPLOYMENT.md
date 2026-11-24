# Deployment preparation

ContextOS is a portfolio prototype, not a production-ready multi-tenant service. The supplied containers are provider-neutral building blocks.

## Components

- Static React frontend served by Nginx.
- FastAPI/uvicorn backend with liveness and PostgreSQL readiness checks.
- PostgreSQL 16 with pgvector and persistent storage.
- External OpenAI API access from the backend only.

## Required configuration

Copy `.env.production.example` to `.env.production` (or inject the same values with a secret manager). Set `DATABASE_URL`, `POSTGRES_PASSWORD`, `OPENAI_API_KEY`, `CORS_ALLOWED_ORIGINS`, and model settings. For a public showcase use:

```text
CONTEXTOS_ENV=production
DEMO_MODE=true
DEMO_WRITE_ENABLED=false
PROJECT_STORE=postgres
HISTORICAL_STORE=postgres
AI_RATE_LIMIT_PER_MINUTE=10
WRITE_RATE_LIMIT_PER_MINUTE=30
```

Never put `OPENAI_API_KEY` or `DEMO_OPERATOR_KEY` in the frontend build. If shared writes are needed, place the API behind real identity, per-user database isolation, and a distributed rate limiter. The built-in demo operator key is only a prototype control.

## Release sequence

1. Provision PostgreSQL with the pgvector extension and backups.
2. Run `alembic upgrade head` as a one-off release job.
3. Run `python -m app.seed_historical` once with backend-only OpenAI credentials.
4. Deploy the API and verify `/health/live` and `/health/ready`.
5. Build the frontend with `VITE_API_BASE_URL` pointing to the public API.
6. Verify CORS, TLS, security headers, read-only public mode, logs, and alerting.

The backend container runs `alembic upgrade head` from `start.sh` before starting Uvicorn. On Render, leave the **Docker Command** field empty so the image's tested `CMD` is used; `PORT` and `WEB_CONCURRENCY` are read from the platform environment.

## Single-host container deployment

The production Compose file serves the frontend and API on one origin. Nginx proxies `/api/*` and `/health*` to the private API container; only port `8080` is published. The `migrate` one-shot service must complete before the API starts.

```bash
cp .env.production.example .env.production
# Replace every placeholder and use a generated database password.
POSTGRES_PASSWORD='same-password-used-in-DATABASE_URL' \
  docker compose -f docker-compose.production.yml up -d --build

curl -fsS http://127.0.0.1:8080/health/live
curl -fsS http://127.0.0.1:8080/health/ready
curl -fsS http://127.0.0.1:8080/api/v1/projects
```

Leave `PUBLIC_API_URL` unset for this same-origin layout. Set it only when the frontend and API are deployed to different public origins. Historical evidence seeding is deliberately not automatic because it may call the configured embedding provider; run it as an explicit, monitored release job:

```bash
docker compose -f docker-compose.production.yml run --rm api uv run python -m app.seed_historical
```

Terminate TLS at the hosting platform or an edge proxy and expose the frontend container only. Do not publish PostgreSQL or the API container directly.

## Provider options

Any container platform plus managed PostgreSQL/pgvector is suitable. A static host can serve the frontend while a container or Python service hosts FastAPI. Operational requirements include TLS termination, secret management, database backups, migration jobs, outbound OpenAI access, centralized logs, and a distributed edge rate limiter.

The in-process limiter and prototype demo identity are insufficient for a horizontally scaled or anonymously writable deployment. In read-only public mode visitors can inspect projects, schedules, evidence, and previously seeded proposal history, but cannot create, approve, execute, or reset workflows. Letting unrelated visitors exercise mutations safely requires real identity plus per-user or per-session data isolation, which this prototype does not yet provide.

## Neon database

The repository is linked through `neon.ts`; the local `.neon` pointer and pulled `.env` values are git-ignored. Neon provides two connection strings:

- `DATABASE_URL` is the pooled connection used by the FastAPI/SQLAlchemy runtime.
- `DATABASE_URL_UNPOOLED` is the direct connection used by Alembic.

Both ordinary `postgresql://` URLs and explicit `postgresql+psycopg://` URLs are normalized to the installed psycopg v3 driver. To reconcile the linked production branch and refresh local environment variables:

```bash
neon deploy
cd backend
UV_CACHE_DIR=/private/tmp/contextos-uv-cache uv run alembic upgrade head
```

Copy both database variables into the Render backend environment. Never expose either value through Vite variables or commit the generated `.env` file.
