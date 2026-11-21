"""Tests for the exact binomial interval used by the analysis script.

The previous implementation used a Wald (normal) interval for n >= 10,
which is wrong at the boundaries (it can exceed [0, 1]) and understates
uncertainty for small samples.
"""

from __future__ import annotations

import pytest

from statistical_analysis import compute_binomial_ci


@pytest.mark.parametrize(
    ("successes", "n", "expected"),
    [
        (0, 10, (0.0, 0.3085)),
        (5, 10, (0.1871, 0.8129)),
        (10, 10, (0.6915, 1.0)),
        (3, 3, (0.2924, 1.0)),
        (50, 100, (0.3983, 0.6017)),
        (1, 3, (0.0084, 0.9057)),
    ],
)
def test_clopper_pearson_matches_reference_values(successes, n, expected):
    lower, upper = compute_binomial_ci(successes, n)
    assert lower == pytest.approx(expected[0], abs=1e-4)
    assert upper == pytest.approx(expected[1], abs=1e-4)


def test_interval_stays_within_unit_range():
    for successes in range(11):
        lower, upper = compute_binomial_ci(successes, 10)
        assert 0.0 <= lower <= upper <= 1.0


def test_empty_sample_returns_zero_interval():
    assert compute_binomial_ci(0, 0) == (0.0, 0.0)


def test_main_finds_the_registry_from_any_working_directory(tmp_path, monkeypatch, capsys):
    from statistical_analysis import EVAL_DIR, load_registry, main

    expected = len(load_registry(EVAL_DIR / "repetitions"))
    monkeypatch.chdir(tmp_path)
    main()
    assert f"Total records analyzed: {expected}" in capsys.readouterr().out
