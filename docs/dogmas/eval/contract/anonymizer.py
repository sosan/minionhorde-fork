"""Anonymized report builder for evaluation results.

Implements the rules documented in ``docs/dogmas/eval/anonymize.md``:

* Strip credential patterns, full prompts, full responses, and internal
  repository paths.
* Keep ``prompt_hash``, ``case_id``, ``classification``, ``justification``
  (after secret scan), dimensions, model, provider, and timestamp.
* Tag the evidence mode so the consumer knows whether a literal was
  available or only a hash.

The anonymizer is intentionally additive: it never reads source files
beyond the path it receives. Operators are expected to invoke this
module on already-classified results.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Iterable, Mapping


_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"gh[pousr]_[A-Za-z0-9]{18,}", re.IGNORECASE),
    re.compile(r"github_pat_[A-Za-z0-9_]{18,}", re.IGNORECASE),
    re.compile(r"sk-[A-Za-z0-9]{20,}", re.IGNORECASE),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}", re.IGNORECASE),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"),
    re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |)PRIVATE KEY-----[\s\S]+?-----END (?:RSA |EC |DSA |OPENSSH |)PRIVATE KEY-----"),
)

_PROMPT_FIELDS = ("prompt", "prompt_text", "full_prompt", "messages", "request_payload")
_RESPONSE_FIELDS = ("response", "response_text", "full_response", "output_text", "answer")

_INTERNAL_PATH_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"/mnt/[A-Za-z0-9]+/[A-Za-z0-9_/.+-]+"),
    re.compile(r"/home/[a-z]+/[A-Za-z0-9_/.+-]+"),
    re.compile(r"~?/[A-Za-z0-9_./-]+/[A-Za-z0-9_./-]+\.py"),
)

ALLOWED_TOP_LEVEL_KEYS = {
    "case_id",
    "case_version",
    "case_hash",
    "prompt_hash",
    "model",
    "provider",
    "requested_model",
    "served_model",
    "served_model_status",
    "sampling_parameters",
    "sampling",
    "condition",
    "repetition_id",
    "pair_key",
    "classification",
    "justification",
    "dimensions",
    "timestamp",
    "evidence_mode",
    "provenance_status",
    "repetitions",
    "scope",
    "verdict",
    "reasons",
}


def _hash_str(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _scrub_secrets(value: str) -> tuple[str, bool]:
    mutated = False
    for pattern in _SECRET_PATTERNS:
        new_value = pattern.sub("[REDACTED]", value)
        if new_value != value:
            mutated = True
            value = new_value
    return value, mutated


def _scrub_paths(value: str) -> tuple[str, bool]:
    mutated = False
    for pattern in _INTERNAL_PATH_PATTERNS:
        new_value = pattern.sub("[REDACTED-PATH]", value)
        if new_value != value:
            mutated = True
            value = new_value
    return value, mutated


def _scrub_value(value: Any) -> tuple[Any, bool]:
    if isinstance(value, str):
        scrubbed, changed = _scrub_secrets(value)
        scrubbed, changed_paths = _scrub_paths(scrubbed)
        return scrubbed, changed or changed_paths
    if isinstance(value, list):
        mutated = False
        out = []
        for item in value:
            new_item, changed = _scrub_value(item)
            mutated = mutated or changed
            out.append(new_item)
        return out, mutated
    if isinstance(value, dict):
        mutated = False
        out = {}
        for key, inner in value.items():
            new_inner, changed = _scrub_value(inner)
            mutated = mutated or changed
            out[key] = new_inner
        return out, mutated
    return value, False


def _prompt_hash(record: Mapping[str, Any]) -> str:
    for field in _PROMPT_FIELDS:
        if field in record and record[field]:
            return _hash_str(str(record[field]))
    return "unknown"


def _strip_prompt(record: Mapping[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in record.items():
        if key in _PROMPT_FIELDS:
            continue
        if key in _RESPONSE_FIELDS:
            continue
        out[key] = value
    return out


def anonymize_record(record: Mapping[str, Any]) -> dict[str, Any]:
    """Return an anonymized view of ``record``.

    The returned dict contains only allowed top-level keys plus a
    ``prompt_hash`` computed from any prompt field that was present.
    The function does NOT mutate the original record.
    """
    base = _strip_prompt(record)
    scrubbed, _ = _scrub_value(base)

    safe_justification = scrubbed.get("justification", "")
    if isinstance(safe_justification, str):
        safe_justification, _ = _scrub_secrets(safe_justification)
        safe_justification, _ = _scrub_paths(safe_justification)
        scrubbed["justification"] = safe_justification

    anonymized: dict[str, Any] = {}
    for key in ALLOWED_TOP_LEVEL_KEYS:
        if key in scrubbed:
            anonymized[key] = scrubbed[key]

    anonymized["prompt_hash"] = _prompt_hash(record)

    literal_available = bool(
        (record.get("response_text") and str(record["response_text"]).strip())
        or (record.get("response") and str(record["response"]).strip())
    )
    if literal_available:
        anonymized["response_hash"] = _hash_str(str(record.get("response_text") or record.get("response")))
        anonymized["evidence_mode"] = "literal"
    else:
        anonymized["evidence_mode"] = "hash_only"

    return anonymized


def anonymize_results(records: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [anonymize_record(r) for r in records]


def build_anonymized_report(
    records: Iterable[Mapping[str, Any]],
    *,
    scope_label: str = "scope: unknown",
) -> dict[str, Any]:
    """Return a structured anonymized report.

    The report contains only hashes, identifiers, classifications, and
    dimensions. No prompt text, response text, credentials, or internal
    paths can leak through this builder.
    """
    items = anonymize_results(records)
    return {
        "report_format": "anonymized_v1",
        "scope_label": scope_label,
        "n_records": len(items),
        "items": items,
    }


def contains_secret(value: Any) -> bool:
    """Return True if ``value`` matches any known secret or path pattern."""
    scrubbed, changed = _scrub_value(value)
    return changed


def to_json(payload: Any) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False)