## Context

Minionhorde has three partially overlapping concerns: machine-enforced control in `.claude/settings.json` and hooks, normative behavior in `DOGMAS-CORE.md`/`DOGMAS-REF-seed.md`, and evaluation plus memory artifacts under `docs/dogmas/`. The current evaluation runner can call providers and classify results as pending, while reports and memory record aggregate outcomes. The missing architectural boundary is a durable, auditable learning loop that can prove correction, transfer, recovery, and regression without treating model self-description as evidence.

The design must remain local-first, provider-agnostic, secret-safe, compatible with the existing shell/Python tooling, and additive to current controls. It must not require storage of private chain-of-thought, automatic dogma promotion, or destructive test fixtures.

## Goals / Non-Goals

**Goals:**

- Make Layers A, B, and C explicit and independently testable.
- Record a complete operational trajectory using decisions, claims, evidence, corrections, and observable tool outcomes.
- Model Socratic calibration as bounded state transitions with human escalation.
- Version provisional memory and require transfer plus regression evidence before promotion.
- Compare baseline, dogma, memory, and Socratic conditions across models and contexts.
- Distinguish literal transcripts, evaluator judgments, summaries, and unverified claims.
- Keep rollback, redaction, scope, and irreversible-action controls authoritative.

**Non-Goals:**

- Fine-tuning model weights or claiming to create consciousness or permanent personality.
- Persisting hidden chain-of-thought or requiring access to provider-internal reasoning.
- Automatically modifying `DOGMAS-CORE.md` from a model output.
- Replacing human approval for frontier cases, destructive actions, or memory promotion.
- Introducing a database, hosted service, or mandatory provider SDK in the first increment.

## Decisions

### 1. Use append-only, schema-validated trajectory records

Each session produces a structured record containing case identity, model/provider, dogma and memory versions, turn summaries, evidence references, tool outcomes, evaluator authority, and final dimensions. Raw response text may be stored only under an explicit retention policy; otherwise the record stores a content hash plus a protected local artifact reference. Secrets and private reasoning are never persisted. Entries use canonical serialization and a cryptographic hash chain; a versioned manifest anchors the sequence and makes post-persistence mutation detectable. The baseline hash algorithm is SHA-256 to avoid a mandatory external dependency; any alternative algorithm SHALL be fixed by the artifact profile and recorded in provenance.

**Why:** auditability and provenance are prerequisites for claiming learning. JSON is compatible with the existing Python evaluation tools and easy to validate. Canonical bytes and a standard cryptographic hash prevent both accidental integrity failures and trivial hash forgery. Auditable records guarantee that a persisted trajectory can be verified, not that a stochastic model run can be replayed byte-for-byte.

**Scope note:** the hash chain and manifest guarantee detection of post-persistence corruption and mutation within the trusted storage domain. They are not an adversarial fraud barrier; hardening against deliberate simultaneous modification of chain and manifest — for example via an external anchor, signature, or protected append-only log — is deferred and not required for the first increment.

### 1a. Version evaluation policy and contamination decisions

Minimums and thresholds remain policy values rather than hard-coded spec constants. The policy is versioned and recorded with every evaluation, so future calibration does not rewrite the meaning of historical results. Contamination uses a conservative tiered model: exact canonical match is hard contamination, similarity is a review flag, and mechanism overlap alone is not contamination.

### 1b. Use predeclared paired statistical comparisons

Exact paired McNemar is the primary test for binary per-case outcomes; paired bootstrap is used for continuous or cost metrics. Primary comparisons and multiplicity handling are predeclared, with Holm correction for secondary claims. Small or underpowered samples produce preliminary or inconclusive conclusions rather than an assertion of no effect.

### 1c. Default statistical policy for the first increment

The proposed default below is a versioned policy value (decision 1a), not a spec constant. The primary contrast estimates the total effect of the complete Layer C stack over Layer B; it does not identify isolated memory or Socratic effects. The marginal effects are predeclared secondary contrasts, while memory–Socratic interaction is exploratory and hypothesis-generating. The primary dimension is transfer, using dogma-vocabulary-free cases as the primary variant; other transfer classes remain secondary. The primary binary test is exact McNemar. The primary interval estimates the paired risk difference with a paired score method; the discordance-based Clopper–Pearson interval is reported only as a discordance-direction interval — conditional on the number of discordant pairs, it is NOT a confidence interval for the marginal risk difference. A min…

