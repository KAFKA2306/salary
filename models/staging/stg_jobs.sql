with source as (
    select * from {{ ref('job_candidates') }}
)
select
    job_id,
    company_name,
    title,
    lower(employment_type) as employment_type,
    cast(base_salary_min_jpy as bigint) as base_salary_min_jpy,
    cast(base_salary_max_jpy as bigint) as base_salary_max_jpy,
    cast(fixed_overtime_annual_jpy as bigint) as fixed_overtime_annual_jpy,
    cast(total_salary_min_jpy as bigint) as total_salary_min_jpy,
    cast(salary_basis_verified as boolean) as salary_basis_verified,
    lower(ownership_scope) as ownership_scope,
    cast(customer_facing as boolean) as customer_facing,
    cast(outsourcing as boolean) as outsourcing,
    cast(consulting as boolean) as consulting,
    remote_mode,
    location,
    cast(fixed_overtime_hours as integer) as fixed_overtime_hours,
    cast(data_platform_depth as integer) as data_platform_depth,
    cast(implementation_ratio as integer) as implementation_ratio,
    cast(ai_production as integer) as ai_production,
    cast(cross_company_scope as integer) as cross_company_scope,
    cast(career_fit as integer) as career_fit,
    cast(manufacturing_bridge as integer) as manufacturing_bridge,
    cast(technical_ownership as integer) as technical_ownership,
    cast(workstyle_fit as integer) as workstyle_fit,
    cast(short_term_sales_kpi as boolean) as short_term_sales_kpi,
    cast(management_heavy as boolean) as management_heavy,
    cast(verified as boolean) as verified,
    source_url
from source
