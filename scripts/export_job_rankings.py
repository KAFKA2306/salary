#!/usr/bin/env python3
from pathlib import Path
import csv
import json
import duckdb

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "warehouse" / "job_search.duckdb"
CSV_OUT = ROOT / "artifacts" / "job_ranking.csv"
JSON_OUT = ROOT / "artifacts" / "job_dashboard.json"

GATE_LABELS = {
    "gate_permanent": "正社員ではない",
    "gate_base_salary": "固定残業を除く基本給が800万円未満",
    "gate_salary_verified": "給与内訳が未確認",
    "gate_no_customer_facing": "顧客伴走を含む",
    "gate_no_outsourcing": "受託開発を含む",
    "gate_no_consulting": "コンサル業務を含む",
    "gate_ownership": "自社AI・社内データ基盤・自社プロダクト外",
    "gate_job_verified": "求人条件が未検証",
}

def fetch_dicts(con, sql):
    cursor = con.execute(sql)
    columns = [item[0] for item in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]

def main() -> int:
    CSV_OUT.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB), read_only=True)
    ranking = fetch_dicts(con, """
        select
          r.rank, r.job_id, r.company_name, r.title, r.score,
          r.base_salary_min_jpy, r.base_salary_max_jpy,
          e.total_salary_min_jpy, e.fixed_overtime_annual_jpy,
          e.fixed_overtime_hours, r.remote_mode, r.location, r.source_url,
          e.ownership_scope, e.data_platform_depth, e.implementation_ratio,
          e.ai_production, e.cross_company_scope, e.career_fit,
          e.manufacturing_bridge, e.technical_ownership, e.workstyle_fit,
          e.short_term_sales_kpi, e.management_heavy
        from job_ranking r
        join int_job_eligibility e using (job_id)
        order by r.rank
    """)
    exit_entries = fetch_dicts(con, """
        select
          exit_entry_id, company_name, job_id, kind, author, former_role,
          published_at, relevance, summary, implication, source_url, status
        from exit_entries
        order by company_name, exit_entry_id
    """)
    exit_by_company = {}
    for entry in exit_entries:
        exit_by_company.setdefault(entry["company_name"], []).append(entry)

    rejected = fetch_dicts(con, """
        select
          job_id, company_name, title,
          base_salary_min_jpy, base_salary_max_jpy,
          total_salary_min_jpy, fixed_overtime_annual_jpy, fixed_overtime_hours,
          remote_mode, location, source_url,
          gate_permanent, gate_base_salary, gate_salary_verified,
          gate_no_customer_facing, gate_no_outsourcing, gate_no_consulting,
          gate_ownership, gate_job_verified
        from int_job_eligibility
        where not eligible
        order by company_name, title
    """)

    if ranking:
        with CSV_OUT.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(ranking[0]))
            writer.writeheader()
            writer.writerows(ranking)
    else:
        CSV_OUT.write_text("", encoding="utf-8")

    for row in rejected:
        row["failed_gates"] = [label for gate, label in GATE_LABELS.items() if row.get(gate) is False]
        for gate in GATE_LABELS:
            row.pop(gate, None)

    for row in ranking + rejected:
        row["exit_entries"] = exit_by_company.get(row["company_name"], [])

    dashboard = {
        "policy": {
            "base_salary_floor_jpy": 8_000_000,
            "salary_excludes_fixed_overtime": True,
            "customer_facing_allowed": False,
            "allowed_ownership_scope": ["internal_ai", "internal_data_platform", "own_product"],
        },
        "summary": {
            "eligible_count": len(ranking),
            "rejected_count": len(rejected),
            "top_base_salary_min_jpy": max((row["base_salary_min_jpy"] for row in ranking), default=0),
            "remote_friendly_count": sum(row["remote_mode"] in {"full_remote", "remote", "hybrid"} for row in ranking),
        },
        "eligible": ranking,
        "rejected": rejected,
    }
    JSON_OUT.write_text(json.dumps(dashboard, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(ranking)} ranked jobs to {CSV_OUT}")
    print(f"wrote dashboard with {len(rejected)} rejected jobs to {JSON_OUT}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
