from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ArchiveIntegrityTest(unittest.TestCase):
    def test_manifest_has_unique_paths_and_known_statuses(self) -> None:
        manifest = json.loads((ROOT / "archive-manifest.json").read_text(encoding="utf-8"))
        artifacts = manifest["artifacts"]
        paths = [item["path"] for item in artifacts]
        self.assertEqual(len(paths), len(set(paths)))
        self.assertTrue(paths)
        allowed = {"ARCHIVE_ONLY", "UNKNOWN_PROVENANCE", "SAFE_FOR_REPRODUCTION"}
        self.assertTrue(all(item["current_use_status"] in allowed for item in artifacts))

    def test_known_duplicate_is_not_two_datasets(self) -> None:
        manifest = json.loads((ROOT / "archive-manifest.json").read_text(encoding="utf-8"))
        groups = {tuple(sorted(item["paths"])): item for item in manifest["duplicate_classifications"]}
        group = groups[("SemiCon.csv", "results.csv")]
        self.assertEqual(group["classification"], "unresolved")
        self.assertIn("not count", group["reason"])

    def test_full_archive_audit(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/archive_integrity.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
