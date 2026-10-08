with jobs as (
    select * from {{ ref('stg_jobs') }}
)
select
    *,
    employment_type = 'permanent' as gate_permanent,
    base_salary_min_jpy >= 8000000 as gate_base_salary,
    salary_basis_verified as gate_salary_verified,
    not customer_facing as gate_no_customer_facing,
    not outsourcing as gate_no_outsourcing,
    not consulting as gate_no_consulting,
    ownership_scope in ('internal_ai','internal_data_platform','own_product') as gate_ownership,
    verified as gate_job_verified,
    coalesce((
      employment_type = 'permanent'
      and base_salary_min_jpy >= 8000000
      and salary_basis_verified
      and not customer_facing
      and not outsourcing
      and not consulting
      and ownership_scope in ('internal_ai','internal_data_platform','own_product')
      and verified
    ), false) as eligible
from jobs
