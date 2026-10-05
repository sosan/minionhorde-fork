"""Provider adapters returning structured envelopes.

Each adapter returns a ``ProviderAdapterEnvelope`` (validated against
``schemas/v1/adapter_envelope.schema.json``) rather than a bare response
string. The envelope records response text, requested and provider-served
model, sampling parameters, usage when available, latency, request
identifier, and error classification.

Credentials are read from environment variables inside each adapter but
are NEVER placed in the envelope or returned to callers. The adapter
contract itself holds no secret state. The local ``echo`` adapter is
intended for safe-suite runs that must not contact any provider.

Unsupported metadata is recorded as ``"unknown"``; this module never
fabricates values.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import os
from typing import Any, Mapping, Protocol


class AdapterError(RuntimeError):
    """Raised when an adapter cannot produce a usable envelope."""


class ProviderAdapter(Protocol):
    name: str

    def invoke(self, prompt: str, *, model: str, config: Mapping[str, Any]) -> dict[str, Any]:
        ...


@dataclass(frozen=True)
class AdapterResult:
    envelope: dict[str, Any]


_SECRET_ENV_KEYS = {
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "GOOGLE_API_KEY",
    "AZURE_OPENAI_API_KEY",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "HF_TOKEN",
    "GITHUB_TOKEN",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _empty_envelope(provider: str, requested_model: str, error_classification: str = "none") -> dict[str, Any]:
    return {
        "schema_version": "v1",
        "provider": provider,
        "requested_model": requested_model,
        "response_text": "",
        "served_model": "unknown",
        "served_model_status": "unknown",
        "sampling_parameters": {},
        "usage": {
            "input_tokens": None,
            "output_tokens": None,
            "total_tokens": None,
        },
        "latency_ms": None,
        "request_id": "unknown",
        "error_classification": error_classification,
        "error_message": "",
        "retries": 0,
    }


def envelope_has_secret(envelope: Mapping[str, Any]) -> bool:
    """Return True if any field in the envelope carries a secret value."""
    serialized = repr(envelope).lower()
    for marker in ("sk-", "ghp_", "gho_", "ghu_", "ghs_", "xoxb-", "xoxp-", "akia", "-----begin"):
        if marker in serialized:
            return True
    for key, value in os.environ.items():
        if not value:
            continue
        if key.upper() in _SECRET_ENV_KEYS and value in serialized:
            return True
        if "key" in key.lower() and len(value) >= 16 and value in serialized:
            return True
        if "token" in key.lower() and len(value) >= 16 and value in serialized:
            return True
        if "password" in key.lower() and len(value) >= 6 and value in serialized:
            return True
    return False


class EchoAdapter:
    """Deterministic local adapter that never calls a provider.

    The echo adapter returns a deterministic short response derived from
    the prompt hash. It is intended for safe-suite runs and CI gating
    where contacting a real provider is forbidden.
    """

    name = "echo"

    def invoke(self, prompt: str, *, model: str, config: Mapping[str, Any]) -> dict[str, Any]:
        prompt_hash = _hash(prompt)[:16]
        response_text = f"[echo:{prompt_hash}]"
        envelope = _empty_envelope(self.name, model)
        envelope.update({
            "response_text": response_text,
            "served_model": model,
            "served_model_status": "reported",
            "sampling_parameters": {"raw": "echo-deterministic", "temperature": 0.0},
            "usage": {"input_tokens": len(prompt), "output_tokens": len(response_text), "total_tokens": len(prompt) + len(response_text)},
            "latency_ms": 0,
            "request_id": f"echo-{prompt_hash}",
        })
        return envelope


class AnthropicAdapter:
    name = "anthropic"

    def invoke(self, prompt: str, *, model: str, config: Mapping[str, Any]) -> dict[str, Any]:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            return self._envelope_error(model, "credential_error", "ANTHROPIC_API_KEY missing")
        try:
            import anthropic  # type: ignore
        except ImportError as exc:
            raise AdapterError("anthropic SDK is required for the anthropic adapter") from exc

        client = anthropic.Anthropic(api_key=api_key)
        max_tokens = int(config.get("max_tokens", 1024))
        temperature = config.get("temperature", "unknown")
        started = datetime.now(timezone.utc)
        try:
            message = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception as exc:
            return self._envelope_error(model, "provider_error", str(exc))
        elapsed = (datetime.now(timezone.utc) - started).total_seconds() * 1000.0
        response_text = "".join(block.text for block in message.content if getattr(block, "type", None) == "text")
        envelope = _empty_envelope(self.name, model)
        envelope.update({
            "response_text": response_text,
            "served_model": getattr(message, "model", model),
            "served_model_status": "reported" if getattr(message, "model", None) else "unknown",
            "sampling_parameters": {"raw": "configured", "temperature": temperature},
            "usage": {
                "input_tokens": getattr(getattr(message, "usage", None), "input_tokens", None),
                "output_tokens": getattr(getattr(message, "usage", None), "output_tokens", None),
                "total_tokens": None,
            },
            "latency_ms": elapsed,
            "request_id": getattr(message, "id", "unknown"),
        })
        return envelope

    def _envelope_error(self, model: str, classification: str, message: str) -> dict[str, Any]:
        envelope = _empty_envelope(self.name, model, error_classification=classification)
        envelope["error_message"] = message
        return envelope


class OpenAIAdapter:
    name = "openai"

    def invoke(self, prompt: str, *, model: str, config: Mapping[str, Any]) -> dict[str, Any]:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return self._envelope_error(model, "credential_error", "OPENAI_API_KEY missing")
        try:
            import openai  # type: ignore
        except ImportError as exc:
            raise AdapterError("openai SDK is required for the openai adapter") from exc

        client = openai.OpenAI(api_key=api_key)
        max_tokens = int(config.get("max_tokens", 1024))
        temperature = config.get("temperature", "unknown")
        started = datetime.now(timezone.utc)
        try:
            response = client.chat.completions.create(
                model=model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception as exc:
            return self._envelope_error(model, "provider_error", str(exc))
        elapsed = (datetime.now(timezone.utc) - started).total_seconds() * 1000.0
        choice = response.choices[0] if response.choices else None
        text = getattr(getattr(choice, "message", None), "content", "") if choice else ""
        usage = getattr(response, "usage", None)
        envelope = _empty_envelope(self.name, model)
        envelope.update({
            "response_text": text or "",
            "served_model": getattr(response, "model", model),
            "served_model_status": "reported" if getattr(response, "model", None) else "unknown",
            "sampling_parameters": {"raw": "configured", "temperature": temperature},
            "usage": {
                "input_tokens": getattr(usage, "prompt_tokens", None),
                "output_tokens": getattr(usage, "completion_tokens", None),
                "total_tokens": getattr(usage, "total_tokens", None),
            },
            "latency_ms": elapsed,
            "request_id": getattr(response, "id", "unknown"),
        })
        return envelope

    def _envelope_error(self, model: str, classification: str, message: str) -> dict[str, Any]:
        envelope = _empty_envelope(self.name, model, error_classification=classification)
        envelope["error_message"] = message
        return envelope


REGISTRY: dict[str, ProviderAdapter] = {
    "echo": EchoAdapter(),
    "anthropic": AnthropicAdapter(),
    "openai": OpenAIAdapter(),
}


def get_adapter(name: str) -> ProviderAdapter:
    if name not in REGISTRY:
        raise AdapterError(f"unknown adapter: {name}; available: {sorted(REGISTRY)}")
    return REGISTRY[name]


def run_controlled_condition(
    adapter_name: str,
    *,
    prompt: str,
    model: str,
    config: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Run one controlled-condition invocation and return its envelope.

    The function NEVER persists secrets and never echoes credentials back.
    If the envelope accidentally contains a secret, callers can detect it
    with :func:`envelope_has_secret`.
    """
    adapter = get_adapter(adapter_name)
    envelope = adapter.invoke(prompt, model=model, config=config or {})
    envelope.setdefault("timestamp", _now())
    if envelope_has_secret(envelope):
        raise AdapterError("refusing to return envelope containing secret-like content")
    return envelope


def list_supported_conditions() -> tuple[str, ...]:
    """Return the canonical four-condition labels.

    The labels are bound to the adapter contract here so that the safe
    runner can iterate them deterministically.
    """
    return ("base", "criteria", "criteria_memory", "full")