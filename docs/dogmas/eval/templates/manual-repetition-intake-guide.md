# Manual Repetition Intake Guide

This guide explains how to incorporate a future literal response into the repetition registry without changing prior records or making unsupported provenance claims.

## 1. Identify the registry key

Every record is uniquely identified by:

```text
case_id + model + repetition_id + condition
```

Valid values for the current manifest:

- Cases: 02, 04, 06 as listed in `manual-repetition-manifest.json`.
- Models: `claude-opus-5-max`, `Anthropic`.
- Repetitions: `r01`, `r02`, `r03`.
- Conditions: `C0`, `C1`, `C2`, `C3`.

## 2. Copy the pending record

Locate the matching file under:

```text
docs/dogmas/eval/repetitions/<case_short>/<model>/<repetition_id>-<condition>.json
```

Do not change the composite key. Do not overwrite a record already marked `classified`, `collected`, or `incomplete`.

## 3. Preserve the literal response

Set `response_literal` to the complete response exactly as received, except that secrets, credentials, tokens, and hidden reasoning must not be persisted. If redaction is necessary, record that fact in `notes` without reconstructing the removed value.

Set:

```json
"status": "collected"
```

until the deterministic classifier has run.

## 4. Record provenance conservatively

Use `unknown` for unavailable values:

```json
"served_model": "unknown",
"temperature": "unknown",
"sampling": "unknown",
"other_sampling": "unknown"
```

Never infer these fields from the requested model, response style, or output length. Set `conversation_independent` to `true` only when the operator can confirm a new independent conversation; otherwise use `unknown`.

## 5. Run individual ingestion

Use:

```bash
python3 docs/dogmas/eval/scripts/repetition_ingest.py path/to/record.json
```

The tool:

- validates the case, model, repetition, and condition;
- accepts `unknown` metadata;
- rejects inferred provider metadata;
- rejects duplicate keys after collection/classification;
- leaves records pending when no literal response exists;
- classifies only records containing a literal response.

## 6. Handle incomplete runs

If a run was interrupted, timed out, or produced no usable literal response, set:

```json
"status": "incomplete"
```

Do not classify it as PASS or FAIL. Add the interruption cause to `notes` and preserve any available provenance.

## 7. Generate a partial report

Use:

```bash
python3 docs/dogmas/eval/scripts/repetition_report.py \
  --output docs/dogmas/eval/repetitions/status-report.json
```

The report separates:

```text
collected
pending
incomplete
classified
```

It always emits:

```text
report_status: preliminary_descriptive_only
```

## 8. Interpret results

The report supports descriptive observations only. It does not support statistical superiority, equivalence, causal memory effects, or promotion claims. Preserve disagreements and recovery differences as observations for later human review.
