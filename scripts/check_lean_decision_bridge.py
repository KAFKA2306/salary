"""Lean-to-Python parity across all abstract PASS / FAIL / REVIEW cases."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.job_decision_trace import GATES, build_decision_trace  # noqa: E402


def make_row(failed: bool, unknown: bool, source: bool, allowed: bool) -> dict:
    row = {
        "job_id": "LEAN-MATRIX",
        "eligible": allowed,
        "source_url": "https://example.org/verified-job" if source else "",
    }
    row.update({gate: True for gate in GATES})
    if failed:
        row["gate_permanent"] = False
    if unknown:
        row["gate_salary_verified"] = None
    return row


def main() -> None:
    output = subprocess.run(
        ["lake", "env", "lean", "--run", "DecisionMatrix.lean"],
        cwd=ROOT / "proofs",
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    rows = output.strip().splitlines()
    if len(rows) != 8:
        raise AssertionError(f"Expected eight Lean gate combinations: {rows!r}")
    seen = set()
    for line in rows:
        f, u, s, expected = line.split(",")
        if any(bit not in ("0", "1") for bit in (f, u, s)) or expected not in ("PASS", "FAIL", "REVIEW"):
            raise AssertionError(f"Invalid Lean result: {line!r}")
        key = (f, u, s)
        if key in seen:
            raise AssertionError(f"Duplicate case: {key!r}")
        seen.add(key)
        allowed = expected == "PASS"
        ranking = [{"job_id": "LEAN-MATRIX", "rank": 1}] if allowed else []
        row = make_row(f == "1", u == "1", s == "1", allowed)
        actual = build_decision_trace([row], ranking, "a" * 64, "b" * 64)
        decision = actual["decisions"][0]
        if decision["status"] != expected:
            raise AssertionError(f"Lean/Python divergence {key}: {expected} vs {decision['status']}")
        if (decision["action"] == "publish_ranked_job") != allowed:
            raise AssertionError(f"Incorrect publish action: {key}")
        tampered = {**row, "eligible": not allowed}
        try:
            build_decision_trace([tampered], ranking, "a" * 64, "b" * 64)
        except ValueError as exc:
            if "eligibility conflicts" not in str(exc):
                raise AssertionError(f"Wrong mismatch rejection: {key}") from exc
        else:
            raise AssertionError(f"Incorrect eligibility was not rejected: {key}")
    print("PASS: 8 Lean/Python decision combinations and 8 tampered-eligibility rejections")


if __name__ == "__main__":
    main()
