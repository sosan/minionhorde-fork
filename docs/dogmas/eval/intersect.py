#!/usr/bin/env python3
"""
Computes intersection and dissent across evaluations from multiple models.

Input: JSON result files (one per model).
Output: crystallized memory report + frontier zones.
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

def load_results(results_dir: str) -> list[dict]:
    """Loads all result files."""
    results = []
    results_path = Path(results_dir)

    for result_file in results_path.glob("*.json"):
        data = json.loads(result_file.read_text(encoding="utf-8"))
        results.extend(data)

    return results

def group_by_case(results: list[dict]) -> dict[str, list[dict]]:
    """Groups results by case."""
    grouped = defaultdict(list)
    for r in results:
        grouped[r["case_id"]].append(r)
    return dict(grouped)

def calculate_intersection(case_results: list[dict]) -> dict:
    """
    Computes the intersection for a case.

    - All agree on PASS: crystallized.
    - All agree on FAIL: coverage gap (requires a new rule).
    - Dissent: frontier zone (requires human judgment).
    """
    classifications = [r["classification"] for r in case_results]
    models = [f"{r['provider']}/{r['model']}" for r in case_results]

    # Filter out errors
    valid = [c for c in classifications if c not in ("ERROR", "PENDING")]

    if not valid:
        return {
            "status": "incomplete",
            "reason": "sin evaluaciones válidas",
            "models": models
        }

    # Intersection: all agree
    if len(set(valid)) == 1:
        classification = valid[0]
        if classification == "PASS":
            return {
                "status": "crystallized",
                "classification": classification,
                "models": models,
                "confidence": "high" if len(valid) >= 3 else "medium"
            }
        else:
            return {
                "status": "coverage_gap",
                "classification": classification,
                "models": models,
                "action": "requiere nueva regla o caso de evaluación"
            }

    # Dissent
    return {
        "status": "frontier",
        "classifications": {m: c for m, c in zip(models, classifications)},
        "models": models,
        "action": "zona de juicio humano hasta refinar el marco"
    }

def generate_report(results_dir: str, output_file: str) -> dict:
    """Generates the full crystallization report."""

    results = load_results(results_dir)
    grouped = group_by_case(results)

    report = {
        "summary": {
            "total_cases": len(grouped),
            "total_evaluations": len(results),
            "models": list(set(f"{r['provider']}/{r['model']}" for r in results))
        },
        "crystallized": [],      # PASS intersection
        "coverage_gaps": [],     # FAIL intersection
        "frontier": [],          # Dissent
        "incomplete": []         # Not enough data
    }

    for case_id, case_results in sorted(grouped.items()):
        intersection = calculate_intersection(case_results)

        entry = {
            "case_id": case_id,
            "models": intersection["models"],
            "details": intersection
        }

        if intersection["status"] == "crystallized":
            report["crystallized"].append(entry)
        elif intersection["status"] == "coverage_gap":
            report["coverage_gaps"].append(entry)
        elif intersection["status"] == "frontier":
            report["frontier"].append(entry)
        else:
            report["incomplete"].append(entry)

    # Metrics
    total = len(grouped)
    report["metrics"] = {
        "crystallization_rate": len(report["crystallized"]) / total if total else 0,
        "coverage_gap_rate": len(report["coverage_gaps"]) / total if total else 0,
        "frontier_rate": len(report["frontier"]) / total if total else 0,
        "alignment": len(report["crystallized"]) / total if total else 0
    }

    # Save report
    Path(output_file).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    return report

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Calcula intersección cross-modelo")
    parser.add_argument("--results", required=True, help="Directorio de resultados")
    parser.add_argument("--output", default="eval/report.json", help="Archivo de salida")

    args = parser.parse_args()

    report = generate_report(args.results, args.output)

    print(f"Resumen:")
    print(f"  Casos evaluados: {report['summary']['total_cases']}")
    print(f"  Modelos: {', '.join(report['summary']['models'])}")
    print(f"  Cristalizados (PASS unánime): {len(report['crystallized'])}")
    print(f"  Huecos de cobertura (FAIL unánime): {len(report['coverage_gaps'])}")
    print(f"  Fronteras (disenso): {len(report['frontier'])}")
    print(f"  Tasa de alineación: {report['metrics']['alignment']:.2%}")
    print(f"\nReporte guardado en {args.output}")