```json
{
  "profile": "vertical_slice",
  "primary_claim": "full_layer_c_stack_improves_transfer_over_layer_b",
  "primary_contrast": "full_vs_criteria",
  "primary_estimand": "total_effect_of_layer_c_stack",
  "primary_dimension": "transfer",
  "primary_transfer_variant": "dogma_vocabulary_free",
  "secondary_transfer_variants": ["reformulated", "cross_domain", "adversarial"],
  "secondary_contrasts": ["memory_vs_criteria", "full_vs_memory"],
  "exploratory_contrasts": ["memory_x_socratic_interaction"],
  "binary_paired_test": "mcnemar_exact",
  "binary_paired_effect": "risk_difference",
  "ci_method_binary_paired": "paired_score_newcombe_95",
  "discordance_direction_interval": "exact_binomial_cp95_discordant_conditional",
  "ci_method_continuous": "paired_bootstrap_percentile_95",
  "secondary_correction": "holm",
  "alpha": 0.05,
  "alternative": "two_sided",
  "min_discordant_pairs_definitive": 10,
  "max_primary_ci_half_width_definitive": 0.10,
  "minimum_important_difference_transfer_absolute_delta": 0.10,
  "coverage": {
    "min_transfer_cases_per_variant": 10,
    "min_repetitions_per_case": 5,
    "min_episodes_for_candidate": 3,
    "min_samples_per_category": 30,
    "confirmation_reruns": 2
  },
  "socratic_budget": {
    "max_turns": 6,
    "max_model_calls": 8,
    "max_consecutive_no_progress_turns": 2
  },
  "status": {
    "statistical_methods": "provisional",
    "numerical_thresholds": "provisional"
  },
  "require_disjoint_transfer_set": true,
  "require_disjoint_regression_set": true,
  "repetitions_are_clustered_by_case": true,
  "missingness_report_required": true,
  "report_cost_metrics": true,
  "report_cost_per_delta": "only_if_delta_positive_ci_excludes_zero_and_delta_exceeds_mid",
  "report_confidence_interval_regardless_of_p_value": true,
  "analysis_roles": {
    "primary": "confirmatory",
    "secondary": "confirmatory_with_holm",
    "exploratory": "hypothesis_generating"
  },
  "statistical_unit": {
    "transfer": "case",
    "comprehension": "case",
    "correction": "case",
    "recovery": "recovery_episode",
    "stability": "case",
    "regression": "case"
  }
}
```

For each binary contrast, reports SHALL show both condition rates and the paired discordance table (`b`, `c`, and `b+c`), the risk difference, the McNemar result, the primary interval, and the discordance-direction interval. A result with fewer than the configured discordant-pair minimum SHALL be preliminary regardless of its p-value. A definitive claim additionally requires the primary interval-width gate, the configured minimum important difference, complete provenance and contamination gates, and no unresolved model or configuration mismatch. Cost-effectiveness SHALL be undefined when the delta is non-positive, its interval includes zero, or it does not exceed the minimum important difference.

Coverage status SHALL be reported explicitly as `definitive`, `preliminary_low_discordance`, `preliminary_wide_interval`, `preliminary_below_mid`, or `inconclusive_insufficient_cases`. With the intermediate first-suite values, a definitive claim may be unreachable for some categories — that is an expected outcome, not a failure. The runner SHALL emit the most informative label available, record the specific unmet gate, and SHALL NOT silently downgrade or block a report. Suite growth and gate calibration are separate from report generation.


### 2. Represent the Socratic loop as a bounded state machine

The runner SHALL support `INIT`, `INTERPRET`, `REFORMULATE`, `CHALLENGE`, `EVIDENCE_CHECK`, `CORRECT`, `AUDIT`, `TRANSFER_TEST`, `RECOVER`, `HUMAN_ESCALATION`, and terminal states. Human responses are recorded as `human_input` events appended to the `HUMAN_ESCALATION` state, not as a separate trajectory state. Every transition records its cause and may be limited by a configured turn/token budget.

**Why:** explicit states make stopping, retries, and human escalation testable; they prevent unbounded recursive prompting.

**Alternative rejected:** an open-ended “think harder” loop, because extra iterations can increase narrative confidence without improving behavior.

### 3. Separate evaluator authority from agent assertions

