"""Validation core for the operator-bound human-labeled subset protocol.

This module enforces criteria 1–5 of
``docs/dogmas/eval/LABELED_SUBSET_PROTOCOL.md`` plus the portability,
panel, dual-role, and size rules. The dataclass
``HumanLabeledSubset`` already enforces field-level checks in
``__post_init__``; this module goes further and emits structured issues
with codes and severities.

Scope: descriptive only — every check is a pure function over the
subset plus caller-supplied context (case hashes, current detector
version, current case versions, etc.). No mutation of operator data.

Example:
    from contract.labeled_subset import validate_subset

    verdict = validate_subset(
        subset,
        case_hash_for={"case-A": "hash-A"},
        episode_hashes={"hash-A"},
        condition_for={"case-A": "C0"},
        category_for={"case-A": "comprehension"},
        expected_conditions=("C0", "C1", "C2", "C3"),
        scope="candidate",
        profile=full_suite_profile(),
    )
    if not verdict.valid:
        for issue in verdict.issues:
            print(issue.severity, issue.code, issue.message)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

from contract.p2_3 import Discrimination, classify_discrimination
from contract.p2_5 import ContaminationLevel, HumanLabeledSubset, cohen_kappa, detect_contamination
from contract.profiles import EvaluationProfile, restrict_claim
from contract.schema_store import SchemaStore, SchemaValidationError

__all__ = [
    "Issue",
    "Verdict",
    "validate_subset",
    "validate_against_schema",
    "minimum_size_for_scope",
]

_SCOPE_MIN_SIZES: Mapping[str, int] = {
    "dimension": 3,
    "case": 3,
    "candidate": 48,
    "category": 96,
    "model": 96,
    "global": 96,
}

_PANEL_KAPPA_THRESHOLD = 0.6


@dataclass(frozen=True)
class Issue:
    """A single validation finding."""

    code: str
    severity: str  # "error" or "warning"
    message: str


@dataclass(frozen=True)
class Verdict:
    """The combined result of a subset validation."""

    valid: bool
    issues: list[Issue] = field(default_factory=list)


def minimum_size_for_scope(scope: str) -> int:
    """Return the minimum subset size required for ``scope``."""
    return _SCOPE_MIN_SIZES.get(scope, _SCOPE_MIN_SIZES["candidate"])


def _check_contamination(
    subset: HumanLabeledSubset,
    case_hash_for: Mapping[str, str] | None,
    episode_hashes: Iterable[str] | None,
) -> list[Issue]:
    if not case_hash_for or not episode_hashes:
        return []
    eps = set(episode_hashes)
    issues: list[Issue] = []
    for case_id, case_hash in case_hash_for.items():
        result = detect_contamination(
            case_id=case_id,
            case_hash=case_hash,
            episode_hashes=eps,
            detector_identity=subset.detector_identity,
            detector_version=subset.detector_version,
        )
        if result.level == ContaminationLevel.HARD:
            issues.append(
                Issue(
                    code="contamination_hard",
                    severity="error",
                    message=f"case {case_id} is hard-contaminated ({result.reason})",
                )
            )
        elif result.level == ContaminationLevel.FLAGGED:
            issues.append(
                Issue(
                    code="contamination_flagged",
                    severity="warning",
                    message=f"case {case_id} flagged as contaminated ({result.reason})",
                )
            )
    return issues


def _check_condition_balance(
    condition_for: Mapping[str, str] | None,
    expected_conditions: Sequence[str],
) -> list[Issue]:
    if condition_for is None:
        return [Issue("condition_balance_missing", "error", "no condition_for provided")]
    present = set(condition_for.values())
    missing = [c for c in expected_conditions if c not in present]
    if missing:
        return [
            Issue(
                "condition_balance_missing",
                "error",
                f"missing conditions: {missing}",
            )
        ]
    return []


def _check_category_balance(category_for: Mapping[str, str] | None) -> list[Issue]:
    if category_for is None:
        return [Issue("category_balance_insufficient", "error", "no category_for provided")]
    distinct = set(category_for.values())
    if len(distinct) < 2:
        return [
            Issue(
                "category_balance_insufficient",
                "error",
                f"only {len(distinct)} distinct category; minimum is 2",
            )
        ]
    return []


def _check_edge_labels(
    subset: HumanLabeledSubset,
    category_for: Mapping[str, str] | None,
    discrimination_for: Mapping[str, Sequence[str]] | None,
    label_for: Mapping[str, str] | None,
) -> list[Issue]:
    if category_for is None or discrimination_for is None:
        return []
    labels = label_for if label_for is not None else dict(subset.labels)
    issues: list[Issue] = []
    by_category: dict[str, list[str]] = {}
    for case_id, category in category_for.items():
        by_category.setdefault(category, []).append(labels.get(case_id, ""))
    for category, outcomes in discrimination_for.items():
        bools = [True if o.upper() == "PASS" else False for o in outcomes]
        discrimination = classify_discrimination(category, bools).discrimination
        if discrimination == Discrimination.CEILING:
            continue  # ceiling exemption
        cat_labels = by_category.get(category, [])
        if cat_labels and not any(l.upper() == "PASS" for l in cat_labels):
            issues.append(
                Issue(
                    code="edge_labels_missing_pass",
                    severity="error",
                    message=f"category {category} has no PASS label",
                )
            )
        if cat_labels and not any(l.upper() == "FAIL" for l in cat_labels):
            issues.append(
                Issue(
                    code="edge_labels_missing_fail",
                    severity="error",
                    message=f"category {category} has no FAIL label",
                )
            )
    return issues


def _check_min_size(
    subset: HumanLabeledSubset,
    scope: str | None,
    profile: EvaluationProfile | None,
) -> list[Issue]:
    if scope is None or profile is None:
        return []
    rv = restrict_claim(profile, scope)
    if rv["verdict"] == "block":
        return [
            Issue(
                code="scope_blocked_by_profile",
                severity="error",
                message=(
                    f"scope {scope} blocked by profile {profile.profile_id}: {rv['reason']}"
                ),
            )
        ]
    min_size = minimum_size_for_scope(scope)
    if len(subset.case_ids) < min_size:
        return [
            Issue(
                code="min_size_scope_below_min",
                severity="error",
                message=(
                    f"subset has {len(subset.case_ids)} cases; minimum for "
                    f"scope {scope} is {min_size}"
                ),
            )
        ]
    return []


def _check_dual_role(
    subset: HumanLabeledSubset,
    dual_role: bool,
    decision_principle: str,
    variant_class: str,
    expected_decision_principle: str,
) -> list[Issue]:
    if not dual_role:
        return []
    issues: list[Issue] = []
    if not subset.subset_id.startswith("review-"):
        issues.append(
            Issue(
                code="dual_role_missing_review_prefix",
                severity="error",
                message=f"subset_id {subset.subset_id!r} must start with 'review-'",
            )
        )
    if not decision_principle:
        issues.append(
            Issue(
                code="dual_role_missing_decision_principle",
                severity="error",
                message="dual-role subsets must declare a decision_principle",
            )
        )
    if not variant_class:
        issues.append(
            Issue(
                code="dual_role_missing_variant_class",
                severity="error",
                message="dual-role subsets must declare a variant_class",
            )
        )
    if expected_decision_principle and decision_principle and decision_principle != expected_decision_principle:
        issues.append(
            Issue(
                code="dual_role_decision_principle_mismatch",
                severity="error",
                message=(
                    f"subset decision_principle {decision_principle!r} does not "
                    f"match expected {expected_decision_principle!r}"
                ),
            )
        )
    return issues


def _check_portability(
    subset: HumanLabeledSubset,
    current_detector_version: str | None,
    current_case_versions: Mapping[str, str] | None,
    subset_case_versions: Mapping[str, str] | None,
) -> list[Issue]:
    issues: list[Issue] = []
    if (
        current_detector_version is not None
        and current_detector_version != subset.detector_version
    ):
        issues.append(
            Issue(
                code="portability_detector_version_changed",
                severity="error",
                message=(
                    f"subset detector_version={subset.detector_version!r}; "
                    f"current is {current_detector_version!r}"
                ),
            )
        )
    if current_case_versions is not None and subset_case_versions is not None:
        for case_id in subset.case_ids:
            cur = current_case_versions.get(case_id)
            sub_v = subset_case_versions.get(case_id)
            if cur is not None and sub_v is not None and cur != sub_v:
                issues.append(
                    Issue(
                        code="portability_case_version_changed",
                        severity="error",
                        message=(
                            f"case {case_id}: subset has version {sub_v!r}, "
                            f"current is {cur!r}"
                        ),
                    )
                )
                break
    return issues


def _check_panel(
    panel_labels: Mapping[str, Sequence[str]] | None,
) -> list[Issue]:
    if panel_labels is None:
        return []
    humans = list(panel_labels.keys())
    if len(humans) < 2:
        return []
    issues: list[Issue] = []
    for i in range(len(humans)):
        for j in range(i + 1, len(humans)):
            kappa = cohen_kappa(panel_labels[humans[i]], panel_labels[humans[j]])
            if kappa < _PANEL_KAPPA_THRESHOLD:
                issues.append(
                    Issue(
                        code="panel_kappa_below_threshold",
                        severity="error",
                        message=(
                            f"inter-labeller kappa {kappa:.3f} between "
                            f"{humans[i]!r} and {humans[j]!r} is below "
                            f"{_PANEL_KAPPA_THRESHOLD}"
                        ),
                    )
                )
    return issues


def validate_subset(
    subset: HumanLabeledSubset,
    *,
    case_hash_for: Mapping[str, str] | None = None,
    episode_hashes: Iterable[str] | None = None,
    condition_for: Mapping[str, str] | None = None,
    category_for: Mapping[str, str] | None = None,
    expected_conditions: Sequence[str] = ("C0", "C1", "C2", "C3"),
    label_for: Mapping[str, str] | None = None,
    discrimination_for: Mapping[str, Sequence[str]] | None = None,
    scope: str | None = None,
    profile: EvaluationProfile | None = None,
    dual_role: bool = False,
    decision_principle: str = "",
    variant_class: str = "",
    expected_decision_principle: str = "",
    current_detector_version: str | None = None,
    current_case_versions: Mapping[str, str] | None = None,
    subset_case_versions: Mapping[str, str] | None = None,
    panel_labels: Mapping[str, Sequence[str]] | None = None,
) -> Verdict:
    """Run the full subset validation battery and return a structured verdict."""
    issues: list[Issue] = []
    issues += _check_contamination(subset, case_hash_for, episode_hashes)
    issues += _check_condition_balance(condition_for, expected_conditions)
    issues += _check_category_balance(category_for)
    issues += _check_edge_labels(
        subset, category_for, discrimination_for, label_for
    )
    issues += _check_min_size(subset, scope, profile)
    issues += _check_dual_role(
        subset,
        dual_role,
        decision_principle,
        variant_class,
        expected_decision_principle,
    )
    issues += _check_portability(
        subset,
        current_detector_version,
        current_case_versions,
        subset_case_versions,
    )
    issues += _check_panel(panel_labels)
    has_errors = any(i.severity == "error" for i in issues)
    return Verdict(valid=not has_errors, issues=issues)


def validate_against_schema(
    document: HumanLabeledSubset | dict[str, Any],
    *,
    store: SchemaStore | None = None,
) -> Verdict:
    """Validate a subset (dataclass or its ``to_dict()``) against the
    versioned JSON Schema ``schemas/v1/human_labeled_subset.schema.json``.

    Example:
        verdict = validate_against_schema(subset)
        if not verdict.valid:
            print([i.code for i in verdict.issues])
    """
    doc = document.to_dict() if isinstance(document, HumanLabeledSubset) else dict(document)
    store = store or SchemaStore()
    try:
        store.validate("human_labeled_subset", doc)
    except SchemaValidationError as exc:
        issues = [
            Issue(code="schema_invalid", severity="error", message=str(e.message))
            for e in exc.errors
        ]
        return Verdict(valid=False, issues=issues)
    return Verdict(valid=True, issues=[])