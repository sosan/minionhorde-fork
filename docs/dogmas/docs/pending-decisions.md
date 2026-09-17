# Pending Decisions — Operator Review Guide

> **Purpose:** document open design decisions and identify those requiring your judgment.
> Decisions are grouped by urgency: blockers versus decisions that can wait.

## CATEGORY A — Require operator decision before proceeding

### A-1. Parallelism: path vs. name (coordination/shared-context)

**What happened:** three models converged on the rule that the parallelism gate must compare the same path in `Files:`, not the same filename. The exact verification procedure remains an operator decision.

**Pending decisions:**
1. Must PM verify paths before approving parallelism (declarative roadmap partitioning rather than manual inspection)?
2. What should happen when one Developer mutates a path another Developer still owns: review, reject, or report as a collision?

**Recommendation:** A-1 has high impact because the multi-agent workflow depends on it. Without a clear rule, coordination still depends on PM remembering to check paths manually.

### A-2. Boundary between `~/.bashrc` and the operator’s personal environment

**What happened:** one model accepted editing the operator’s `~/.bashrc` with an explicit order and a complete, reversible PREFLIGHT, while the others rejected it. The ambiguity remains unresolved.

**Pending decisions:**
1. May the agent touch operator dotfiles when the order is explicit and PREFLIGHT is complete?
2. Or is the project/personal boundary non-negotiable?

**Recommendation:** decide and add the result to CORE v4.1 as an explicit rule. A clear rule is better than case-by-case ambiguity.

### A-3. Sample size for definitive claims

**What happened:** with 30 cases and 7 models, pass coverage was uneven (n=3 for five models, n=1 for the others). FAIL was 0% in all cases, but statistical completeness is partial.

**Pending decisions:**
1. Is the current evidence (five models with n=3, 100% PASS) sufficient for a definitive claim?
2. Or should the remaining three passes for each model be completed (90 additional evaluations)?

**Recommendation:** A-3 affects the validity of “crystallized patterns.” Current evidence is sufficient for internal documentation; publication or external audit requires the additional evaluations.

## CATEGORY B — Can wait (documented boundary zones)

### B-1. Pre-approved reversible actions (case 26)

**Status:** models distinguish additive automatic actions from destructive actions requiring confirmation. This is a productive boundary zone.

**Decision:** decide explicitly whether CORE v4.1 includes a “two lanes” rule or leaves case 26 as “escalate to human.”

### B-2. Stable `~/.bashrc` disagreement

**Status:** disagreement is stable across passes. Both positions have merit. The operator chooses.

### B-3. Scope versus improvement (Inv 8)

**Status:** one model added a “more” dropdown without asking for confirmation. Is this “unrequested extra” (violating Inv 8) or neutral presentation formatting?

**Decision:** document in CORE v4.1 whether the agent may offer options without an explicit operator order.

## CATEGORY C — Decisions already made by the system

### C-1. DOGMAS CORE v4.1 does not change because of a PARTIAL

**Rule:** PARTIAL results are recorded in memory; they are promoted to a dogma only after cross-model crystallization (≥3 models, same decision). This was satisfied in all Phase 1 cases.

### C-2. Patterns crystallize through tutoring, not formal evaluation alone

**Rule:** the five patterns crystallized in formal evaluation were confirmed during Phase 2 tutoring using the same models and decisions in a learning context. Tutoring/evaluation convergence is evidence that the patterns are robust.

## Properties of this list

- **Live:** updated after each tutoring session with new incidents and patterns.
- **Focused:** records only decisions that remain open.
- **Prioritized:** Category A (blocking) > B (can wait) > C (already decided).
