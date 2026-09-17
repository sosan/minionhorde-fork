#!/usr/bin/env python3
"""Integrity validation for the evaluation dataset.

Checks, without modifying anything:
- Each JSON is a list of objects.
- Required fields per entry: case_id, model, classification.
- classification in {PASS, PARTIAL, FAIL, CAMBIADO}.
- case_id with expected format (case-NN).
- No duplicates (case_id, model, pass).
- pass consistent with the file name.
- Count per classification and per model.

Usage:
    python3 eval/validate.py
    python3 eval/validate.py --verbose

Output: list of problems (if any) and summary. Exit 1 if problems found.
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

RESULTS_DIR = Path(__file__).resolve().parent / "results"

REQUIRED = ("case_id", "model", "classification")
VALID_CLASSES = {"PASS", "PARTIAL", "FAIL", "CAMBIADO"}
# Two conventions coexist: 'case-NN' and 'path/slug' (e.g. appendixD/secrets-env-dump)
CASE_NN_RE = re.compile(r"^case-\d{2}$")
CASE_SLUG_RE = re.compile(r"^[a-zA-Z0-9_-]+/[a-zA-Z0-9_.-]+$")


def case_id_kind(cid):
    cid = str(cid)
    if CASE_NN_RE.match(cid):
        return "case-NN"
    if CASE_SLUG_RE.match(cid):
        return "slug"
    return "otro"


def expected_pass(filename):
    if filename.startswith("pass3-"):
        return 3
    if filename.startswith("pass2-"):
        return 2
    return 1


def main():
    verbose = "--verbose" in sys.argv
    problems = []
    total = 0
    by_class = Counter()
    by_model = defaultdict(Counter)
    seen_keys = {}
    formats_by_model = {}

    files = sorted(RESULTS_DIR.glob("*.json"))
    if not files:
        print("ERROR: no hay archivos JSON en results/")
        return 1

    for path in files:
        try:
            data = json.loads(path.read_text())
        except json.JSONDecodeError as exc:
            problems.append(f"{path.name}: JSON invalido ({exc})")
            continue
        if not isinstance(data, list):
            problems.append(f"{path.name}: la raiz no es una lista")
            continue

        exp = expected_pass(path.name)
        for idx, item in enumerate(data):
            total += 1
            where = f"{path.name}[{idx}]"

            if not isinstance(item, dict):
                problems.append(f"{where}: no es un objeto")
                continue

            for field in REQUIRED:
                if field not in item or item[field] in (None, ""):
                    problems.append(f"{where}: falta '{field}'")

            cid = item.get("case_id", "")
            if cid:
                kind = case_id_kind(cid)
                if kind == "otro":
                    problems.append(f"{where}: case_id con formato inesperado '{cid}'")
                else:
                    formats_by_model.setdefault(
                        item.get("model", "unknown"), set()
                    ).add(kind)

            cls = item.get("classification", "")
            if cls and cls not in VALID_CLASSES:
                problems.append(f"{where}: classification invalida '{cls}'")

            pnum = item.get("pass")
            if pnum is not None and pnum != exp:
                problems.append(
                    f"{where}: pass={pnum} no coincide con el archivo (esperado {exp})"
                )

            key = (path.name, str(cid), str(item.get("model")), str(item.get("pass")))
            if key in seen_keys:
                problems.append(f"{where}: duplicado (visto en {seen_keys[key]})")
            else:
                seen_keys[key] = where

            if cls in VALID_CLASSES:
                by_class[cls] += 1
            by_model[item.get("model", "unknown")][cls] += 1

    # Detect models mixing case_id formats across passes
    mixed = {m: sorted(k) for m, k in formats_by_model.items() if len(k) > 1}
    if mixed:
        print("MEZCLA DE FORMATOS DE case_id (rompe el calculo de alineacion):")
        for m, kinds in sorted(mixed.items()):
            print(f"  - {m}: {kinds}")
        problems.append(f"{len(mixed)} modelo(s) mezclan formatos de case_id")
        print()

    print(f"Archivos: {len(files)}")
    print(f"Entradas: {total}")
    print()
    print("Clasificacion:", dict(by_class))
    print()
    print("Por modelo:")
    for m in sorted(by_model):
        print(f"  {m:16s} {dict(by_model[m])}")
    print()

    if problems:
        print(f"PROBLEMAS: {len(problems)}")
        for p in (problems if verbose else problems[:20]):
            print(f"  - {p}")
        if not verbose and len(problems) > 20:
            print(f"  ... y {len(problems)-20} mas (usa --verbose)")
        return 1

    print("OK: sin problemas de integridad")
    return 0


if __name__ == "__main__":
    sys.exit(main())
