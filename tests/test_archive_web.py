import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "archive_inspection", ROOT / "scripts" / "browser_archive_inspection.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class ArchiveWebTests(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads((ROOT / "archive-manifest.json").read_text(encoding="utf-8"))

    def test_catalog_uses_manifest_and_excludes_unknown_from_aggregate(self):
        catalog = MODULE.build_catalog(self.manifest)
        self.assertEqual(catalog["artifact_count"], len(self.manifest["artifacts"]))
        self.assertEqual(catalog["eligible_unique_dataset_count"], 0)
        self.assertTrue(all(item["path"] for item in catalog["catalog"]))

    def test_byte_identical_aliases_are_one_duplicate_group(self):
        catalog = MODULE.build_catalog(self.manifest)
        groups = {tuple(group["paths"]) for group in catalog["duplicate_groups"]}
        self.assertIn(("SemiCon.csv", "results.csv"), groups)

    def test_unregistered_artifact_cannot_be_inspected(self):
        with self.assertRaisesRegex(ValueError, "not registered"):
            MODULE.inspect_payload(self.manifest, "not-in-manifest.csv", b"a,b\n1,2\n")

    def test_csv_inspection_is_value_neutral(self):
        detail = MODULE.inspect_csv_bytes(b"name,value\na,1\na,1\nb,\n")
        self.assertEqual(detail["row_count"], 3)
        self.assertEqual(detail["duplicate_row_count"], 1)
        self.assertEqual(detail["column_count"], 2)

    def test_worker_is_module_pyodide_and_no_external_scrape_logic(self):
        worker = (ROOT / "web" / "worker.mjs").read_text(encoding="utf-8")
        app = (ROOT / "web" / "app.mjs").read_text(encoding="utf-8")
        page = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        self.assertIn("pyodide/v314.0.2/full/pyodide.mjs", worker)
        self.assertIn("new Worker('./worker.mjs', { type: 'module' })", app)
        self.assertIn("archive-manifest.json", app)
        self.assertIn("2024年2月の研究snapshot", page)
        self.assertNotIn("requests.get", worker + app)
        self.assertNotIn("fetch('http", app)

    def test_current_benchmark_is_a_separate_fail_loud_surface(self):
        app = (ROOT / "web" / "app.mjs").read_text(encoding="utf-8")
        page = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        self.assertIn("transport-equipment-fy2026-salary-top20.json", app)
        self.assertIn("expected 20 observations", app)
        self.assertIn("EDINET一次資料を確認", page)
        self.assertIn("業界全体の代表標本ではありません", page)
        self.assertLess(page.index("輸送用機器・給与上位20社の報酬比較"), page.index("2024年2月の研究snapshot"))

    def test_current_benchmark_exposes_three_peer_decisions(self):
        app = (ROOT / "web" / "app.mjs").read_text(encoding="utf-8")
        page = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        for metric_id in ("salary-band", "age-band", "tenure-band"):
            self.assertIn(f'id="{metric_id}"', page)
            self.assertIn(f"#{metric_id}", app)
        self.assertIn("current benchmark three-axis metrics missing", app)
        self.assertIn("年齢・比較群内の位置", page)
        self.assertIn("勤続年数・比較群内の位置", page)

    def test_company_selection_precedes_reference_detail(self):
        page = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        self.assertIn("まず比較する会社を選ぶ", page)
        self.assertIn("比較群の基準値を見る", page)
        self.assertLess(page.index('id="company-select"'), page.index('id="salary-q1"'))


if __name__ == "__main__":
    unittest.main()
