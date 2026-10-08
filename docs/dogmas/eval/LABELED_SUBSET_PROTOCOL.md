# Human-Labeled Subset Protocol (operator-bound, task 10.1)

## Status

The agreement/equivalence/contamination-calibration mechanisms are
implemented in `contract/p2_5.py` — `HumanLabeledSubset`,
`measure_judge_agreement`, `cohen_kappa`, `detect_contamination`. The
labeled dataset itself is an operator responsibility — it does not exist
in `fixtures/`. This document records the operator-bound protocol: who
labels, which cases, how the subset is selected, what size is the
minimum, and which contract functions the operator must use to validate
and consume it.

## Scope and inputs

The subset feeds `contract.p2_5.measure_judge_agreement(judge_labels,
human_labels, *, threshold=0.8, min_subset_size=3, statistic="cohen_kappa")`
which returns a `KappaAgreement` with `validated=True` once `kappa >=
threshold` over at least `min_subset_size` items. It is the single input
the operator is expected to provide, and the only one whose absence
blocks judge calibration.

## Selection criteria (operator-approved, mandatory)

The subset MUST be:

1. **Pre-declared** — every `case_id` in the subset is fixed before any judge
   output is observed. No case may be added to the subset after its judge
   labels are known.
2. **Balanced across conditions** — the subset includes at least one
   `case_id` from each of the four conditions (C0, C1, C2, C3) for at least
   one model so the agreement number is not condition-biased.
3. **Balanced across categories** — the subset spans at least two of the
   measurement dimensions (comprehension, correction, transfer, regression)
   so the agreement number is not category-biased.
4. **Non-contaminated** — every `case_id` MUST be drawn from the
   configured, non-contaminated case set. The operator validates each
   candidate `case_id` against `contract.p2_5.detect_contamination`
   (case-hash equality / declared semantic similarity). For memory
   conditions, also `contract/memory_candidates.detect_support_contamination`
   applies the same case-hash rule plus a similarity mode; a subset that
   crosses contaminated support is invalid.
5. **Representative of edge labels** — at least one pass and at least one
   fail per dimension in the subset, so the kappa is not dominated by a
   single label.

> Note on criterion 5: dimensions classified as `ceiling` by
> `contract.p2_3.classify_discrimination` admit a single outcome by
> construction. The "edge labels" rule is exempt for ceiling-only
> dimensions, on the condition that the operator records the rationale in
> `selection_criteria`.

## Minimum size

The `min_subset_size` parameter (default 3 in the contract) is the
**statistical** floor. For claim scopes beyond `case`, the subset MUST be
large enough that the 95% confidence interval of the observed agreement
falls entirely above the threshold. As a working rule:

- `candidate`-scope claims: subset >= 12 cases per condition × 4 conditions
  = 48 labels.
- `model`-scope claims: subset >= 24 cases per condition × 4 conditions
  = 96 labels.
- Other scopes: use the `candidate` floor unless the operator documents
  otherwise.

The numbers 12 / 24 are operator-defined. They are not derived from a
power calculation in this revision. They MUST be revisited once a
documented sample-size calculation is added to the contract, and any
change to the rule MUST be recorded in the audit trail.

### Claim-scope linkage

The sizes above are calibrated against the claim scopes that
`contract.profiles.restrict_claim(profile, scope)` (`contract/profiles.py:76`)
emits. The link is:

- `dimension` / `case` scope — `min_subset_size = 3` is sufficient.
- `candidate` scope — the 48-label rule.
- `category` / `model` scope — the 96-label rule.

When `restrict_claim` returns `block` for a scope under the active
profile (`vertical_slice@v1` allows only `candidate` and `dimension`,
preliminary only; `full_suite@v1` allows every scope), a subset that
meets the floor for that scope is necessary; it is not sufficient on its
own.

## Labeller policy (single vs panel)

The protocol assumes a single labeller unless the operator states
otherwise in `selection_criteria`. The valid configurations are:

- **Single labeller** — one human, one label per case. The detector's
  kappa is the only agreement number reported.
