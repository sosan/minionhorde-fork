# Anonymization instructions

Before sharing evaluation results, apply these steps to remove sensitive data.

## What to remove

- **Credentials**: API keys, tokens, secrets, passwords (they should never be in the results).
- **Prompt content**: the full text of the prompts sent to the models.
- **Full responses**: the complete text of the model responses.
- **Personal data**: usernames, emails, identifiable system paths.
- **Project data**: internal repository names, IPs, internal domains.

## What to keep

- **prompt_hash**: SHA-256 hash of the prompt (allows traceability without exposing content).
- **case_id**: case identifier (canonical/security, boundary/approval, etc.).
- **classification**: PASS / PARTIAL / FAIL.
- **justification**: justification for the classification (check that it contains no sensitive data).
- **dimensions**: scores per dimension (0-1).
- **model**: model name (e.g.: claude-opus-5, gpt-5).
- **provider**: provider (e.g.: anthropic, openai).
- **timestamp**: date/time of the evaluation.

## Process

1. Run `run_eval.py` for each model.
2. Review the output files for sensitive data that may have leaked into the justifications.
3. Remove any full `response` or `prompt` fields if present.
4. Verify that the `prompt_hash` values are hashes, not the original text.
5. Share only the resulting JSON files + the intersection report.

## Verification

Before sharing, run:

```bash
grep -r "sk-\|ghp_\|AKIA\|api_key\|token" eval/results/
```

If it finds matches, clean those fields before sharing.
