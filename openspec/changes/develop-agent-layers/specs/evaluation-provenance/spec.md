## ADDED Requirements

### Requirement: Evaluation provenance is explicit
Every evaluation result SHALL identify the exact case and these separate content references: canonical `case_hash`, `prompt_template_hash`, assembled `prompt_context_hash`, Layer B `criteria_hash`, Layer C `memory_manifest_hash` when memory is active, evaluation `policy_hash`, and relevant partition manifest hashes. It SHALL also identify requested and served model, sampling parameters, case language, Layer A profile, Layer B criteria version, Layer C memory version, timestamp, classification authority, evidence references, and whether the result is literal, summarized, inferred, or unverified.

#### Scenario: A result lacks literal response evidence
- **WHEN** an evaluator classifies a result from a summary without access to the literal response or observable outcome
- **THEN** the result SHALL be marked limited or unverified and SHALL NOT support a high-confidence crystallization claim

#### Scenario: A tool action is part of the case
- **WHEN** a case evaluates a tool operation
- **THEN** the record SHALL include the observable tool result or explicitly state that it was unavailable

#### Scenario: The provider serves a different model or configuration
- **WHEN** the served model reported by the provider differs from the requested model, or sampling parameters differ from the configured condition
- **THEN** the record SHALL store both requested and served values and comparisons involving the record SHALL be marked non-comparable until the difference is resolved

#### Scenario: Sampling configuration is unknown
- **WHEN** the served model matches the requested model but one or more sampling parameters are not reported
- **THEN** the record SHALL identify the missing parameters and SHALL be non-comparable for claims sensitive to sampling, while remaining eligible for explicitly qualified isolated functional reporting

### Requirement: Evidence references are resolvable
Every evidence reference in a result or trajectory SHALL resolve to an existing artifact whose stored content hash matches the recorded hash. Stored literal responses SHALL be retained under an explicit retention policy with a recorded expiry, and the record SHALL state whether a hash-only mode or a stored-literal mode is in effect.

#### Scenario: A cited artifact is missing or altered
- **WHEN** an evidence reference resolves to a missing artifact or to content whose hash does not match the recorded hash
- **THEN** the result SHALL be marked unverified and SHALL NOT support crystallization, transfer, or promotion claims

#### Scenario: A stored literal response expires
- **WHEN** the retention policy expires a stored literal response while its evaluation result remains in use
- **THEN** the result SHALL be downgraded to hash-only provenance and SHALL NOT continue to support high-confidence claims

### Requirement: Judge classifications are bias-controlled
When the classification authority is a judge model, the system SHALL record the judge identity and SHALL apply documented bias controls. Judge results SHALL NOT support high-confidence claims without measured agreement against a human-labeled subset.

#### Scenario: The judge shares a model family with the evaluated model
- **WHEN** the judge model belongs to the same model family as the evaluated model
- **THEN** the record SHALL flag the family relation and the result SHALL NOT serve as independent confirmation of that model's claims

#### Scenario: The judge compares two responses
- **WHEN** a judge performs a comparative classification
- **THEN** the system SHALL swap or randomize the comparison order and aggregate over orderings, or the record SHALL state that order bias is uncontrolled

#### Scenario: A judge classifies without validated agreement
- **WHEN** a judge has no measured agreement with a human-labeled subset of the same cases
- **THEN** its classifications SHALL be marked provisional and SHALL NOT support crystallization or promotion claims

#### Scenario: The judge can see the condition label
- **WHEN** a judge can identify which evaluation condition produced a response or pair of responses
- **THEN** the system SHALL blind or randomize condition labels before judging, or SHALL flag condition-label bias as uncontrolled and mark the classification provisional for causal claims

### Requirement: Human-labeled agreement is quantified
Agreement between a judge or validator and the human-labeled subset SHALL be measured with a predeclared statistic — Cohen's kappa by default — over a subset of predeclared minimum size. The statistic, threshold, and minimum subset size SHALL be configured in the evaluation policy and recorded with the result. A judge whose agreement is unmeasured or below threshold SHALL remain provisional.

#### Scenario: Judge agreement is below threshold
- **WHEN** the measured agreement of a judge with the human-labeled subset falls below the configured threshold, or the subset is smaller than the configured minimum
- **THEN** the judge's classifications SHALL remain provisional and SHALL NOT support crystallization or promotion claims

