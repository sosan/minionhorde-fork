## ADDED Requirements

### Requirement: Operational trajectories are recorded
The system SHALL record each learning session as a structured trajectory containing case identity, requested and served model, provider, sampling parameters, case language, Layer A profile, Layer B criteria version, Layer C memory version, bounded turns, decisions, claims, assumptions, uncertainties, evidence references, corrections, evaluator authority, observable outcomes, and cost observables — input tokens, output tokens, total tokens when derivable, latency, model calls, provider errors or retries, and monetary cost when available. Unavailable cost fields SHALL be recorded as `unknown`, not zero.

#### Scenario: A trajectory completes
- **WHEN** a session reaches a terminal state
- **THEN** the system SHALL persist a schema-valid record with its terminal state, reason, versions, and evaluation status

#### Scenario: A trajectory is interrupted
- **WHEN** the provider, tool, budget, or human interrupts a session
- **THEN** the system SHALL persist an incomplete record with the interruption cause and SHALL NOT classify it as a successful learning result

### Requirement: Trajectory records are immutable and per-turn structured
Trajectory records SHALL be append-only. Corrections, retries, and post-terminal annotations SHALL be added as new entries with provenance, never by overwriting prior entries. Each turn SHALL carry a unique identifier, the state it belongs to, the transition cause, changed and preserved claims, and its evidence references.

#### Scenario: A trajectory entry is modified after persistence
- **WHEN** any persisted entry of a completed trajectory is altered in place instead of appended
- **THEN** the system SHALL detect the mutation, invalidate the evaluation results that depend on that record, and flag the record as corrupted in its provenance

#### Scenario: A turn lacks evidence linkage
- **WHEN** a turn changes or preserves a claim without referencing its supporting evidence
- **THEN** the record SHALL mark that claim as unverified for the affected turn and it SHALL NOT count toward correction or comprehension results

### Requirement: Socratic calibration is bounded and explicit
The system SHALL support the states `INIT`, `INTERPRET`, `REFORMULATE`, `CHALLENGE`, `EVIDENCE_CHECK`, `CORRECT`, `AUDIT`, `TRANSFER_TEST`, `RECOVER`, and `HUMAN_ESCALATION`, plus terminal states. Human input SHALL be recorded as a response event attached to the `HUMAN_ESCALATION` state, not as a second trajectory state. Each transition SHALL record its triggering evidence or decision.

#### Scenario: The agent reformulates a criterion
- **WHEN** calibration reaches `REFORMULATE`
- **THEN** the trajectory SHALL record the interpreted premises, assumptions, uncertainties, and a reformulation that can be evaluated independently

#### Scenario: A challenge identifies a valid error
- **WHEN** a challenge supplies evidence that contradicts an agent claim
- **THEN** the agent SHALL identify the affected claim, explain the reason for change, preserve claims that remain supported, and transition to `AUDIT` or `RECOVER`

#### Scenario: A challenge is unsupported
- **WHEN** a challenge contains no verifiable evidence or conflicts with a higher-precedence control
- **THEN** the system SHALL record the challenge as unsupported and SHALL NOT force a correction

#### Scenario: A challenge targets a correct decision
- **WHEN** an unsupported challenge targets a decision that independent evidence confirms is correct
- **THEN** preserving the decision SHALL be recorded as a stability pass and changing it SHALL be recorded as a stability failure

### Requirement: Challenges have independent provenance and declared objective
Every challenge SHALL record its objective (`corrective`, `adversarial`, or `mixed`) in addition to its generator authority (`human`, `rule`, `judge`, `heuristic`, or `unverified`), generator identity and version, requested and served generator model when applicable, generator sampling parameters when applicable, generation timestamp, target claim or turn, challenge content hash, evidence references, and whether the challenge was generated, selected, or edited by a human. A corrective challenge targets a supported error; an adversarial challenge tests resistance or stability; a mixed challenge SHALL identify the objective of each sub-challenge. A challenge SHALL NOT be treated as valid causal evidence solely because it changed the agent's decision. The challenge generator SHALL be distinct from the evaluated agent record, and any shared model family SHALL be flagged.

#### Scenario: A rule-generated challenge is applied
- **WHEN** a deterministic rule emits a challenge targeting an identified claim
- **THEN** the record SHALL include the rule identifier and version, input claim hash, evidence references, and deterministic generation metadata

#### Scenario: A model-generated challenge is applied
- **WHEN** a judge or provider model generates a challenge
- **THEN** the record SHALL include requested and served model identity, sampling parameters, prompt/context hash, generator authority, and model-family relation to the evaluated agent; missing metadata SHALL make the challenge provisional

