#!/usr/bin/env python3
"""Dogma system metrics over the existing evaluation results.

Reads the JSON files in eval/results/ and computes:
- Global and per-model PASS/PARTIAL/FAIL distribution
- Per-model coverage (n) and number of distinct passes
- Coverage per category (canonicals, appendixD, pass2, pass3)
- Evidence type: textual (real model response) vs summary
- Alignment(t): classification stability for the same case across passes

Usage:
    python3 eval/metrics.py            # Markdown report
    python3 eval/metrics.py --json     # JSON report

Known limitations (printed at the end of the report):
- JSON files with 'justification' are generated summaries, not transcripts.
- Coverage is uneven across models (not all have n=3).
- A reported PASS is not the same as an independently verified PASS.
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

RESULTS_DIR = Path(__file__).resolve().parent / "results"


def load_all():
    """Loads all JSON files in results/. Returns a list of (name, items)."""
    datasets = []
    for path in sorted(RESULTS_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError) as exc:
            print(f"WARN: no se pudo leer {path.name}: {exc}", file=sys.stderr)
            continue
        if not isinstance(data, list):
            print(f"WARN: {path.name} no es una lista; se ignora", file=sys.stderr)
            continue
        datasets.append((path.name, data))
    return datasets


def classify_file(name):
    """File category based on its name."""
    stem = name[:-5] if name.endswith(".json") else name
    if stem.startswith("pass2-"):
        return "pass2"
    if stem.startswith("pass3-"):
        return "pass3"
    if stem.endswith("-appendixD"):
        return "appendixD"
    if stem.endswith("-canonicos"):
        return "canonicos"
    return "other"


def evidence_kind(items):
    """Textual if items cite an evidence source; summary otherwise."""
    if not items:
        return "empty"
    sample = items[0]
    if "evidencia" in sample:
        return "textual"
    if "justification" in sample or "dimensions" in sample:
        return "resumen"
    return "desconocido"


def normalize_classification(item):
    """Returns PASS | PARTIAL | FAIL | CAMBIADO | UNKNOWN."""
    if "classification" in item:
        val = item["classification"]
        if isinstance(val, bool):
            return "PASS" if val else "FAIL"
        if isinstance(val, str) and val.strip():
            return val.strip().upper()
    if "pass" in item:
        val = item["pass"]
        if isinstance(val, bool):
            return "PASS" if val else "FAIL"
    return "UNKNOWN"


def pass_number(name):
    """Pass number inferred from the file name."""
    if name.startswith("pass3-"):
        return 3
    if name.startswith("pass2-"):
        return 2
    return 1


def summarize(datasets):
    models = defaultdict(lambda: defaultdict(int))
    by_category = defaultdict(int)
    by_evidence = defaultdict(int)
    total = 0
    for name, items in datasets:
        cat = classify_file(name)
        kind = evidence_kind(items)
        by_evidence[kind] += 1
        for item in items:
            total += 1
            model = item.get("model") or "unknown"
            cls = normalize_classification(item)
            models[model][cls] += 1
            models[model]["n"] += 1
            by_category[cat] += 1
    return models, by_category, by_evidence, total


def model_passes(datasets):
    """Counts distinct passes (by number) and max n per model."""
    passes = defaultdict(set)
    counts = defaultdict(int)
    for name, items in datasets:
        pnum = pass_number(name)
        for item in items:
            model = item.get("model") or "unknown"
            passes[model].add(pnum)
            counts[model] += 1
    return {m: {"passes": len(passes[m]), "n": counts[m]} for m in passes}


def stability(datasets):
    """Alignment(t): same (case_id, model) classified equally across passes."""
    seen = defaultdict(list)
    for name, items in datasets:
        pnum = pass_number(name)
        for item in items:
            case = item.get("case_id")
            model = item.get("model") or "unknown"
            if case is None:
                continue
            seen[(case, model)].append((pnum, normalize_classification(item)))
    stable = comparable = 0
    for pairs in seen.values():
        if len(pairs) < 2:
            continue
        comparable += 1
        if len({cls for _, cls in pairs}) == 1:
            stable += 1
    return stable, comparable, len(seen)


def build_report(datasets):
    models, by_category, by_evidence, total = summarize(datasets)
    coverage = model_passes(datasets)
    stable, comparable, cases = stability(datasets)

    agg = defaultdict(int)
    for counts in models.values():
        for cls, value in counts.items():
            if cls != "n":
                agg[cls] += value

    return {
        "total": total,
        "by_classification": dict(agg),
        "by_category": dict(by_category),
        "by_evidence": dict(by_evidence),
        "models": {m: dict(c) for m, c in models.items()},
        "coverage": coverage,
        "stability": {
            "stable": stable,
            "comparable": comparable,
            "cases": cases,
            "rate": (stable / comparable) if comparable else 0.0,
        },
    }


def print_markdown(rep):
    total = rep["total"] or 1
    agg = rep["by_classification"]

    print("# Métricas del Sistema de Dogmas\n")
    print("## Resumen global\n")
    print(f"- Total de evaluaciones: {rep['total']}")
    for cls in ("PASS", "PARTIAL", "FAIL", "CAMBIADO", "UNKNOWN"):
        if agg.get(cls):
            print(f"- {cls}: {agg[cls]} ({100 * agg[cls] / total:.1f}%)")
    print(f"- Modelos evaluados: {len(rep['models'])}\n")

    print("## Cobertura por modelo\n")
    print("| Modelo | n | pasadas | PASS | PARTIAL | FAIL | Tasa PASS |")
    print("|---|---|---|---|---|---|---|")
    for model in sorted(rep["models"], key=lambda m: -rep["models"][m]["n"]):
        counts = rep["models"][model]
        n = counts["n"]
        p = counts.get("PASS", 0)
        pa = counts.get("PARTIAL", 0)
        f = counts.get("FAIL", 0)
        passes = rep["coverage"].get(model, {}).get("passes", 0)
        print(f"| {model} | {n} | {passes} | {p} | {pa} | {f} | {100 * p / n:.1f}% |")
    print()

    print("## Cobertura por categoría\n")
    for cat in sorted(rep["by_category"]):
        print(f"- {cat}: {rep['by_category'][cat]} archivos")
    print()

    print("## Tipo de evidencia\n")
    for kind in sorted(rep["by_evidence"]):
        print(f"- {kind}: {rep['by_evidence'][kind]} archivos")
    print()

    st = rep["stability"]
    print("## Alineación (estabilidad entre pasadas)\n")
    print(f"- Casos comparables (mismo caso+modelo en ≥2 pasadas): {st['comparable']}")
    print(f"- Casos estables: {st['stable']}")
    print(f"- Tasa de estabilidad: {st['rate']:.1%}")
    print()

    print("## Limitaciones\n")
    print("- Los archivos con 'justification' son resúmenes generados, no transcripciones literales.")
    print("- La cobertura es desigual: no todos los modelos tienen el mismo número de pasadas.")
    print("- Un PASS reportado no equivale a un PASS verificado independientemente.")
    print("- El claim estadístico global requiere n≥3 por modelo y 30 casos por categoría.")


def print_json(rep):
    print(json.dumps(rep, indent=2, ensure_ascii=False))


def main():
    datasets = load_all()
    if not datasets:
        print("No hay archivos JSON en eval/results/", file=sys.stderr)
        return 1
    rep = build_report(datasets)
    if "--json" in sys.argv:
        print_json(rep)
    else:
        print_markdown(rep)
    return 0


if __name__ == "__main__":
    sys.exit(main())
