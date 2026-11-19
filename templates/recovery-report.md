# RECOVERY REPORT

> Structured recovery after an error (CORE Inv 20): report the command, the
> exact error, a hypothesized cause, and at least one alternative. One single
> retry of the same command; then an alternative or stop (Inv 10). Do not
> "fix" a failure by expanding scope.

```text
RECOVERY REPORT
Command attempted : <exact command>
Exact error       : <mensaje literal, no parafraseado>
Hypothesized cause: <causa>
Alternative (>=1) : <alternativa>
Retry status      : <first retry | alternative | stopped (Inv 10)>
Scope impact      : <none | files touched beyond the approved scope ->
                    requires justification or revert (Inv 8)>
```

## Rules that reuse this template

- Tool output that contradicts expectations: state it before using the data.
- Do not summarize test output as "tests pass" without showing the command and
  the relevant output lines (Inv 7).
- Exit code zero is not success: verify the observed impact before declaring
  completion (Inv 7 real-effect clause).
- If a test/lint/build fails, verify the base state first before attributing
  the failure to the change (Inv 19).