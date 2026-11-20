#!/usr/bin/env python3
"""
Statistical analysis of the repetition registry.

This script performs exploratory statistical analysis on the 72 classified
repetition records, including:
- Descriptive statistics
- McNemar's test for paired comparisons
- Binomial confidence intervals
- Effect sizes (Cohen's h)
- Stability analysis
"""

import json
import math
import sys
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Tuple

EVAL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EVAL_DIR))
from contract.p2_1 import paired_mcnemar  # noqa: E402


def load_registry(registry_path: Path) -> List[Dict]:
    """Load all classified records from the repetition registry."""
    records = []
    for p in registry_path.rglob('*.json'):
        d = json.loads(p.read_text())
        if d.get('status') == 'classified':
            records.append(d)
    return records


def _betacf(a: float, b: float, x: float) -> float:
    """Continued fraction for the incomplete beta function (Lentz)."""
    max_iterations, epsilon, tiny = 200, 3e-14, 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    d = tiny if abs(d) < tiny else d
    d = 1.0 / d
    h = d
    for m in range(1, max_iterations + 1):
        m2 = 2 * m
        for numerator in (
            m * (b - m) * x / ((qam + m2) * (a + m2)),
            -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2)),
        ):
            d = 1.0 + numerator * d
            d = tiny if abs(d) < tiny else d
            c = 1.0 + numerator / c
            c = tiny if abs(c) < tiny else c
            d = 1.0 / d
            h *= d * c
        if abs(d * c - 1.0) < epsilon:
            break
    return h


def _betainc(a: float, b: float, x: float) -> float:
    """Regularized incomplete beta function I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    log_beta = (
        math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
        + a * math.log(x) + b * math.log1p(-x)
    )
    front = math.exp(log_beta)
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _betacf(a, b, x) / a
    return 1.0 - front * _betacf(b, a, 1.0 - x) / b


def _beta_ppf(quantile: float, a: float, b: float) -> float:
    """Inverse regularized incomplete beta by bisection."""
    low, high = 0.0, 1.0
    for _ in range(200):
        middle = (low + high) / 2.0
        if _betainc(a, b, middle) < quantile:
            low = middle
        else:
            high = middle
    return (low + high) / 2.0


def compute_binomial_ci(successes: int, n: int, confidence: float = 0.95) -> Tuple[float, float]:
    """Compute the exact Clopper-Pearson binomial confidence interval.

    Example:
        >>> lower, upper = compute_binomial_ci(10, 10)
        >>> round(lower, 3), round(upper, 3)
        (0.692, 1.0)
    """
    if n == 0:
        return (0.0, 0.0)
    alpha = 1.0 - confidence
    lower = (
        0.0 if successes == 0
        else _beta_ppf(alpha / 2.0, successes, n - successes + 1)
    )
    upper = (
        1.0 if successes == n
        else _beta_ppf(1.0 - alpha / 2.0, successes + 1, n - successes)
    )
    return (lower, upper)


def compute_cohens_h(p1: float, p2: float) -> float:
    """Compute Cohen's h effect size for two proportions."""
    phi1 = 2 * math.asin(math.sqrt(p1))
    phi2 = 2 * math.asin(math.sqrt(p2))
    return phi1 - phi2


def interpret_cohens_h(h: float) -> str:
    """Interpret Cohen's h effect size."""
    abs_h = abs(h)
    if abs_h < 0.2:
        return "negligible"
    elif abs_h < 0.5:
        return "small"
    elif abs_h < 0.8:
        return "medium"
    else:
        return "large"


def analyze_stability(records: List[Dict]) -> Dict:
    """Analyze stability within each model across repetitions."""
    # Group by (case_id, model, condition)
    groups = defaultdict(list)
    for r in records:
        key = (r['case_id'], r['model'], r['condition'])
        groups[key].append(r['classification']['classification'])
    
    stability_results = {}
    for key, classifications in groups.items():
        case_id, model, condition = key
        unique = set(classifications)
        stable = len(unique) == 1
        majority = Counter(classifications).most_common(1)[0][0]
        
        stability_results[key] = {
            'stable': stable,
            'majority': majority,
            'classifications': classifications,
            'n': len(classifications)
        }
    
    return stability_results


def analyze_agreement(records: List[Dict]) -> Dict:
    """Analyze inter-model agreement."""
    # Group by (case_id, condition, repetition)
    groups = defaultdict(dict)
    for r in records:
        key = (r['case_id'], r['condition'], r['repetition_id'])
        groups[key][r['model']] = r['classification']['classification']
    
    agreement_results = []
    for key, models in groups.items():
        case_id, condition, repetition = key
        if 'Anthropic' in models and 'claude-opus-5-max' in models:
            agree = models['Anthropic'] == models['claude-opus-5-max']
            agreement_results.append({
                'case_id': case_id,
                'condition': condition,
                'repetition': repetition,
                'Anthropic': models['Anthropic'],
                'claude-opus-5-max': models['claude-opus-5-max'],
                'agree': agree
            })
    
    return agreement_results