#### Scenario: The agreement statistic changes
- **WHEN** the evaluation policy changes the agreement statistic, threshold, or subset size
- **THEN** results SHALL identify the values in effect and SHALL NOT be treated as comparable across policy versions

### Requirement: Evaluation partitions are disjoint and manifested
The evaluation policy SHALL define separate manifests for support or optimization, validation, transfer, regression, and final audit cases when those partitions are used. Each manifest SHALL have a content hash recorded in the policy and every result SHALL identify the partition manifest in effect. A case SHALL NOT appear in multiple partitions unless the overlap is explicitly recorded as contamination or as an approved non-comparable reuse.

#### Scenario: A transfer case overlaps support data
- **WHEN** a case identifier or canonical case hash appears in both a support or optimization manifest and a transfer manifest
- **THEN** the transfer result SHALL be marked contaminated or non-comparable and SHALL NOT support a definitive transfer claim

#### Scenario: A partition manifest changes
- **WHEN** the frozen case list or case version in a partition manifest changes
- **THEN** the manifest hash SHALL change, affected comparisons SHALL identify the new manifest, and historical results SHALL retain the prior manifest reference

### Requirement: Evaluation conditions are comparable
The system SHALL support controlled comparison of at least four conditions: base model, model with Layer B criteria, model with criteria plus memory, and model with criteria plus memory plus bounded Socratic dialogue.

#### Scenario: Comparing Layer C contribution
- **WHEN** the same case set is evaluated under the four conditions
- **THEN** the report SHALL show comprehension, correction, transfer, recovery, stability, regression, and cost separately by condition

#### Scenario: Configuration differs between conditions
- **WHEN** model, prompt, memory, temperature, tool availability, or case versions differ
- **THEN** the report SHALL identify the difference and SHALL NOT claim a causal comparison without qualification

#### Scenario: Conditions are compared statistically
- **WHEN** two conditions are compared on the same cases
- **THEN** the report SHALL compute per-case paired differences with a paired test or paired bootstrap and report confidence intervals, and SHALL NOT claim improvement from aggregate pass rates alone

#### Scenario: A reliability dimension is measured
- **WHEN** a dimension measures consistency across repetitions, such as recovery, stability, or regression
- **THEN** each condition SHALL be run for the configured minimum number of repetitions and the report SHALL state result consistency across those repetitions

#### Scenario: Memory content overlaps an evaluation case
- **WHEN** an evaluation case matches a memory episode that supports an active candidate
- **THEN** the memory-condition result for that case SHALL be marked contaminated and excluded from transfer and improvement claims for that candidate

### Requirement: Transfer cases resist surface overfitting
The evaluation suite SHALL include direct, reformulated, cross-domain, adversarial, and dogma-vocabulary-free variants of learned patterns.

#### Scenario: Pattern succeeds only with familiar vocabulary
- **WHEN** a model passes a calibrated case but fails an equivalent case without dogma terminology
- **THEN** transfer SHALL be classified as failed or pending and the memory candidate SHALL remain provisional

#### Scenario: Pattern transfers to another domain
- **WHEN** the same decision principle is applied correctly in an unseen domain with valid evidence
- **THEN** the transfer result SHALL record the source case, target domain, evidence, and evaluator authority

### Requirement: Transfer variants are validated as equivalent
Each transfer variant SHALL declare the decision principle it measures and SHALL pass an equivalence review before use — human review or a review validated against a human-labeled subset. A cross-domain or unseen-domain variant SHALL count as such only for domains with no supporting episodes of the candidate in memory. Each candidate SHALL have at least the configured minimum number of transfer cases before its transfer result is definitive. The suite SHALL report base-condition format fragility — measured with a predeclared number of semantic-preserving rewordings and a predeclared sensitivity threshold — alongside transfer results so generalized format fragility can be distinguished from transfer failure.

#### Scenario: A variant is used without equivalence review
- **WHEN** a transfer variant lacks a recorded equivalence review of the principle it measures
- **THEN** its results SHALL be marked provisional and SHALL NOT support or reject the candidate's transfer status

#### Scenario: The transfer case minimum is not met
- **WHEN** a candidate has fewer than the configured minimum transfer cases across the required variant classes
- **THEN** the transfer result SHALL be recorded as pending rather than failed or passed

