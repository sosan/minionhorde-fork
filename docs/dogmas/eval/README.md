# Local evaluation package — Cross-model crystallization

This package lets you run the evaluation cases across multiple model families
locally, without sharing credentials with third parties.

## Structure

- `run_eval.py` — runs cases against local models.
- `results_schema.json` — standardized output schema.
- `intersect.py` — computes intersection and dissent across models.
- `anonymize.md` — instructions for anonymizing results before sharing.

## Usage

1. Configure the APIs in your environment (environment variables, never in code).
2. Run `run_eval.py` for each model.
3. Run `intersect.py` to consolidate.
4. Anonymize per `anonymize.md`.
5. Share only the aggregated results.

## Contract exercise manifest

`exercise-manifest.json` is the content-addressed inventory of evaluation
contracts and their evidence status. `check_manifest.py` recomputes reachability
from registered runner entrypoints and validates that `real_run`,
`synthetic_run`, `internally_wired`, and `test_only` declarations match the
actual import graph. Run:

```bash
python3 docs/dogmas/eval/check_manifest.py
```

The current safe runner uses the deterministic `echo` adapter. It provides
synthetic protocol evidence only; the manifest deliberately supports no real
provider claims, judge-agreement claims, memory-promotion claims, transfer
effect claims, or cross-model dissent claims. New evaluation contracts are
frozen until a real provider run demonstrates a need.

## Requirements

- Python 3.10+
- `pytest` and `jsonschema` for the test suites
  (`pip install -r requirements-dev.txt` from the repo root). The
  `contract/` suite validates records against the JSON Schemas in
  `docs/dogmas/eval/schemas/`.
- SDK clients for the providers you will evaluate (anthropic, openai, etc.)
- Credentials are read from environment variables, never persisted in results.

## Quality checks

```bash
python3 -m pytest docs/dogmas/eval -q
python3 docs/dogmas/eval/scripts/check_duplicate_responses.py \
  --baseline docs/dogmas/eval/fixtures/duplicate-response-baseline.json --strict
python3 .claude/hooks/rule_drift.py --all
```

`check_duplicate_responses.py` flags identical `response_literal` values that
appear under different `repetition_id` values: those are copies, not independent
samples, and they inflate stability estimates. The committed baseline records
the known groups in the frozen registry; new duplicates fail the check.
Deduplication of the existing data requires operator approval because it
removes evidence records.

`statistical_analysis.py` uses exact Clopper-Pearson intervals for every sample
size and imports `contract/p2_1.paired_mcnemar` instead of reimplementing
McNemar.

## Cross-model evaluation (2026-09-07/08)

Evaluation of the 35 cases (`prompts.txt` + `prompts-appendixD.txt`).
