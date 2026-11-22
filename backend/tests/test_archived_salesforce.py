import os

from fastapi.testclient import TestClient

from app.main import app


def test_backend_starts_without_salesforce_configuration(monkeypatch) -> None:
    for key in list(os.environ):
        if key.startswith("SALESFORCE_"):
            monkeypatch.delenv(key,raising=False)
    client=TestClient(app)
    assert client.get("/health").json()=={"status":"ok"}
    assert client.get("/api/v1/projects/acme-crm").status_code==200


def test_salesforce_and_crm_context_routes_are_not_registered() -> None:
    client=TestClient(app)
    assert client.get("/api/v1/integrations/salesforce/status").status_code==404
    assert client.get("/api/v1/integrations/salesforce/authorize").status_code==404
    assert client.get("/api/v1/projects/acme-crm/crm-context").status_code==404
    assert client.post("/api/v1/projects/acme-crm/crm-context/refresh").status_code==404


def test_acme_domain_scenario_remains_independent() -> None:
    client=TestClient(app)
    project=client.get("/api/v1/projects/acme-crm").json()
    schedule=client.get("/api/v1/projects/acme-crm/schedule").json()
    assert project["project_type"]=="CRM integration"
    assert project["blockers"][0]["credential_readiness"]=="awaiting_customer"
    assert project["blockers"][0]["condition_satisfied"] is False
    assert schedule["forecast_status"]=="unresolved"
    assert any(task["id"]=="acme-sandbox-validation" for task in project["tasks"])