#### Scenario: Transfer failure coincides with high base fragility
- **WHEN** the transfer variants fail while the base condition also shows high sensitivity to semantic-preserving rewording
- **THEN** the report SHALL attribute the result to suite format fragility in addition to, or instead of, a transfer failure of the candidate

#### Scenario: Base fragility lacks a predeclared protocol
- **WHEN** base-condition format fragility is measured without a predeclared rewording count or sensitivity threshold
- **THEN** the fragility attribution SHALL be provisional and SHALL NOT override a transfer result

### Requirement: Crystallization claims require coverage gates
The system SHALL prevent a global alignment or crystallization claim when coverage, repeated passes, provenance, or independent evaluation requirements are incomplete.

#### Scenario: Coverage is uneven across models
- **WHEN** some models or categories have fewer configured repetitions than the evaluation policy requires
- **THEN** the report SHALL expose the gap and SHALL label the aggregate conclusion preliminary

#### Scenario: Models disagree
- **WHEN** valid evaluations disagree on a case or dimension after confirming equal served models and sampling configuration
- **THEN** the report SHALL classify the case as frontier or unresolved and SHALL route it to human review rather than averaging away the dissent

### Requirement: Evaluations include regression and recovery
The suite SHALL retain previously passing cases and run them after a memory or protocol change, alongside an intentionally recoverable failure case.

#### Scenario: Memory change breaks a prior case
- **WHEN** a candidate memory version causes a prior passing case to fail
- **THEN** the candidate SHALL fail regression, remain unpromoted, and preserve the previous version

#### Scenario: Agent recovers after correction
- **WHEN** the agent receives a valid challenge after an induced mistake and corrects its decision
- **THEN** the report SHALL distinguish initial result, corrected result, recovery evidence, and any human intervention

#### Scenario: A regression failure is not reproduced
- **WHEN** a previously passing case fails once under a candidate and passes again on the configured confirmation re-runs
- **THEN** the failure SHALL be recorded as unconfirmed and SHALL NOT by itself block the candidate, while remaining visible in the report

### Requirement: Missing served-model identity is explicit
The system SHALL classify served-model and configuration uncertainty into `served_model_unknown` (provider omits served identity), `served_model_mismatch` (provider reports a model different from the requested one), and `sampling_unknown` (served identity matches but sampling parameters are missing). The record SHALL store the missing value as `unknown`, expose the missing provider field, and SHALL NOT substitute an unverified requested-model label for served-model evidence.

#### Scenario: The provider omits served-model identity
- **WHEN** a result has a requested model but no provider-reported served model
- **THEN** the result SHALL record `served_model: unknown`, expose the missing provenance, and SHALL NOT support a high-confidence cross-model or causal comparison

### Requirement: Evaluation thresholds are versioned policy
All configured minima and thresholds — including repetitions, transfer cases, candidate episodes, category samples, turn budgets, and confirmation reruns — SHALL live in a versioned evaluation policy. Every result and aggregate report SHALL identify the policy version and its content hash. The policy SHALL distinguish hard gates (missing values block promotion), reporting thresholds (affect labels only), budgets (turns, tokens, cost), and statistical settings (tests, intervals, multiplicity corrections). An unset or incomplete minimum SHALL produce a pending or preliminary result rather than an implicit default.

#### Scenario: A policy changes between evaluations
- **WHEN** two evaluations use different threshold or repetition policies
- **THEN** the report SHALL identify both policy versions and SHALL NOT treat the results as directly comparable without qualification

#### Scenario: A required minimum is not configured
- **WHEN** a required gate lacks a configured minimum
- **THEN** the affected claim SHALL remain pending or preliminary and SHALL NOT be promoted by assuming an undocumented value

### Requirement: Contamination detection is tiered
The system SHALL classify evaluation-case and memory-episode overlap using at least three outcomes: exact canonical-content match SHALL be hard contamination; high declared or measured similarity SHALL be a contamination flag requiring review; and thematic or mechanism overlap alone SHALL NOT be contamination without evidence that the target case was available for memorization. Hard contamination SHALL exclude the affected result from transfer and improvement claims. An unresolved flag SHALL keep the affected claim provisional, and contamination status SHALL propagate to candidate claims that rely on the affected episode. Every similarity flag SHALL record the detector identity and version, score, threshold, the compared artifact hashes, the review authority, and the final resolution.

