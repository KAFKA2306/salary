#!/usr/bin/env python3
"""Read-only, day-granularity freshness audit for salary job evidence.

An evidence recheck is not a dbt build. This audit never triggers builds or
modifies candidate rankings; it emits stable observations for review.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import date, datetime
from pathlib import Path
from typing import Mapping, Sequence
from zoneinfo import ZoneInfo


def parse_day(value: object) -> date | None:
    if not isinstance(value, str) or len(value) != 10:
        return None
    try:
        day = date.fromisoformat(value)
    except ValueError:
        return None
    return day if day.isoformat() == value else None


def audit_evidence(
    active_job_ids: Sequence[str], documents: Sequence[Mapping[str, object]],
    *, as_of: date, max_age_days: int,
) -> list[dict[str, object]]:
    """Emit one signal per active job, retaining unknown and missing states."""
    if not isinstance(max_age_days, int) or isinstance(max_age_days, bool) or max_age_days < 0:
        raise ValueError("max_age_days must be a nonnegative integer")
    if not isinstance(as_of, date):
        raise ValueError("as_of must be a date")
    by_job: dict[str, list[Mapping[str, object]]] = {}
    for document in documents:
        job_id = document.get("job_id")
        if not isinstance(job_id, str) or not job_id.strip():
            raise ValueError("evidence document without job_id")
        by_job.setdefault(job_id, []).append(document)

    signals = []
    for job_id in sorted(set(active_job_ids)):
        if not isinstance(job_id, str) or not job_id.strip():
            raise ValueError("invalid active job_id")
        records = by_job.get(job_id, [])
        days = [parse_day(doc.get("observed_at")) for doc in records]
        if not records:
            conclusion, kind, reason, latest, age = "failure", "coverage_gap", "missing_evidence", None, None
        elif any(day is None for day in days):
            conclusion, kind, reason, latest, age = "unknown", "evidence_unverified", "invalid_observed_at", None, None
        elif any(day > as_of for day in days if day is not None):
            conclusion, kind, reason, latest, age = "unknown", "evidence_unverified", "future_observed_at", None, None
        else:
            latest = max(day for day in days if day is not None)
            age = (as_of - latest).days
            stale = age > max_age_days
            conclusion = "failure" if stale else "success"
            kind = "stale_evidence" if stale else "evidence_fresh"
            reason = "evidence_too_old" if stale else "within_day_sla"
        signals.append({
            "owner": "KAFKA2306", "repository": "salary", "source_kind": "job_evidence",
            "source_id": job_id,
            "fingerprint": hashlib.sha256(f"job-evidence:{job_id}".encode()).hexdigest()[:24],
            "kind": kind, "conclusion": conclusion, "reason": reason,
            "observed_at": latest.isoformat() if latest else None,
            "age_days": age, "as_of": as_of.isoformat(), "max_age_days": max_age_days,
        })
    return signals


def audit_repository(root: Path, *, as_of: date, max_age_days: int) -> list[dict[str, object]]:
    with (root / "seeds" / "job_candidates.csv").open(encoding="utf-8", newline="") as handle:
        active_job_ids = [row["job_id"] for row in csv.DictReader(handle)]
    documents = []
    for path in sorted((root / "evidence").glob("*.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(document, dict):
            raise ValueError(f"evidence file must be an object: {path.name}")
        documents.append(document)
    return audit_evidence(active_job_ids, documents, as_of=as_of, max_age_days=max_age_days)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--max-age-days", type=int, required=True)
    parser.add_argument("--as-of", help="YYYY-MM-DD in Asia/Tokyo (defaults to current local day)")
    args = parser.parse_args()
    as_of = parse_day(args.as_of) if args.as_of else datetime.now(ZoneInfo("Asia/Tokyo")).date()
    if as_of is None:
        parser.error("--as-of must be YYYY-MM-DD")
    signals = audit_repository(args.root, as_of=as_of, max_age_days=args.max_age_days)
    summary = {state: sum(s["conclusion"] == state for s in signals) for state in ("success", "failure", "unknown")}
    print(json.dumps({"summary": summary, "signals": signals}, ensure_ascii=False, indent=2))
    return 0  # Audit evidence, never block builds solely because a posting aged.


if __name__ == "__main__":
    raise SystemExit(main())
