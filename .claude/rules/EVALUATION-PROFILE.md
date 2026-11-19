# EVALUATION PROFILE v1 — Domain invariants E2-E12

> **Status:** canonical for the evaluation domain. Source: CORE v4.1
> "Evaluation profile invariants (P0-P2.7)", moved unmodified in CORE v4.2
> (SRP split, task C2). Numbering is preserved; E1 remains in the universal
> CORE as a Layer A/B authority boundary.
>
> **Load on demand.** This profile is domain-specific. It is loaded via the
> `evaluation-contracts` skill when the task evaluates agent behavior, memory,
> provenance, transfer, recovery, regression, stability, or cross-model
> results. Machine contracts and schemas under `docs/dogmas/eval/` remain
> authoritative even when this file is not in context.

## Invariants

- **E2 — Evidence provenance.** Every evaluation result records the case and
  configuration provenance, requested and served model, sampling, language,
  evaluator authority, evidence mode, and observable tool outcome availability.
- **E3 — Evidence resolution.** Every cited evidence hash must resolve to an
  existing artifact whose content hash matches. Missing, altered, expired, or
  unverified evidence downgrades the result and blocks high-confidence claims.
- **E4 — Append-only learning records.** Trajectories, corrections, retries,
  reviews, and memory amendments append new provenance-bearing records; history
  is never overwritten in place.
- **E5 — Judge independence.** Judge identity, model-family relation, condition
  blinding, comparison order, and human-labeled agreement are recorded. An
  unvalidated judge remains provisional.
- **E6 — Paired statistical claims.** Same-case comparisons preserve pairing,
  report discordance and confidence intervals, predeclare primary contrasts,
  and apply documented multiplicity controls to secondary claims.
- **E7 — Transfer discipline.** Transfer variants declare domain, class, mutation
  distance, and decision principle. They require equivalence review; contaminated
  or vocabulary-only variants cannot support definitive cross-domain claims.
- **E8 — Dissent preservation.** Valid cross-model disagreement is retained as
  frontier or unresolved dissent and routed to human review; it is not averaged
  away. Configuration-different results are non-comparable.
- **E9 — Coverage gates.** Claims remain pending, preliminary, or scoped down when
  sample minima, reliability repetitions, provenance, agreement, or partition
  coverage are insufficient. Non-significance alone is not equivalence.
- **E10 — Challenge attribution.** Every challenge declares corrective,
  adversarial, or mixed objective and records provenance. Correction and
  stability outcomes are attributed only to dimensions supported by that objective.
- **E11 — Memory safety.** Active memory conflicts are detected and escalated;
  injection is bounded by entries and tokens; secrets are redacted before storage
  or injection; audit findings are recorded as security events.
- **E12 — Memory validity.** Memory entries expire or become stale when TTL,
  served model, criteria, policy, or tooling context changes. Stale, archived,
  redacted, or conflicted entries are excluded from automatic injection.

## Enforcement map (invariant → machine contract)

| Inv | Machine contract(s) | Tests |
|---|---|---|
| E2 | `schemas/v1/evaluation_result.schema.json`, `provenance_adapter.py`, `provenance_enrichment.py` | `test_3_1_provenance_enrichment.py`, `test_3_4_metrics_breakdown.py` |
| E3 | `evidence_custody.py` | `test_evidence_custody.py` |
| E4 | `append_log.py`, `trajectory_provenance.py` | `test_10_26_append_log.py`, `test_trajectory_provenance.py` |
| E5 | `p2_1.py` (`audit_judge.py`) | `test_p2_1.py` |
| E6 | `p2_3.py` | `test_p2_3.py` |
| E7 | `transfer_variants.py` | `test_transfer_variants.py` |
| E8 | `p2_4.py` | `test_p2_4.py` |
| E9 | `coverage_gates.py` | `test_coverage_gates.py` |
| E10 | `p2_6.py` | `test_p2_6.py` |
| E11 | `p2_7.py`, `memory_contamination.py` | `test_p2_7.py`, `test_memory_contamination.py` |
| E12 | `p2_7.py`, `memory_retrieval.py` | `test_p2_7.py`, `test_10_15_memory_retrieval.py` |

## Exercise status

Machine contracts and tests for this profile live under
`docs/dogmas/eval/contract/`; the on-demand procedure is
`.claude/skills/evaluation-contracts/SKILL.md`. Contract exercise status
(whether a contract is exercised by a real runner or only by tests) is declared
in the evaluation exercise manifest; see the `evaluation-exercise-readiness`
capability.