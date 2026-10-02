## 1. Baseline and contracts

- [ ] 1.1 Inventory current evaluation files, memory entries, hooks, and existing test conventions; record the compatibility constraints in the implementation context.
- [x] 1.2 Define versioned schemas for trajectory records, evaluator provenance, memory candidates, and controlled evaluation conditions.
- [ ] 1.3 Add synthetic fixtures covering complete, interrupted, unverified, and secret-redacted trajectories without real credentials or destructive actions.
- [x] 1.4 Add schema and fixture validation tests before changing the evaluation runner.

## 2. Layer A and Layer B integration

- [ ] 2.1 Define the serialized Layer A control profile and Layer B criteria profile consumed by an evaluation record.
- [ ] 2.2 Integrate version/profile capture without weakening existing permissions, redaction, audit, phase-gate, scope, or irreversible-action controls.
- [ ] 2.3 Add tests proving Layer C recommendations cannot override Layer A/B controls or authorize irreversible operations.
- [ ] 2.4 Add bounded-budget and no-progress stop checks for interactions that enter the learning loop.

## 3. Evaluation provenance

- [ ] 3.1 Extend evaluation result handling to record response evidence mode, evaluator authority, observable tool outcome availability, and configuration hashes.
- [x] 3.2 Preserve compatibility with legacy result files while marking missing provenance as limited or unverified.
- [ ] 3.3 Add controlled-condition metadata for base, dogmas, memory, and dogmas-plus-memory-plus-Socratic runs.
- [ ] 3.4 Update validation and metrics to report provenance, coverage, dissent, confidence limits, and cost separately.
- [ ] 3.5 Add regression tests for incomplete coverage, mixed configurations, missing literal evidence, and model disagreement.
- [ ] 3.6 Record requested model, served model reported by the provider, sampling parameters, and case language in every evaluation result; mark comparisons non-comparable when served model or sampling differ.
- [x] 3.7 Implement judge bias controls: record judge identity and model-family relation to the evaluated model, swap comparison order for comparative judgments, and mark judge classifications provisional until agreement is validated against a human-labeled subset.
- [x] 3.8 Add paired per-case comparison (McNemar or paired bootstrap) with confidence intervals for all cross-condition claims; report aggregate pass rates only alongside the paired analysis.
- [x] 3.9 Implement evidence-reference resolution: verify every cited artifact exists and its content hash matches the recorded hash; mark results unverified on mismatch or missing artifact, and downgrade expired stored literals to hash-only provenance.
- [x] 3.10 Define and enforce the retention policy for stored literal responses (explicit expiry date, hash-only fallback) and record the evidence mode (hash-only vs stored-literal) in every result.

## 4. Socratic trajectory vertical slice

- [x] 4.1 Implement a bounded state machine for INIT, INTERPRET, REFORMULATE, CHALLENGE, EVIDENCE_CHECK, CORRECT, AUDIT, and terminal/human-input states.
- [x] 4.2 Record claims, facts, inferences, assumptions, uncertainties, challenges, evidence references, changed claims, and preserved claims per turn.
- [x] 4.3 Implement one safe synthetic calibration case with one deliberate mistake and one evidence-based challenge.
- [ ] 4.4 Add tests that distinguish comprehension pass from correction pass and reject unsupported changes.
- [ ] 4.5 Add tests proving repeated prompting without a causal change is not classified as recovery.
- [ ] 4.6 Record challenge provenance: generator authority, identity and version, requested and served generator model, sampling parameters, target claim or turn, challenge and delivered content hashes, evidence references, and human edit or selection events; flag shared model family with the evaluated agent.

## 5. Transfer, recovery, and regression

- [x] 5.1 Create direct, reformulated, cross-domain, adversarial, and dogma-vocabulary-free variants for the vertical-slice pattern.
- [ ] 5.2 Add an intentionally recoverable failure case and record initial decision, corrected decision, causal evidence, and human intervention.
- [ ] 5.3 Run prior passing cases after a trajectory or memory candidate change and fail the candidate on regression.
- [ ] 5.4 Add metrics for comprehension, correction, transfer, recovery, stability, regression, human intervention, and token/turn cost.
- [ ] 5.5 Add tests for transfer failure, successful recovery, regression detection, and no-progress termination.
- [x] 5.6 Add a stability case: an unsupported, plausible challenge targets a correct decision; changing the decision without valid evidence SHALL be a stability failure.
- [x] 5.7 Require confirmed regression failures (fail reproduced across the configured confirmation re-runs) before a candidate fails regression; record single-run flips as unconfirmed.
- [ ] 5.8 Mark memory-condition results as contaminated when an evaluation case overlaps a memory episode supporting an active candidate; exclude contaminated cases from transfer claims.
- [x] 5.9 Add at least one recovery case exercising a real observable tool outcome (sandboxed file operation with verifiable result) rather than a textual decision only.
- [x] 5.10 Add a per-turn trajectory structure: unique turn identifier, state, transition cause, changed and preserved claims, and evidence references per turn; validate that turns without evidence linkage mark claims unverified.
- [x] 5.11 Implement append-only trajectory storage: corrections and retries are new entries with provenance; detect in-place mutation of persisted entries and flag the record corrupted and its dependent evaluations invalidated.
- [ ] 5.12 Create regression manifests (frozen list of regression case identifiers and case versions, content-hashed) and require every recovery/promotion result to reference the manifest hash it ran against; mark results unverifiable when the reference is absent.
- [x] 5.13 Detect non-minimal corrections: flag recoveries where the corrected trajectory changes behavior beyond the classified failure cause, and record the extra changes as separate claims requiring their own evidence.