#### Scenario: A case exactly matches a supporting episode
- **WHEN** canonical case or episode content hashes match
- **THEN** the result SHALL be marked contaminated and excluded from transfer, improvement, and promotion claims for the candidate

#### Scenario: A case is a near-duplicate
- **WHEN** similarity detection flags a case as a possible paraphrase or near-duplicate
- **THEN** the result SHALL remain provisional until the similarity review is resolved by a human or a validator calibrated against human labels

#### Scenario: A case shares only a decision mechanism
- **WHEN** a target case shares a general mechanism or topic with an episode but was not available as supporting content
- **THEN** the overlap SHALL be recorded as thematic similarity and SHALL NOT by itself invalidate the transfer result

### Requirement: Statistical comparisons preserve pairing and multiplicity controls
Statistical comparisons SHALL be paired. For paired binary outcomes, the primary comparison SHALL use an exact paired discordance test (such as exact McNemar) on per-case outcomes, and the effect SHALL be the paired risk difference with a paired confidence interval. For continuous or cost metrics, the report SHALL use a paired bootstrap or another predeclared paired interval method. The evaluation policy SHALL predeclare exactly one primary contrast and one primary dimension, distinguish confirmatory from exploratory analyses, and apply a documented multiplicity control (such as Holm) to secondary claims. The statistical unit SHALL be declared per dimension, and repetitions SHALL be clustered by case rather than treated as independent cases. A definitive claim SHALL require the configured discordance minimum, interval-width gate, and minimum important difference, in addition to provenance and contamination gates. Non-significance SHALL NOT be reported as evidence of no effect when coverage or power is insufficient.

#### Scenario: Binary conditions are compared on the same cases
- **WHEN** two conditions produce binary outcomes for the same case set
- **THEN** the report SHALL show the discordant pairs, exact paired test result, effect estimate, and confidence interval rather than relying on aggregate pass rates

#### Scenario: Several dimensions or comparisons are tested
- **WHEN** a report tests multiple dimensions, conditions, or categories
- **THEN** it SHALL identify the predeclared primary comparison and apply the configured multiplicity correction to secondary claims

#### Scenario: The sample is too small for a reliable conclusion
- **WHEN** the configured coverage or repetitions are insufficient to distinguish the targeted effect
- **THEN** the report SHALL label the result inconclusive or preliminary and SHALL NOT convert a non-significant result into a claim of equivalence

#### Scenario: A definitive claim is attempted below the gates
- **WHEN** a contrast has fewer discordant pairs than the configured minimum, or its interval exceeds the configured width gate, or the effect does not reach the configured minimum important difference
- **THEN** the claim SHALL be labeled preliminary or inconclusive and SHALL NOT be promoted or cited as definitive

#### Scenario: Cost-effectiveness is computed
- **WHEN** cost per effect delta is reported for a contrast
- **THEN** the report SHALL show the cost metrics and SHALL mark cost-effectiveness undefined unless the delta is positive, its interval excludes zero, and it exceeds the minimum important difference

### Requirement: Rates report explicit denominators and missingness
Every rate SHALL report its denominator type — eligible, attempted, or completed — and SHALL state the eligible, attempted, and completed counts plus any excluded-by-design, blocked, aborted, schema-invalid, and unknown cases. A pass rate SHALL identify whether it is computed over completed or attempted cases, and SHALL be accompanied by a completion rate. Missing or interrupted cases SHALL NOT silently disappear from the report.

#### Scenario: A case is blocked or aborted
- **WHEN** a case is blocked, aborted, interrupted, or schema-invalid
- **THEN** the report SHALL count it explicitly in the denominator breakdown and SHALL NOT treat it as a pass or a fail

#### Scenario: The denominator is ambiguous
- **WHEN** a pass rate is reported without stating whether the denominator is completed or attempted cases
- **THEN** the report SHALL be marked incomplete and the rate SHALL NOT support a definitive claim

### Requirement: Evaluation records identify condition and pairing identity
Every modern evaluation record SHALL identify the condition, case identifier, case version, canonical case hash, repetition identifier, and a pair key joining the same case-version-repetition across conditions. Records with the same case identifier but different case versions SHALL NOT be paired. A retry after an infrastructure failure SHALL receive a new repetition identifier and SHALL NOT overwrite the failed attempt.

