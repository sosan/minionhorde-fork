## ADDED Requirements

### Requirement: Layer boundaries are explicit
The system SHALL represent three distinct layers: Layer A for machine-enforced control, Layer B for normative criteria and dogmas, and Layer C for operational learning. Layer C SHALL NOT override, weaken, or authorize behavior prohibited by Layers A or B.

#### Scenario: Learning candidate conflicts with a safety control
- **WHEN** a Layer C candidate recommends disabling a permission denial, redaction rule, scope gate, or irreversible-action control
- **THEN** the system SHALL reject the recommendation and retain the Layer A/B control

#### Scenario: Layer metadata is reported
- **WHEN** an evaluation or trajectory is completed
- **THEN** the record SHALL identify the active Layer A control profile, Layer B criteria version, and Layer C memory/trajectory version

### Requirement: Machine controls remain authoritative
Layer A SHALL enforce or preserve tool permissions, secret redaction, audit logging, scope checks, phase gates, and separate confirmation for irreversible operations independently of model assertions.

#### Scenario: Model claims an operation is safe
- **WHEN** the model requests an operation covered by an existing machine control
- **THEN** the machine control SHALL evaluate the operation and SHALL NOT rely solely on the model's safety justification

#### Scenario: Tool output contains a protected value
- **WHEN** a tool response matches a configured secret pattern
- **THEN** the output SHALL be redacted before persistence or downstream evaluation and the event SHALL record only non-secret metadata

#### Scenario: A protected value would reach memory or a derived artifact
- **WHEN** content matching a configured secret pattern would be persisted into memory, a derived pattern, a summary, or any Layer C artifact
- **THEN** Layer A redaction SHALL apply before persistence, independently of whether the content appeared in tool output, a model response, or an episode, and the redaction event SHALL record only non-secret metadata

#### Scenario: Existing stored content is scanned
- **WHEN** stored trajectories, memory entries, or derived artifacts are scanned for protected values
- **THEN** a detected value SHALL be removed, the affected artifact SHALL be re-versioned, and the leak SHALL be reported as a security event rather than silently deleted

### Requirement: Criteria are versioned and traceable
Layer B SHALL identify the exact dogma and security-policy versions used for a decision, and SHALL distinguish normative rules from incidents, hypotheses, and examples.

#### Scenario: A decision cites a rule
- **WHEN** an evaluator records an applied criterion
- **THEN** the record SHALL contain the rule identifier and criteria version

#### Scenario: A candidate pattern is not yet normative
- **WHEN** a pattern has evidence but has not passed promotion gates
- **THEN** the system SHALL label it provisional and SHALL NOT present it as an active dogma

### Requirement: Layer transitions are bounded
The system SHALL define explicit budgets and stop conditions for any interaction that crosses from criteria application into learning or recovery.

#### Scenario: No progress occurs during calibration
- **WHEN** the configured number of turns is exhausted or consecutive turns produce no new evidence or decision change
- **THEN** the system SHALL stop the loop and report the reason

#### Scenario: Human judgment is required
- **WHEN** evidence is contradictory, the case is frontier-classified, or a requested action is irreversible
- **THEN** the system SHALL enter the `HUMAN_ESCALATION` state rather than silently deciding through Layer C

#### Scenario: An automation phase transition is evaluated
- **WHEN** the system evaluates advancing an automation phase, such as moving a category from human tutoring to automated evaluation
- **THEN** the transition SHALL require the configured minimum sample per category and SHALL express its thresholds with confidence intervals rather than point rates

### Requirement: Field classes define comparability and language policy
The system SHALL classify every field of a schema-validated record as a machine field or an operator-facing field. Machine fields — identifiers, enums, hashes, numbers, booleans, timestamps — SHALL be language-neutral tokens and SHALL be the only fields consumed by comparison or aggregation. Operator-facing fields — free-text reasons, human guidance, escalation and tutoring reports — SHALL be tagged as operator-facing, MAY use the operator's language, and SHALL NOT be consumed by machine comparison or aggregation. Model-facing text — evaluation cases, judge-facing prompts, and reformulations that enter the model context — SHALL be treated as a controlled confound: its language SHALL be pinned per artifact class, held constant across comparison conditions, and recorded in provenance.

#### Scenario: A machine field has an invalid type
- **WHEN** a field declared for comparison or aggregation contains free text instead of its declared enum, number, boolean, timestamp, identifier, or hash type
- **THEN** schema validation SHALL reject the record or mark it `schema-invalid`, exclude it from comparison and aggregation, and SHALL NOT silently demote the field to operator-facing metadata

#### Scenario: Free text is explicitly operator-facing
- **WHEN** a free-text reason, guidance, escalation note, or tutoring report is declared as operator-facing
- **THEN** the field MAY use the operator's language and SHALL remain excluded from machine comparison and aggregation

#### Scenario: Operator-facing fields differ in language
- **WHEN** two schema-validated records use different natural languages for their operator-facing fields
- **THEN** comparison SHALL rely only on machine fields, which remain comparable regardless of language, and the records SHALL NOT be marked non-comparable on language grounds alone

#### Scenario: Case language is a controlled confound
- **WHEN** the same case is evaluated across the comparison conditions
- **THEN** the case and prompt language SHALL be held constant and recorded in the provenance record, and a language change SHALL invalidate cross-pass comparability and require a new baseline

#### Scenario: Report language differs from case language
- **WHEN** the operator-facing or report language differs from the evaluation case language
- **THEN** the difference SHALL be recorded in provenance and SHALL NOT by itself affect the comparability of machine fields

### Requirement: Layer C may propose, never apply, Layer B amendments
Layer C SHALL NOT modify Layer A or Layer B. When evaluation evidence contradicts a Layer B criterion, is inconsistent with another criterion, or shows a precedence error, Layer C MAY propose a structured amendment for human review. A proposal SHALL include the current criterion, the contradicting evidence references, a proposed text or precedence change, and the affected precedences. The proposal SHALL NOT take effect without human approval, and an approved amendment SHALL require re-running the evaluation suite to detect regression in other criteria.

#### Scenario: Evidence contradicts a Layer B criterion
- **WHEN** a provisional or stronger claim exposes a criterion contradiction with resolvable evidence
- **THEN** the system SHALL emit a structured amendment proposal for human review and SHALL NOT apply it

#### Scenario: A proposed amendment changes precedence
- **WHEN** a proposal would change rule precedence rather than rule text
- **THEN** the proposal SHALL mark the precedence change explicitly and SHALL NOT take effect without separate human approval

#### Scenario: An amendment is applied without regression
- **WHEN** a Layer B amendment is applied without re-running the evaluation suite
- **THEN** the amendment SHALL be marked unverified and SHALL NOT be treated as a stable criterion change
