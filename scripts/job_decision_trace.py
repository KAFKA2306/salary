"""Deterministic, fail-closed job eligibility decision lineage.

This module reuses dbt gate results; it does not independently recompute
salary, customer-facing, or ranking eligibility.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

GATES = (
    "gate_permanent",
    "gate_base_salary",
    "gate_salary_verified",
    "gate_no_customer_facing",
    "gate_no_outsourcing",
    "gate_no_consulting",
    "gate_ownership",
    "gate_job_verified",
)
RULE_ID = "job-search-hard-gates-v1"


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_decision_trace(gate_rows, ranking, source_hash: str, policy_hash: str) -> dict:
    rank_by_job = {}
    for item in ranking:
        job_id = item["job_id"]
        if job_id in rank_by_job:
            raise ValueError(f"duplicate ranking job ID: {job_id}")
        rank_by_job[job_id] = item["rank"]
    records = []
    seen = set()
    for row in sorted(gate_rows, key=lambda item: item["job_id"]):
        job_id = row["job_id"]
        if not job_id or job_id in seen:
            raise ValueError(f"duplicate or empty decision job ID: {job_id}")
        seen.add(job_id)
        missing = set(GATES) - row.keys()
        if missing:
            raise ValueError(f"missing dbt gate columns for {job_id}: {sorted(missing)}")
        gates = {}
        for key in GATES:
            value = row[key]
            if value not in (True, False, None):
                raise ValueError(f"invalid gate result for {job_id}: {key}={value!r}")
            gates[key] = "PASS" if value is True else "FAIL" if value is False else "UNKNOWN"
        failures = sorted(key for key, value in gates.items() if value == "FAIL")
        unknown = sorted(key for key, value in gates.items() if value == "UNKNOWN")
        url = row.get("source_url")
        source_valid = isinstance(url, str) and url.startswith(("https://", "http://"))
        if failures:
            status = "FAIL"
        elif unknown or not source_valid:
            status = "REVIEW"
        else:
            status = "PASS"
        if bool(row.get("eligible")) != (status == "PASS"):
            raise ValueError(f"dbt eligibility conflicts with explicit gates for {job_id}")
        is_ranked = job_id in rank_by_job
        if is_ranked != (status == "PASS"):
            raise ValueError(f"published ranking conflicts with gate decision for {job_id}")
        records.append({
            "decision_id": f"{job_id}:{RULE_ID}",
            "job_id": job_id,
            "status": status,
            "rule_id": RULE_ID,
            "gate_results": gates,
            "failed_gate_ids": failures,
            "unknown_gate_ids": unknown,
            "source_url": url if source_valid else None,
            "source_claim": "supplied_job_source_not_live_reverified",
            "rank": rank_by_job.get(job_id),
            "action": "publish_ranked_job" if status == "PASS" else "withhold_ranking",
        })
    if seen != set(rank_by_job):
        raise ValueError("ranking contains a job absent from gate decisions")
    return {
        "schema_version": 1,
        "rule_id": RULE_ID,
        "inputs": {
            "source_file": "seeds/job_candidates.csv",
            "source_sha256": source_hash,
            "ontology_file": "ontology/job_search.yml",
            "ontology_sha256": policy_hash,
            "decision_view": "analytics.int_job_eligibility",
        },
        "summary": {
            "pass": sum(r["status"] == "PASS" for r in records),
            "fail": sum(r["status"] == "FAIL" for r in records),
            "review": sum(r["status"] == "REVIEW" for r in records),
            "total": len(records),
        },
        "decisions": records,
    }