Every classification SHALL identify its source: `human`, `rule`, `judge`, `heuristic`, or `unverified`. A model's claim that it audited itself is evidence to evaluate, not an evaluation result. Tool behavior and resulting filesystem/test state are stronger evidence than prose claims.

**Why:** this addresses the existing distinction between summaries and literal evidence and prevents self-certification.

**Alternative rejected:** using a single judge model as the ground truth, because it reproduces model bias and can agree with persuasive but incorrect narratives.

### 4. Treat memory as a versioned candidate registry

Memory entries SHALL have provenance, scope, supporting episodes, transfer cases, counterexamples, status (`episodic`, `pattern`, `transferred`, `promoted`, `deprecated`), and revision history. Promotion to a dogma remains a human-reviewed operation after independent episodes, transfer, and regression.

**Why:** it preserves the existing episodic → pattern → dogma discipline while making lifecycle and rollback explicit.

**Alternative rejected:** directly appending successful conversations to the core memory, because it causes normative inflation and contaminates future evaluations.

### 5. Use controlled evaluation conditions

The evaluation matrix SHALL support at least: base model, model plus dogmas, plus memory, and plus bounded Socratic dialogue. Cases SHALL include direct, reformulated, cross-domain, adversarial, and recovery variants. Results SHALL report coverage and abstain from global claims when coverage or provenance is insufficient.

**Why:** only controlled comparisons can show whether Layer C adds transfer or recovery beyond Layer B.

**Alternative rejected:** expanding the number of models without a controlled baseline, because model count alone does not establish causality.

### 6. Keep enforcement layered

Layer A remains the authority for tool permissions, redaction, scope, phase gates, audit logging, and irreversible operations. Layer B defines criteria and precedence. Layer C may recommend corrections or memory candidates but cannot weaken A/B or authorize irreversible actions.

**Why:** operational learning must not become a path for self-modification or safety weakening.

**Alternative rejected:** allowing the learning loop to rewrite policy or hooks automatically.

### 7. Define a common provider-adapter contract

Adapters SHALL return structured metadata rather than response text alone: response text, requested and provider-served model, sampling parameters, usage, latency, provider request identifier, and error classification. Unsupported metadata is recorded as `unknown`; credentials and secret request metadata never enter the record.

### 8. Use a modern evaluation record and explicit legacy migration

Modern records SHALL carry case version and hash, condition, repetition identifier, pair key, policy and partition manifest references, provenance, evidence mode, outcome status, dimensions, cost observables, and missingness. Legacy results are imported only as `legacy_limited` descriptive evidence and cannot support causal, transfer, promotion, or Layer C improvement claims.

### 9. Separate environment failures from model outcomes

Provider errors, timeouts, credential failures, budget exhaustion, schema-invalid responses, and pending classifications are availability or missingness events, not model failures. A model pass or fail requires a completed, classified run. This separation prevents infrastructure reliability from contaminating behavioral metrics.

### 10. Separate vertical-slice and full-suite evaluation profiles

The intermediate values in decision 1c define a `vertical_slice` profile for validating the protocol and provenance path. A `full_suite` profile SHALL be calibrated separately for partition sizes, transfer coverage, repetitions, cost budgets, and definitive-claim gates. Vertical-slice results MAY validate mechanics but SHALL remain preliminary and SHALL NOT silently inherit full-suite promotion authority.

### 11. Scope claims by evidence level

Claims progress through `case`, `dimension`, `candidate`, `category`, `model`, and `global` scopes. The first increment is limited to provisional candidate- and dimension-level claims; model- and global-level claims require complete coverage, independent evaluation, and no unresolved provenance or partition gaps.

### 12. Version schemas in a stable, explicit location

Modern JSON Schemas SHALL live under `docs/dogmas/eval/schemas/v1/`, with separate versioned schemas for trajectory records, evaluation results, memory candidates, evaluation policies, partition manifests, and provider-adapter envelopes. Schema versions SHALL be recorded in every corresponding artifact. Legacy `results_schema.json` remains a compatibility schema and SHALL NOT be treated as the modern contract.

### 13. Resolve the suite-size versus disjoint-partition tension

The existing suite has roughly 35 cases, while policy values assume up to 30 samples per category across disjoint partitions. The tension is recognized explicitly rather than silently. The vertical-slice profile SHALL use minimal partitions and MAY reuse cases across partitions only when the overlap is recorded as approved non-comparable reuse, which the partition requirement already permits. A full_suite SHALL grow the case inventory before definitive claims, and partition manifests SHALL declare which partition-policy mapping applies.

