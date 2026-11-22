# ContextOS implementation plan

## Repository structure

- `backend/`: FastAPI service, deterministic domain logic, persistence models, migrations, and tests
- `frontend/`: React/Vite client (introduced in slice 2)
- `docs/`: architecture, API, implementation, and demo documentation
- `docker-compose.yml`: local PostgreSQL with pgvector

## Vertical slices

1. **Project data and deterministic scheduler — implemented.** Define project/task/resource data, seed five projects, calculate schedules, validate graphs and simulations, expose read/simulation APIs, and test core invariants.
2. **Dashboard and project details — implemented.** React/Tailwind application shell, API-derived portfolio metrics, project/task/resource views, working-day timeline, project events, deterministic risk evidence, responsive navigation, and component tests. Persistence remains intentionally seed-backed until the repository slice.
3. **Historical context retrieval and AI recovery planning — implemented.** Twelve sourced synthetic incidents, deterministic test fixtures, PostgreSQL/pgvector persistence and cosine search, OpenAI embeddings, Responses API structured proposals, evidence validation, deterministic simulations, corrected forecast semantics, and Recovery Intelligence UI.
3a. **Advanced conditional recovery planning — implemented.** Salesforce OAuth credential readiness, hypothetical customer unblock dates, qualified-resource validation, fair scenario comparison, and before/after recovery impact UI.
4. **AI proposal generation — folded into Slice 3.** The proposal service is read-only; approval and execution remain separate future work.
5. **Approval and controlled execution — implemented.** Versioned persisted proposals, explicit demo-operator approval/rejection, stale-state checks, idempotent transactional execution, project version overlays, and post-write actual/conditional recalculation.
6. **Audit history and full tests — partially implemented.** Immutable backend audit persistence plus rollback, duplicate execution, blocker preservation, and lifecycle tests are complete. Playwright browser automation remains future work.
7. **UI polish and documentation.** Accessibility, responsive states, loading/error states, demo walkthrough, final architecture and API docs, and Docker validation.
8. **External CRM connector — archived.** The prior Salesforce Developer Edition prototype was removed from the active API and UI because its read-only context panel did not contribute to the core recovery workflow. Historical implementation details are retained in `docs/ARCHIVED_SALESFORCE_INTEGRATION.md`; database tables are preserved without active access.

## Slice 1 acceptance criteria

- Dependency cycles and missing predecessors are rejected.
- Blocked tasks cannot start without a satisfied condition or explicit hypothetical unblock date.
- Resource constraints serialize work assigned to the same resource.
- The scheduler returns earliest start/finish dates and critical tasks.
- Simulations reject silent duration reductions and invalid dependency edits.
- Five projects and the Acme deadline scenario are available through typed endpoints.
- Unit and API tests pass with Python 3.12.

## Slice 2 acceptance criteria

- Portfolio metrics are derived from `GET /api/v1/projects`, never hardcoded.
- Project overview combines detail data with scheduler output without recalculating authoritative dates.
- Timeline bars use backend start/completion dates and omit weekend columns.
- Blocked, dependency-impacted, and critical-path tasks are visibly distinguished.
- Resource names, blocker conditions, and project events are served by the additive project-detail contract.
- Loading, error, and empty states are implemented.
- Portfolio, project, risk, and timeline navigation is covered by component tests.
- The frontend type-checks and builds as a production Vite bundle.

## Slice 3 acceptance criteria

- Required unscheduled tasks produce an `unresolved` project forecast with no completion date.
- Explicit unblock-date simulations produce `conditional` forecasts with disclosed assumptions.
- Twelve synthetic incidents have stable IDs, source references, event dates, and retrievable embeddings.
- The PostgreSQL repository uses pgvector cosine distance and an HNSW index.
- OpenAI Responses output is schema-validated, restricted to allowlisted changes, and checked against retrieved evidence IDs.
- Proposal task changes are passed through the existing deterministic scheduler without mutation.
- Missing keys, timeouts, malformed output, unsupported actions, dependency cycles, and unknown evidence fail visibly.
- Recovery UI never substitutes fabricated content when OpenAI is unavailable.