#### Scenario: A challenge is human-edited
- **WHEN** a human edits or selects generated challenge content before delivery
- **THEN** the record SHALL preserve the generated content hash, final delivered content hash, editor authority, edit or selection event, and both evidence references

#### Scenario: A challenge lacks independent evidence
- **WHEN** a challenge has no resolvable evidence or relies only on the evaluated agent's self-description
- **THEN** the challenge SHALL be marked unsupported or provisional and SHALL NOT support a verified correction or recovery claim

#### Scenario: The challenger shares a model family with the evaluated agent
- **WHEN** the challenge generator belongs to the same model family as the evaluated agent
- **THEN** the record SHALL flag the relationship and SHALL NOT treat the challenge as independent confirmation without external evidence or human validation

### Requirement: Correction is evaluated separately from comprehension
The system SHALL produce separate results for comprehension, correction, transfer, recovery, stability, and regression. A positive result in one dimension SHALL NOT imply a positive result in another.

#### Scenario: The agent understands but cannot transfer
- **WHEN** the reformulation is correct but the agent fails an unseen-domain case
- **THEN** comprehension SHALL be recorded as passing and transfer SHALL be recorded as failing or pending

#### Scenario: The agent changes without evidence
- **WHEN** the final decision changes but no valid causal evidence is linked to the change
- **THEN** correction SHALL NOT be classified as a verified pass

### Requirement: Recovery is evidence-based
The system SHALL support bounded recovery by classifying a failure, identifying its cause, applying a minimal correction, rerunning the original case, and running regression cases. Repeating the same prompt without a change in cause or context SHALL NOT count as recovery.

#### Scenario: Recovery succeeds
- **WHEN** a corrected trajectory passes the original case and its regression cases without a new failure
- **THEN** recovery SHALL be recorded as passing with the correction and evidence references

#### Scenario: Recovery introduces regression
- **WHEN** the correction fixes the original case but breaks a previously passing case
- **THEN** recovery SHALL be marked failed, the candidate SHALL remain provisional, and the prior memory version SHALL remain selectable

### Requirement: Regression suites are manifested and corrections are minimal
Each memory candidate and each recovery run SHALL reference the hash of the regression manifest in effect — the frozen list of regression case identifiers and case versions — and recovery SHALL be evaluated against that manifest. A correction SHALL address only the identified cause; any additional change SHALL be recorded and SHALL mark the recovery as non-minimal.

#### Scenario: Recovery is claimed without a manifest reference
- **WHEN** a recovery or promotion result does not reference the regression manifest hash it was run against
- **THEN** the result SHALL be marked unverifiable and SHALL NOT support promotion

#### Scenario: The correction exceeds the identified cause
- **WHEN** the corrected trajectory changes behavior beyond the classified cause of failure
- **THEN** the recovery SHALL be marked non-minimal, the extra changes SHALL be recorded as separate claims requiring their own evidence, and the recovery result SHALL NOT be classified as a verified minimal correction

### Requirement: Memory candidates are versioned and reversible
The system SHALL represent memory entries with status, provenance, supporting episodes, transfer cases, counterexamples, scope, parent version, and deprecation information. Automatic promotion to an active dogma SHALL be prohibited.

#### Scenario: A candidate is proposed
- **WHEN** at least the configured minimum number of episodes from distinct sessions or cases share a mechanism, with none marked contaminated
- **THEN** the system SHALL create a provisional candidate referencing those episodes and SHALL identify required transfer and regression tests

#### Scenario: Promotion is attempted with contamination or open dissent
- **WHEN** a candidate's supporting episodes include contaminated cases, or a frontier-classified dissent on the pattern remains unresolved
- **THEN** promotion SHALL be rejected until the episodes are replaced and the dissent is routed to human review and closed

#### Scenario: A candidate passes validation
- **WHEN** a candidate passes transfer and regression checks and receives the required human review
- **THEN** it MAY be marked promoted in a new memory version while retaining the previous version for rollback

#### Scenario: A candidate becomes invalid
- **WHEN** a later case contradicts the candidate within its declared scope
- **THEN** the system SHALL mark it deprecated or narrowed, preserve its history, and SHALL NOT delete the evidence

#### Scenario: Retrieved memory content carries instructions
- **WHEN** candidate content retrieved into the model context contains instructions or behavior-modifying content
- **THEN** the content SHALL be treated as untrusted data without instruction authority, and the evaluation suite SHALL include at least one memory-injection case exercising this boundary