- **Panel** — N humans (N >= 2), each labels independently. The
  operator reports:
  - Per-pair Cohen's kappa between humans (inter-labeller agreement).
  - Detector kappa against the panel's majority label.
  - Detector kappa against each individual labeller (sensitivity check).

Panel results whose inter-labeller kappa is below 0.6 are invalid; the
operator MUST collect new labels for the disputed cases before the subset
is consumed by `measure_judge_agreement`.

The labeller identity (initials or pseudonym) is recorded in
`selection_criteria` but is not exposed in the public `HumanLabeledSubset`
record — the dataclass does not carry that field. The labeller-identity
mapping is kept in the operator's private audit trail, never in the
repo.

## Detector identity and version

`HumanLabeledSubset` records `detector_identity` and `detector_version`.
These are mandatory so that agreement numbers can be attributed to a
specific judge, not a black box. The operator selects the judge (model,
build, prompt) once and freezes it for the duration of the subset's
measurement window — i.e. from the moment the first detector output is
recorded against the subset until the last label is consumed by
`measure_judge_agreement`. Any change to the judge inside that window
invalidates the subset.

## Schema version pin

The protocol is pinned to `HumanLabeledSubset` as defined in
`contract/p2_5.py` (v1 — frozen dataclass fields `subset_id`, `case_ids`,
`labels`, `selection_criteria`, `detector_identity`, `detector_version`).
There is no JSON Schema file yet; the closest versioned sibling is
`docs/dogmas/eval/schemas/v1/memory_candidate.schema.json` (covers
`MemoryCandidateRecord`, not the subset). The dataclass with `to_dict()`
is canonical until a JSON Schema is added under
`docs/dogmas/eval/schemas/v1/`, at which point the protocol migrates
through `contract/schema_versions.py`. A subset whose schema_version is
older than the current contract is loaded only through the versioned
reader and never merged with newer subsets.

## Validation step (operator action)

Before persisting the JSON, the operator MUST run two validations:

1. Instantiate the dataclass locally so `__post_init__` runs the field
   checks:

```python
from contract.p2_5 import HumanLabeledSubset
subset = HumanLabeledSubset(
    subset_id="<id>",
    case_ids=tuple(<case_ids>),
    labels=dict(<labels>),
    selection_criteria="<copy of the criteria above>",
    detector_identity="<judge model>",
    detector_version="<build hash>",
)
```

2. Run `contract.labeled_subset.validate_subset(...)` to enforce
   criteria 1–5 (contamination, balance, edge labels, ceiling exemption,
   dual-role prefix, portability, panel kappa, size-scaled scope). The
   function returns a `Verdict` whose `issues` carry codes and severities.
   Any `error` issue blocks persistence; `warning` issues are advisory.

`__post_init__` enforces only: `subset_id` non-empty, `case_ids`
non-empty, `selection_criteria` non-empty, every `case_id` has a label.
It does NOT enforce criteria 1–5 — those are now enforced by
`validate_subset` (contamination, balance, edge labels, dual-role
prefix, portability, panel kappa, size-scaled scope). Criterion 1
(temporal pre-declaration) is the single item the validator cannot
close on its own: it requires a stateful comparison between the subset
declaration timestamp and the first judge output, which the pure
validation layer does not carry. The operator records the pre-declaration
timestamp in `selection_criteria`; temporal pre-declaration enforcement
is deferred (see Non-goals in `docs/specs/labeled-subset-protocol.md`).

`validate_subset` is covered by `contract/test_labeled_subset.py` (15
focused tests). The protocol recommends running the dataclass tests and
the validator tests locally before persisting.

## Output contract

A single JSON object matching `HumanLabeledSubset.to_dict()`:

```
{
  "subset_id": "<operator-assigned stable id>",
  "case_ids": ["<case_id>", ...],
  "labels": {"<case_id>": "PASS|FAIL|PARTIAL", ...},
  "selection_criteria": "<copy of the approved criteria above, possibly with additions>",
  "detector_identity": "<judge model>",
  "detector_version": "<build hash>"
}
```

Saved under `docs/dogmas/eval/fixtures/human-labeled-subset/<subset_id>.json`.

