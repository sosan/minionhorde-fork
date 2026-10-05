"""Tests for the provider-adapter envelope contract (task 7.1)."""

from __future__ import annotations

from typing import Any

import pytest

from contract import providers
from contract.providers import (
    AdapterError,
    AnthropicAdapter,
    EchoAdapter,
    OpenAIAdapter,
    envelope_has_secret,
    get_adapter,
    list_supported_conditions,
    run_controlled_condition,
)


def test_echo_adapter_returns_envelope_with_reported_identity() -> None:
    envelope = EchoAdapter().invoke("hello world", model="local/echo-v0", config={})
    assert envelope["schema_version"] == "v1"
    assert envelope["provider"] == "echo"
    assert envelope["requested_model"] == "local/echo-v0"
    assert envelope["served_model"] == "local/echo-v0"
    assert envelope["served_model_status"] == "reported"
    assert envelope["error_classification"] == "none"
    assert envelope["response_text"].startswith("[echo:")
    assert envelope["usage"]["input_tokens"] == len("hello world")
    assert envelope["latency_ms"] == 0
    assert envelope["request_id"].startswith("echo-")


def test_echo_adapter_deterministic_for_same_prompt() -> None:
    a = EchoAdapter().invoke("stable", model="m", config={})
    b = EchoAdapter().invoke("stable", model="m", config={})
    assert a["response_text"] == b["response_text"]
    assert a["request_id"] == b["request_id"]


def test_unknown_adapter_raises() -> None:
    with pytest.raises(AdapterError):
        get_adapter("nonexistent-provider")


def test_supported_conditions_are_documented() -> None:
    assert list_supported_conditions() == ("base", "criteria", "criteria_memory", "full")


def test_run_controlled_condition_returns_validated_envelope() -> None:
    envelope = run_controlled_condition("echo", prompt="ping", model="local/echo-v0")
    for key in ("schema_version", "provider", "requested_model", "response_text", "served_model", "served_model_status", "error_classification"):
        assert key in envelope, f"missing {key}"
    assert envelope["error_classification"] == "none"


def test_envelope_has_secret_detects_common_markers() -> None:
    good_envelope = EchoAdapter().invoke("hello", model="m", config={})
    assert envelope_has_secret(good_envelope) is False

    leaked = dict(good_envelope)
    leaked["response_text"] = "see AKIAIOSFODNN7EXAMPLE key"
    assert envelope_has_secret(leaked) is True

    leaked_pat = dict(good_envelope)
    leaked_pat["response_text"] = "GHU_abc123 example"
    assert envelope_has_secret(leaked_pat) is True


def test_run_controlled_condition_refuses_secret_leak(monkeypatch: pytest.MonkeyPatch) -> None:
    class LeakyAdapter:
        name = "leaky"

        def invoke(self, prompt: str, *, model: str, config: dict[str, Any]) -> dict[str, Any]:
            return {
                "schema_version": "v1",
                "provider": "leaky",
                "requested_model": model,
                "response_text": "leak AKIAIOSFODNN7EXAMPLE here",
                "served_model": model,
                "served_model_status": "reported",
                "error_classification": "none",
            }

    monkeypatch.setitem(providers.REGISTRY, "leaky", LeakyAdapter())
    with pytest.raises(AdapterError):
        run_controlled_condition("leaky", prompt="anything", model="m")


def test_anthropic_adapter_without_api_key_returns_credential_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    envelope = AnthropicAdapter().invoke("hi", model="claude-test", config={})
    assert envelope["error_classification"] == "credential_error"
    assert "ANTHROPIC_API_KEY" in envelope["error_message"]
    assert envelope["response_text"] == ""


def test_openai_adapter_without_api_key_returns_credential_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    envelope = OpenAIAdapter().invoke("hi", model="gpt-test", config={})
    assert envelope["error_classification"] == "credential_error"
    assert envelope["response_text"] == ""


def test_anthropic_adapter_propagates_provider_error(monkeypatch: pytest.MonkeyPatch) -> None:
    import sys
    import types

    class _FakeMessages:
        def create(self, *args, **kwargs):
            raise RuntimeError("upstream 503")

    class _FakeAnthropic:
        def __init__(self, *args, **kwargs):
            self.messages = _FakeMessages()

    fake = types.ModuleType("anthropic")
    fake.Anthropic = _FakeAnthropic
    monkeypatch.setitem(sys.modules, "anthropic", fake)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    envelope = AnthropicAdapter().invoke("hi", model="claude-test", config={})
    assert envelope["error_classification"] == "provider_error"
    assert "upstream 503" in envelope["error_message"]


def test_openai_adapter_propagates_provider_error(monkeypatch: pytest.MonkeyPatch) -> None:
    import sys
    import types

    class _FakeCompletions:
        def create(self, *args, **kwargs):
            raise RuntimeError("rate limit")

    class _FakeChat:
        completions = _FakeCompletions()

    class _FakeOpenAI:
        def __init__(self, *args, **kwargs):
            self.chat = _FakeChat()

    fake = types.ModuleType("openai")
    fake.OpenAI = _FakeOpenAI
    monkeypatch.setitem(sys.modules, "openai", fake)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    envelope = OpenAIAdapter().invoke("hi", model="gpt-test", config={})
    assert envelope["error_classification"] == "provider_error"
    assert "rate limit" in envelope["error_message"]


def test_envelope_omits_credential_environment_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MY_TEST_KEY_VAR", "AKIA_SECRETXYZ000000")
    envelope = EchoAdapter().invoke("hello", model="m", config={})
    assert "AKIA_SECRETXYZ000000" not in repr(envelope)
    assert envelope_has_secret(envelope) is False