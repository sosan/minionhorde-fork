"""Transfer-variant generation and equivalence-review contracts.

Variants are generated deterministically from a source case. Generation does not
claim semantic equivalence: every variant records the decision principle and must
receive an equivalence review before its result can count as transfer evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import hashlib
import re
from typing import Callable, Iterable, Mapping


class VariantClass(StrEnum):
    DIRECT = "direct"
    REFORMULATED = "reformulated"
    CROSS_DOMAIN = "cross_domain"
    ADVERSARIAL = "adversarial"
    DOGMA_VOCABULARY_FREE = "dogma_vocabulary_free"


class ReviewStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class EquivalenceReview:
    """Review that a variant measures the same decision principle."""

    reviewer_id: str
    authority: str
    status: ReviewStatus
    decision_principle: str
    rationale_hash: str
    human_labeled_subset_validated: bool = False

    def __post_init__(self) -> None:
        if not self.reviewer_id or not self.authority:
            raise ValueError("reviewer_id and authority are required")
        if not self.decision_principle:
            raise ValueError("decision_principle is required")
        if len(self.rationale_hash) != 64:
            raise ValueError("rationale_hash must be a SHA-256 hash")
        if self.status == ReviewStatus.APPROVED and self.authority == "human_labeled_subset" and not self.human_labeled_subset_validated:
            raise ValueError("human-labeled-subset review must be validated")

    def to_dict(self) -> dict[str, object]:
        return {
            "reviewer_id": self.reviewer_id,
            "authority": self.authority,
            "status": self.status.value,
            "decision_principle": self.decision_principle,
            "rationale_hash": self.rationale_hash,
            "human_labeled_subset_validated": self.human_labeled_subset_validated,
        }


@dataclass
class TransferVariant:
    variant_id: str
    source_case_id: str
    source_case_hash: str
    variant_class: VariantClass
    target_domain: str
    source_domain: str
    decision_principle: str
    prompt: str
    prompt_hash: str
    mutation_distance: int
    equivalence_review: EquivalenceReview | None = None
    supporting_memory_domains: tuple[str, ...] = ()
    metadata: dict[str, object] = field(default_factory=dict)

    @property
    def review_status(self) -> ReviewStatus:
        if self.equivalence_review is None:
            return ReviewStatus.PENDING
        return self.equivalence_review.status

    @property
    def transfer_eligible(self) -> bool:
        """Whether this variant may contribute to a transfer claim."""
        if self.review_status != ReviewStatus.APPROVED:
            return False
        if self.variant_class == VariantClass.CROSS_DOMAIN and self.target_domain in self.supporting_memory_domains:
            return False
        return True

    def attach_review(self, review: EquivalenceReview) -> None:
        if review.decision_principle != self.decision_principle:
            raise ValueError("equivalence review principle does not match variant")
        self.equivalence_review = review

    def to_dict(self) -> dict[str, object]:
        return {
            "variant_id": self.variant_id,
            "source_case_id": self.source_case_id,
            "source_case_hash": self.source_case_hash,
            "variant_class": self.variant_class.value,
            "source_domain": self.source_domain,
            "target_domain": self.target_domain,
            "decision_principle": self.decision_principle,
            "prompt": self.prompt,
            "prompt_hash": self.prompt_hash,
            "mutation_distance": self.mutation_distance,
            "equivalence_review": self.equivalence_review.to_dict() if self.equivalence_review else None,
            "review_status": self.review_status.value,
            "transfer_eligible": self.transfer_eligible,
            "supporting_memory_domains": list(self.supporting_memory_domains),
            "metadata": dict(self.metadata),
        }


def _replace_terms(text: str, replacements: Mapping[str, str]) -> str:
    result = text
    for old, new in replacements.items():
        result = re.sub(rf"\b{re.escape(old)}\b", new, result, flags=re.IGNORECASE)
    return result


def _make_variant(
    source_case_id: str,
    source_prompt: str,
    source_domain: str,
    variant_class: VariantClass,
    target_domain: str,
    decision_principle: str,
    prompt: str,
    supporting_memory_domains: Iterable[str],
    metadata: Mapping[str, object] | None = None,
) -> TransferVariant:
    source_hash = content_hash(source_prompt)
    variant_id = f"{source_case_id}:{variant_class.value}:{content_hash(prompt)[:12]}"
    return TransferVariant(
        variant_id=variant_id,
        source_case_id=source_case_id,
        source_case_hash=source_hash,
        variant_class=variant_class,
        target_domain=target_domain,
        source_domain=source_domain,
        decision_principle=decision_principle,
        prompt=prompt,
        prompt_hash=content_hash(prompt),
        mutation_distance=sum(a != b for a, b in zip(source_prompt, prompt)) + abs(len(source_prompt) - len(prompt)),
        supporting_memory_domains=tuple(supporting_memory_domains),
        metadata=dict(metadata or {}),
    )


def generate_transfer_variants(
    *,
    source_case_id: str,
    prompt: str,
    source_domain: str,
    decision_principle: str,
    target_domain: str | None = None,
    domain_replacements: Mapping[str, str] | None = None,
    dogma_vocabulary: Mapping[str, str] | None = None,
    reformulator: Callable[[str], str] | None = None,
    supporting_memory_domains: Iterable[str] = (),
) -> list[TransferVariant]:
    """Generate the five required variant classes for one source case.

    Callers may provide domain-specific replacements or a reviewed reformulator;
    otherwise conservative deterministic transformations are used. The generated
    records remain pending until an equivalence review is attached.
    """
    target_domain = target_domain or source_domain
    domain_replacements = domain_replacements or {}
    dogma_vocabulary = dogma_vocabulary or {}
    reformulated = reformulator(prompt) if reformulator else re.sub(r"\s+", " ", prompt).strip()
    cross_domain = _replace_terms(prompt, domain_replacements) if domain_replacements else prompt
    adversarial = (
        prompt.rstrip() + "\n\nConsider the tempting but unsupported claim in the scenario; reject it unless the stated evidence verifies it."
    )
    dogma_free = _replace_terms(prompt, dogma_vocabulary) if dogma_vocabulary else prompt
    return [
        _make_variant(source_case_id, prompt, source_domain, VariantClass.DIRECT, source_domain, decision_principle, prompt, supporting_memory_domains, {"mutation": "none"}),
        _make_variant(source_case_id, prompt, source_domain, VariantClass.REFORMULATED, source_domain, decision_principle, reformulated, supporting_memory_domains, {"mutation": "surface_rewording"}),
        _make_variant(source_case_id, prompt, source_domain, VariantClass.CROSS_DOMAIN, target_domain, decision_principle, cross_domain, supporting_memory_domains, {"mutation": "domain_mapping"}),
        _make_variant(source_case_id, prompt, source_domain, VariantClass.ADVERSARIAL, source_domain, decision_principle, adversarial, supporting_memory_domains, {"mutation": "unsupported_distractor"}),
        _make_variant(source_case_id, prompt, source_domain, VariantClass.DOGMA_VOCABULARY_FREE, source_domain, decision_principle, dogma_free, supporting_memory_domains, {"mutation": "vocabulary_substitution"}),
    ]


def validate_variant_set(variants: Iterable[TransferVariant], *, minimum_per_class: int = 1) -> dict[str, object]:
    """Report coverage and pending equivalence reviews without overclaiming."""
    variants = list(variants)
    counts = {variant_class.value: 0 for variant_class in VariantClass}
    for variant in variants:
        counts[variant.variant_class.value] += 1
    missing = [name for name, count in counts.items() if count < minimum_per_class]
    pending = [variant.variant_id for variant in variants if variant.review_status != ReviewStatus.APPROVED]
    return {
        "variant_count": len(variants),
        "counts": counts,
        "missing_classes": missing,
        "pending_reviews": pending,
        "status": "ready" if not missing and not pending else "pending",
    }