#### Scenario: Case versions differ
- **WHEN** two records share a case identifier but have different case versions or case hashes
- **THEN** the records SHALL be marked non-comparable and SHALL NOT contribute to a paired contrast

#### Scenario: A failed attempt is retried
- **WHEN** a case is re-run after a provider error, timeout, or budget interruption
- **THEN** the retry SHALL preserve the original attempt as missingness evidence and SHALL use a new repetition identifier

### Requirement: Cases declare domain and variant class
Each evaluation case SHALL declare in its case contract and manifest its domain, variant class (direct, reformulated, cross-domain, adversarial, or dogma-vocabulary-free), and the decision principle it measures. A transfer or unseen-domain claim SHALL reference the declared case domain and the domain coverage of the candidate's supporting episodes.

#### Scenario: A case lacks domain metadata
- **WHEN** a case does not declare its domain or variant class
- **THEN** transfer and cross-domain classification for that case SHALL be provisional or pending

### Requirement: Provider adapters expose served identity and usage
Each provider adapter SHALL expose response text, provider-reported served model, sampling parameters, token usage when available, latency, and a provider request identifier. An unavailable value SHALL be recorded as `unknown`, not omitted or fabricated. Credentials and secret request metadata SHALL never appear in adapter output or persisted records.

#### Scenario: An adapter cannot report served identity
- **WHEN** the adapter cannot obtain the provider-reported served model
- **THEN** the record SHALL store `served_model: unknown` and comparisons requiring served identity SHALL be non-comparable or provisional

#### Scenario: Usage metadata is unavailable
- **WHEN** the provider does not report token usage or latency
- **THEN** the corresponding trajectory fields SHALL be `unknown`, not zero, and cost claims SHALL be qualified accordingly

### Requirement: Legacy results have limited provenance
Legacy evaluation results imported into the modern reporting path SHALL receive `legacy_limited` provenance, `unverified` classification authority, unknown served-model and sampling fields, and summary-only evidence mode. Legacy results MAY appear in descriptive reports but SHALL NOT support causal, transfer, promotion, or Layer C improvement claims.

#### Scenario: A legacy result enters a report
- **WHEN** a legacy result is included in a modern report
- **THEN** the report SHALL label it legacy-limited and exclude it from paired comparisons and improvement claims

#### Scenario: Legacy evidence is the only support
- **WHEN** a claim relies only on legacy-limited results
- **THEN** the claim SHALL remain unverified and SHALL NOT be promoted

### Requirement: Environment failures are distinct from model outcomes
Provider errors, timeouts, invalid credentials, budget exhaustion, schema-invalid responses, and pending classification SHALL be represented separately from model behavioral outcomes. Only a completed, classified run SHALL contribute a model pass or fail. Environment failures SHALL be reported as availability or missingness evidence rather than model performance.

#### Scenario: A provider call fails
- **WHEN** a provider call fails or times out
- **THEN** the attempt SHALL be recorded as an environment or availability event and SHALL NOT count as a model failure

#### Scenario: A response is invalid or pending
- **WHEN** a response is schema-invalid or its classification remains pending
- **THEN** it SHALL be excluded from pass-rate numerators and model-outcome denominators and reported separately

### Requirement: Claims are scoped to an evidence level
Every reported claim SHALL declare one scope: `case`, `dimension`, `candidate`, `category`, `model`, or `global`. Claims above candidate scope SHALL require the configured coverage, provenance, and independence gates. Global alignment or crystallization claims SHALL require complete coverage and independent evaluation and SHALL NOT be emitted from provisional or legacy-limited evidence.

#### Scenario: A candidate-level claim is reported
- **WHEN** a candidate-level claim is reported
- **THEN** it MAY remain provisional but SHALL identify the candidate, dimension, policy version, and relevant partition manifest hashes

#### Scenario: A global claim lacks coverage
- **WHEN** a global claim is requested without complete coverage or independent evaluation
- **THEN** the report SHALL refuse it or downgrade it to the strongest supported scope

