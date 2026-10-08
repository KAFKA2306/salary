[▶ ビューを開く](https://salary-job-view.vercel.app)

# salary → Job Search Decision Platform

このrepositoryの主用途を、給与調査archiveから**自分専用の就活意思決定基盤**へ変更する。

旧CSV / Notebook / official compensation dataは provenance を失わないため archive lane として保持する。新しいcurrent laneでは、求人を「企業名の一覧」ではなく、**求人・給与・働き方・職務所有範囲・証拠を結んだOntology**として扱う。

## Hard gates

求人は以下をすべて満たした場合だけ ranking 対象にする。

1. 正社員
2. 固定残業代を除いた基本年収下限が 8,000,000 円以上
3. 外部顧客への伴走、商談、要件定義、導入支援、コンサルを主業務に含まない
4. 受託開発ではない
5. 社内AI / 社内データ基盤 / 自社プロダクトのいずれかを所有する
6. 給与内訳と職務内容に根拠URLがある

「想定年収800万円」でも固定残業込みなら fail。給与内訳が不明なら pass にせず REVIEW にする。

## Architecture

```text
source evidence
   ↓
Airflow
   ├─ ingest / snapshot
   ├─ ontology validation
   ├─ dbt seed
   ├─ dbt build
   └─ publish ranking
        ↓
PostgreSQL 15 / dbt
   ├─ staging
   ├─ hard-gate eligibility
   └─ scored ranking
        ↓
decision surface
```

### Ontology

`ontology/job_search.yml`

中心entity:
- Company
- JobPosting
- Compensation
- WorkStyle
- RoleProfile
- Evidence
- ExitEntry
- FitAssessment

重要なrelation:
- Company OFFERS JobPosting
- JobPosting HAS_COMPENSATION Compensation
- JobPosting HAS_ROLE RoleProfile
- Evidence SUPPORTS JobPosting / Compensation / RoleProfile
- ExitEntry INFORMS Company
- FitAssessment EVALUATES JobPosting

### dbt

`dbt_project.yml` と `models/`

dbtの責務は判断ロジックをSQLとして固定すること。

- `stg_jobs`: raw seedの型・表現を正規化
- `int_job_eligibility`: hard gateを1件ずつ判定
- `job_ranking`: 通過求人だけを重み付きscoreで並べる

### Airflow

`dags/job_search_pipeline.py`

DAG:
`validate ontology → dbt seed → dbt build → export ranking`

外部サイト取得はsource adapterとして後付けし、ranking logicと分離する。取得失敗時に古い値をcurrentとして昇格させない。

## Scoring

Hard gateを通過した求人だけ100点満点で比較する。

- 自社データ/AI基盤の所有: 25
- 技術実装・設計比率: 20
- AI/ML/LLMの本番利用: 15
- 全社横断・影響範囲: 15
- 経歴接続: 15
- 働き方: 10

短期売上KPI責任、固定残業の大きさ、管理職専任は減点情報として保持する。

## Local run

PostgreSQL 15 はDocker Composeでローカル起動する。外部クラウド契約は不要。

```bash
docker compose up -d postgres
python -m pip install -r requirements-job-search.txt
python scripts/validate_job_ontology.py
dbt seed --profiles-dir config/dbt
dbt build --profiles-dir config/dbt
python scripts/export_job_rankings.py
```

接続先は `JOB_SEARCH_DB_HOST` / `JOB_SEARCH_DB_PORT` / `JOB_SEARCH_DB_NAME` /
`JOB_SEARCH_DB_USER` / `JOB_SEARCH_DB_PASSWORD` で上書きできる。未指定時は
Composeの `job_search@localhost:5432/job_search` を使う。

生成物:
- PostgreSQL schema `analytics`
- `artifacts/job_ranking.csv`

## Current seed

`seeds/job_candidates.csv` は探索中求人のcurrent入力用。給与や職務条件が未確認なら、推測で埋めず `verified=false` とする。

`seeds/exit_entries.csv` は退職者・元社員の公開情報。企業単位で求人カードへ紐付けるが、hard gateやランキング点数には使わない。見つからない場合も `status=not_found` として探索済みであることだけ残す。

## Archive lane

旧給与調査資産は引き続きarchiveとして保持する。
`archive-manifest.json` と `scripts/archive_integrity.py` の整合性ルールは壊さない。

## Principle

このrepositoryは「高そうな会社リスト」ではなく、**自分が応募すべき求人を根拠付きで機械判定するシステム**にする。

## Operational ontology

[Project ontology](ontology/project.yaml) maps domain objects, relationships, evidence rules, guarded actions and outcome metrics to the shared [Causal–Evidence Core](https://github.com/KAFKA2306/know/blob/main/ontology/causal-evidence-core.yaml). The manifest documents the intended decision boundary; it does not by itself implement or authorize new real-world actions.

## Decision lineage (runnable)

`python scripts/export_job_rankings.py` writes `artifacts/job_decision_trace.json` from the **existing dbt `int_job_eligibility` decisions**. For every job it records the PASS/FAIL/UNKNOWN result of each hard gate, the overall PASS/FAIL/REVIEW outcome, source URL (when supplied), ranking action and rank. The input CSV and ontology are identified by SHA-256; the output is deterministic for identical inputs.

A reported job URL is **not** proof of live re-verification. An unavailable input or unresolved gate cannot authorize ranking. A verified hard-gate failure yields FAIL, missing evidence with no known failures yields REVIEW. A disagreement between dbt, the published ranking and the trace fails the export.

GitHub Actions runs actual gate/trace tests and retains the generated trace as a 30-day run artifact. No applications are sent, and the published dashboard format stays unchanged. This is an execution trace, **not** a measured improvement in job-search success.
