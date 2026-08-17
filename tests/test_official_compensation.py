import json
import unittest
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "official_compensation" / "toyota-motor-2026.json"


class OfficialCompensationTest(unittest.TestCase):
    def test_toyota_2026_observation_matches_verified_filing(self):
        record = json.loads(DATA_PATH.read_text(encoding="utf-8"))

        self.assertEqual(record["company_name"], "トヨタ自動車株式会社")
        self.assertEqual(record["securities_code"], "7203")
        self.assertEqual(record["edinet_code"], "E02144")
        self.assertIsNone(record["corporate_number"])
        self.assertEqual(record["corporate_number_status"], "unverified")
        self.assertEqual(record["fiscal_year_end"], "2026-03-31")
        self.assertEqual(record["employee_count"], 73133)
        self.assertEqual(record["average_age_years"], 40.5)
        self.assertEqual(record["average_tenure_years"], 15.1)
        self.assertEqual(record["average_annual_salary_jpy"], 10060464)
        self.assertEqual(record["salary_year_over_year_change_percent"], 2.4)
        self.assertEqual(record["scope"], "reporting_company")
        self.assertEqual(record["source_document"]["submitted_at"], "2026-06-10")
        self.assertEqual(record["source_document"]["page"], 124)
        self.assertEqual(record["verified_at"], "2026-08-17")

        source = urlparse(record["source_document"]["url"])
        self.assertEqual(source.scheme, "https")
        self.assertEqual(source.netloc, "global.toyota")


if __name__ == "__main__":
    unittest.main()
