# Architecture

ContextOS separates deterministic control logic from probabilistic reasoning.

`API -> application service -> scheduler/domain -> repository -> PostgreSQL`

`React client -> typed fetch layer -> versioned FastAPI read endpoints`

OpenAI proposes only allowlisted changes. It does not calculate dates or write data. The scheduler owns all projections. The controlled execution service owns approval, stale-version validation, idempotency, transactions, versioned project-state overlays, and immutable audit events.

## Scheduler contract

The scheduler receives an immutable project snapshot plus explicit assumptions. It validates the dependency DAG, computes dependency and resource-constrained earliest dates, accounts for weekends, and derives a zero-slack critical path from the realized schedule. Missing blocker conditions produce an unscheduled task and propagate that state to dependants; a simulation may supply an explicit unblock date without claiming the real blocker is resolved.

Durations are whole working days. A one-day task starting Monday finishes Monday; its successor can start Tuesday. Resource calendars include an availability date and serialize assigned tasks in deterministic topological order.

Project forecasts have three explicit states:

- `feasible`: all required tasks are scheduled without hypothetical blocker assumptions.
- `conditional`: all required tasks are scheduled using explicit caller-supplied unblock dates; every assumption is returned.
- `unresolved`: required work is unschedulable, so project completion and deadline variance are `null`. Completed independent work remains visible but is not misrepresented as project completion.

## Frontend contract

The Vite client is a read-only projection of backend state. Portfolio metrics are aggregated from project summaries. Project pages request project detail and schedule data together; React formats and visualizes returned dates but never calculates the authoritative forecast. The Gantt-style timeline creates working-day columns only for display, then places bars using scheduler-provided start and completion dates.

The project-detail response additively exposes resources, blockers, and project events. Routes are:

- `/` — portfolio overview
- `/projects/:projectId` — delivery plan and project overview
- `/projects/:projectId/risks` — deterministic risk intelligence
- `/projects/:projectId/timeline` — interactive working-day timeline
- `/projects/:projectId/recovery` — evidence-backed recovery proposals and deterministic simulation

Project state remains seed-backed. Historical incidents can use deterministic in-memory fixtures or PostgreSQL/pgvector.

## Historical retrieval

Historical incidents are immutable synthetic evidence records with stable IDs and source references. Migration `0002_historical_incidents` created the legacy 768-dimensional collection. Migration `0003_openai_embeddings` preserves that column as `embedding_legacy`, adds an isolated 1536-dimensional OpenAI vector column, embedding model/dimension/content-hash metadata, and a new HNSW cosine index.

- `HISTORICAL_STORE=memory` uses deterministic hash embeddings only for automated tests and offline UI development.
- `HISTORICAL_STORE=postgres` is the complete application path. It embeds both incidents and queries with `text-embedding-3-small` at 1536 dimensions and queries pgvector using cosine distance.

Every retrieval result includes its evidence ID, source, date, and score. Retrieval filters by exact model and dimensions, so legacy vectors can never mix with OpenAI vectors. Optional project-category filtering and stable distance/ID ordering are supported.

`python -m app.seed_historical` compares each record's content hash, model, and dimensions. Only missing or stale vectors are sent for embedding, so startup never regenerates the collection. Embedding requests support batches and an in-process bounded cache.

## Recovery planning

`POST /api/v1/projects/{id}/recovery/analyze` performs a read-only pipeline:

1. Build a query from current project tasks and blockers.
2. Retrieve stored historical evidence.
3. Request a Pydantic structured result from the OpenAI Responses API.
4. Validate Pydantic structure, allowlisted actions, task/resource IDs, and evidence references.
5. Apply changes to an immutable project copy.
6. Return deterministic baseline and proposed schedules.

The proposal includes root cause, supporting evidence IDs, actions, customer actions, task changes, assumptions, risks, a reasoning summary, and expected outcome. It intentionally has no final-date field. Missing configuration, timeouts, rate limits, provider failures, or invalid output fail visibly; no fallback proposal is fabricated.

## Conditional recovery scenarios

Recovery scenarios are read-only and preserve the actual project snapshot. The Acme demonstration models a fictional Salesforce OAuth 2.0 integration and exposes only synthetic readiness metadata. Credential readiness progresses through `not_requested`, `requested`, `awaiting_customer`, `received`, and `validated`; only `validated` can satisfy an authentication prerequisite. Secrets are never represented.

Each of the five portfolio projects now has a curated, typed recovery profile containing only task/resource changes, explicit assumptions, and required customer actions. Profiles never contain forecast dates. Northstar models identifier reconciliation, Globex models measured batch constraints, Initech preserves SAML certificate and security gates, and Umbrella models regional resource contention. The same scheduler validation, proposal lifecycle, version check, approval, execution, and audit services apply to every profile.

