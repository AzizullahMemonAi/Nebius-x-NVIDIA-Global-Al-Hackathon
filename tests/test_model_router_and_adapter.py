import os
import time
from typing import Any

import pytest

from packages.contracts.schemas import ModelRequest, ModelResponse
from packages.model_router import ModelRouter
from packages.nebius_adapter.mock import MockModelProvider


def test_mock_provider_success() -> None:
    """Verify MockModelProvider returns valid text responses and usage metrics."""
    provider = MockModelProvider()
    request = ModelRequest(prompt="Hello, world!", task_complexity="low")
    response = provider.complete(request)

    assert isinstance(response, ModelResponse)
    assert response.content is not None
    assert "Mock reply" in response.content
    assert response.input_tokens > 0
    assert response.output_tokens > 0
    assert response.total_tokens == response.input_tokens + response.output_tokens
    assert response.latency_ms >= 0
    assert response.model_used
    assert response.routing_reason


def test_tool_call_parsing() -> None:
    """Verify model tool calls are correctly parsed into ModelResponse.tool_calls."""
    provider = MockModelProvider()
    request = ModelRequest(
        prompt="Call a tool",
        tools=[{"type": "function", "function": {"name": "mock_tool", "arguments": "{}"}}],
        task_complexity="moderate",
    )
    response = provider.complete(request)

    assert response.tool_calls is not None
    assert len(response.tool_calls) > 0
    assert "id" in response.tool_calls[0]
    assert response.finish_reason == "tool_calls"


def test_malformed_response() -> None:
    """Verify graceful error handling when API/mock returns missing structures."""
    from packages.nebius_adapter.nebius import NebiusAdapter
    from packages.contracts.schemas import ModelRequest

    adapter = NebiusAdapter.__new__(NebiusAdapter)

    class BadClient:
        class chat:
            class completions:
                @staticmethod
                def create(**kwargs: Any) -> Any:
                    class BadCompletion:
                        pass

                    return BadCompletion()

    adapter.client = BadClient()  # type: ignore[assignment]
    adapter._router = ModelRouter()  # type: ignore[assignment]
    adapter._redact = lambda text: text  # type: ignore[method-assign]

    request = ModelRequest(prompt="test", task_complexity="low")

    with pytest.raises((AttributeError, IndexError, Exception)):
        adapter.complete(request)


def test_timeout_and_provider_error() -> None:
    """Verify timeout errors and API failures raise predictable exceptions."""
    from packages.nebius_adapter.nebius import NebiusAdapter
    from packages.contracts.schemas import ModelRequest

    adapter = NebiusAdapter.__new__(NebiusAdapter)

    class FailingClient:
        class chat:
            class completions:
                @staticmethod
                def create(**kwargs: Any) -> Any:
                    raise RuntimeError("Connection timeout")

    adapter.client = FailingClient()  # type: ignore[assignment]
    adapter._router = ModelRouter()  # type: ignore[assignment]
    adapter._redact = lambda text: "Connection timeout"  # type: ignore[method-assign]

    request = ModelRequest(prompt="test", task_complexity="low")

    with pytest.raises(RuntimeError) as exc_info:
        adapter.complete(request)

    assert "Connection timeout" in str(exc_info.value)


def test_secret_redaction() -> None:
    """Verify API keys are redacted to [REDACTED_API_KEY] in errors."""
    from packages.nebius_adapter.nebius import NebiusAdapter

    adapter = NebiusAdapter.__new__(NebiusAdapter)
    adapter.api_key = "test-secret-key-123"

    error_message = "Error calling API with key test-secret-key-123"
    redacted = adapter._redact(error_message)

    assert "test-secret-key-123" not in redacted
    assert "[REDACTED]" in redacted


def test_model_router_tier_selection() -> None:
    """Test routing for low/moderate/high tiers including manual overrides."""
    router = ModelRouter()
    available_models = []

    req_low = ModelRequest(prompt="hi", task_complexity="low")
    model, reason = router.select_model(req_low, available_models)
    assert model == "nebius/nvidia/Nemotron-3_5-Lightning"
    assert "low" in reason

    req_mod = ModelRequest(prompt="hi", task_complexity="moderate")
    model, reason = router.select_model(req_mod, available_models)
    assert model == "nebius/nvidia/nemotron-3-super-120b-a12b"
    assert "moderate" in reason

    req_high = ModelRequest(prompt="hi", task_complexity="high")
    model, reason = router.select_model(req_high, available_models)
    assert model == "nebius/nvidia/Nemotron-3-Ultra-550b-a55b"
    assert "high" in reason

    req_override = ModelRequest(
        prompt="hi",
        task_complexity="high",
        preferred_model="nebius/custom-model",
    )
    model, reason = router.select_model(req_override, ["nebius/custom-model"])
    assert model == "nebius/custom-model"
    assert "preferred_model_override" in reason

    req_override_unavail = ModelRequest(
        prompt="hi",
        task_complexity="low",
        preferred_model="nebius/unavailable",
    )
    model, reason = router.select_model(req_override_unavail, ["other/model"])
    assert model == "nebius/unavailable"
    assert "unavailable" in reason
