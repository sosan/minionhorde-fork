#!/usr/bin/env python3
"""
Output Redaction Layer — Appendix A regex (B.6)

Intercepta la salida de herramientas en PostToolUse y redacta secretos
antes de que lleguen al modelo. Usa los patrones del Appendix A de
docs/agent_security_policy.md más la heurística de entropía (Appendix A).

Uso: hook PostToolUse (matcher Bash|Write|Edit|Read). Lee JSON de stdin,
devuelve updatedToolOutput con el stdout redactado si hubo coincidencias.

No requiere infraestructura externa. Registra redacciones en el audit log.
"""

import json
import re
import sys
from datetime import datetime, timezone

# --- Patrones del Appendix A (starter set) ---
PATTERNS = [
    # Cloud
    (r"\b(?:AKIA|ASIA|AIDA|AROA|ANPA|ANVA|ASCA)[A-Z0-9]{16}\b", "aws_access_key"),
    (r"aws_secret_access_key\s*[=:]\s*['\"]?[A-Za-z0-9/+=]{40}", "aws_secret_key"),
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
    # Key material (multiline/DOTALL)
    (r"-----BEGIN [A-Z ]*PRIVATE KEY(?: BLOCK)?-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY(?: BLOCK)?-----", "private_key_block"),
    # Tokens & headers
    (r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b", "jwt"),
    (r"Authorization:\s*(?:Bearer|Basic|Token|ApiKey)\s+[A-Za-z0-9\-._~+/=]+", "authorization_header"),
    # Connection strings & assignments
    (r"(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis|amqp|mssql|ldap|smb|s?ftp|s3|gs)://[^:\s/]+:[^@\s/]+@", "connection_string"),
    (r"(?i)(?:password|pwd|passwd)\s*=\s*[^;\s'\"]{6,}", "password_assignment"),
    (r"(?i)\b(?:token|secret|password|passwd|api[_-]?key|apikey|client[_-]?secret|auth[_-]?token|access[_-]?key|private[_-]?key)\b\s*[=:]\s*['\"]?[^\s'\"]{10,}", "secret_assignment"),
    (r"[?&](?:sig|token|key|api_?key|access_token|X-Amz-Signature)=[A-Za-z0-9%\-_.~]{16,}", "url_secret_param"),
]

# Heurística de entropía (Appendix A): identifier con nombre tipo secreto
# cuyo valor es ≥32 caracteres alfanuméricos sin espacios → tratar como secreto
ENTROPY_PATTERN = re.compile(
    r"(?i)\b(?:key|token|secret|password|passwd|credential|apikey|api_key|auth)"
    r"\s*[=:]\s*['\"]?([A-Za-z0-9+/=_-]{32,})['\"]?"
)


def redact(text: str) -> tuple[str, list[str]]:
    """Aplica todos los patrones. Devuelve (texto redactado, types detectados)."""
    detected = []

    for pattern, label in PATTERNS:
        compiled = re.compile(pattern, re.DOTALL)
        if compiled.search(text):
            detected.append(label)
            text = compiled.sub(f"[REDACTED:{label}]", text)

    # Heurística de entropía
    for match in ENTROPY_PATTERN.finditer(text):
        value = match.group(1)
        if value and len(value) >= 32:
            detected.append("high_entropy_secret")
            start, end = match.start(1), match.end(1)
            text = text[:start] + "[REDACTED:high_entropy_secret]" + text[end:]

    return text, sorted(set(detected))


def audit_log(event: str, tool: str, target: str, types: list[str]) -> None:
    """Registra en el audit log (sin secretos)."""
    import os
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", ".")
    log_dir = os.path.join(project_dir, ".claude", "audit")
    os.makedirs(log_dir, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    entry = (
        f"- timestamp: {timestamp}\n"
        f"  event: {event}\n"
        f"  tool: {tool}\n"
        f"  target: {target}\n"
        f"  redacted_types: {','.join(types)}\n"
    )
    with open(os.path.join(log_dir, "audit.log"), "a", encoding="utf-8") as f:
        f.write(entry)


def main() -> int:
    input_json = sys.stdin.read()
    if not input_json.strip():
        return 0

    try:
        data = json.loads(input_json)
    except json.JSONDecodeError:
        return 0

    tool_name = data.get("tool_name", "unknown")
    tool_input = data.get("tool_input", {})
    tool_response = data.get("tool_response", {})

    # Solo redactamos salida de herramientas que pueden devolver texto
    if tool_name not in ("Bash", "Read", "Write", "Edit", "WebFetch", "WebSearch"):
        return 0

    # Extraer stdout (Bash) o contenido (Read/WebFetch)
    stdout = ""
    if isinstance(tool_response, dict):
        stdout = tool_response.get("stdout", "")
    elif isinstance(tool_response, str):
        stdout = tool_response

    if not stdout:
        return 0

    redacted, types = redact(stdout)

    if not types:
        return 0

    # Registrar en audit log (solo types, sin secretos)
    target = tool_input.get("file_path", tool_input.get("command", ""))[:80]
    audit_log("secret_redacted", tool_name, target, types)

    # Devolver output redactado al modelo
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "updatedToolOutput": {
                "stdout": redacted,
                "stderr": tool_response.get("stderr", "") if isinstance(tool_response, dict) else "",
                "interrupted": False,
                "isImage": False,
            },
            "additionalContext": (
                f"[REDACTION] Secrets were redacted from the output of {tool_name} "
                f"(types: {', '.join(types)}). The command already ran; only the output "
                f"was hidden. Do not retry the command to 'see' the value."
            ),
        }
    }

    sys.stdout.write(json.dumps(output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