### Requirement: Memory retrieval is explicit and contamination-aware
The retrieval mechanism that brings memory candidates into model context SHALL be declared in the evaluation policy and recorded per trajectory. Exact-match retrieval SHALL use canonical case and episode hashes; similarity-based retrieval SHALL record the detector identity and version, similarity score, and threshold. Contamination treatment SHALL be consistent with the retrieval mode: similarity retrieval SHALL trigger near-duplicate contamination review, while exact-match-only retrieval SHALL NOT treat thematic similarity as contamination for retrieval purposes.

#### Scenario: Retrieval is similarity-based
- **WHEN** memory is retrieved by similarity rather than exact canonical match
- **THEN** each retrieved item SHALL record the detector identity and version, score, and threshold, and near-duplicate contamination review SHALL apply

#### Scenario: Retrieval is exact-match only
- **WHEN** memory is retrieved by exact canonical match only
- **THEN** thematic overlap SHALL NOT by itself count as contamination for retrieval, and the memory-injection boundary SHALL remain tested separately

### Requirement: Memory candidates resolve internal conflicts
When two or more active memory entries contradict each other within their declared scope, the system SHALL detect the conflict, record it, and define injection precedence for retrieval. A conflict SHALL NOT be resolved by injecting both entries with equal authority. The resolution SHALL be recorded with the reasoning and the affected entries.

#### Scenario: Two active candidates contradict
- **WHEN** two active memory entries make opposite or incompatible claims within overlapping scope
- **THEN** the system SHALL record the conflict, apply the configured precedence rule, and SHALL NOT inject both as equally authoritative guidance

#### Scenario: A conflict remains unresolved
- **WHEN** no configured rule resolves a detected memory conflict
- **THEN** the conflict SHALL be escalated to human review and the affected entries SHALL be marked conflicting until resolved

### Requirement: Memory injection is budgeted and pruned
Each memory-bearing trajectory SHALL respect a configured injection budget — maximum retrieved entries and maximum retrieved tokens per case. The system SHALL support pruning and archival of deprecated or stale memory entries so the active memory does not grow unboundedly, and a pruning or archival event SHALL be recorded.

#### Scenario: Memory injection exceeds the budget
- **WHEN** retrieval would inject more entries or tokens than the configured budget for a case
- **THEN** retrieval SHALL be truncated to the budget, the truncation SHALL be recorded, and the report SHALL show injection coverage alongside the result

#### Scenario: Memory grows beyond the active set
- **WHEN** active memory exceeds the configured size threshold
- **THEN** the system SHALL propose pruning or archival candidates, require human confirmation, and record the resulting manifest change

### Requirement: Memory content is redacted before storage
Candidate and memory entries SHALL be redacted against the configured secret patterns before persistence, and redaction events SHALL be recorded. Stored memory SHALL be audited periodically for leaked protected values, and a detected leak SHALL be removed and reported.

#### Scenario: An episode contains a protected value
- **WHEN** an episode or candidate contains a value matching a configured secret pattern
- **THEN** the value SHALL be redacted before the memory entry is persisted and the redaction event SHALL be recorded without the secret

#### Scenario: Memory is audited for leaked secrets
- **WHEN** a periodic audit scans stored memory entries
- **THEN** a detected protected value SHALL be removed, the entry SHALL be re-versioned, and the leak SHALL be reported as a security event

### Requirement: Memory entries expire or revalidate by context
Active memory entries SHALL be revalidated on a configured time-to-live or when model, criteria, policy, or tooling context changes. An entry that is not revalidated SHALL be marked stale and SHALL lose automatic injection authority until revalidated.

#### Scenario: Context changes after a pattern is stored
- **WHEN** the served model, Layer B criteria, evaluation policy, or tooling changes after an entry was stored
- **THEN** the affected entries SHALL be marked for revalidation and SHALL NOT be injected with full authority until revalidated

#### Scenario: An entry exceeds its time-to-live
- **WHEN** a memory entry has not been revalidated within its configured time-to-live
- **THEN** it SHALL be marked stale, excluded from automatic injection, and listed for review or deprecation

### Requirement: Learning avoids private reasoning persistence
The system SHALL persist structured claims, decisions, evidence, and changes rather than requiring unrestricted storage of hidden chain-of-thought or provider-internal reasoning.

#### Scenario: A provider returns internal reasoning metadata
- **WHEN** the provider response contains hidden or provider-internal reasoning
- **THEN** the system SHALL exclude it from the standard trajectory record and SHALL retain only permitted summaries or observable evidence

