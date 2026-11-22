import pytest
from fastapi import HTTPException

from app.security import require_demo_write


def test_public_production_demo_is_read_only_by_default(monkeypatch) -> None:
    monkeypatch.setenv("CONTEXTOS_ENV", "production")
    monkeypatch.delenv("DEMO_WRITE_ENABLED", raising=False)
    with pytest.raises(HTTPException) as error:
        require_demo_write(None)
    assert error.value.status_code == 403
    assert error.value.detail == "This public demo is read-only."


def test_demo_operator_key_is_compared_without_exposing_it(monkeypatch) -> None:
    monkeypatch.setenv("CONTEXTOS_ENV", "demo")
    monkeypatch.setenv("DEMO_WRITE_ENABLED", "true")
    monkeypatch.setenv("DEMO_OPERATOR_KEY", "synthetic-test-key")
    with pytest.raises(HTTPException, match="operator key"):
        require_demo_write("wrong-key")
    require_demo_write("synthetic-test-key")
