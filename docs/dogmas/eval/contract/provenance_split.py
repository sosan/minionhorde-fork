"""Split provenance hashes per role (task 9.8).

Each evaluation record carries a content hash per provenance role:

    case, prompt_template, assembled_context, criteria, memory, policy,
    partition_manifest

Changing exactly one component MUST change exactly one role hash. The
``attribute_change`` helper reports which single role differs between
two splits and refuses to silently absorb multi-role diffs or no-op
diffs.
"""

from __future__ import annotations

from typing import Any, Mapping

from .canonical import digest

PROVENANCE_ROLES: tuple[str, ...] = (
    "case",
    "prompt_template",
    "assembled_context",
    "criteria",
    "memory",
    "policy",
    "partition_manifest",
)


def split_provenance(components: Mapping[str, Any]) -> dict[str, str]:
    """Return a sha256 hash per provenance role.

    ``components`` maps each role to a JSON-serializable structure. Roles
    absent from the input produce ``""`` so the output is always keyed
    by the full :data:`PROVENANCE_ROLES` tuple.
    """
    result: dict[str, str] = {}
    for role in PROVENANCE_ROLES:
        value = components.get(role)
        if value is None:
            result[role] = ""
            continue
        canonical = _canonical(value)
        result[role] = digest(canonical)
    return result


def attribute_change(before: Mapping[str, str], after: Mapping[str, str]) -> str:
    """Return the single role that differs between ``before`` and ``after``.

    Raises ``ValueError`` when zero roles differ (no-op) or more than
    one role differs (ambiguous attribution).
    """
    diff = [role for role in PROVENANCE_ROLES if before.get(role) != after.get(role)]
    if len(diff) == 0:
        raise ValueError("no provenance role changed; nothing to attribute")
    if len(diff) > 1:
        raise ValueError(
            f"multiple provenance roles changed: {diff}; single-component attribution only"
        )
    return diff[0]


def _canonical(value: Any) -> Any:
    """Stable canonicalization for hashing (sort keys, recurse into containers)."""
    if isinstance(value, Mapping):
        return {key: _canonical(value[key]) for key in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_canonical(item) for item in value]
    return value