### Requirement: Trajectory lifecycle states are explicit
The system SHALL distinguish terminal states `COMPLETED`, `ABORTED`, and `FAILED` from resumable states `BLOCKED` and `HUMAN_ESCALATION`. `COMPLETED` SHALL mean that the configured objective and evidence gates were reached; `ABORTED` SHALL mean that an external interruption ended the run; `FAILED` SHALL mean that the run reached its stopping condition without satisfying the objective; `BLOCKED` SHALL mean that progress requires an unresolved dependency; and `HUMAN_ESCALATION` SHALL mean that human judgment or authorization is required. `BLOCKED` and `HUMAN_ESCALATION` SHALL NOT count as model failures until a subsequent resolved run reaches `FAILED`. Resumable states SHALL be persisted with their dependency and required input, SHALL retain the same trajectory identifier across resumptions, and SHALL record each resumption as a new appended entry. A resumable trajectory that is abandoned SHALL terminate as `ABORTED` with an abandonment reason rather than remaining open indefinitely.

#### Scenario: A trajectory reaches a terminal state
- **WHEN** a trajectory enters `COMPLETED`, `ABORTED`, or `FAILED`
- **THEN** the record SHALL include the terminal reason, terminal evidence, whether the state is eligible for evaluation, and whether resumption requires a new trajectory

#### Scenario: A trajectory requires external input
- **WHEN** progress is impossible without an unresolved dependency or human decision
- **THEN** the trajectory SHALL enter `BLOCKED` or `HUMAN_ESCALATION`, record the dependency and required input, and SHALL remain resumable without being counted as a failure

#### Scenario: Human input resolves an escalation
- **WHEN** a human supplies a decision, authorization, or correction for a `HUMAN_ESCALATION` state
- **THEN** the trajectory SHALL append a `human_input` response event with its authority, evidence, and decision, and SHALL transition to the next state or a terminal state

#### Scenario: A blocked trajectory is abandoned
- **WHEN** an operator or policy abandons a `BLOCKED` or `HUMAN_ESCALATION` trajectory without resolving it
- **THEN** the trajectory SHALL terminate as `ABORTED` with the abandonment reason and SHALL NOT be classified as `FAILED` or as model evidence

### Requirement: Append-only integrity is verifiable
Every persisted trajectory SHALL use versioned canonical serialization and a cryptographic content hash for each entry, a hash link to the preceding entry, and a versioned manifest containing the trajectory identifier, entry count, first and last entry hashes, hash algorithm, canonicalization version, and manifest hash. Canonical serialization SHALL use UTF-8 JSON with recursively sorted keys, no insignificant whitespace, normalized Unicode, and deterministic numeric canonicalization equivalent to RFC 8785 JSON Canonicalization Scheme: integers and finite numbers SHALL have one canonical representation, `-0` SHALL canonicalize as `0`, and NaN or infinite values SHALL be rejected. The fields `content_hash` and `prev_hash` SHALL be excluded when computing an entry's content hash. Verification SHALL recompute canonical bytes and hashes before any result derived from the trajectory is used.

#### Scenario: An entry is mutated or removed
- **WHEN** an entry is altered, reordered, truncated, or removed after persistence
- **THEN** hash-chain or manifest verification SHALL detect the inconsistency, mark the trajectory corrupted, invalidate dependent evaluation results, and preserve the corruption event as provenance

#### Scenario: An append is valid
- **WHEN** a new turn or annotation is appended with the expected predecessor hash and updated manifest
- **THEN** verification SHALL accept the new version while preserving all prior entries and manifest history

#### Scenario: Verification metadata is unavailable
- **WHEN** a trajectory lacks the required canonicalization, hash, or manifest metadata
- **THEN** the trajectory SHALL be treated as limited provenance and SHALL NOT support high-confidence correction, transfer, recovery, or promotion claims

### Requirement: Evidence custody and amendment lifecycle are explicit
Each trajectory and evaluation artifact SHALL record producer actor, classifier actor, custodian actor, and independence status (`independent`, `same_process`, or `unknown`) when applicable. Artifacts SHALL record observation, recording, evaluation, and amendment timestamps where distinct. A trajectory SHALL progress through custody states `OPEN`, `FROZEN`, `AMENDED`, `SUPERSEDED`, or `CORRUPTED`; after `FROZEN`, no original entry may be overwritten. An amendment SHALL append its reason, author, evidence, superseded version, and timestamp.

#### Scenario: A frozen trajectory is amended
- **WHEN** a post-evaluation correction or annotation is required
- **THEN** the original frozen record SHALL remain intact, and an amendment SHALL reference the original manifest and explain the changed interpretation

#### Scenario: The same process produces and classifies evidence
- **WHEN** the producer and classifier are the same process or their independence is unknown
- **THEN** the record SHALL expose that status and claims requiring independent evaluation SHALL remain provisional