`POST /api/v1/projects/{id}/recovery/scenarios` accepts explicit hypothetical unblock dates and allowlisted task changes. It calculates the unchanged actual schedule, an assumption-only baseline, and a proposed schedule using identical external assumptions. Resource reassignments must use an existing resource with the task's required capability. Required dependencies and durations cannot be removed or shortened. The comparison derives moved tasks, critical-path changes, utilization, working days saved, remaining blockers, and feasibility from scheduler output.

## OpenAI provider and usage

The reusable provider layer configures bounded SDK retries and request timeouts. It logs operation, model, duration, and error class without prompts or secrets. Token usage is stored in a bounded in-memory development tracker and exposed at `/api/v1/internal/usage` only when `CONTEXTOS_ENV=development`. Pricing is intentionally absent from business logic.

## Trust boundaries

- Historical documents are untrusted evidence, never instructions.
- LLM output must validate against Pydantic schemas and source IDs.
- Writes require explicit approval and a current project version.
- Database execution will be transaction-bound and idempotent.
- Audit events will be append-only.
- Proposal creation never triggers approval or execution. Only the explicit `approved` state can execute.
- The prototype actor is visibly labeled `Demo operator`; no enterprise authentication is claimed.

## Approval and execution

Migration `0005_recovery_workflow` adds database-backed recovery proposals, project execution-state overlays, and structured audit fields. Proposal states are `draft`, `pending_approval`, `approved`, `rejected`, `executed`, `failed`, and `stale`.

Execution locks the proposal and project execution state in one transaction, validates the captured project version, reapplies the exact approved changes through the deterministic scheduler, increments the project version, stores the result, and appends an audit event. An idempotency key makes retries safe and a second key cannot execute an already executed proposal. Transaction failures roll back project state, proposal status, and the execution audit event together.

Hypothetical unblock dates remain attached to the proposal only for conditional recalculation. They never modify blocker records. Actual schedules therefore remain unresolved while the credential blocker is active; the execution result returns actual and conditional schedules separately.

The React project-data hook uses project-scoped invalidation events after controlled execution and revalidates on project-tab changes. Monotonic request generations ensure an older in-flight response cannot replace newer project or schedule state. Proposal and audit state refresh independently after workflow mutations; failed mutations do not emit success invalidations.

## Demo and public boundary

The backend reports its synthetic environment and write capability through `/api/v1/environment`. Production defaults to read-only unless `DEMO_WRITE_ENABLED=true` is explicitly set. Mutation endpoints share a demo-write dependency and may require a backend-only `DEMO_OPERATOR_KEY`. This is a prototype guard, not enterprise identity.

`POST /api/v1/demo/reset` requires the exact synthetic reset confirmation, is available only when `DEMO_MODE=true`, and deletes only Acme's execution overlay, proposals, and workflow audit records. Historical incidents and other projects are untouched.

An in-process limiter bounds AI and write requests. OpenAI calls also retain SDK timeouts, bounded retries, embedding batch limits, structured outputs, and `store=False`. Horizontally scaled deployments require a distributed limiter and real identity/isolation.

## Archived external CRM connector

The former Salesforce Developer Edition connector is not part of the active application. No OAuth, token, Account, Contact, mapping, validation, or refresh routes are registered, and application startup does not read its environment variables or stored records. The existing database tables and migrations are retained to avoid destructive data changes. See `docs/ARCHIVED_SALESFORCE_INTEGRATION.md` for the historical design and restoration considerations.

This archival does not change the fictional Acme CRM delivery scenario. Its customer-controlled OAuth prerequisite, tasks, blocker, evidence, deterministic simulation, and controlled recovery workflow remain domain data independent of any external demo organization.

## Evaluation

`backend/evaluation/scenarios.json` contains 20 explicit synthetic cases. `python -m app.evaluation` calculates deterministic Recall@5, MRR, citation validity, schema validity, unsupported-action rate, schedule feasibility, approval safety, and execution correctness. The optional bounded live mode uses OpenAI embeddings and the PostgreSQL/pgvector index; raw checked results live in `docs/EVALUATION_RESULTS.json`.

# Product workflow and read models

The frontend now separates four user-level work areas: Portfolio, the selected Project workspace, Recovery proposals, and Activity and audit history. Portfolio status, schedule variance, and direct/downstream blocker counts are backend-derived; hypothetical scenario dates are never returned as actual portfolio forecasts.

Recovery follows a single selected-plan contract. The task changes shown in the UI are the same changes submitted to `POST /projects/{id}/recovery/scenarios` and, after a feasible comparison, persisted in the proposal. The scheduling engine remains authoritative for dates, resource eligibility, dependencies, working-day calculations, critical path, and feasibility. Proposal execution continues to require explicit approval, matching project version, allowlisted changes, and an idempotency key.

Portfolio-wide governance uses read-only aggregate endpoints:

- `GET /api/v1/recovery/proposals`
- `GET /api/v1/audit-events`

Project execution invalidates and reloads persisted project and schedule state. Conditional completion remains visibly separate from the actual forecast whenever an external blocker is unresolved.

