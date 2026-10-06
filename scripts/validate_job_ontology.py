#!/usr/bin/env python3
from pathlib import Path
import sys
import yaml

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "ontology" / "job_search.yml"

REQUIRED_ENTITIES = {
    "Company", "JobPosting", "Compensation", "WorkStyle",
    "RoleProfile", "Evidence", "FitAssessment", "Application",
}
REQUIRED_GATES = {
    "employment_type", "base_salary_min_jpy", "customer_facing",
    "outsourcing", "consulting", "allowed_ownership_scope",
    "require_salary_basis_verified", "require_verified_job",
}

def main() -> int:
    data = yaml.safe_load(PATH.read_text(encoding="utf-8"))
    entities = set(data.get("entities", {}))
    gates = data.get("hard_gates", {})
    missing_entities = REQUIRED_ENTITIES - entities
    missing_gates = REQUIRED_GATES - set(gates)
    errors = []
    if missing_entities:
        errors.append(f"missing entities: {sorted(missing_entities)}")
    if missing_gates:
        errors.append(f"missing hard gates: {sorted(missing_gates)}")
    if gates.get("base_salary_min_jpy") != 8_000_000:
        errors.append("base salary hard gate must be exactly 8,000,000 JPY")
    if gates.get("customer_facing") is not False:
        errors.append("customer_facing hard gate must be false")
    if errors:
        print("\n".join(f"ERROR: {e}" for e in errors), file=sys.stderr)
        return 1
    print("job ontology OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