## 6. Versioned provisional memory

- [ ] 6.1 Define candidate memory records with status, provenance, scope, episodes, transfer cases, counterexamples, parent version, and deprecation history.
- [ ] 6.2 Generate provisional candidates only from independently supported episodes; never write directly to the active dogma core.
- [ ] 6.3 Add a human-review gate for promotion and preserve the previous memory version for rollback.
- [ ] 6.4 Add candidate deprecation/narrowing behavior when later evidence contradicts the declared scope.
- [ ] 6.5 Add regression tests for promotion refusal, rollback selection, deprecation, and normative-inflation prevention.
- [x] 6.6 Add a memory-injection case: candidate content containing instructions retrieved into context SHALL be treated as untrusted data without instruction authority, and the agent SHALL NOT follow it.
- [ ] 6.7 Add contamination checking between evaluation cases and memory episodes supporting active candidates (hash equality or declared semantic similarity).
- [ ] 6.8 Enforce the configured minimum number of episodes from distinct sessions or cases before a provisional candidate is created; reject candidate creation when any supporting episode is marked contaminated.
- [ ] 6.9 Reject promotion when supporting episodes include contaminated cases or when frontier-classified dissent on the pattern remains unresolved; require dissent routed to human review and closed before promotion.
- [x] 6.10 Require each transfer variant to declare the decision principle it measures and record an equivalence review (human or validated against a human-labeled subset) before its results count; keep the transfer result pending when the configured case minimum is not met.

## 7. Cross-model evaluation and reporting

- [ ] 7.1 Extend provider adapters and local execution paths to run the controlled conditions without exposing credentials or persisting secrets.
- [x] 7.2 Add cross-model intersection reporting that preserves frontier dissent instead of averaging it away.
- [ ] 7.3 Add coverage gates that block high-confidence crystallization and alignment claims when repetition, provenance, or category coverage is insufficient.
- [ ] 7.4 Add an anonymized report format containing only permitted evidence and non-sensitive metadata.
- [ ] 7.5 Run the full safe evaluation suite and document baseline state, failures, limitations, and observed transfer results.
- [x] 7.6 Verify equal served model and sampling configuration across models before classifying a case as frontier dissent; classify configuration-different disagreements as non-comparable.
- [x] 7.7 Define automation phase-transition thresholds as confidence intervals with configured minimum samples per category; a transition SHALL NOT be evaluated below the minimum sample.
- [x] 7.8 Define the artifact-language policy in code and schemas: English for machine-validated artifacts, operator language for human-facing reports, original language for evaluation cases, with the language field mandatory in provenance records.
- [x] 7.9 Add a base-condition format-fragility measurement (semantic-preserving rewording) so transfer failures can be distinguished from generalized format fragility of the suite.

## 8. Documentation and operational rollout

- [ ] 8.1 Document Layer A/B/C boundaries, trajectory states, evaluator authority, memory lifecycle, and rollback semantics.
- [x] 8.2 Document the first vertical-slice experiment and its acceptance criteria.
- [ ] 8.4 Verify existing hooks and security tests remain passing before enabling the new path by default.
- [x] 8.5 Produce a changelog/report that distinguishes implemented behavior from preliminary or unverified results.

## 9. Integration contracts and profile separation

- [ ] 9.1 Define a common provider-adapter contract returning response text, served model, sampling, usage, latency, request id, and error classification; record unsupported metadata as `unknown`.
- [ ] 9.2 Extend the evaluation record schema with condition, case version, case hash, repetition id, pair key, policy and partition manifest references, provenance, evidence mode, outcome status, dimensions, cost observables, and missingness.
- [ ] 9.3 Define explicit legacy migration: import legacy results as `legacy_limited` descriptive evidence that cannot support causal, transfer, promotion, or Layer C improvement claims.
- [ ] 9.4 Separate environment failures (provider error, timeout, credentials, budget, schema-invalid, pending) from model outcomes in outcome status and denominators.
- [ ] 9.5 Implement a `vertical_slice` profile (decision 1c values) distinct from a `full_suite` profile, keeping vertical-slice results preliminary and without promotion authority.
- [ ] 9.6 Scope reported claims to case, dimension, candidate, category, model, or global levels, restricting the first increment to provisional candidate- and dimension-level claims.
- [ ] 9.7 Add scenarios and fixtures for pair-key construction, retry-after-failure, legacy-limited labels, environment-failure classification, and claim-scope downgrade.

