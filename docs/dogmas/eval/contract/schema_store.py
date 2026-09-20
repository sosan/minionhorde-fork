"""Schema loading and validation for the modern evaluation contract.

Loads versioned JSON Schemas from ``docs/dogmas/eval/schemas/v1/`` and
validates documents against them. Kept additive relative to the legacy
``results_schema.json`` (see design decision 12).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema

SCHEMAS_DIR = Path(__file__).resolve().parent.parent / "schemas" / "v1"


class SchemaStore:
    def __init__(self, schemas_dir: Path = SCHEMAS_DIR) -> None:
        self.schemas_dir = Path(schemas_dir)
        self._schemas: dict[str, dict] = {}

    def load(self, name: str) -> dict:
        """Load and cache a schema by filename (with or without suffix)."""
        if not name.endswith(".schema.json"):
            name = f"{name}.schema.json"
        if name not in self._schemas:
            path = self.schemas_dir / name
            if not path.exists():
                raise FileNotFoundError(f"schema not found: {path}")
            self._schemas[name] = json.loads(path.read_text(encoding="utf-8"))
        return self._schemas[name]

    def validate(self, name: str, document: Any) -> None:
        """Validate ``document`` against the named schema, raising on failure."""
        schema = self.load(name)
        validator = jsonschema.Draft202012Validator(schema)
        errors = sorted(validator.iter_errors(document), key=lambda e: list(e.path))
        if errors:
            raise SchemaValidationError(errors)

    def validate_into(self, name: str, document: dict) -> None:
        """Validate a document in place, collecting errors on the document."""
        try:
            self.validate(name, document)
        except SchemaValidationError as exc:
            document["validation"] = {"valid": False, "errors": [str(e.message) for e in exc.errors]}
        else:
            document["validation"] = {"valid": True, "errors": []}


class SchemaValidationError(Exception):
    def __init__(self, errors: list) -> None:
        self.errors = errors
        super().__init__(f"schema validation failed with {len(errors)} error(s)")
