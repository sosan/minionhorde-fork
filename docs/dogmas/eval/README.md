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

## Requirements

- Python 3.10+
- SDK clients for the providers you will evaluate (anthropic, openai, etc.)
- Credentials are read from environment variables, never persisted in results.

## Cross-model evaluation (2026-09-07/08)

Evaluation of the 35 cases (`prompts.txt` + `prompts-appendixD.txt`).