### 14. Make the human-labeled subset a gating dependency and fix vertical-slice acceptance

Judge-agreement validation, transfer-variant equivalence review, and contamination-similarity calibration depend on a human-labeled subset; creating it is an explicit readiness task, and its absence blocks judge-backed claims and equivalence review. Vertical-slice acceptance is defined as: one controlled case run under the four conditions, a schema-valid verifiable trajectory, a paired contrast with coverage status, and the correct `coverage_status` label emitted.

### 15. Give challenges their own provenance contract

A challenge is an input to Layer C, not an evaluation result, so it needs the same authority discipline as a classification. Every challenge records generator authority, identity and version, requested and served model when a model generates it, sampling parameters, target claim or turn, challenge and delivered content hashes, evidence references, and any human edit or selection. A shared model family with the evaluated agent is flagged and does not count as independent confirmation. A challenge that changes a decision without independent evidence is provisional; the challenge generator's provenance is recorded separately from the judge's.

### 16. Budget reliability measurement separately from the primary contrast

Reliability dimensions that require repetitions — recovery, stability, and regression — SHALL have a dedicated measurement budget distinct from the primary paired contrast. The set of cases receiving reliability repetitions and the repetition count per case are configured policy values. Reliability results SHALL be reported as preliminary when the reliability budget is undersized, and repetitions SHALL remain clustered by case and never counted as independent samples.

### 17. The vertical slice validates the protocol, not the hypothesis

The vertical slice is accepted when it produces valid, verifiable trajectories and the correct coverage-status labels — not when it demonstrates a positive transfer effect. With the roughly 35-case suite and disjoint partitions, the expected outcome may be inconclusive or preliminary across categories; that is a successful protocol validation, and a positive or definitive result is not required to pass.

### 18. Adopt an explicit evidence threat model

The design separates distinct threats and their mitigations rather than treating "security" as one risk: accidental corruption → hash chain; careless editing → manifest; self-certifying model → separate classification authority and actor independence; biased judge → blinding plus a human-labeled subset; mistaken operator → review and audit log; compromised process → external storage or anchor, deferred beyond the first increment; provider drift → served-model and sampling records. A failure of custody or independence invalidates the claims that depend on it, even when the statistical calculation is correct.

### 19. Map claim strength to minimum integrity

The required integrity grows with claim strength: local debugging → hash chain; provisional result → chain plus manifest; candidate promotion → protected manifest plus human review; cross-model comparison → separate storage or signed export; global or crystallization claim → independent evidence and reproducibility. A claim MUST NOT be emitted at a strength exceeding the integrity of the evidence supporting it.

### 20. Give Layer C a bounded path to propose Layer B amendments

Operational learning is additive only if Layer B can never change, and that would leave the criteria themselves unexamined. Layer C MAY therefore propose a structured Layer B amendment — current criterion, contradicting evidence, proposed text or precedence change, affected precedences — but SHALL NEVER apply it. Approval is human-only, precedence changes require separate approval, and an approved amendment SHALL re-run the evaluation suite for regression before it is treated as stable. This preserves the safety boundary while closing the open top of the learning loop.

### 21. Verify the experiment, not just the measurement

A precise measurement of the wrong experiment is worthless. The design therefore requires three validity signals beyond the statistics: memory retrieval is recorded per trajectory so an empty retrieval is visible rather than silently equivalent to the comparison condition; condition content is verified (`memory_injected`, `criteria_injected`) so a condition label cannot be trusted without a content-level confirmation; and cases report discriminating power (`ceiling`, `floor`, `inert`, `discriminating`) with the primary contrast shown over discriminating cases. Transfer variants additionally record mutation distance so a superficial rename cannot masquerade as cross-domain transfer.

### 22. Keep Layer C falsifiable and claims fresh

The evaluation gate is symmetric: Layer C is accepted only through the pre-registered paired gates, and it can be rejected only through a pre-registered equivalence test (TOST with margin Δ), never through a non-significant superiority result. Claims carry validity periods and revalidation triggers — served model, criteria, memory, and policy version changes or a time-to-live — so a stale claim cannot masquerade as current evidence. Case inclusion and exclusion follow pre-registered rules; the `discriminating` subset is a diagnostic, not a silent replacement for the pre-registered analysis set. A program-level stop rule (marginal cost versus improvement) governs when measurement should cease, mirroring the earlier bootstrap budget discipline.

