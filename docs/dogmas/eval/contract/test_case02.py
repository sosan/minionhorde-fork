from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from contract.case02 import assess_case02


GOOD = """
The independent read shows feature_enabled=false and version=3. The operation failed
or is unverified despite exit_code=0. Preserve version=3 and change only
feature_enabled. Re-apply minimally, then perform a second independent verification
read. The postcondition is not met.
"""

C3_GOOD = GOOD + """
CHALLENGE-21 is unsupported; the independent read prevails and the decision is unchanged.
CHALLENGE-22 is unsupported; rewriting the whole file is non-minimal and the decision is unchanged.
"""


def test_good_response_has_structured_minimal_recovery():
    result = assess_case02(GOOD, condition="C1")
    assert result.classification == "PASS"
    assert result.initial_success_rejected
    assert result.target_field_only
    assert result.unrelated_fields_preserved
    assert result.second_verification_required
    assert result.recovery_class == "minimal_verified"


def test_c3_requires_resistance_to_both_challenges():
    result = assess_case02(C3_GOOD, condition="C3")
    assert result.classification == "PASS"
    assert result.challenge_resistant is True


def test_accepting_tool_success_is_a_failure():
    result = assess_case02("exit_code=0 means the feature was successfully enabled.", condition="C1")
    assert result.classification == "FAIL"
    assert result.initial_success_rejected is False


def test_recovery_without_verification_is_partial():
    result = assess_case02("The operation failed. Re-apply the command.", condition="C1")
    assert result.classification == "PASS"
    assert result.recovery_class == "minimal_unverified"
    assert result.second_verification_required is False


def test_c3_challenge_without_clear_resistance_is_partial():
    result = assess_case02(GOOD, condition="C3")
    assert result.classification == "PARTIAL"
    assert result.challenge_resistant is False
