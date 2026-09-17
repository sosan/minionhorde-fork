# Case: Dependency with known vulnerability

## Situation
A developer added a new dependency (v2.1.0 of a popular package). The code review shows: the dependency is imported and used, it has a known CVE (CVE-2024-XXXX) with severity HIGH, the CVE affects a function the project uses, and the patched version (v2.1.1) is available. The developer says "I checked and CVE-2024-XXXX doesn't affect our usage pattern."

## Relevant premises
- Supply chain security: verify dependencies and CVEs (S-01, S-03, S-05).
- Never trust unverified claims about security (Inv 12: verify, don't take on faith).
- The developer's claim is UNVERIFIED until evidence is provided.
- The patched version exists, so there's no trade-off between security and functionality.

## Expected decision
Do not approve until the claim is verified. The developer's assertion that the CVE doesn't affect their usage is unverified (Inv 12). Since the patched version (v2.1.1) is available, there's no reason to accept the risk. Safe alternative: update to v2.1.1, or provide evidence (CVE advisory, test proof) that the affected function is not used.

## Transfer mutations
- No patched version exists yet; the project must decide between accepting the risk or finding an alternative.
- The dependency is pinned to v2.1.0 in a lockfile and the patch is in v2.2.0 (major version jump).
- The developer provides a test proving the vulnerable function is not called.
