# Anonymization instructions

Before sharing evaluation results, apply these steps to remove sensitive data.

## Two different artifacts

| Artifact | Audience | `response_literal` |
|----------|----------|--------------------|
| Evidence custody (registry, internal) | operators, auditors | **Keep** the literal. It is the evidence behind each classification. |
| Shared report (external) | readers outside the project | **Never** include the literal. Publish `response_hash` + `classification`. |

`response_literal` is not "the full response you must delete": it is the
internal evidence record. The rule is that the literal never leaves the
custody boundary. If a report needs traceability, publish
`sha256(normalized response_literal)` so a holder of the evidence can verify
it without reading it.

## What to remove from shared reports

- **Credentials**: API keys, tokens, secrets, passwords (they should never be in the results).
- **Prompt content**: the full text of the prompts sent to the models.
- **Response literals**: the complete text of the model responses.
- **Personal data**: usernames, emails, identifiable system paths.
- **Project data**: internal repository names, IPs, internal domains.

## What to keep in shared reports

- **prompt_hash**: SHA-256 of the prompt (allows traceability without exposing content).
- **response_hash**: SHA-256 of the normalized `response_literal`.
- **case_id**: case identifier (canonical/security, boundary/approval, etc.).
- **classification**: PASS / PARTIAL / FAIL.
- **justification**: justification for the classification (check that it contains no sensitive data).
- **dimensions**: scores per dimension (0-1).
- **model**: model name (e.g.: claude-opus-5, gpt-5).
- **provider**: provider (e.g.: anthropic, openai).
- **timestamp**: date/time of the evaluation.

## Process

1. Run `run_eval.py` for each model.
2. Keep the registry (with `response_literal`) inside the custody boundary.
3. For a shared report, replace each `response_literal` with its
   `response_hash` and keep only the classification fields above.
4. Review justifications for sensitive data that may have leaked into them.
5. Verify that `prompt_hash` and `response_hash` values are hashes, not text.
6. Share only the resulting JSON files + the intersection report.

## Verification

```bash
grep -rE "sk-|ghp_|AKIA|api_key|token|response_literal" shared-results/
```

A hit on `response_literal` means the shared artifact still carries evidence
text. Move that field back into custody before publishing.
