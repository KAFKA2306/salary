"""Meaningful tests for evidence-gated publication and UNKNOWN separation."""
import unittest
from scripts.job_decision_trace import GATES, build_decision_trace


def example(**updates):
    row = {"job_id": "JOB-ONE", "eligible": True, "source_url": "https://example.org/job"}
    row.update({gate: True for gate in GATES})
    row.update(updates)
    return row


class DecisionTraceTests(unittest.TestCase):
    def build(self, rows, ranking):
        return build_decision_trace(rows, ranking, "a" * 64, "b" * 64)

    def test_passing_job_has_a_traceable_publish_action(self):
        result = self.build([example()], [{"job_id": "JOB-ONE", "rank": 1}])
        item = result["decisions"][0]
        self.assertEqual(item["status"], "PASS")
        self.assertEqual(item["action"], "publish_ranked_job")
        self.assertEqual(item["rank"], 1)
        self.assertEqual(result["summary"]["pass"], 1)

    def test_known_failure_is_fail_but_missing_salary_evidence_is_review(self):
        failed = example(job_id="JOB-FAIL", eligible=False, gate_base_salary=False)
        unknown = example(job_id="JOB-REVIEW", eligible=False, gate_salary_verified=None)
        result = self.build([unknown, failed], [])
        self.assertEqual([r["status"] for r in result["decisions"]], ["FAIL", "REVIEW"])
        self.assertIn("gate_salary_verified", result["decisions"][1]["unknown_gate_ids"])
        self.assertEqual(result["summary"], {"pass": 0, "fail": 1, "review": 1, "total": 2})

    def test_unknown_or_unverified_cannot_be_published(self):
        for row in [
            example(source_url="", eligible=True),
            example(eligible=True, gate_job_verified=None),
            example(eligible=False),
        ]:
            with self.subTest(row=row):
                with self.assertRaises(ValueError):
                    self.build([row], [{"job_id": "JOB-ONE", "rank": 1}])


if __name__ == "__main__":
    unittest.main()
