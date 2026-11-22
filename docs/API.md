# API notes

FastAPI serves the authoritative OpenAPI document at `/openapi.json` and interactive documentation at `/docs`.

Schedule simulation is deliberately read-only. `POST /api/v1/projects/{id}/schedule/simulate` accepts:

```json
{
  "unblock_dates": {"acme-api-credentials": "2026-11-20"},
  "task_changes": [
    {"task_id": "acme-sandbox-validation", "resource_id": "eng"}
  ]
}
```

An omitted duration preserves the original. A lower duration is rejected because agents cannot silently shorten work. Simulation responses include both baseline and projected schedules plus the computed working-day delta.

Required dependencies cannot be removed. Resource changes are accepted only when the resource exists and has the task's required capability.

## Conditional recovery comparison

`POST /api/v1/projects/{id}/recovery/scenarios` accepts a scenario name, hypothetical `unblock_dates`, `task_changes`, and explicit assumptions. It returns actual, assumption-only baseline, and proposed schedules plus scheduler-derived impact metrics. Baseline and proposed schedules always use identical external assumptions; actual blocker state remains unchanged.

## Forecast semantics

Every schedule returns `forecast_status` and `forecast_assumptions`:

- `feasible` includes an unconditional completion date.
- `conditional` includes a completion date and explicit unblock assumptions.
- `unresolved` returns `forecast_completion: null` and `variance_working_days: null`.

## Historical context and recovery

- `GET /api/v1/projects/{id}/historical-context?limit=5` returns stored evidence and retrieval scores.
- `POST /api/v1/projects/{id}/recovery/analyze` returns evidence, a schema-validated proposal, and deterministic baseline/proposed schedules.

Recovery returns `503` when OpenAI is unavailable, `502` for invalid model output, and `422` for invalid deterministic changes. It never writes project data.

`GET /api/v1/internal/usage` is available only when `CONTEXTOS_ENV=development`. It reports model names, token counts, durations, and error classes without prompts or API keys.

## Approval workflow

- `POST /api/v1/projects/{id}/recovery/proposals` creates a validated draft.
- `GET /api/v1/projects/{id}/recovery/proposals` returns proposal history.
- `POST /api/v1/recovery/proposals/{proposal_id}/submit` requests approval.
- `POST /api/v1/recovery/proposals/{proposal_id}/approve` explicitly approves as the labeled demo operator.
- `POST /api/v1/recovery/proposals/{proposal_id}/reject` explicitly rejects.
- `POST /api/v1/recovery/proposals/{proposal_id}/execute` executes an approved proposal with an idempotency key.
- `GET /api/v1/projects/{id}/audit-events` returns immutable backend-generated history.

Execution returns `409` for invalid lifecycle transitions, duplicate execution with a different key, or stale project versions. Hypothetical unblock dates are used only for the separately labeled conditional schedule.

## Environment and demo reset

- `GET /api/v1/environment` reports synthetic-data, write-enabled, and prototype-authentication state.
- `POST /api/v1/demo/reset` is write-guarded, requires `DEMO_MODE=true`, and accepts only `{"confirmation":"RESET SYNTHETIC DEMO","actor":"Demo operator"}`.
- `GET /health/live` checks process liveness.
- `GET /health/ready` checks PostgreSQL connectivity without exposing connection details.

Production mode defaults to read-only. The in-process limiter returns `429` for excessive AI or write requests.