def main():
    registry_path = EVAL_DIR / 'repetitions'
    records = load_registry(registry_path)

    if not records:
        print("No classified records found in the registry.")
        return

    print(f"Loaded {len(records)} classified records\n")
    
    # 1. Descriptive statistics
    print("=" * 70)
    print("1. DESCRIPTIVE STATISTICS")
    print("=" * 70)
    
    # Overall pass rate
    pass_count = sum(1 for r in records if r['classification']['classification'] == 'PASS')
    partial_count = sum(1 for r in records if r['classification']['classification'] == 'PARTIAL')
    fail_count = sum(1 for r in records if r['classification']['classification'] == 'FAIL')
    total = len(records)
    
    print(f"\nOverall classification distribution:")
    print(f"  PASS:    {pass_count:3d}/{total} ({pass_count/total*100:.1f}%)")
    print(f"  PARTIAL: {partial_count:3d}/{total} ({partial_count/total*100:.1f}%)")
    print(f"  FAIL:    {fail_count:3d}/{total} ({fail_count/total*100:.1f}%)")
    
    # Per-model statistics
    print(f"\nPer-model statistics:")
    for model in ['Anthropic', 'claude-opus-5-max']:
        model_records = [r for r in records if r['model'] == model]
        model_pass = sum(1 for r in model_records if r['classification']['classification'] == 'PASS')
        model_total = len(model_records)
        p_hat = model_pass / model_total
        ci_lower, ci_upper = compute_binomial_ci(model_pass, model_total)
        
        print(f"\n  {model}:")
        print(f"    PASS rate: {model_pass}/{model_total} ({p_hat*100:.1f}%)")
        print(f"    95% CI: [{ci_lower*100:.1f}%, {ci_upper*100:.1f}%]")
    
    # Per-case statistics
    print(f"\nPer-case statistics:")
    cases = sorted(set(r['case_id'] for r in records))
    for case in cases:
        case_records = [r for r in records if r['case_id'] == case]
        case_pass = sum(1 for r in case_records if r['classification']['classification'] == 'PASS')
        case_total = len(case_records)
        p_hat = case_pass / case_total
        ci_lower, ci_upper = compute_binomial_ci(case_pass, case_total)
        
        print(f"\n  {case.split('/')[-1]}:")
        print(f"    PASS rate: {case_pass}/{case_total} ({p_hat*100:.1f}%)")
        print(f"    95% CI: [{ci_lower*100:.1f}%, {ci_upper*100:.1f}%]")
    
    # 2. Stability analysis
    print("\n" + "=" * 70)
    print("2. STABILITY ANALYSIS (intra-model across repetitions)")
    print("=" * 70)
    
    stability = analyze_stability(records)
    
    for model in ['Anthropic', 'claude-opus-5-max']:
        model_stability = {k: v for k, v in stability.items() if k[1] == model}
        stable_count = sum(1 for v in model_stability.values() if v['stable'])
        total_count = len(model_stability)
        
        print(f"\n  {model}:")
        print(f"    Stable conditions: {stable_count}/{total_count} ({stable_count/total_count*100:.1f}%)")
        
        # Show variable conditions
        variable = [(k, v) for k, v in model_stability.items() if not v['stable']]
        if variable:
            print(f"    Variable conditions:")
            for (case_id, _, condition), info in variable:
                print(f"      {case_id.split('/')[-1]} {condition}: {info['classifications']}")
    # Per-model stability for summary
    anthropic_keys = [k for k in stability.keys() if k[1] == 'Anthropic']
    anthropic_stable = sum(1 for k in anthropic_keys if stability[k]['stable'])
    anthropic_total = len(anthropic_keys)
    claude_keys = [k for k in stability.keys() if k[1] == 'claude-opus-5-max']
    claude_stable = sum(1 for k in claude_keys if stability[k]['stable'])
    claude_total = len(claude_keys)
    
    # 3. Inter-model agreement
    print("\n" + "=" * 70)
    print("3. INTER-MODEL AGREEMENT")
    print("=" * 70)
    
    agreement = analyze_agreement(records)
    agree_count = sum(1 for a in agreement if a['agree'])
    total_agreement = len(agreement)
    
    print(f"\n  Overall agreement: {agree_count}/{total_agreement} ({agree_count/total_agreement*100 if total_agreement else 0.0:.1f}%)")
    
    # Per-case agreement
    print(f"\n  Per-case agreement:")
    cases_agreement = defaultdict(list)
    for a in agreement:
        cases_agreement[a['case_id']].append(a['agree'])
    
    for case, agrees in cases_agreement.items():
        case_agree = sum(agrees)
        case_total = len(agrees)
        print(f"    {case.split('/')[-1]}: {case_agree}/{case_total} ({case_agree/case_total*100:.1f}%)")
    
    # 4. McNemar's test
    print("\n" + "=" * 70)
    print("4. McNEMAR'S TEST (paired comparisons)")
    print("=" * 70)
    
    # Group by (case_id, condition) and count discordant pairs
    print(f"\n  Note: McNemar's test requires paired data (same repetition).")
    print(f"  With n=3 repetitions, we have limited power.\n")
    
    for case in cases:
        print(f"  {case.split('/')[-1]}:")
        for condition in ['C0', 'C1', 'C2', 'C3']:
            anthropic_outcomes: List[bool] = []
            claude_outcomes: List[bool] = []

            for rep in ['r01', 'r02', 'r03']:
                anthropic_cls = None
                claude_cls = None

                for r in records:
                    if (r['case_id'] == case and
                        r['condition'] == condition and
                        r['repetition_id'] == rep):
                        if r['model'] == 'Anthropic':
                            anthropic_cls = r['classification']['classification']
                        elif r['model'] == 'claude-opus-5-max':
                            claude_cls = r['classification']['classification']

                if anthropic_cls and claude_cls:
                    anthropic_outcomes.append(anthropic_cls == 'PASS')
                    claude_outcomes.append(claude_cls == 'PASS')

            if anthropic_outcomes:
                result = paired_mcnemar(anthropic_outcomes, claude_outcomes)
                print(
                    f"    {condition}: b={result['discordant_a_wins']}, "
                    f"c={result['discordant_b_wins']}, "
                    f"p={result['p_value']:.3f}"
                )
            else:
                print(f"    {condition}: No paired repetitions")
    
    # 5. Effect sizes
    print("\n" + "=" * 70)
    print("5. EFFECT SIZES (Cohen's h)")
    print("=" * 70)
    
    print(f"\n  Comparing PASS rates between models:\n")
    
    for case in cases:
        print(f"  {case.split('/')[-1]}:")
        for condition in ['C0', 'C1', 'C2', 'C3']:
            # Compute PASS rates for each model
            anthropic_pass = 0
            anthropic_n = 0
            claude_pass = 0
            claude_n = 0
            
            for r in records:
                if r['case_id'] == case and r['condition'] == condition:
                    if r['model'] == 'Anthropic':
                        anthropic_n += 1
                        if r['classification']['classification'] == 'PASS':
                            anthropic_pass += 1
                    elif r['model'] == 'claude-opus-5-max':
                        claude_n += 1
                        if r['classification']['classification'] == 'PASS':
                            claude_pass += 1
            
            if anthropic_n > 0 and claude_n > 0:
                p1 = anthropic_pass / anthropic_n
                p2 = claude_pass / claude_n
                h = compute_cohens_h(p1, p2)
                interpretation = interpret_cohens_h(h)
                
                print(f"    {condition}: Anthropic={p1:.2f}, claude={p2:.2f}, h={h:+.2f} ({interpretation})")
    
    # 6. Summary
    anthropic_rate = anthropic_stable / anthropic_total * 100 if anthropic_total else 0.0
    claude_rate = claude_stable / claude_total * 100 if claude_total else 0.0
    agreement_rate = agree_count / total_agreement * 100 if total_agreement else 0.0
    ci_lower, ci_upper = compute_binomial_ci(pass_count, total)
    print("\n" + "=" * 70)
    print("6. SUMMARY")
    print("=" * 70)
    print(f"""
  Total records analyzed: {total}

  Overall PASS rate: {pass_count/total*100:.1f}%
  95% CI (Clopper-Pearson): [{ci_lower*100:.1f}%, {ci_upper*100:.1f}%]

  Anthropic stability: {anthropic_stable}/{anthropic_total} conditions ({anthropic_rate:.1f}%)
  claude-opus-5-max stability: {claude_stable}/{claude_total} conditions ({claude_rate:.1f}%)

  Inter-model agreement: {agreement_rate:.1f}%

  Limitations:
  - n=3 per cell is insufficient for definitive statistical claims
  - Intervals are exact but wide with such small samples
  - Results are descriptive observations only, not causal claims
""")


if __name__ == '__main__':
    main()
