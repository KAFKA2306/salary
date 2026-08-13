"""Browser-safe archive inspection for the historical salary snapshot.

This module intentionally uses only the Python standard library for inspection.
Network access, when running in Pyodide, is limited to same-origin files selected
from archive-manifest.json.
"""

from __future__ import annotations

import csv
import io
import json
from collections import defaultdict
from typing import Any

UNKNOWN_STATUS = "UNKNOWN_PROVENANCE"


def _artifacts(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        raise ValueError("manifest.artifacts must be a list")
    return artifacts


def build_catalog(manifest: dict[str, Any]) -> dict[str, Any]:
    artifacts = _artifacts(manifest)
    seen_paths: set[str] = set()
    by_blob: dict[str, list[str]] = defaultdict(list)
    catalog: list[dict[str, Any]] = []
    for item in artifacts:
        path = item.get("path")
        blob = item.get("git_blob_sha")
        if not isinstance(path, str) or not path or path in seen_paths:
            raise ValueError("manifest artifact paths must be unique non-empty strings")
        if not isinstance(blob, str) or len(blob) != 40:
            raise ValueError(f"invalid git blob sha for {path}")
        seen_paths.add(path)
        by_blob[blob].append(path)
        catalog.append({
            "path": path,
            "role": item.get("role", "UNKNOWN"),
            "status": item.get("current_use_status", "UNKNOWN"),
            "git_blob_sha": blob,
            "size_bytes": item.get("size_bytes"),
            "source_category": item.get("source_category", "UNKNOWN"),
            "captured_at": item.get("captured_at", "UNKNOWN"),
            "period": item.get("period", "UNKNOWN"),
        })
    unique_eligible_blobs = {
        item["git_blob_sha"] for item in catalog
        if item["status"] not in {UNKNOWN_STATUS, "ARCHIVE_ONLY"}
    }
    duplicate_groups = [
        {"git_blob_sha": blob, "paths": sorted(paths)}
        for blob, paths in sorted(by_blob.items()) if len(paths) > 1
    ]
    return {
        "archive_as_of": manifest.get("archive_as_of", "UNKNOWN"),
        "artifact_count": len(catalog),
        "eligible_unique_dataset_count": len(unique_eligible_blobs),
        "catalog": catalog,
        "duplicate_groups": duplicate_groups,
    }


def inspect_csv_bytes(raw: bytes) -> dict[str, Any]:
    encoding = "utf-8-sig"
    try:
        text = raw.decode(encoding)
    except UnicodeDecodeError:
        encoding = "cp932"
        text = raw.decode(encoding)
    if not text:
        return {"encoding": encoding, "row_count": 0, "column_count": 0, "duplicate_row_count": 0, "empty_columns": []}
    dialect = csv.Sniffer().sniff(text[:8192], delimiters=",\t;")
    rows = list(csv.reader(io.StringIO(text), dialect))
    header = rows[0] if rows else []
    body = rows[1:] if rows else []
    normalized = [tuple(cell.strip() for cell in row) for row in body]
    empty_columns = [
        name or f"column_{index}" for index, name in enumerate(header)
        if all(index >= len(row) or not row[index].strip() for row in body)
    ]
    return {
        "encoding": encoding,
        "delimiter": dialect.delimiter,
        "row_count": len(body),
        "column_count": len(header),
        "duplicate_row_count": len(normalized) - len(set(normalized)),
        "empty_columns": empty_columns,
    }


def inspect_payload(manifest: dict[str, Any], selected_path: str, raw: bytes | None = None) -> dict[str, Any]:
    catalog = build_catalog(manifest)
    selected = next((item for item in catalog["catalog"] if item["path"] == selected_path), None)
    if selected is None:
        raise ValueError("selected artifact is not registered in archive-manifest.json")
    same_blob = sorted(item["path"] for item in catalog["catalog"] if item["git_blob_sha"] == selected["git_blob_sha"])
    detail: dict[str, Any] = {}
    if selected_path.lower().endswith(".csv"):
        if raw is None:
            raise ValueError("CSV inspection requires file bytes")
        detail = inspect_csv_bytes(raw)
    return {
        "archive_as_of": catalog["archive_as_of"],
        "artifact": selected,
        "same_blob_paths": same_blob,
        "aggregate_eligible": selected["status"] not in {UNKNOWN_STATUS, "ARCHIVE_ONLY"},
        "detail": detail,
    }


async def inspect_same_origin(manifest_url: str, artifact_url: str, selected_path: str) -> str:
    from pyodide.http import pyfetch
    manifest_response = await pyfetch(manifest_url)
    if not manifest_response.ok:
        raise RuntimeError(f"manifest fetch failed: HTTP {manifest_response.status}")
    manifest = await manifest_response.json()
    registered = {item["path"] for item in _artifacts(manifest)}
    if selected_path not in registered:
        raise ValueError("selected artifact is not registered in archive-manifest.json")
    raw = None
    if selected_path.lower().endswith(".csv"):
        response = await pyfetch(artifact_url)
        if not response.ok:
            raise RuntimeError(f"artifact fetch failed: HTTP {response.status}")
        raw = await response.bytes()
    return json.dumps(inspect_payload(manifest, selected_path, raw), ensure_ascii=False)
