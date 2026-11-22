import os

os.environ["HISTORICAL_STORE"] = "memory"
os.environ["PROJECT_STORE"] = "memory"

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_lists_ten_projects_without_duplicates() -> None:
    response = client.get("/api/v1/projects")
    assert response.status_code == 200
    assert len(response.json()) == 10
    assert len({item["id"] for item in response.json()}) == 10
    acme = next(item for item in response.json() if item["id"] == "acme-crm")
    assert acme["delivery_risk"] == "off_track"
    assert acme["blocked_tasks"] >= 1
    assert acme["directly_blocked_tasks"] == 1
    assert acme["downstream_affected_tasks"] == acme["blocked_tasks"] - 1
    assert acme["forecast_completion"] is None
    assert acme["forecast_status"] == "unresolved"
    assert acme["variance_working_days"] is None


def test_acme_schedule_exposes_blocker_evidence() -> None:
    response = client.get("/api/v1/projects/acme-crm/schedule")
    assert response.status_code == 200
    tasks = {item["task_id"]: item for item in response.json()["tasks"]}
    assert "credentials" in tasks["acme-api-build"]["blocked_reason"].lower()


def test_acme_detail_exposes_resources_blockers_and_events() -> None:
    response = client.get("/api/v1/projects/acme-crm")
    assert response.status_code == 200
    body = response.json()
    assert {resource["id"] for resource in body["resources"]} == {"impl", "eng", "qa"}
    assert body["blockers"][0]["id"] == "acme-api-credentials"
    assert body["blockers"][0]["condition_satisfied"] is False
    assert body["blockers"][0]["credential_readiness"] == "awaiting_customer"
    assert dict(body["blockers"][0]["metadata"])["connected_app"] == "Required"
    assert body["events"][0]["kind"] == "blocker_reported"


def test_simulation_is_marked_projection_only() -> None:
    response = client.post("/api/v1/projects/acme-crm/schedule/simulate", json={"unblock_dates": {"acme-api-credentials": "2026-11-20"}})
    assert response.status_code == 200
    body = response.json()
    assert body["projection_only"] is True
    assert body["projected"]["forecast_completion"] == "2026-12-03"
    assert body["projected"]["forecast_status"] == "conditional"
    assert body["projected"]["forecast_assumptions"] == [
        "Simulation assumes the API credentials blocker is resolved on November 20, 2026. Actual blocker remains open."
    ]


def test_unknown_project_returns_404() -> None:
    assert client.get("/api/v1/projects/missing").status_code == 404


def test_conditional_recovery_scenario_compares_identical_assumptions() -> None:
    response = client.post(
        "/api/v1/projects/acme-crm/recovery/scenarios",
        json={
            "name": "November 23 optimized",
            "unblock_dates": {"acme-api-credentials": "2026-11-23"},
            "task_changes": [
                {"task_id": "acme-sandbox-validation", "resource_id": "eng"}
            ],
            "assumptions": ["Customer date is hypothetical."],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["actual"]["forecast_status"] == "unresolved"
    assert body["baseline"]["forecast_completion"] == "2026-12-04"
    assert body["proposed"]["forecast_completion"] == "2026-12-02"
    assert body["working_days_saved"] == 2
    assert body["causal_explanation"] == "Reassigning Validate connector in Salesforce sandbox from QA specialist to Integration engineer frees QA specialist to start Execute integration tests earlier. Go-live readiness consequently finishes 2 working days sooner."
    assert body["projection_only"] is True


def test_historical_context_is_structured_and_traceable() -> None:
    response = client.get("/api/v1/projects/acme-crm/historical-context")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 5
    assert all(item["id"].startswith("INC-") for item in body)
    assert all(item["evidence_source"] for item in body)
    assert all("retrieval_score" in item for item in body)


def test_recovery_analysis_requires_openai_configuration(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    response = client.post("/api/v1/projects/acme-crm/recovery/analyze")
    assert response.status_code == 503
    assert "not configured" in response.json()["detail"]


def test_development_usage_summary_does_not_expose_secrets() -> None:
    response = client.get("/api/v1/internal/usage")
    assert response.status_code == 200
    body = response.json()
    assert {"requests", "input_tokens", "output_tokens", "errors", "events"} <= body.keys()
    assert "api_key" not in str(body).lower()
