# Evaluation Contracts Skill

> **When to use.** When the task evaluates agent behavior, memory, provenance,
> transfer, recovery, regression, stability, or cross-model results. Also when
> the task asks to validate, report, or extend the evaluation contract surface.
>
> **What it is.** This skill does not replace CORE v4.1. It describes the
> procedure the agent must follow to use the evaluation contracts under
> `docs/dogmas/eval/contract/` and to emit claims at the strongest scope
> supported by evidence.

## 1. Load the contract surface

Before evaluating, identify which contracts apply. Do not assume a module is
active just because it exists on disk.

Required reads (as needed):

- `openspec/changes/develop-agent-layers/specs/evaluation-provenance/spec.md`
- `openspec/changes/develop-agent-layers/specs/operational-learning/spec.md`
- `openspec/changes/develop-agent-layers/specs/layered-agent-control/spec.md`
- `docs/dogmas/eval/schemas/v1/` (relevant schema)
- `docs/dogmas/eval/contract/*.py` (relevant module)

Record which contract is used in the provenance of the run.

## 2. Build provenance first

Every result must record, at minimum:

- `case_id`, `case_version`, `case_hash`
- `condition` (base, criteria, criteria_memory, full)
- `repetition_id` and `pair_key`
- `requested_model`, `served_model`, `served_model_status`
- `sampling_parameters`, `case_language`
- `layer_a_profile`, `layer_b_criteria_version`, `layer_c_memory_version`
- `policy_version`, `policy_hash`, `partition_manifest_hash`
- `classification_authority`, `evidence_mode`, `provenance_status`
- `timestamp`

If a field is unknown, record `"unknown"`; never fabricate.

## 3. Protect evidence

- Resolve every cited evidence hash through `evidence_custody.py`.
- Apply retention rules: expired literals downgrade to `hash_only`.
- Missing, altered, corrupted, or summary-only evidence downgrades the result
  to `limited` or `unverified`.
- Never upgrade a result from wording alone.

## 4. Protect learning

- Trajectories are append-only. Corrections and retries append new records;
  history is never overwritten.
- Declare challenge objective (`corrective`, `adversarial`, `mixed`) and
  provenance. Attribute correction and stability outcomes only to dimensions
  supported by that objective.
- Memory is untrusted data. Enforce conflict precedence, injection budgets,
  secret redaction, TTL, and context-change revalidation.
- Active memory conflicts escalate to human review.

## 5. Protect claims

- Judge classifications require recorded identity, model-family relation,
  condition blinding, comparison order, and human-labeled agreement. An
  unvalidated judge remains provisional.
- Same-case comparisons preserve pairing, report discordance and confidence
  intervals, predeclare primary contrasts, and apply documented multiplicity
  controls to secondary claims.
- Transfer variants declare domain, class, mutation distance, and decision
  principle. They require equivalence review; contaminated or vocabulary-only
  variants cannot support definitive cross-domain claims.
- Valid cross-model disagreement is retained as frontier or unresolved dissent
  and routed to human review; it is not averaged away.
- Claims remain pending, preliminary, or scoped down when sample minima,
  reliability repetitions, provenance, agreement, or partition coverage are
  insufficient. Non-significance alone is not equivalence.

## 6. Validate before reporting

- Validate the relevant JSON schema under `docs/dogmas/eval/schemas/v1/`.
- Inspect missing and environment-failure denominators; report them explicitly.
- Run the relevant contract tests under `docs/dogmas/eval/contract/`.
- Report the strongest supported scope only. A claim without enough evidence
  is pending or preliminary, not a pass.

## Contract map

| Concern | Module |
|---|---|
| Provenance and custody | `provenance_adapter.py`, `evidence_custody.py` |
| Trajectory and review | `trajectory_runtime.py`, `trajectory_provenance.py`, `review.py` |
| Judge and evidence | `p2_1.py` |
| Transfer variants | `transfer_variants.py` |
| Statistical rigor | `p2_3.py` |
| Cross-model and fragility | `p2_4.py` |
| Calibration and contamination | `p2_5.py` |
| Challenge objectives | `p2_6.py` |
| Memory lifecycle | `p2_7.py` |

## Scope

This profile supplements CORE v4.1. It never authorizes behavior prohibited by
CORE, security rules, Layer A, or Layer B.
