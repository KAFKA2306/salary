# salary

[![Archive integrity](https://github.com/KAFKA2306/salary/actions/workflows/archive-integrity.yml/badge.svg)](https://github.com/KAFKA2306/salary/actions/workflows/archive-integrity.yml)

このrepositoryには、性質の異なる2つのlaneがあります。**混ぜて使いません。**

1. **verified official observations** — `data/official_compensation/` に置く一次資料ベースのcurrent観測。
2. **2024-02 research archive** — 第三者Web情報を探索したNotebook / CSV snapshot。現在値として利用不可。

継続収集databaseや企業ランキングserviceではありません。

## Verified official observations

currentの正準データは `data/official_compensation/transport-equipment-fy2026-salary-top20.json` です。

2026年3月期の「輸送用機器」上場企業から平均年間給与が非欠損の企業を候補抽出し、給与上位20社について有価証券報告書の「提出会社の状況」へ戻って、従業員数、平均年齢、平均勤続年数、平均年間給与を同じ範囲で再確認しています。各観測はEDINET書類IDと一次資料URLを保持します。法人番号は未確認なのでnullのままです。

この20社は**輸送用機器業界全体の代表標本ではありません**。平均年間給与上位20社の比較群です。正準データ内の比較値は、この20社から再計算した四分位と中央値であり、業界全体の中央値として解釈しません。

`web/` の先頭では、このcurrent正準データから会社を1社選び、次を確認できます。

- 平均年間給与
- 比較群中央値との差
- 比較群の四分位上の位置
- 平均年齢
- 平均勤続年数
- 対象年度
- EDINET一次資料

データが欠ける場合は古い値やarchiveへfallbackせず、読み込み失敗を明示します。

2024 archiveの値、連結従業員数、子会社の給与値をcurrent比較へ混在させません。候補抽出用のbulk値と一次資料原文が異なる場合は一次資料を優先します。

## 2024 research archive

`archive-manifest.json` がarchive artifactの正準台帳です。各artifactについてpath、Git blob SHA、size、role、利用statusを保持し、分からないprovenanceは推測せず`UNKNOWN`のままにします。

CIが証明するのは**archiveの整合性**です。元の給与値が正しい、現在も有効、企業間で比較可能、という意味ではありません。

### 信頼できること

- manifest登録artifactの現在のGit blob SHA / size
- `ARCHIVE_ONLY` / `UNKNOWN_PROVENANCE`などの利用status
- manifestとtracked artifactが一致していること
- Notebook内のcredential候補・個人絶対pathなどの監査結果
- 同一blobが別名で存在する場合のduplicate classification

### 信頼できないこと

- 2024 snapshotを現在の給与水準として使うこと
- provenance不明CSVを一次情報や正準datasetとみなすこと
- archive integrity PASSをdata accuracyの証明とみなすこと
- 定義・年度・対象者が異なる値をそのままrankingすること

`SemiCon.csv` と `results.csv` は同一Git blobです。historical notebook側には`results.csv`参照が残る一方、producer intentを復元できないため、現時点では`unresolved`として両方を保持し、別datasetとして二重集計しません。

## Static decision surface / archive explorer

`web/` はbackend・database・live scrapingなしのstatic surfaceです。

先頭のcurrent報酬比較は `data/official_compensation/transport-equipment-fy2026-salary-top20.json` だけを使います。その下のarchive explorerは `archive-manifest.json` 登録済みartifactだけを対象にし、Pyodide Web WorkerでPythonのinspection logicを実行します。

- currentとarchiveを別sectionで表示する
- `UNKNOWN_PROVENANCE` / `ARCHIVE_ONLY`をcurrent値として集計しない
- duplicate blobを別datasetとして数えない
- archive側は2024年snapshotであることを明示する

GitHub Pagesの公開serviceを前提にはしていません。CI内でstatic buildとlocal HTTP smokeを検証します。

## Verification

```bash
python -m unittest discover -s tests -v
python scripts/archive_integrity.py --report archive-report.json
```

GitHub Actionsは以下を検証します。

- auditor / testsのcompile
- archive manifest / hash / duplicate / Notebook security audit
- official observation regression tests
- current報酬比較用JSONを含むstatic site build + local HTTP smoke
- archive explorer build + local HTTP smoke
- generated residueを除去したclean checkout

## Structure

```text
data/official_compensation/        verified official observations
archive-manifest.json              2024 archive authority
*.csv / *.ipynb                    preserved research artifacts
scripts/archive_integrity.py       repository-side archive audit
scripts/browser_archive_inspection.py
web/                               current decision surface + archive explorer
tests/                             current/archive boundary and regression checks
```

## Rules for future work

- archiveの不明値を後付け推定しない
- archiveをcurrent dataへ自動昇格させない
- current dataは一次資料から再取得し、source / period / unit / identity / verified_atを持たせる
- observed facts、derived comparison、interpretationを分離する
- 比較群を業界全体と誤認させない
- current data取得失敗時にarchiveや根拠のないdefaultへfallbackしない
- duplicateや不要artifactは証拠を確認してから削除し、削除仮説が外れたら戻す
- 一時的な作業状態はREADMEへ複製せずIssuesで管理する

## Active work

- Issue #5: 一次情報ベースの報酬benchmark検証
- Issue #16: repository simplification

https://github.com/KAFKA2306/salary/issues
