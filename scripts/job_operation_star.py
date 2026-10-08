"""Observed local ranking-export effects as a small operational star schema.

One fact is one job decision in one export run. This is NOT a live job
application, employer verification, or evidence of improved job-search success.
"""
from __future__ import annotations

import csv
from pathlib import Path

FACT_GRAIN = "one job decision per local export run"


def read_ranked_export(path: Path) -> dict[str, int] | None:
    """Read actual output; None means no prior snapshot (not a negative fact)."""
    if not path.exists():
        return None
    if path.stat().st_size == 0:
        return {}
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or not {"job_id", "rank"}.issubset(reader.fieldnames):
            raise ValueError("existing ranking export has no job_id/rank columns")
        ranked = {}
        for row in reader:
            job_id = row["job_id"]
            try:
                rank = int(row["rank"])
            except (ValueError, TypeError) as exc:
                raise ValueError(f"invalid ranking rank for {job_id!r}") from exc
            if not job_id or job_id in ranked or rank < 1:
                raise ValueError(f"duplicate or invalid ranked job: {job_id!r}")
            ranked[job_id] = rank
        return ranked


def build_operation_star(
    trace: dict,
    before: dict[str, int] | None,
    after: dict[str, int] | None,
    *,
    run_id: str,
    executed_at_utc: str,
    actor: str,
) -> dict:
    """Fail closed if the persisted local export contradicts dbt lineage."""
    if not run_id or not executed_at_utc or not actor:
        raise ValueError("run ID, execution time and actor are required")
    if after is None:
        raise ValueError("ranking export is missing after execution")

    decisions = trace["decisions"]
    expected = {row["job_id"]: int(row["rank"]) for row in decisions if row["status"] == "PASS"}
    if expected != after:
        raise ValueError("actual ranking export contradicts authorized PASS decisions")
    if len(decisions) != len({row["job_id"] for row in decisions}):
        raise ValueError("duplicate decision job ID")

    facts = []
    jobs = []
    for decision in decisions:
        job_id = decision["job_id"]
        authorized = decision["status"] == "PASS"
        before_state = "UNKNOWN" if before is None else (
            "RANKED" if job_id in before else "WITHHELD"
        )
        after_state = "RANKED" if job_id in after else "WITHHELD"
        previous = None if before is None else before.get(job_id)
        current = after.get(job_id)
        change = "BASELINE_UNKNOWN" if before is None else (
            "UNCHANGED" if previous == current else "CHANGED"
        )
        jobs.append({"job_id": job_id, "source_url": decision["source_url"]})
        facts.append({
            "fact_id": f"{run_id}:{decision['decision_id']}",
            "run_id": run_id,
            "job_id": job_id,
            "rule_id": decision["rule_id"],
            "decision_id": decision["decision_id"],
            "decision_status": decision["status"],
            "guard": "ALLOW" if authorized else "DENY",
            "action": decision["action"],
            "before_local_export": before_state,
            "after_local_export": after_state,
            "rank_before": previous,
            "rank_after": current,
            "execution_status": "CONFIRMED_LOCAL_EXPORT",
            "feedback": change,
            "business_outcome": "NOT_MEASURED",
            "recovery": "rebuild_from_dbt_and_recheck_export",
        })

    inputs = trace["inputs"]
    return {
        "schema_version": 1,
        "grain": FACT_GRAIN,
        "scope": "local_csv_export_only_not_web_publication_or_job_application",
        "dimensions": {
            "run": {
                "run_id": run_id,
                "executed_at_utc": executed_at_utc,
                "actor": actor,
                "source_sha256": inputs["source_sha256"],
                "ontology_sha256": inputs["ontology_sha256"],
                "decision_view": inputs["decision_view"],
            },
            "rule": {"rule_id": trace["rule_id"]},
            "jobs": jobs,
        },
        "facts": facts,
        "metrics": {
            "decision_count": len(facts),
            "allow_count": sum(row["guard"] == "ALLOW" for row in facts),
            "denied_count": sum(row["guard"] == "DENY" for row in facts),
            "confirmed_local_exports": len(facts),
            "known_changed_local_export_count": sum(row["feedback"] == "CHANGED" for row in facts),
            "business_outcome_measured_count": 0,
        },
    }
