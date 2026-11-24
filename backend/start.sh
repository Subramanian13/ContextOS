#!/bin/sh
set -eu

# Free Render services do not provide a separate pre-deploy migration step.
# Alembic upgrades are idempotent, so applying them before each process start
# keeps both Render and the provider-neutral container image consistent.
uv run alembic upgrade head

exec uv run uvicorn app.main:app \
  --host 0.0.0.0 \
  --port "${PORT:-8000}" \
  --workers "${WEB_CONCURRENCY:-2}" \
  --proxy-headers \
  --no-access-log
