with eligible as (
    select * from {{ ref('int_job_eligibility') }} where eligible
),
scored as (
    select
      *,
      round(
        technical_ownership / 5.0 * 25
        + implementation_ratio / 5.0 * 20
        + ai_production / 5.0 * 15
        + cross_company_scope / 5.0 * 15
        + career_fit / 5.0 * 15
        + workstyle_fit / 5.0 * 10
        - case when short_term_sales_kpi then 8 else 0 end
        - case when management_heavy then 5 else 0 end
      , 1) as score
    from eligible
)
select
  row_number() over(order by score desc, base_salary_min_jpy desc) as rank,
  job_id, company_name, title, score,
  base_salary_min_jpy, base_salary_max_jpy,
  remote_mode, location, source_url
from scored
order by rank
