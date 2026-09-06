import json
import math
import unittest
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = (
    ROOT
    / "data"
    / "official_compensation"
    / "transport-equipment-fy2026-salary-top20.json"
)


def linear_quantile(values, quantile):
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


class OfficialCompensationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset = json.loads(DATA_PATH.read_text(encoding="utf-8"))
        cls.records = cls.dataset["observations"]

    def test_current_cohort_uses_20_verified_reporting_company_observations(self):
        self.assertEqual(self.dataset["cohort_definition"]["industry"], "輸送用機器")
        self.assertEqual(self.dataset["cohort_definition"]["fiscal_year_end"], "2026-03-31")
        self.assertEqual(len(self.records), 20)
        self.assertEqual(len({row["edinet_code"] for row in self.records}), 20)
        self.assertEqual(len({row["securities_code"] for row in self.records}), 20)

        for row in self.records:
            self.assertEqual(row["fiscal_year_end"], "2026-03-31")
            self.assertEqual(row["scope"], "reporting_company")
            self.assertGreater(row["employee_count"], 0)
            self.assertGreater(row["average_age_years"], 0)
            self.assertGreater(row["average_tenure_years"], 0)
            self.assertGreater(row["average_annual_salary_jpy"], 0)
            self.assertIsNone(row["corporate_number"])
            self.assertEqual(row["corporate_number_status"], "unverified")
            self.assertEqual(row["verified_at"], "2026-09-06")

            source = row["source_document"]
            self.assertTrue(source["doc_id"].startswith("S100"))
            parsed = urlparse(source["url"])
            self.assertEqual(parsed.scheme, "https")
            self.assertEqual(parsed.netloc, "disclosure2.edinet-fsa.go.jp")
            self.assertIn(source["doc_id"], source["url"])
            self.assertEqual(source["section"], "従業員の状況")

    def test_toyota_observation_matches_2026_filing(self):
        toyota = next(row for row in self.records if row["edinet_code"] == "E02144")
        self.assertEqual(toyota["company_name"], "トヨタ自動車株式会社")
        self.assertEqual(toyota["securities_code"], "7203")
        self.assertEqual(toyota["employee_count"], 73133)
        self.assertEqual(toyota["average_age_years"], 40.5)
        self.assertEqual(toyota["average_tenure_years"], 15.1)
        self.assertEqual(toyota["average_annual_salary_jpy"], 10060464)
        self.assertEqual(toyota["salary_year_over_year_change_percent"], 2.4)
        self.assertEqual(toyota["source_document"]["doc_id"], "S100Y8NY")

    def test_suzuki_keeps_month_precision_from_primary_filing(self):
        suzuki = next(row for row in self.records if row["edinet_code"] == "E02167")
        self.assertEqual(suzuki["average_age_years"], 41.5)
        self.assertEqual(suzuki["average_tenure_years"], 18.5)

    def test_benchmark_is_recomputed_from_canonical_observations(self):
        metrics = self.dataset["benchmark"]["metrics"]
        for field in (
            "average_annual_salary_jpy",
            "average_age_years",
            "average_tenure_years",
        ):
            values = [row[field] for row in self.records]
            self.assertAlmostEqual(metrics[field]["q1"], linear_quantile(values, 0.25))
            self.assertAlmostEqual(metrics[field]["median"], linear_quantile(values, 0.50))
            self.assertAlmostEqual(metrics[field]["q3"], linear_quantile(values, 0.75))

    def test_current_observations_are_not_archive_artifacts(self):
        manifest = json.loads((ROOT / "archive-manifest.json").read_text(encoding="utf-8"))
        archive_paths = {item["path"] for item in manifest["artifacts"]}

        self.assertFalse(manifest["policy"]["current_decision_use"])
        self.assertNotIn(DATA_PATH.relative_to(ROOT).as_posix(), archive_paths)


if __name__ == "__main__":
    unittest.main()