#### Scenario: A record is superseded or corrupted
- **WHEN** a later valid interpretation supersedes an earlier one, or integrity verification fails
- **THEN** the record SHALL preserve the prior version, record the supersession or corruption event, and prevent silent substitution in reports

### Requirement: Memory retrieval is recorded per trajectory
Every trajectory in a condition that activates memory SHALL record the retrieval outcome: the number of retrieved items, the retrieved content hashes, the retrieved token count when available, or an explicit `retrieved: none`. A case whose retrieval is empty SHALL be marked `no_memory_retrieved` and SHALL NOT contribute to the `full_vs_criteria` or `full_vs_memory` contrasts, because an empty retrieval makes the memory condition equivalent to its comparison condition.

#### Scenario: A memory condition retrieves nothing
- **WHEN** a condition that activates memory retrieves no candidate for a case
- **THEN** the record SHALL state `retrieved: none`, the case SHALL be marked `no_memory_retrieved`, and it SHALL be excluded from the contrasts that would otherwise treat the condition as different

#### Scenario: Retrieval is partially empty
- **WHEN** retrieval returns fewer items than the configured expectation for a case
- **THEN** the record SHALL state the retrieved counts and hashes, and the report SHALL show retrieval coverage alongside the contrast result

### Requirement: Append-only records support ordered concurrent writers and crash recovery
The trajectory store SHALL define an ordering authority for concurrent appends, such as a single writer, serialized lock, or monotonic sequence allocator. Each append SHALL be atomic or journaled so a process crash cannot leave an ambiguous partial entry. Recovery SHALL detect incomplete appends, preserve the last valid manifest, and either discard the incomplete suffix or record it as an aborted write without rewriting valid history. A fork or competing append SHALL be recorded and SHALL NOT be silently merged.

#### Scenario: Two conditions append concurrently
- **WHEN** two workers attempt to append to the same trajectory or manifest concurrently
- **THEN** the ordering authority SHALL serialize or reject one append, and the record SHALL preserve the resulting order or conflict explicitly

#### Scenario: A writer crashes during append
- **WHEN** a process crashes during entry or manifest persistence
- **THEN** recovery SHALL retain the last valid chain prefix, classify the incomplete write as aborted or incomplete, and SHALL NOT treat the partial entry as evaluation evidence

### Requirement: Schema evolution preserves historical verification
Every artifact SHALL record its schema version. A newer reader SHALL support versioned adapters for older artifacts or emit a new migrated artifact that references the original hash chain and schema version; historical records SHALL never be rewritten in place. Migrated artifacts SHALL record migration tool identity, source schema version, target schema version, migration timestamp, and source artifact hash. Claims depending on an unmigratable artifact SHALL remain limited provenance.

#### Scenario: A v1 artifact is read by a v2 reader
- **WHEN** a v2 reader encounters a valid v1 artifact
- **THEN** it SHALL use a declared v1 adapter or produce a separately hashed v2 migration artifact while preserving the v1 record

#### Scenario: A migration changes semantic meaning
- **WHEN** a schema migration cannot preserve a field's semantic meaning
- **THEN** the field SHALL be marked unknown or non-comparable, and dependent claims SHALL be downgraded rather than silently remapped
## Implementation status (audited)

Verified contract-level implementations and focused tests are available for:

- Bounded trajectory state, per-turn structured records, append-only integrity,
  mutation detection, recovery confirmation, and non-minimal correction checks:
  `trajectory_runtime.py`, `trajectory_provenance.py`, and their tests.
- Comprehension versus correction separation, including evidence-linked
  correction requirements: `test_4_4_4_5.py`.
- Repeated prompting without a causal evidence or context change is not recovery;
  a new evidence transition is required: `test_4_4_4_5.py`.
- Challenge provenance and declared objectives: `p2_6.py` and `test_p2_6.py`.
- Transfer variants and equivalence review: `transfer_variants.py` and its tests.
- Memory conflicts, injection budgets, redaction/audit events, and stale-entry
  revalidation: `p2_7.py` and `test_p2_7.py`.
- Retrieval mode metadata, contamination tiers, calibration, and reliability
  budgets: `p2_5.py` and `test_p2_5.py`.
The following remain pending as full integrations: versioned memory candidate
lifecycle and promotion/rollback, regression manifests, retrieval metadata wired
into every trajectory, condition-content verification, crash recovery and
ordered journaled appends, schema migration adapters, and complete recovery /
transfer metrics. See `tasks.md` for the authoritative checklist.
