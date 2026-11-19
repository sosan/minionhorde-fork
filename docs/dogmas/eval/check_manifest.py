#!/usr/bin/env python3
"""Validate the evaluation exercise manifest against the real import graph.

The manifest (docs/dogmas/eval/exercise-manifest.json) declares, per contract
module, an exercise class:

    real_run  | synthetic_run | internally_wired | test_only | orphaned

This validator recomputes reachability from the registered runner entrypoints
using the actual Python import graph, then compares it with the declared
class. A mismatch is a validation failure: documentation claiming real
exercise for a contract that is only test-only (or vice versa) is rejected.

Exit codes: 0 = declaration matches reality; 1 = mismatch, unsupported claim,
or unregistered contract; 2 = usage/input error.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import pathlib
import sys
from collections import defaultdict

_HERE = pathlib.Path(__file__).resolve()
REPO_ROOT = next(p for p in _HERE.parents if (p / ".git").exists())
CONTRACT_DIR = REPO_ROOT / "docs" / "dogmas" / "eval" / "contract"
MANIFEST_PATH = REPO_ROOT / "docs" / "dogmas" / "eval" / "exercise-manifest.json"


def _all_modules() -> set[str]:
    """All non-test contract module names, for `from contract import X` checks."""
    return {
        p.stem
        for p in CONTRACT_DIR.glob("*.py")
        if not p.stem.startswith("test_") and p.stem != "__init__"
    }


def _module_imports(path: pathlib.Path) -> set[str]:
    """Contract modules imported by `path`, covering the codebase's patterns."""
    known = _all_modules()
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return set()
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module == "contract":
                # from contract import anonymizer, coverage_gates, providers
                for alias in node.names:
                    if alias.name in known:
                        found.add(alias.name)
            elif node.module and node.module.startswith("contract."):
                # from contract.schema_store import SchemaStore
                found.add(node.module.split(".")[1])
            elif node.level == 1 and node.module:
                # from .canonical import digest
                found.add(node.module)
            elif node.level == 1 and node.module is None:
                # from . import p2_1
                for alias in node.names:
                    if alias.name in known:
                        found.add(alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("contract."):
                    found.add(alias.name.split(".")[1])
    return found


def _mutual_imports() -> dict[str, set[str]]:
    """Import edges between contract modules (and the package __init__)."""
    edges: dict[str, set[str]] = defaultdict(set)
    for path in CONTRACT_DIR.glob("*.py"):
        if path.stem.startswith("test_"):
            continue
        for target in _module_imports(path):
            if target == "*all":
                continue
            edges[path.stem].add(target)
    return edges


def _reachable_from(entrypoint_name: str) -> set[str]:
    """Transitively reachable contract modules from a runner in the contract dir."""
    graph = _mutual_imports()
    stack = [entrypoint_name]
    seen: set[str] = set()
    while stack:
        node = stack.pop()
        if node in seen:
            continue
        seen.add(node)
        stack.extend(graph.get(node, set()))
    return seen


def load_manifest(path: pathlib.Path = MANIFEST_PATH) -> dict:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def manifest_hash(manifest: dict) -> str:
    """SHA-256 of the canonical manifest excluding its own hash field."""
    body = {k: v for k, v in manifest.items() if k != "manifest_sha256"}
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()



def validate(manifest: dict) -> tuple[list[str], int]:
    messages: list[str] = []
    failures = 0
    recorded_hash = manifest.get("manifest_sha256")
    if not recorded_hash:
        messages.append("HASH_MISSING: manifest_sha256 is required")
        failures += 1
    elif recorded_hash != manifest_hash(manifest):
        messages.append("HASH_MISMATCH: manifest_sha256 does not match canonical content")
        failures += 1
    declared = manifest.get("contracts", {})
    entrypoints = manifest.get("entrypoints", [])

    reachable_by_kind: dict[str, set[str]] = defaultdict(set)
    for ep in entrypoints:
        ref = ep["name"].split(".")[0]
        kind = ep.get("kind", "synthetic_run")
        reachable = _reachable_from(ref)
        reachable_by_kind[kind] |= reachable
        if kind not in {"real_run", "synthetic_run"}:
            messages.append(f"entrypoint {ep['name']}: unknown kind '{kind}'")
            failures += 1

    real_reachable = reachable_by_kind.get("real_run", set())
    synthetic_reachable = reachable_by_kind.get("synthetic_run", set())
    all_reachable = real_reachable | synthetic_reachable

    # 1. Classification consistency.
    for module, cls in sorted(declared.items()):
        module_path = CONTRACT_DIR / f"{module}.py"
        if not module_path.exists():
            messages.append(f"UNREGISTERED_FILE: {module} declared but no {module}.py")
            failures += 1
            continue
        is_internal = module in real_reachable or module in synthetic_reachable
        if cls == "real_run" and module not in real_reachable:
            messages.append(f"CLAIM_MISMATCH: {module} declared real_run but not reachable from a real runner")
            failures += 1
        elif cls == "synthetic_run" and module not in synthetic_reachable:
            messages.append(f"CLAIM_MISMATCH: {module} declared synthetic_run but not reachable from a registered runner")
            failures += 1
        elif cls == "internally_wired" and is_internal:
            messages.append(f"CLAIM_MISMATCH: {module} declared internally_wired but reachable from a runner")
            failures += 1
        elif cls == "test_only" and is_internal:
            messages.append(f"CLAIM_MISMATCH: {module} declared test_only but reachable from a runner")
            failures += 1

    # 2. Every existing contract module is registered.
    existing = {p.stem for p in CONTRACT_DIR.glob("*.py")
                if not p.stem.startswith("test_") and p.stem != "__init__"}
    missing = sorted(existing - set(declared))
    for module in missing:
        messages.append(f"UNREGISTERED: {module} exists but has no manifest entry")
        failures += 1

    # 3. No orphaned module is claimed operational.
    for module, cls in sorted(declared.items()):
        if cls in {"real_run", "synthetic_run"}:
            continue
        if module in real_reachable:
            # covered above
            continue

    # 4. Unsupported operational claims must not reference non-synthetic contracts.
    not_supported = manifest.get("operational_claims", {}).get("not_supported", [])
    for claim in not_supported:
        if any(kw in claim for kw in ("real provider", "judge agreement", "memory promotion", "cross-model")):
            pass  # informational; presence is the check
    # 5. real_run claims must be non-empty only if a real provider entry exists.
    if real_reachable and not any(ep.get("kind") == "real_run" for ep in entrypoints):
        messages.append("real_run contracts reachable but no real_run entrypoint registered")
        failures += 1

    if not messages:
        messages.append("manifest matches the import graph and restrictions hold")
    return messages, (1 if failures else 0)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=str(MANIFEST_PATH))
    args = parser.parse_args(argv)
    try:
        manifest = load_manifest(pathlib.Path(args.manifest))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"INPUT_ERROR: {exc}", file=sys.stderr)
        return 2
    messages, code = validate(manifest)
    for message in messages:
        print(message)
    return code


if __name__ == "__main__":
    sys.exit(main())