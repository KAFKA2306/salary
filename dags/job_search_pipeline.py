from __future__ import annotations

from datetime import datetime
from airflow import DAG
from airflow.operators.bash import BashOperator

ROOT = "/opt/airflow/repo"

with DAG(
    dag_id="job_search_decision_pipeline",
    start_date=datetime(2026, 10, 1),
    schedule="@daily",
    catchup=False,
    tags=["job-search", "dbt", "ontology"],
) as dag:
    validate_ontology = BashOperator(
        task_id="validate_ontology",
        bash_command=f"cd {ROOT} && python scripts/validate_job_ontology.py",
    )

    dbt_seed = BashOperator(
        task_id="dbt_seed",
        bash_command=f"cd {ROOT} && dbt seed --profiles-dir config/dbt",
    )

    dbt_build = BashOperator(
        task_id="dbt_build",
        bash_command=f"cd {ROOT} && dbt build --profiles-dir config/dbt",
    )

    export_ranking = BashOperator(
        task_id="export_ranking",
        bash_command=f"cd {ROOT} && python scripts/export_job_rankings.py",
    )

    validate_ontology >> dbt_seed >> dbt_build >> export_ranking