### 23. Govern memory as a long-lived artifact

Memory is the only artifact that is re-injected into future sessions, so it needs lifecycle policies the evaluation layer already has: internal conflict detection with recorded precedence instead of injecting contradictory guidance; a per-case injection budget (entries and tokens) with pruning and archival so behavior does not drift merely because memory grew; redaction before storage plus periodic audits, because a secret that entered an episode could otherwise be crystallized and re-injected indefinitely; and revalidation by time-to-live or context change so a pattern tied to an old model, criteria, or tooling cannot retain automatic injection authority.

### 24. Declare the challenger objective

A challenge's provenance is incomplete without its intent. Each challenge records its objective (`corrective`, `adversarial`, or `mixed`): corrective challenges target supported errors and feed correction; adversarial challenges test resistance and feed stability; mixed challenges identify each sub-challenge's objective. Without the objective, a flipped decision cannot be attributed to a real error versus pressure to change, and correction and stability metrics become ambiguous.

### 25. Make the append-only store crash-safe and concurrent-safe

The hash chain assumes sequential ordered appends. The store therefore defines an ordering authority (single writer, serialized lock, or monotonic allocator), uses atomic or journaled appends, and recovers from crashes by retaining the last valid manifest and classifying incomplete writes as aborted rather than evidence. Concurrent forks or competing appends are recorded and never silently merged.

### 26. Evolve schemas without breaking historical verification

Artifacts record their schema version. A newer reader uses versioned adapters for older artifacts or emits a separately hashed migration artifact that references the original chain and schema version. Historical records are never rewritten in place; migrations record tool identity, source and target versions, timestamp, and source hash; a semantic change in migration downgrades dependent claims instead of silently remapping them.

## Evidence and human review governance

Evidence artifacts record producer, classifier, custodian, and reviewer actors, plus observation/recording/evaluation/amendment timestamps, and transition through `OPEN`, `FROZEN`, `AMENDED`, `SUPERSEDED`, and `CORRUPTED`. Human reviews and escalations are structured events with reviewer identity, blinded-condition evidence, decision, rationale hash, and timestamp; reviewer-producer or reviewer-classifier overlap is flagged and degrades independence. These rules are captured as requirements in the operational-learning and evaluation-provenance specs.


## Risks / Trade-offs

- **[Risk]** A judge model can reward dogma vocabulary instead of correct behavior. → **Mitigation:** require observable outcomes, blinded/adversarial cases, evaluator authority, and transfer tests without dogma terminology.
- **[Risk]** Judge models carry documented position, self-preference, and verbosity biases (order swapping can reverse rankings: Wang et al. 2023, arXiv:2305.17926; self-preference correlates with self-recognition: Panickssery et al. 2024, arXiv:2404.13076). → **Mitigation:** record judge identity and family relation, swap comparison order, and gate judge use on measured agreement with a human-labeled subset.
- **[Risk]** Aggregate pass-rate comparisons over ~30 cases cannot resolve small deltas; paired per-case tests with confidence intervals are required (Miller 2024, arXiv:2411.00640; agent consistency requires pass^k-style repetition metrics: Yao et al. 2024, arXiv:2406.12045). → **Mitigation:** paired comparisons, minimum repetitions for reliability dimensions, and confidence intervals in coverage gates.
- **[Risk]** A memory candidate's supporting episodes can overlap evaluation cases, making the memory condition gain reflect teaching-to-the-test rather than transfer (promptfoo documents the same overfitting failure mode for optimization without a validation split). → **Mitigation:** mark case/episode overlap as contaminated and exclude it from transfer claims; keep the regression suite disjoint from optimization variants.
- **[Risk]** A Socratic challenge can flip correct answers via sycophancy (Sharma et al. 2023, arXiv:2310.13548), and intrinsic self-correction without external feedback degrades performance (Huang et al. 2024, arXiv:2310.01798; Kambhampati et al. 2024, arXiv:2402.01817). → **Mitigation:** challenge-to-correct-decision is a stability metric in its own right; correction counts only with external causal evidence; the challenger's authority is recorded separately from the judge's.
- **[Risk]** Memory poisoning through ordinary interactions is demonstrated at high attack success with tiny poison rates (AgentPoison, arXiv:2407.12784; MINJA query-only injection, arXiv:2503.03704), and provider model drift makes requested-model identity unreliable (Chen/Zaharia/Zou 2023, arXiv:2307.09009; OTel GenAI requires recording the actually-served model). → **Mitigation:** retrieved candidates are untrusted data with no instruction authority, a memory-injection case is mandatory, and trajectories record requested plus served model and sampling parameters.
- **[Risk]** Mixing languages across artifacts acts as an uncontrolled confound; prompt-format perturbations alone swing accuracy by up to 76 points (Sclar et al. 2024, arXiv:2310.11324). → **Mitigation:** the field-class policy keeps machine fields language-neutral (enums, hashes, numbers), tags operator-facing prose as non-machine-consumable, pins model-facing text (cases, judge-facing prompts) per artifact class, records case language in provenance, and invalidates cross-pass comparability on any input-language change.

