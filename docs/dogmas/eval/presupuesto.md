# Bootstrap Budget

Estimated cost to calibrate an agent from scratch up to the irreducible range.

## Cost per tutoring session

| Concept | Estimated tokens | Notes |
|---|---|---|
| System prompt (CORE + policy) | ~3-5k | Loaded once per session |
| Worked canonical case | ~2-4k | Per case (question + reflection + critique) |
| Worked adversarial case | ~3-5k | More expensive (conflict, deliberation) |
| Mutated case (transfer) | ~2-3k | Per mutation |
| Tone exam (30 cases) | ~15-25k | 30 cases × ~500-800 tokens |
| Consolidation and heartbeat | ~1-2k | Per session |

## Cost per model family

| Family | Models | Cases per run | Runs | Total cost |
|---|---|---|---|---|
| Anthropic | Claude Opus 5, Sonnet | 30 | 3 | ~90-150k tokens |
| Anthropic | QW 3.8 Max, QWEN5.3max | 30 | 3 | ~90-150k tokens |
| Anthropic | Anthropic, Anthropic | 30 | 3 | ~90-150k tokens |
| Meta | Anthropic, nemotron | 30 | 3 | ~90-150k tokens |

Total cost for full crystallization (4 families, 30 cases, 3 runs): **~360-600k tokens**.

## Total expected cost

1. **Initial bootstrap** (1 orientation session + 5 canonical cases + 5 adversarial cases + 5 mutations): ~50-80k tokens.
2. **Iterative calibration** (3 critique rounds): ~150-250k tokens.
3. **Cross-model crystallization** (4 families × 30 cases × 3 runs): ~360-600k tokens.
4. **Final exam and consolidation**: ~20-30k tokens.

**Estimated total: ~580-960k tokens** to reach the irreducible range with statistical confidence (n=90 per category).

## Cost/benefit comparison

Refinement stops when:
- The marginal cost of an additional round exceeds the observed FAIL rate reduction.
- With 100% unanimous PASS across 7 models, the marginal cost of extra rounds is >90% of the total cost to gain <0.1% FAIL.
- **Decision: do not add more models/families (7 is enough).** The marginal benefit of an 8th model does not justify the cost.

**But the 3 passes ARE necessary:** going from n=1 to n=3 per case adds no models, it only repeats the 30 cases on the same 7 — it is the minimum cost to turn a preliminary estimate into a claim with 95% CI and ≤5% error. Skipping passes 2 and 3 would leave crystallization at MEDIUM confidence.

## Tracking

- Tokens consumed per round: record in MEMORY.
- FAIL rate per category: record in eval/report.json.
- Stop when: marginal_cost / FAIL_reduction > threshold (default: 1000 tokens per 0.1% FAIL).
