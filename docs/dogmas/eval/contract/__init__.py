"""Modern evaluation contract: canonical serialization, hash integrity, schemas.

Foundation for the `develop-agent-layers` change. Kept additive: the legacy
`docs/dogmas/eval/results_schema.json` remains a compatibility contract.
"""

from .canonical import (
    CANONICAL_VERSION,
    HASH_ALGORITHM,
    canonical_bytes,
    canonical_json,
    content_hash,
    digest,
    sha256_hex,
)

__all__ = [
    "CANONICAL_VERSION",
    "HASH_ALGORITHM",
    "canonical_bytes",
    "canonical_json",
    "content_hash",
    "digest",
    "sha256_hex",
]
