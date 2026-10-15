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

    # The FAIL/REVIEW precedence and illegal-publication combinations
    # are exhaustively checked against Lean in check_lean_decision_bridge.py.


if __name__ == "__main__":
    unittest.main()
