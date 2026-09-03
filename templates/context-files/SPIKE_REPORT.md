# Spike: {{Topic}} — {{Date}}

## Metadata
| Field | Value |
|-------|-------|
| Spike ID | `SPIKE-{{NNN}}` |
| Research Brief | `docs/spikes/{{topic}}-brief.md` |
| Status | `viable | not-viable | conditional` |
| Author | `Architect + Developer` |
| Date | `{{YYYY-MM-DD}}` |
| Duration | `~{{X}}h` |

## Research Question
{{The question this spike aimed to answer}}

## Technology Evaluation

| Option | Pros | Cons | Effort (if feature) | Fit |
|--------|------|------|---------------------|-----|
| {{Option A}} | {{pros}} | {{cons}} | {{low/med/high}} | {{good/partial/poor}} |
| {{Option B}} | {{pros}} | {{cons}} | {{low/med/high}} | {{good/partial/poor}} |
| {{Option C}} | {{pros}} | {{cons}} | {{low/med/high}} | {{good/partial/poor}} |

## Alternatives Analysis

### {{Alternative 1}} — REJECTED
- **Why considered:** {{reason}}
- **Why rejected:** {{reason}}
- **What we learned:** {{learning}}

### {{Alternative 2}} — REJECTED
- **Why considered:** {{reason}}
- **Why rejected:** {{reason}}
- **What we learned:** {{learning}}

## Risk Assessment

| Risk | Severity | Likelihood | Mitigation |
|------|----------|------------|------------|
| {{risk 1}} | {{High/Med/Low}} | {{High/Med/Low}} | {{mitigation}} |
| {{risk 2}} | {{High/Med/Low}} | {{High/Med/Low}} | {{mitigation}} |

## POC Implementation

- **Branch:** `spike/{{topic}}`
- **Files:**
  - `{{file 1}}` — {{purpose}}
  - `{{file 2}}` — {{purpose}}
- **What it demonstrates:** {{summary of what the POC proves}}
- **How to run:** {{instructions}}
- **Result:** {{works / partially works / fails}}
- **Observations:** {{what we noticed during implementation}}

## Conclusions

### Viability: [VIABLE / NOT VIABLE / CONDITIONAL]

{{Explanation of why this conclusion was reached. What evidence supports it?}}

### Estimated Effort (if escalated to feature)

| Metric | Estimate |
|--------|----------|
| Files to modify | {{number}} |
| New files | {{number}} |
| New dependencies | {{list or none}} |
| Complexity | {{low/medium/high}} |
| Estimated time | {{hours/days}} |

## Lessons Learned

- {{What we learned that we didn't expect}}
- {{What was harder/easier than expected}}
- {{What we would do differently}}

## Recommendation

{{Concrete recommendation:}}
- **If VIABLE:** "Escalate to Tier 1/2. Use {{option}} as the approach. Reference this spike report as `decision_*` entity."
- **If NOT VIABLE:** "Do not pursue. {{Reason}}. Consider {{alternative}} instead."
- **If CONDITIONAL:** "Viable only if {{condition}}. Requires {{additional work}} before escalating."

## Decision

| Field | Value |
|-------|-------|
| Decision | {{chosen option or rejection}} |
| Rationale | {{why}} |
| Alternatives Rejected | {{list}} |
| Risk Level | {{low/medium/high}} |
