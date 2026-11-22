from __future__ import annotations

import hashlib
import logging
import threading
import time
from collections import OrderedDict
from dataclasses import asdict, dataclass
from typing import Any, Sequence

from pydantic import BaseModel

logger = logging.getLogger("contextos.ai")


class AIProviderError(RuntimeError):
    pass


class AIProviderTimeoutError(AIProviderError):
    pass


class AIProviderRateLimitError(AIProviderError):
    pass


class AIStructuredOutputError(AIProviderError):
    pass


@dataclass(frozen=True, slots=True)
class UsageEvent:
    operation: str
    model: str
    input_tokens: int
    output_tokens: int
    duration_ms: int
    error: str | None = None


class UsageTracker:
    def __init__(self, max_events: int = 200) -> None:
        self._events: list[UsageEvent] = []
        self._max_events = max_events
        self._lock = threading.Lock()

    def record(self, event: UsageEvent) -> None:
        with self._lock:
            self._events = (self._events + [event])[-self._max_events :]

    def summary(self) -> dict[str, Any]:
        with self._lock:
            events = list(self._events)
        return {
            "requests": len(events),
            "input_tokens": sum(event.input_tokens for event in events),
            "output_tokens": sum(event.output_tokens for event in events),
            "errors": sum(event.error is not None for event in events),
            "events": [asdict(event) for event in events],
        }


USAGE_TRACKER = UsageTracker()


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class OpenAIEmbeddingProvider:
    def __init__(
        self,
        api_key: str,
        model: str = "text-embedding-3-small",
        dimensions: int = 1536,
        *,
        timeout_seconds: float = 20.0,
        max_retries: int = 2,
        cache_size: int = 512,
        client: Any | None = None,
        usage: UsageTracker = USAGE_TRACKER,
    ) -> None:
        if dimensions <= 0:
            raise ValueError("Embedding dimensions must be positive")
        if client is None:
            from openai import OpenAI

            client = OpenAI(
                api_key=api_key,
                timeout=timeout_seconds,
                max_retries=max_retries,
            )
        self.client = client
        self.model = model
        self.dimensions = dimensions
        self.usage = usage
        self.cache_size = cache_size
        self._cache: OrderedDict[str, list[float]] = OrderedDict()

    @property
    def identifier(self) -> str:
        return f"openai:{self.model}:{self.dimensions}"

    def embed(self, text: str) -> list[float]:
        return self.embed_many([text])[0]

    def embed_query(self, text: str) -> list[float]:
        return self.embed(text)

    def embed_many(self, texts: Sequence[str]) -> list[list[float]]:
        values = list(texts)
        if not values or len(values) > 128:
            raise ValueError("Embedding batch size must be between 1 and 128")
        if any(not isinstance(text, str) or not text.strip() for text in values):
            raise ValueError("Embedding inputs must be non-empty strings")

        results: list[list[float] | None] = [None] * len(values)
        missing: list[str] = []
        missing_positions: list[int] = []
        for position, text in enumerate(values):
            key = self._cache_key(text)
            cached = self._cache.get(key)
            if cached is not None:
                self._cache.move_to_end(key)
                results[position] = list(cached)
            else:
                missing.append(text)
                missing_positions.append(position)

        if missing:
            started = time.monotonic()
            try:
                response = self.client.embeddings.create(
                    model=self.model,
                    input=missing,
                    dimensions=self.dimensions,
                )
                vectors = [list(item.embedding) for item in response.data]
                if len(vectors) != len(missing) or any(
                    len(vector) != self.dimensions for vector in vectors
                ):
                    raise AIProviderError("OpenAI returned invalid embedding dimensions")
                tokens = int(getattr(response.usage, "prompt_tokens", 0) or 0)
                self._record("embedding", started, tokens, 0)
            except Exception as exc:
                self._record("embedding", started, 0, 0, type(exc).__name__)
                raise _map_openai_error(exc) from exc
            for position, text, vector in zip(missing_positions, missing, vectors, strict=True):
                results[position] = vector
                self._put_cache(self._cache_key(text), vector)
        return [list(vector) for vector in results if vector is not None]

    def _cache_key(self, text: str) -> str:
        return f"{self.identifier}:{content_hash(text)}"

    def _put_cache(self, key: str, vector: list[float]) -> None:
        self._cache[key] = list(vector)
        self._cache.move_to_end(key)
        while len(self._cache) > self.cache_size:
            self._cache.popitem(last=False)

    def _record(
        self,
        operation: str,
        started: float,
        input_tokens: int,
        output_tokens: int,
        error: str | None = None,
    ) -> None:
        duration = int((time.monotonic() - started) * 1000)
        self.usage.record(
            UsageEvent(operation, self.model, input_tokens, output_tokens, duration, error)
        )
        logger.info(
            "OpenAI operation=%s model=%s duration_ms=%s error=%s",
            operation,
            self.model,
            duration,
            error or "none",
        )


class OpenAIResponsesProvider:
    def __init__(
        self,
        api_key: str,
        model: str,
        output_type: type[BaseModel],
        *,
        timeout_seconds: float = 30.0,
        max_retries: int = 2,
        client: Any | None = None,
        usage: UsageTracker = USAGE_TRACKER,
    ) -> None:
        if client is None:
            from openai import OpenAI

            client = OpenAI(
                api_key=api_key,
                timeout=timeout_seconds,
                max_retries=max_retries,
            )
        self.client = client
        self.model = model
        self.output_type = output_type
        self.usage = usage

    def generate(self, system_instruction: str, prompt: str) -> BaseModel:
        started = time.monotonic()
        try:
            response = self.client.responses.parse(
                model=self.model,
                instructions=system_instruction,
                input=prompt,
                text_format=self.output_type,
                store=False,
            )
            parsed = response.output_parsed
            if parsed is None:
                raise AIStructuredOutputError(
                    "OpenAI returned no structured recovery proposal"
                )
            usage = getattr(response, "usage", None)
            input_tokens = int(getattr(usage, "input_tokens", 0) or 0)
            output_tokens = int(getattr(usage, "output_tokens", 0) or 0)
            self._record(started, input_tokens, output_tokens)
            return parsed
        except Exception as exc:
            self._record(started, 0, 0, type(exc).__name__)
            raise _map_openai_error(exc) from exc

    def _record(
        self,
        started: float,
        input_tokens: int,
        output_tokens: int,
        error: str | None = None,
    ) -> None:
        duration = int((time.monotonic() - started) * 1000)
        self.usage.record(
            UsageEvent("generation", self.model, input_tokens, output_tokens, duration, error)
        )
        logger.info(
            "OpenAI operation=generation model=%s duration_ms=%s error=%s",
            self.model,
            duration,
            error or "none",
        )


def _map_openai_error(exc: Exception) -> AIProviderError:
    if isinstance(exc, AIProviderError):
        return exc
    try:
        from openai import APITimeoutError, RateLimitError

        if isinstance(exc, APITimeoutError):
            return AIProviderTimeoutError("OpenAI request timed out")
        if isinstance(exc, RateLimitError):
            return AIProviderRateLimitError("OpenAI rate limit exceeded")
    except ImportError:
        pass
    return AIProviderError("OpenAI request failed")
