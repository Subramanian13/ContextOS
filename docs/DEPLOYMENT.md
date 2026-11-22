# Deployment preparation

ContextOS is a portfolio prototype, not a production-ready multi-tenant service. The supplied containers are provider-neutral building blocks.

## Components

- Static React frontend served by Nginx.
- FastAPI/uvicorn backend with liveness and PostgreSQL readiness checks.
- PostgreSQL 16 with pgvector and persistent storage.
- External OpenAI API access from the backend only.

## Required configuration

Copy `.env.example` to a secret-managed production environment and set `DATABASE_URL`, `OPENAI_API_KEY`, `CORS_ALLOWED_ORIGINS`, and model settings. For a public showcase use:

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

## Provider options

Any container platform plus managed PostgreSQL/pgvector is suitable. A static host can serve the frontend while a container or Python service hosts FastAPI. Operational requirements include TLS termination, secret management, database backups, migration jobs, outbound OpenAI access, centralized logs, and a distributed edge rate limiter.

The in-process limiter and prototype demo identity are insufficient for a horizontally scaled or anonymously writable deployment.
