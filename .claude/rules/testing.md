# Testing Protocol

- Write tests for new features (TDD: test before code)
- Include edge cases and error scenarios
- Prefer integration-style tests over excessive mocking
- Coverage target: >85% on changed areas
- Don't test trivial code (getters, setters, constants)
- Run tests before finishing task
- TDD: Test creates stubs (FAIL) → Developer implements (PASS) → Test validates
- Max 3 fix iterations before escalation to PM
- For Tier 2: ALWAYS run existing tests to check for regressions
- For Tier 3: Run bug-reproduction test + nearby regression tests