## Dual validation role

The subset is not only the judge-calibration input. It is also an
**authority** for equivalence reviews of transfer variants:
`contract/transfer_variants.py` (`EquivalenceReview` with
`authority="human_labeled_subset"`) requires
`human_labeled_subset_validated=True` on an APPROVED review, or the
dataclass constructor raises. That means a subset used to validate a
variant must satisfy stricter constraints than a judge-only subset:

- It MUST be scoped to the **same `decision_principle`** as the variants
  it validates — the human labels are a check on the *principle*, not on
  the surface wording.
- It MUST be scoped to the **same `variant_class`** family (direct,
  reformulated, cross-domain, adversarial, dogma-vocabulary-free) — a
  subset that validates a direct variant does not validate a
  cross-domain one.
- A subset used for review validation is still subject to every criterion
  in "Selection criteria" (pre-declared, balanced, non-contaminated,
  edge labels, ceiling exemption). The reviewer identity must match the
  `reviewer_id` recorded in the `EquivalenceReview`.

The `human-labeled-subset/` storage directory MUST NOT mix judge-only
subsets with review-authority subsets. Prefix review-authority subsets
with `review-` in `subset_id` (e.g. `review-direct-variants-001`) so the
consumer can tell which authority a subset carries.

## Portability

A subset is reusable across conditions (C0/C1/C2/C3) **only when**:
- `case_id` + `case_version` are unchanged, and
- detector `identity` + `version` are unchanged.

If the detection rubric, the detector build, or the case content changes
across conditions, the subset is invalidated for the later condition.
A single stored subset MAY carry labels for multiple conditions — that
is still one logical subset. Reuse beyond the condition set is blocked;
each subset declares the conditions it covers and the consumer verifies
that against the manifest before using it.

## Failure modes / audit trail

Failure modes of the subset, each with an operator action:

| Failure | Detection | Operator action |
|---|---|---|
| Detector changed mid-window | `detector_version` differs from the frozen one | Re-state subset, re-run agreement; mark old run `superseded` |
| Case content/expected answer changed | `case_version` differs | Drop that case from the subset, or re-state it; do not silently relabel |
| Subset used across a version boundary | `schema_version` older than current | Load via versioned reader only; mark `legacy`; never merge |
| Panel disagreement unresolved | inter-labeller kappa < 0.6 | Re-label disputed cases; subset invalid until resolved |
| Subset orphaned by detector retirement | no active measurement references it | Archive, mark `deprecated`; exclude from automatic injection |

Every call to `measure_judge_agreement` writes an audit entry: date,
`subset_id`, `detector_identity`/`version`, `kappa`, `n`, `threshold`,
`min_subset_size`. Entries are append-only (E4); they never overwrite
prior measurements. The audit entry is the record that the operator
consulted the subset and with what result — the same record that
`implementation-status.md` calls "the labeled dataset is operator
responsibility".

## Re-validation

Every agreement measurement is point-in-time. When the judge model, judge
build, detection rubric, or any subset case's expected answer changes,
the subset is re-stated from `no-old-read` data, and the agreement
measurement is re-run. Old results remain in the audit trail; they are
not deleted, but they are excluded from automatic injection once the
detector changes (memory validity, E12).

## What this protocol does NOT do

- It does not invent labels. Until a human labels arrive, no
  `human-labeled-subset/*.json` exists in the repo, and
  `measure_judge_agreement` is not invoked.
- It does not auto-promote any detector. Every detector remains
  provisional until its validated kappa is recorded against a fresh
  subset.
- It does not take a position on **whether prompts are private**. The
  response side is governed by `contract/anonymizer.py` (which strips
  secret patterns, prompts, responses, and internal paths), but human
  labels on non-secret fields may still expose internal vocabulary. The
  operator decides whether to expose them and, if so, applies the same
  redaction policy to the labels as to the responses.
- It does not enforce temporal pre-declaration (criterion 1). The
  validator covers every other criterion; pre-declaration requires
  stateful runtime data the pure validation layer does not carry, so it
  stays an operator responsibility (deferred in the spec's Non-goals).