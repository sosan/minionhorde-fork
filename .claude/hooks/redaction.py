"""Shared secret-redaction patterns for hooks and audit logging.

The module is deliberately dependency-light: it only uses the standard
library so every hook can import it without installing anything.

Example:
    >>> redact('password = "hunter2hunter2"')[0]
    'password = "[REDACTED:password_assignment]"'
"""

from __future__ import annotations

import re
from typing import Any

TOKEN_PATTERNS: list[tuple[str, str]] = [
    # Cloud
    (r"\b(?:AKIA|ASIA|AIDA|AROA|ANPA|ANVA|ASCA)[A-Z0-9]{16}\b", "aws_access_key"),
    (r"(?i)aws_secret_access_key\s*[=:]\s*['\"]?[A-Za-z0-9/+=]{40}", "aws_secret_key"),
    (r"\bAIza[0-9A-Za-z\-_]{35}\b", "gcp_api_key"),
    (r'"private_key"\s*:\s*"-----BEGIN', "private_key"),
    # Git hosts
    (r"\bgh[pousr]_[A-Za-z0-9]{36,}\b", "github_token"),
    (r"\bgithub_pat_[A-Za-z0-9_]{22,}\b", "github_pat"),
    (r"\bglpat-[A-Za-z0-9_\-]{20,}\b", "gitlab_pat"),
    (r"\bglrt-[A-Za-z0-9_\-]{20,}\b", "gitlab_rt"),
    # AI / SaaS
    (r"\bsk-(?:proj-|svcacct-|ant-)?[A-Za-z0-9\-_]{20,}\b", "openai_anthropic_key"),
    (r"\bhf_[A-Za-z0-9]{30,}\b", "huggingface_token"),
    (r"\br8_[A-Za-z0-9]{20,}\b", "replicate_token"),
    (r"\bgsk_[A-Za-z0-9]{30,}\b", "groq_key"),
    (r"\bdop_v1_[a-z0-9]{32,}\b", "digitalocean_token"),
    (r"\bdp\.st\.[a-z0-9.\-]{20,}\b", "doppler_token"),
    (r"\bshpat_[A-Za-z0-9\-_]{20,}\b", "shopify_token"),
    (r"\bNRAK-[A-Z0-9]{18,}\b", "newrelic_key"),
    (r"\bPMAK-[A-Za-z0-9\-_]{20,}\b", "postman_key"),
    (r"\b(?:secret|ntn)_[A-Za-z0-9]{40,}\b", "notion_token"),
    # Payments / messaging
    (r"\b(?:sk|rk)_live_[A-Za-z0-9]{18,}\b", "stripe_key"),
    (r"\bwhsec_[A-Za-z0-9]{16,}\b", "stripe_webhook_secret"),
    (r"\bSG\.[A-Za-z0-9\-_]{22}\.[A-Za-z0-9\-_]{43}\b", "sendgrid_key"),
    (r"\bxox[baprs]-[A-Za-z0-9\-]{10,}\b", "slack_token"),
    (r"https://hooks\.slack\.com/services/T[A-Z0-9]+/B[A-Z0-9]+/[A-Za-z0-9]+", "slack_webhook"),
    (r"https://discord(?:app)?\.com/api/webhooks/\d+/[A-Za-z0-9\-_]+", "discord_webhook"),
    (r"\b\d{6,10}:AA[A-Za-z0-9\-_]{30,}\b", "telegram_token"),
    # Infra / registries
    (r"\bdckr_pat_[A-Za-z0-9\-_]{20,}\b", "dockerhub_token"),
    (r"\bnpm_[A-Za-z0-9]{36}\b", "npm_token"),
    (r"\bpypi-[A-Za-z0-9\-_]{50,}\b", "pypi_token"),
    (r"\bhvs\.[A-Za-z0-9\-_]{20,}\b", "vault_token"),
    (r"\bAGE-SECRET-KEY-1[0-9A-Z]{50,}\b", "age_secret_key"),
    # Key material (multiline)
    (
        r"-----BEGIN [A-Z ]*PRIVATE KEY(?: BLOCK)?-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY(?: BLOCK)?-----",
        "private_key_block",
    ),
    # Tokens & headers
    (r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b", "jwt"),
    (
        r"Authorization:\s*(?:Bearer|Basic|Token|ApiKey)\s+[A-Za-z0-9\-._~+/=]+",
        "authorization_header",
    ),
    # URL secret parameters
    (
        r"[?&](?:sig|token|key|api_?key|access_token|X-Amz-Signature)=[A-Za-z0-9%\-_.~]{16,}",
        "url_secret_param",
    ),
]

CONNECTION_RE = re.compile(
    r"(?i)((?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis|amqp|mssql|ldap|smb|s?ftp|s3|gs)"
    r"://[^:\s/]+:)([^\s]+?)(@(?=[^@\s/]+(?:[/?#]|\s|$)))"
)

JSON_QUOTED_RE = re.compile(
    r"(?i)([\"'])([A-Za-z0-9_.-]*(?:password|passwd|pwd|secret|token|api[_-]?key|apikey|"
    r"client[_-]?secret|auth[_-]?token|access[_-]?key|private[_-]?key|aws_secret_access_key)"
    r"[A-Za-z0-9_.-]*)\1\s*:\s*([\"'])((?:\\.|(?!\3).)*)\3"
)

JSON_UNQUOTED_RE = re.compile(
    r"(?i)([\"'])([A-Za-z0-9_.-]*(?:password|passwd|pwd|secret|token|api[_-]?key|apikey|"
    r"client[_-]?secret|auth[_-]?token|access[_-]?key|private[_-]?key|aws_secret_access_key)"
    r"[A-Za-z0-9_.-]*)\1\s*:\s*([^\s,}]+)"
)

ENTROPY_RE = re.compile(
    r"(?i)\b(?:key|token|secret|password|passwd|credential|apikey|api_key|auth)\b"
    r"\s*[=:]\s*['\"]?([A-Za-z0-9+/=_-]{32,})['\"]?"
)

PASSWORD_RE = re.compile(
    r"(?i)\b(password|pwd|passwd)\b(\s*[=:]\s*)([\"']?)(?!\[REDACTED:)([^;\s\"']{6,})\3"
)

SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)\b(token|secret|password|passwd|api[_-]?key|apikey|client[_-]?secret|"
    r"auth[_-]?token|access[_-]?key|private[_-]?key|aws_secret_access_key)\b"
    r"(\s*[=:]\s*)([\"']?)(?!\[REDACTED:)([^\s\"']{10,})\3"
)

