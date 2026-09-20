"""Canonical JSON and content hashing for the evaluation contract.

Implements the canonical form required by the trajectory integrity contract
(see the operational-learning spec, "Append-only integrity is verifiable", and
design decision 1):

- UTF-8 output, no ASCII escaping
- object keys sorted by UTF-16 code units (RFC 8785 / JCS ordering)
- no insignificant whitespace
- minimal string escaping
- deterministic numbers: ES6 ``Number::toString`` form, ``-0`` canonicalized to
  ``0``, ``NaN`` and infinities rejected
- a fixed canonicalization version recorded alongside every hash

Only the subset the contract needs is implemented; unsupported values raise.
"""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any

CANONICAL_VERSION = "rfc8785-subset/1"
HASH_ALGORITHM = "sha256"

# Fields excluded from an entry's own content hash (integrity metadata).
INTEGRITY_FIELDS = ("content_hash", "prev_hash")


def _utf16_sort_key(text: str) -> tuple[int, ...]:
    """Sort key using UTF-16 code units, per RFC 8785 key ordering."""
    encoded = text.encode("utf-16-be", "surrogatepass")
    return tuple(int.from_bytes(encoded[i : i + 2], "big") for i in range(0, len(encoded), 2))


def _format_number(value: float) -> str:
    """Render a finite float in ES6 Number::toString form.

    Matches JSON.stringify output for the values the contract stores.
    """
    if math.isnan(value) or math.isinf(value):
        raise ValueError("NaN and Infinity are not representable in canonical JSON")
    if value == 0:
        return "0"  # covers -0.0

    negative = value < 0
    text = repr(abs(value))

    if "e" in text or "E" in text:
        mantissa, exponent = text.lower().split("e")
        exp = int(exponent)
    else:
        mantissa, exp = text, 0

    if "." in mantissa:
        integer_part, fraction_part = mantissa.split(".")
    else:
        integer_part, fraction_part = mantissa, ""

    digits = integer_part + fraction_part
    k_exp = exp - len(fraction_part)

    # Leading zeros do not change int(digits), so the power of ten is unchanged.
    while len(digits) > 1 and digits.startswith("0"):
        digits = digits[1:]
    # Removing a trailing zero divides int(digits) by ten, so compensate by
    # increasing the power of ten.
    while len(digits) > 1 and digits.endswith("0"):
        digits = digits[:-1]
        k_exp += 1

    k = len(digits)
    n = k + k_exp  # value == digits * 10^(n-k)

    if k <= n <= 21:
        rendered = digits + "0" * (n - k)
    elif 0 < n <= 21:
        rendered = digits[:n] + "." + digits[n:]
    elif -6 < n <= 0:
        rendered = "0." + "0" * (-n) + digits
    else:
        head = digits[0]
        rest = digits[1:]
        exponent = n - 1
        sign = "+" if exponent >= 0 else "-"
        rendered = f"{head}.{rest}e{sign}{abs(exponent)}" if rest else f"{head}e{sign}{abs(exponent)}"

    return "-" + rendered if negative else rendered


def _encode(value: Any, out: list[str]) -> None:
    if value is None:
        out.append("null")
    elif value is True:
        out.append("true")
    elif value is False:
        out.append("false")
    elif isinstance(value, str):
        out.append(json.dumps(value, ensure_ascii=False))
    elif isinstance(value, int):
        out.append(str(value))
    elif isinstance(value, float):
        out.append(_format_number(value))
    elif isinstance(value, (list, tuple)):
        out.append("[")
        for index, item in enumerate(value):
            if index:
                out.append(",")
            _encode(item, out)
        out.append("]")
    elif isinstance(value, dict):
        out.append("{")
        for index, key in enumerate(sorted(value, key=_utf16_sort_key)):
            if not isinstance(key, str):
                raise TypeError(f"canonical JSON object keys must be strings, got {type(key)!r}")
            if index:
                out.append(",")
            out.append(json.dumps(key, ensure_ascii=False))
            out.append(":")
            _encode(value[key], out)
        out.append("}")
    else:
        raise TypeError(f"unsupported type for canonical JSON: {type(value)!r}")


def canonical_json(value: Any) -> str:
    """Return the canonical JSON text for ``value``."""
    out: list[str] = []
    _encode(value, out)
    return "".join(out)


def canonical_bytes(value: Any) -> bytes:
    """Return the canonical UTF-8 byte serialization of ``value``."""
    return canonical_json(value).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def content_hash(entry: dict) -> str:
    """Hash an entry's payload, excluding its own integrity metadata fields."""
    payload = {key: value for key, value in entry.items() if key not in INTEGRITY_FIELDS}
    return sha256_hex(canonical_bytes(payload))


def digest(value: Any) -> str:
    """SHA-256 of the canonical serialization of ``value``."""
    return sha256_hex(canonical_bytes(value))