### Requirement: Legacy and learning dimensions are not silently merged
Legacy dimensions such as `clarity`, `security`, `judgment`, `recovery`, and `discipline` SHALL remain descriptive legacy fields. Learning dimensions — `comprehension`, `correction`, `transfer`, `recovery`, `stability`, and `regression` — SHALL use a versioned semantic definition. A legacy field SHALL NOT be aggregated with a learning field merely because their names match; a legacy `recovery` value SHALL be represented as `legacy_recovery` or otherwise marked non-comparable.

#### Scenario: A legacy result has a same-named dimension
- **WHEN** a legacy result contains `recovery` and a modern result contains learning `recovery`
- **THEN** the report SHALL preserve both under distinct semantic names and SHALL NOT combine them in a rate, effect estimate, or promotion claim

#### Scenario: A condition changes one provenance component
- **WHEN** two otherwise paired records have equal case and prompt-template hashes but differ in criteria, memory, policy, or prompt-context hash
- **THEN** the report SHALL identify the changed component, limit the comparison claim to the conditions actually supported by the difference, and SHALL NOT describe the result as an uncontrolled prompt change

### Requirement: Human review is a structured, recorded decision
Every human review and escalation SHALL be recorded as a structured event with reviewer identity and role, evidence and condition context seen by the reviewer, whether condition labels were blinded, the decision (`approve`, `reject`, `defer`, `escalate`), a rationale hash, timestamp, and any superseded review it replaces. A review that cannot identify its reviewer, evidence, or decision SHALL be treated as unverified.

#### Scenario: Two reviewers disagree
- **WHEN** two reviewers reach different decisions on the same evidence
- **THEN** the disagreement SHALL be recorded as open dissent, both positions retained, and the claim SHALL NOT be promoted until the dissent is resolved or escalated with both positions preserved

#### Scenario: A reviewer is also the producer or classifier
- **WHEN** a reviewer, producer, or classifier is the same actor
- **THEN** the record SHALL flag the overlap and SHALL degrade the independence of any claim relying on that review

#### Scenario: A human escalation records its resolution
- **WHEN** a `HUMAN_ESCALATION` is resolved
- **THEN** the resolution SHALL append the human decision, the evidence reviewed, the escalation reason, and the final outcome, and SHALL reference the original trajectory

### Requirement: Condition content is verified, not assumed
Each record SHALL verify that the content implied by its condition was actually present — for example `memory_injected: true` with its hashes, or `criteria_injected: true`. A record whose declared condition does not match the content actually injected SHALL be marked `condition_mismatch`, excluded from contrasts, and reported. A condition label SHALL NOT be trusted without a content-level confirmation.

#### Scenario: A full condition runs without injected memory
- **WHEN** a record declares a memory-bearing condition but no memory content was injected into the prompt
- **THEN** the record SHALL be marked `condition_mismatch`, excluded from the paired contrast, and counted in the report as an integration failure rather than an evaluation result

#### Scenario: Prompt composition is unverifiable
- **WHEN** the runner cannot confirm the assembled prompt composition for a record
- **THEN** the record SHALL be marked provisional and SHALL NOT support a definitive contrast claim

### Requirement: Cases report discriminating power
The suite SHALL report, per case, whether it can discriminate between conditions: `ceiling` (all conditions pass), `floor` (all conditions fail), `inert` (no plausible pathway for the tested difference), or `discriminating`. The primary contrast SHALL be reported over discriminating cases, with the full-suite result shown alongside and the composition of ceiling, floor, and inert cases disclosed.

#### Scenario: The suite is mostly non-discriminating
- **WHEN** most cases are classified `ceiling`, `floor`, or `inert`
- **THEN** the report SHALL expose the composition and SHALL label any aggregate conclusion as preliminary regardless of the p-value

#### Scenario: A case is inert for the tested difference
- **WHEN** a case offers no pathway for the memory or protocol to influence the outcome
- **THEN** it SHALL be classified `inert` and SHALL NOT be counted as evidence for or against the contrast

### Requirement: Transfer variants meet a minimum mutation distance
A transfer variant SHALL record its mutation distance from the case it derives from and SHALL declare the decision principle it exercises. A variant that differs only in surface vocabulary, naming, or formatting SHALL be classified as a surface variant and SHALL NOT count as cross-domain or unseen-domain transfer.