SECRET_KEY_RE = re.compile(
    r"(?i)^(?:password|passwd|pwd|secret|token|api[_-]?key|apikey|client[_-]?secret|"
    r"auth[_-]?token|access[_-]?key|private[_-]?key|aws_secret_access_key)$"
)


def redact(text: str) -> tuple[str, list[str]]:
    """Redact secrets from ``text`` and return the detected type labels.

    Example:
        >>> redact("postgres://user:S3cr3t@ss@db")
        ('postgres://user:[REDACTED:connection_string]@db', ['connection_string'])
    """
    if not isinstance(text, str) or not text:
        return text, []

    detected: list[str] = []

    def replace_simple(pattern: str, label: str) -> None:
        nonlocal text
        compiled = re.compile(pattern, re.DOTALL)
        if compiled.search(text):
            detected.append(label)
            text = compiled.sub(f"[REDACTED:{label}]", text)

    for pattern, label in TOKEN_PATTERNS:
        replace_simple(pattern, label)

    if CONNECTION_RE.search(text):
        detected.append("connection_string")
        text = CONNECTION_RE.sub(
            lambda m: f"{m.group(1)}[REDACTED:connection_string]{m.group(3)}", text
        )

    def replace_json_quoted(match: re.Match[str]) -> str:
        if match.group(4).startswith("[REDACTED:"):
            return match.group(0)
        detected.append("json_secret")
        return f"{match.group(1)}{match.group(2)}{match.group(1)}: {match.group(3)}[REDACTED:json_secret]{match.group(3)}"

    if JSON_QUOTED_RE.search(text):
        text = JSON_QUOTED_RE.sub(replace_json_quoted, text)

    def replace_json_unquoted(match: re.Match[str]) -> str:
        if match.group(3).startswith("[REDACTED:"):
            return match.group(0)
        detected.append("json_secret")
        return f"{match.group(1)}{match.group(2)}{match.group(1)}: [REDACTED:json_secret]"

    if JSON_UNQUOTED_RE.search(text):
        text = JSON_UNQUOTED_RE.sub(replace_json_unquoted, text)

    if ENTROPY_RE.search(text):
        detected.append("high_entropy_secret")
        text = ENTROPY_RE.sub(
            lambda m: m.group(0).replace(m.group(1), "[REDACTED:high_entropy_secret]"),
            text,
        )

    if PASSWORD_RE.search(text):
        detected.append("password_assignment")
        text = PASSWORD_RE.sub(
            lambda m: f"{m.group(1)}{m.group(2)}{m.group(3)}[REDACTED:password_assignment]{m.group(3)}",
            text,
        )

    if SECRET_ASSIGNMENT_RE.search(text):
        detected.append("secret_assignment")
        text = SECRET_ASSIGNMENT_RE.sub(
            lambda m: f"{m.group(1)}{m.group(2)}{m.group(3)}[REDACTED:secret_assignment]{m.group(3)}",
            text,
        )

    return text, sorted(set(detected))


def redact_obj(value: Any) -> tuple[Any, list[str]]:
    """Recursively redact strings inside dicts/lists and return detected types.

    Example:
        >>> redact_obj({"password": "hunter2hunter2"})[0]
        {'password': '[REDACTED:secret_key]'}
    """
    detected: list[str] = []

    if isinstance(value, str):
        redacted, types = redact(value)
        return redacted, types

    if isinstance(value, list):
        items = []
        for item in value:
            redacted, types = redact_obj(item)
            items.append(redacted)
            detected.extend(types)
        return items, sorted(set(detected))

    if isinstance(value, dict):
        result: dict[Any, Any] = {}
        for key, item in value.items():
            if isinstance(key, str) and SECRET_KEY_RE.match(key) and not isinstance(item, (dict, list)):
                if item not in (None, ""):
                    result[key] = "[REDACTED:secret_key]"
                    detected.append("secret_key")
                else:
                    result[key] = item
                continue
            redacted, types = redact_obj(item)
            result[key] = redacted
            detected.extend(types)
        return result, sorted(set(detected))

    return value, []