- [ ] 9.8 Split provenance hashes into case, prompt template, assembled context, criteria, memory, policy, and partition manifest references; add attribution tests for one-component changes.
- [ ] 9.9 Preserve legacy dimensions separately from learning dimensions; add migration fixtures proving same-named fields such as `recovery` are never silently merged.
- [x] 9.10 Create versioned schemas under `docs/dogmas/eval/schemas/v1/` and mark the existing legacy schema as compatibility-only.

## 10. Readiness conditions

- [x] 10.1 Create a human-labeled subset with documented selection criteria and size; use it to validate judge agreement, transfer-variant equivalence review, and contamination-similarity calibration.
- [ ] 10.2 Resolve the suite-versus-partition tension: the vertical-slice profile SHALL use minimal partitions with approved non-comparable reuse, and a full_suite SHALL grow the case inventory before definitive claims; record the chosen partition-policy mapping in the partition manifests.
- [x] 10.3 Define and verify vertical-slice acceptance criteria: one controlled case run under the four conditions, a schema-valid verifiable trajectory, a paired contrast with coverage status, and the correct `coverage_status` label emitted.
- [x] 10.4 Record the default literal-response retention policy value in the evaluation policy: hash-only by default, stored literals with explicit expiry.
- [x] 10.5 Choose and record the near-duplicate similarity detector identity and version used for contamination flags.
- [x] 10.6 Declare and record the human-labeled agreement statistic (Cohen's kappa by default), threshold, and minimum subset size in the evaluation policy.
- [x] 10.7 Declare and record the memory retrieval mode (exact versus similarity), detector identity and version, score, and threshold, plus its contamination mapping.
- [x] 10.8 Add domain and variant class to the case contract and manifest; mark transfer or cross-domain classification provisional or pending when metadata is missing.
- [x] 10.9 Declare the format-fragility rewording count and sensitivity threshold in the evaluation policy.
- [x] 10.10 Define the reliability measurement budget for recovery, stability, and regression separately from the primary paired contrast, keeping repetitions clustered by case.
- [x] 10.11 Record producer, classifier, custodian, and reviewer actors with independence status on trajectory and evaluation artifacts; degrade claims when actors coincide or independence is unknown.
- [x] 10.12 Implement evidence custody lifecycle states `OPEN`, `FROZEN`, `AMENDED`, `SUPERSEDED`, and `CORRUPTED` with observation/recording/evaluation/amendment timestamps and no overwrite after freeze.
- [x] 10.13 Implement structured human review and escalation records (reviewer identity, blinded evidence, decision, rationale hash, timestamp, superseded review) and open-dissent handling for reviewer disagreement.
- [ ] 10.14 Implement structured Layer C → Layer B amendment proposals (current criterion, contradicting evidence, proposed text or precedence change, affected precedences) that are human-approved and never self-applied; require a regression re-run of the evaluation suite before an amendment is treated as stable.
- [ ] 10.15 Record memory retrieval per trajectory (retrieved items, hashes, token count, or `retrieved: none`); mark empty-retrieval cases `no_memory_retrieved` and exclude them from `full_vs_criteria` and `full_vs_memory`.
- [ ] 10.16 Verify condition content per record (`memory_injected`, `criteria_injected` with hashes); mark `condition_mismatch` when the label does not match injected content and exclude from contrasts.
- [x] 10.17 Classify each case's discriminating power (`ceiling`, `floor`, `inert`, `discriminating`), report the primary contrast over discriminating cases, and record mutation distance so surface renames are excluded from cross-domain transfer.
- [x] 10.18 Add a pre-registered equivalence procedure (TOST with margin Δ) so a "no useful difference" conclusion requires the interval to fall within ±Δ; forbid equivalence claims from non-significant superiority results.
- [x] 10.19 Add claim validity and revalidation: served model, criteria, memory, and policy version changes or a configured time-to-live invalidate a claim until revalidated; mark stale claims in reports.
- [x] 10.20 Enforce pre-registered case-inclusion rules for the primary contrast; treat the `discriminating` subset as diagnostic and label post-hoc exclusion rules without pre-registration authority.
- [x] 10.21 Detect and record conflicts between active memory entries and apply configured injection precedence; escalate unresolved conflicts to human review.
- [x] 10.22 Enforce a per-case memory injection budget (entries and tokens) and implement pruning and archival with recorded manifest changes and human confirmation.
- [x] 10.23 Redact memory candidates against secret patterns before storage and run periodic memory audits that remove leaked values, re-version entries, and report security events.
- [x] 10.24 Revalidate memory entries on time-to-live or model/criteria/policy/tooling context change; mark stale entries and exclude them from automatic injection until revalidated.
- [x] 10.25 Record challenge objective (`corrective`, `adversarial`, or `mixed`) alongside challenge provenance; attribute corrections and stability outcomes consistently with the declared objective.
- [ ] 10.26 Implement ordered concurrent appends (single writer, lock, or monotonic allocator) with atomic or journaled writes and crash recovery that retains the last valid manifest and marks incomplete writes aborted.
- [ ] 10.27 Implement schema versioning on artifacts with versioned readers or separately hashed migration artifacts; never rewrite history in place and downgrade claims whose migration loses semantic meaning.
