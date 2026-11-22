from types import SimpleNamespace
from datetime import date

import httpx
import pytest
from openai import APITimeoutError, RateLimitError

from app.ai import (
    AIProviderRateLimitError,
    AIProviderTimeoutError,
    OpenAIEmbeddingProvider,
    OpenAIResponsesProvider,
    UsageTracker,
    AIStructuredOutputError,
    content_hash,
)
from app.recovery import RecoveryProposal, build_prompt
from app.schemas import RecoveryAnalysisRequest
from app.domain.scheduler import calculate_schedule
from app.seed import ACME
from app.historical import INCIDENTS
from app.seed_historical import embedding_is_stale


class FakeEmbeddings:
    def __init__(self, dimensions: int, error: Exception | None = None) -> None:
        self.dimensions = dimensions
        self.error = error
        self.calls = 0

    def create(self, *, model, input, dimensions):
        self.calls += 1
        if self.error:
            raise self.error
        return SimpleNamespace(
            data=[SimpleNamespace(embedding=[float(index)] * self.dimensions) for index, _ in enumerate(input, 1)],
            usage=SimpleNamespace(prompt_tokens=len(input) * 3),
        )


class FakeEmbeddingClient:
    def __init__(self, resource) -> None:
        self.embeddings = resource


def test_embedding_dimensions_batch_and_cache() -> None:
    resource = FakeEmbeddings(1536)
    usage = UsageTracker()
    provider = OpenAIEmbeddingProvider(
        "test", client=FakeEmbeddingClient(resource), usage=usage
    )
    first = provider.embed_many(["credential blocker", "crm integration"])
    second = provider.embed_many(["credential blocker", "crm integration"])
    assert [len(vector) for vector in first] == [1536, 1536]
    assert first == second
    assert resource.calls == 1
    assert usage.summary()["input_tokens"] == 6


def test_embedding_dimension_mismatch_fails() -> None:
    provider = OpenAIEmbeddingProvider(
        "test", client=FakeEmbeddingClient(FakeEmbeddings(8))
    )
    with pytest.raises(Exception, match="invalid embedding dimensions"):
        provider.embed("test")


def test_embedding_timeout_is_explicit() -> None:
    error = APITimeoutError(request=httpx.Request("POST", "https://api.openai.com"))
    provider = OpenAIEmbeddingProvider(
        "test", client=FakeEmbeddingClient(FakeEmbeddings(1536, error))
    )
    with pytest.raises(AIProviderTimeoutError):
        provider.embed("test")


def test_embedding_rate_limit_is_explicit() -> None:
    response = httpx.Response(
        429,
        request=httpx.Request("POST", "https://api.openai.com"),
        json={"error": {"message": "limited"}},
    )
    error = RateLimitError("limited", response=response, body=None)
    provider = OpenAIEmbeddingProvider(
        "test", client=FakeEmbeddingClient(FakeEmbeddings(1536, error))
    )
    with pytest.raises(AIProviderRateLimitError):
        provider.embed("test")


def proposal() -> RecoveryProposal:
    return RecoveryProposal(
        root_cause_explanation="Credential approval gates connector work.",
        supporting_evidence_ids=["INC-001"],
        recommended_actions=["Prepare independent tests."],
        proposed_task_changes=[],
        required_customer_actions=["Provide credentials."],
        assumptions=["Credential timing remains unknown."],
        risks=["The blocker may persist."],
        reasoning_summary="Independent work is available, but completion remains unresolved.",
        expected_outcome_explanation="Prepared work reduces delay after unblock.",
    )


class FakeResponses:
    def __init__(self) -> None:
        self.calls = []

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            output_parsed=proposal(),
            usage=SimpleNamespace(input_tokens=120, output_tokens=80),
        )


def test_responses_api_structured_generation_and_usage() -> None:
    responses = FakeResponses()
    client = SimpleNamespace(responses=responses)
    usage = UsageTracker()
    provider = OpenAIResponsesProvider(
        "test", "gpt-5.4-mini", RecoveryProposal, client=client, usage=usage
    )
    result = provider.generate("system", "project")
    assert result.reasoning_summary
    assert responses.calls[0]["text_format"] is RecoveryProposal
    assert responses.calls[0]["store"] is False
    assert usage.summary()["input_tokens"] == 120
    assert usage.summary()["output_tokens"] == 80


def test_recovery_prompt_includes_explicit_what_if_assumptions() -> None:
    prompt = build_prompt(
        ACME,
        calculate_schedule(ACME),
        [],
        RecoveryAnalysisRequest(
            unblock_dates={"acme-api-credentials": date(2026, 11, 23)},
            assumptions=["Customer date is hypothetical."],
        ),
    )
    assert '"scenario_assumptions": ["Customer date is hypothetical."]' in prompt
    assert '"acme-api-credentials": "2026-11-23"' in prompt


def test_invalid_structured_response_is_rejected() -> None:
    client = SimpleNamespace(
        responses=SimpleNamespace(
            parse=lambda **kwargs: SimpleNamespace(
                output_parsed=None,
                usage=SimpleNamespace(input_tokens=10, output_tokens=2),
            )
        )
    )
    provider = OpenAIResponsesProvider(
        "test", "gpt-5.4-mini", RecoveryProposal, client=client
    )
    with pytest.raises(AIStructuredOutputError):
        provider.generate("system", "project")


def test_embedding_model_or_content_mismatch_requires_reindex() -> None:
    incident = INCIDENTS[0]
    current = SimpleNamespace(
        embedding=[0.0] * 1536,
        embedding_model="text-embedding-3-small",
        embedding_dimensions=1536,
        embedding_content_hash=content_hash(incident.search_text),
    )
    assert not embedding_is_stale(current, incident, "text-embedding-3-small", 1536)
    assert embedding_is_stale(current, incident, "text-embedding-3-large", 1536)
    assert embedding_is_stale(current, incident, "text-embedding-3-small", 1024)
