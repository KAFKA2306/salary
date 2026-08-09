#!/usr/bin/env python3
"""Validate the salary repository as an immutable historical archive."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "archive-manifest.json"
ARTIFACT_SUFFIXES = {".csv", ".ipynb", ".md", ".py"}
EXCLUDED = {"README.md", "archive-manifest.json"}
SECRET_PATTERNS = {
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "github_token": re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"),
    "aws_access_key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "generic_secret": re.compile(r"(?i)(?:api[_-]?key|token|password)\s*[=:]\s*['\"][^'\"]{8,}"),
}
PERSONAL_PATH = re.compile(r"(?i)(?:[A-Z]:\\Users\\[^\\\s]+|/Users/[^/\s]+|/home/[^/\s]+)")
NON_BLOCKING_NOTEBOOK_FINDINGS = {"personal_absolute_path"}


def git_blob_sha(path: Path) -> str:
    result = subprocess.run(
        ["git", "hash-object", str(path)], cwd=ROOT, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tracked_artifacts() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, check=True, capture_output=True, text=True
    )
    paths = []
    for raw in result.stdout.splitlines():
        path = Path(raw)
        if raw in EXCLUDED or raw.startswith(("scripts/", "tests/", ".github/")):
            continue
        if path.suffix.lower() in ARTIFACT_SUFFIXES:
            paths.append(raw)
    return sorted(paths)


def inspect_csv(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    encoding = "utf-8-sig"
    try:
        text = raw.decode(encoding)
    except UnicodeDecodeError:
        encoding = "cp932"
        text = raw.decode(encoding)
    sample = text[:8192]
    dialect = csv.Sniffer().sniff(sample, delimiters=",\t;")
    rows = list(csv.reader(text.splitlines(), dialect))
    header = rows[0] if rows else []
    body = rows[1:] if rows else []
    empty_columns = [
        name or f"column_{index}"
        for index, name in enumerate(header)
        if all(index >= len(row) or not row[index].strip() for row in body)
    ]
    normalized = [tuple(cell.strip() for cell in row) for row in body]
    return {
        "encoding": encoding,
        "delimiter": dialect.delimiter,
        "row_count": len(body),
        "columns": header,
        "duplicate_row_count": len(normalized) - len(set(normalized)),
        "empty_columns": empty_columns,
    }


def inspect_notebook(path: Path) -> dict[str, Any]:
    notebook = json.loads(path.read_text(encoding="utf-8"))
    cells = notebook.get("cells", [])
    source = "\n".join(
        "".join(cell.get("source", [])) for cell in cells if cell.get("cell_type") == "code"
    )
    output_count = sum(len(cell.get("outputs", [])) for cell in cells)
    execution_counts = [
        cell.get("execution_count")
        for cell in cells
        if cell.get("cell_type") == "code" and cell.get("execution_count") is not None
    ]
    findings = []
    for name, pattern in SECRET_PATTERNS.items():
        if pattern.search(source):
            findings.append(name)
    if PERSONAL_PATH.search(source):
        findings.append("personal_absolute_path")
    kernelspec = notebook.get("metadata", {}).get("kernelspec", {})
    return {
        "cell_count": len(cells),
        "output_count": output_count,
        "execution_count_entries": len(execution_counts),
        "kernel": kernelspec.get("display_name", "UNKNOWN"),
        "security_findings": sorted(set(findings)),
    }


def blocking_notebook_findings(findings: list[str]) -> list[str]:
    """Return credential-like findings that must fail CI.

    Historical absolute paths remain visible in the audit report, but they are
    provenance/reproducibility findings rather than evidence of a live secret.
    """
    return sorted(set(findings) - NON_BLOCKING_NOTEBOOK_FINDINGS)


def load_manifest() -> dict[str, Any]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def audit() -> tuple[list[str], dict[str, Any]]:
    manifest = load_manifest()
    entries = manifest.get("artifacts", [])
    by_path = {entry["path"]: entry for entry in entries}
    errors: list[str] = []
    tracked = tracked_artifacts()

    missing = sorted(set(tracked) - set(by_path))
    stale = sorted(set(by_path) - set(tracked))
    if missing:
        errors.append(f"unregistered artifacts: {missing}")
    if stale:
        errors.append(f"manifest paths not tracked: {stale}")

    hashes: dict[str, list[str]] = defaultdict(list)
    report_entries = []
    for path_text in sorted(set(tracked) & set(by_path)):
        path = ROOT / path_text
        entry = by_path[path_text]
        blob = git_blob_sha(path)
        hashes[blob].append(path_text)
        if entry.get("git_blob_sha") != blob:
            errors.append(f"blob hash mismatch: {path_text}")
        if entry.get("size_bytes") != path.stat().st_size:
            errors.append(f"size mismatch: {path_text}")
        detail: dict[str, Any] = {}
        if path.suffix.lower() == ".csv":
            detail = inspect_csv(path)
        elif path.suffix.lower() == ".ipynb":
            detail = inspect_notebook(path)
            blocking = blocking_notebook_findings(detail["security_findings"])
            if blocking:
                errors.append(f"notebook secret findings: {path_text}: {blocking}")
        report_entries.append(
            {
                "path": path_text,
                "sha256": sha256(path),
                "git_blob_sha": blob,
                "size_bytes": path.stat().st_size,
                "role": entry["role"],
                "current_use_status": entry["current_use_status"],
                "detail": detail,
            }
        )

    duplicate_groups = []
    classifications = manifest.get("duplicate_classifications", [])
    classified = {tuple(sorted(item["paths"])) for item in classifications}
    for blob, paths in sorted(hashes.items()):
        if len(paths) < 2:
            continue
        group = tuple(sorted(paths))
        duplicate_groups.append({"git_blob_sha": blob, "paths": list(group)})
        if group not in classified:
            errors.append(f"unclassified duplicate: {list(group)}")

    for item in classifications:
        if item.get("classification") not in {"intentional_alias", "duplicate", "unresolved"}:
            errors.append(f"invalid duplicate classification: {item}")

    report = {
        "schema_version": 1,
        "artifact_count": len(report_entries),
        "artifacts": report_entries,
        "duplicate_groups": duplicate_groups,
    }
    return errors, report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    errors, report = audit()
    if args.report:
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"archive integrity OK: {report['artifact_count']} artifacts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