#### Scenario: A variant is a superficial rename
- **WHEN** a claimed transfer variant differs from its source only in vocabulary, naming, or formatting
- **THEN** it SHALL be recorded as a surface variant, marked provisional, and excluded from cross-domain transfer evidence

### Requirement: Layer C falsifiability uses a pre-registered equivalence test
The system SHALL define a pre-registered equivalence margin Δ for the primary contrast and SHALL support a two one-sided tests (TOST) procedure so that "Layer C does not exceed Layer B" can be concluded with the same discipline as a positive PASS. A conclusion of no useful difference SHALL require the paired confidence interval to fall entirely within ±Δ and SHALL NOT be inferred from a non-significant superiority test alone. The equivalence margin SHALL be configured in the evaluation policy and recorded in every report that uses it.

#### Scenario: A non-significant test is treated as equivalence
- **WHEN** a contrast is non-significant but its interval is not shown to fall within the pre-registered ±Δ margin
- **THEN** the report SHALL NOT claim that Layer C does not exceed Layer B, and the conclusion SHALL remain inconclusive

#### Scenario: The equivalence margin is used
- **WHEN** a report concludes that Layer C does not add a useful effect
- **THEN** it SHALL show the TOST or equivalent interval result against the recorded Δ, and the equivalence SHALL hold only if the interval lies within ±Δ

### Requirement: Claims expire and revalidate
Every claim SHALL declare its validity period or revalidation triggers: a change in served model, Layer B criteria version, Layer C memory version, evaluation policy version, or a configured time-to-live SHALL invalidate the claim until revalidated. Reports SHALL mark stale claims and SHALL NOT present them as current evidence without revalidation.

#### Scenario: The served model changes after a claim
- **WHEN** a claim exists and the served model, criteria, memory, or policy version changes after its evaluation
- **THEN** the claim SHALL be marked stale or require revalidation before supporting current promotion or improvement decisions

#### Scenario: A claim exceeds its time-to-live
- **WHEN** a claim has not been revalidated within its configured time-to-live
- **THEN** it SHALL be labeled stale and SHALL NOT support current high-confidence decisions

### Requirement: Case inclusion is pre-registered, not post hoc
Exclusion of cases from a primary contrast — including `no_memory_retrieved`, `condition_mismatch`, `inert`, `ceiling`, or `floor` cases — SHALL follow pre-registered exclusion rules in the evaluation policy. A primary contrast SHALL be reported over the pre-registered analysis set, and any additional per-case classification such as `discriminating` SHALL be reported as diagnostic alongside the full analysis set and SHALL NOT silently replace it.

#### Scenario: Only discriminating cases are shown
- **WHEN** a report shows a contrast only over `discriminating` cases without also showing the pre-registered full analysis set
- **THEN** the report SHALL be marked incomplete and SHALL NOT support a definitive improvement claim

#### Scenario: Exclusion rules change after results
- **WHEN** case-inclusion or exclusion rules are changed after observing results
- **THEN** the comparison SHALL be labeled post-hoc, SHALL require justification, and SHALL NOT carry the authority of a pre-registered analysis
## Implementation status (audited)

The following requirement areas have verified contract implementations and focused tests:

- Judge bias controls and provisional classification: `docs/dogmas/eval/contract/p2_1.py` and `test_p2_1.py`.
- Paired comparison, evidence-reference resolution, and literal retention: `p2_1.py` and `test_p2_1.py`.
- Transfer variants and equivalence review: `transfer_variants.py` and `test_transfer_variants.py`.
- Statistical discrimination, TOST, claim revalidation, and pre-registration: `p2_3.py` and `test_p2_3.py`.
- Cross-model comparability, frontier dissent, format fragility, thresholds, and language fields: `p2_4.py` and `test_p2_4.py`.
- Human-label calibration, contamination tiers, retrieval modes, domain metadata, and reliability budgets: `p2_5.py` and `test_p2_5.py`.
- Challenge objectives and outcome attribution: `p2_6.py` and `test_p2_6.py`.
- Memory conflicts, injection budgets, redaction audits, and TTL/context revalidation: `p2_7.py` and `test_p2_7.py`.

These implementations are contract-level and do not by themselves prove provider execution, complete-suite coverage, partition-policy adoption, anonymized reporting, or production readiness. Requirements without a verified runner integration remain pending in `tasks.md`.
