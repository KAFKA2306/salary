"""Behavior checks for observed export state, not a second eligibility model."""
import csv
import tempfile
import unittest
from pathlib import Path

from scripts.job_decision_trace import GATES, build_decision_trace
from scripts.job_operation_star import build_operation_star, read_ranked_export


def trace_for(rows, ranking):
    return build_decision_trace(rows, ranking, "a" * 64, "b" * 64)


def job(job_id, **updates):
    record = {"job_id": job_id, "eligible": True, "source_url": "https://example.org/job"}
    record.update({gate: True for gate in GATES})
    record.update(updates)
    return record


def facts(trace, before, after):
    return build_operation_star(
        trace, before, after, run_id="ci-42-1",
        executed_at_utc="2026-10-08T09:00:00+00:00", actor="github-actions",
    )


class OperationStarTests(unittest.TestCase):
    def test_successful_export_has_observed_effect_and_unknown_initial_baseline(self):
        trace = trace_for([job("JOB-A")], [{"job_id": "JOB-A", "rank": 1}])
        star = facts(trace, None, {"JOB-A": 1})
        event = star["facts"][0]
        self.assertEqual((event["guard"], event["after_local_export"]), ("ALLOW", "RANKED"))
        self.assertEqual(event["before_local_export"], "UNKNOWN")
        self.assertEqual(event["feedback"], "BASELINE_UNKNOWN")
        self.assertEqual(event["business_outcome"], "NOT_MEASURED")
        self.assertEqual(star["metrics"]["business_outcome_measured_count"], 0)
        self.assertEqual(star["metrics"]["confirmed_local_action_checks"], 1)
        self.assertEqual(star["metrics"]["ranked_local_jobs"], 1)

    def test_withheld_fail_and_review_both_have_verified_absence(self):
        trace = trace_for([
            job("JOB-F", eligible=False, gate_base_salary=False),
            job("JOB-R", eligible=False, gate_salary_verified=None),
        ], [])
        star = facts(trace, {}, {})
        self.assertEqual({f["decision_status"] for f in star["facts"]}, {"FAIL", "REVIEW"})
        self.assertTrue(all(f["guard"] == "DENY" and f["after_local_export"] == "WITHHELD"
                            for f in star["facts"]))
        self.assertEqual(star["metrics"]["denied_count"], 2)
        self.assertEqual(star["metrics"]["withheld_local_jobs"], 2)
        self.assertEqual(star["metrics"]["ranked_local_jobs"], 0)

    def test_export_drift_is_rejected(self):
        trace = trace_for([job("JOB-A")], [{"job_id": "JOB-A", "rank": 1}])
        for actual in ({}, {"JOB-A": 2}, {"JOB-A": 1, "JOB-UNAPPROVED": 2}, None):
            with self.subTest(actual=actual), self.assertRaises(ValueError):
                facts(trace, {}, actual)

    def test_output_readback_rejects_duplicate_ids(self):
        with tempfile.TemporaryDirectory() as dirname:
            path = Path(dirname) / "ranking.csv"
            self.assertIsNone(read_ranked_export(path))
            path.write_text("", encoding="utf-8")
            self.assertEqual(read_ranked_export(path), {})
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerows([["job_id", "rank"], ["A", 1], ["A", 2]])
            with self.assertRaises(ValueError):
                read_ranked_export(path)


if __name__ == "__main__":
    unittest.main()