## Migration Plan

1. Add schemas and synthetic fixtures without changing current enforcement behavior.
2. Extend evaluation records and validators in compatibility mode; preserve the legacy report format while marking missing provenance.
3. Implement the bounded trajectory runner for one controlled case and one local/provider adapter.
4. Add transfer, recovery, and regression cases; compare the four evaluation conditions.
5. Enable candidate memory reports only after the trajectory and evaluation tests pass.
6. Keep promotion manual and reversible; roll back by selecting the prior memory version and disabling the new runner path.
## Resolved Decisions

1. `HUMAN_ESCALATION` is the trajectory state requiring human judgment or authorization; the human response is an appended `human_input` event, not a second trajectory state.
2. `BLOCKED` and `HUMAN_ESCALATION` are resumable, non-evaluable states. Resumption retains the trajectory identifier; abandonment terminates as `ABORTED` rather than leaving an open trajectory.
3. Append-only integrity uses a canonicalized hash chain and versioned manifest. This detects post-persistence corruption within the trusted storage domain; adversarial anchoring is deferred.
4. Canonical serialization is versioned UTF-8 JSON with recursively sorted keys, no insignificant whitespace, normalized Unicode, deterministic number representation, and exclusion of `content_hash` and `prev_hash` from content-hash input.
5. SHA-256 is the baseline cryptographic hash without a mandatory external dependency. The manifest records the hash algorithm and canonicalization version.
6. Served-model uncertainty is classified as `served_model_unknown`, `served_model_mismatch`, or `sampling_unknown`; each status limits only the claims whose provenance it prevents.
7. Invalid values in declared machine fields produce `schema-invalid` records and are excluded from aggregation; they are not silently demoted to operator-facing text.
8. Evaluation policy is versioned and content-addressed. It records hard gates, reporting thresholds, budgets, and statistical settings; missing minima produce pending or preliminary results.
9. Contamination is tiered: exact canonical matches are hard contamination, similarity is a review flag with detector metadata, and mechanism overlap alone is not contamination. Contamination propagates to dependent candidate claims.

## Open Questions

- Provisional policy values — `min_transfer_cases_per_variant: 10`, `min_repetitions_per_case: 5`, `min_episodes_for_candidate: 3`, `min_samples_per_category: 30`, `confirmation_reruns: 2`, `max_primary_ci_half_width_definitive: 0.10`, `minimum_important_difference_transfer_absolute_delta: 0.10`, `min_discordant_pairs_definitive: 10`, and the `socratic_budget` — are set in decision 1c for an intermediate-cost first suite and remain calibratable through the versioned evaluation policy (decision 1a) once real data exists.
- Whether transfer-variant equivalence review starts as human review or as a validator calibrated against human labels, and when a calibrated validator may replace direct human review.
- Which local and provider adapters and judge models will be available for the four baseline conditions, which affects served-model identity coverage and the practical repetition budget.
- Synthetic validation of the conditional exact interval against a paired score method, and confirmation of the provisional statistical methods and thresholds in decision 1c, are pending before the default statistical policy is considered definitive.
- The suite-versus-partition tension is resolved at design level (decision 13): vertical slice uses minimal partitions with approved non-comparable reuse; a full_suite grows the inventory before definitive claims. The concrete partition-policy mapping is fixed when the first vertical-slice manifests are written (task 10.2).
