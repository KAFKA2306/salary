# Verified fail-closed job eligibility

`JobDecision.lean` models the PASS / FAIL / REVIEW decision summary that
`scripts/job_decision_trace.py` derives from eight dbt-provided hard gates:

- At least one known FAIL always determines FAIL, even if other gates are UNKNOWN.
- Without known failures, an UNKNOWN gate or unverifiable source is REVIEW.
- Publication is permitted only when there is no FAIL, no UNKNOWN, and the source is valid.

Lean proves the finite summary logic. Its eight-case matrix is executed and
matched against Python `build_decision_trace`, including rejection of
inconsistent `eligible` fields. This **does not** prove the upstream dbt
salary gates, source freshness, data collection, or actual job applications.
Retain the dbt, database, provenance, integration and security checks.

```sh
cd proofs && lake build && cd ..
python scripts/check_lean_decision_bridge.py
```
