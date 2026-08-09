# salary

`salary`は、企業の給与・残業・年齢別給与に関する公開Web情報を探索した、**2024年2月時点のNotebook・CSV snapshot**です。

現在稼働している給与data収集基盤、継続更新される企業比較service、公式統計databaseではありません。repository内の数値を現在の給与水準や企業評価へ使用しないでください。

## 現在の状態

| 項目 | 状態 |
|---|---|
| 主な作業時期 | 2024年2月 |
| 継続収集workflow | なし |
| 定期更新 | なし |
| archive integrity CI | あり |
| 再現可能な取得・分析環境 | 未整備 |
| data source・取得日時の正準台帳 | `archive-manifest.json`。不明値は`UNKNOWN` |
| 現在値としての利用 | 不可 |

## repositoryに残っているもの

| file | 内容 |
|---|---|
| `archive-manifest.json` | 全主要artifactの役割、Git blob SHA、size、利用状態、重複分類 |
| `scripts/archive_integrity.py` | manifest、CSV、Notebook、重複、hashを検証する標準libraryのみの監査CLI |
| `IR.ipynb` | 企業情報・給与情報を探索したNotebook |
| `ticker.ipynb` | 上場企業listを加工したNotebook |
| `visual00IR-TS.ipynb` | 取得dataの可視化試作 |
| `IR-TS_concat.csv` | 当時の処理結果を結合したCSV snapshot |
| `note.md` | 調査時のURL、HTML selector、作業memo |

Notebookには実行済みcell outputが含まれます。これらは取得時点、欠損処理、企業identity、source改訂を十分に追跡できる正準dataではありません。

## archive integrityの確認

```bash
python scripts/archive_integrity.py --report archive-report.json
python -m unittest discover -s tests -v
```

監査は次を確認します。

- CSV、Notebook、memo、legacy scriptがmanifestへ登録されていること
- 現在のfile contentから計算したGit blob SHAとsizeが台帳と一致すること
- 同一内容の別名fileが分類されていること
- CSVのencoding、delimiter、列、行数、完全重複行、空列
- Notebookのcell数、output数、kernel、実行順、秘密情報候補、個人絶対path候補
- 各artifactのSHA-256を含む`archive-report.json`の生成

`SemiCon.csv`と`results.csv`は同一Git blobです。生成意図を復元できないため`unresolved`として登録し、別datasetとして二重集計してはいけません。

新しいartifactを追加または既存artifactを変更した場合は、`archive-manifest.json`のGit blob SHAとsizeも更新します。CIは未登録file、hash差分、未分類の同一内容fileを失敗させます。

## 当時の試行

主な試行は次のとおりです。

- 企業名から第三者口コミsiteを検索する
- HTMLから給与・残業・年齢別給与らしき値を抽出する
- 上場企業listとtickerを加工する
- CSVへ保存し、Notebookで比較・可視化する

この説明は残存codeの内容を示すものであり、現在も取得できること、利用条件を満たすこと、値が正確であることを保証しません。

## 再現できない主な理由

- Notebookに`C:\Users\...`など個人Windows環境の絶対pathが残っています。
- package version、Python version、lock fileが定義されていません。
- scraping対象のHTML構造とselectorは変更される可能性があります。
- request間隔、retry、rate limit、robots、利用規約への対応が正準化されていません。
- raw response、取得日時、source URL、parser version、error logを保持するpipelineがありません。
- 同名企業、法人格変更、持株会社化、上場廃止などのidentity解決がありません。
- Notebook outputとCSVの生成関係を機械的に検証できません。

## dataを読む際の制約

### 鮮度

repository内のdataは2024年2月頃の作業snapshotです。現在値ではありません。

### source

一部は第三者口コミsite由来の値を探索しています。企業の公式開示、法定開示、統計機関の一次dataとは性質が異なります。

### 比較可能性

企業ごとに回答者数、職種、年齢、雇用形態、集計期間、欠損が異なる可能性があります。単純な横比較やrankingには使用できません。

### 単位と定義

給与が年収・月収・総報酬のどれか、残業時間の集計期間、税込・税引後、平均・中央値などの定義が正準化されていません。

### Notebook output

実行済みoutputは調査時の観測結果であり、現在のWeb pageや最新値を示しません。再実行して同じ結果になる保証もありません。

## セキュリティと利用条件

- third-party siteを再取得する前に、現在の利用規約、robots、著作権、database権、rate limitを確認してください。
- browser cookie、login情報、API key、個人情報をNotebookへ保存しないでください。
- 個人単位の投稿や識別可能な情報を収集・公開しないでください。
- CSVやNotebook outputを外部公開する場合、sourceの再配布条件を確認してください。
- 不明なNotebookを信頼済みとして開かず、codeとoutputを確認してください。

## 再開する場合

給与分析を再構築する場合は、まず一次情報を正準にします。

1. 有価証券報告書の平均年間給与、平均年齢、平均勤続年数
2. 企業の公式採用情報・報酬制度
3. 政府統計など定義と調査方法が公開されたdata
4. source URL、書類ID、対象期間、取得日時、単位、revisionを持つraw table
5. raw、normalized、derived metrics、visualizationを分離したpipeline
6. 法人番号・証券code・EDINET codeによる企業identity管理
7. parser test、schema test、data freshness test、CI

現行の企業開示・EDINET基盤へ統合する場合は、`KAFKA2306/investor`を候補とします。manifest上の`UNKNOWN_PROVENANCE` artifactを自動投入せず、source再取得、schema migration、人手reviewを必須にします。

## 既知の制約

- 現在のcodeを一般環境で再実行する手順はありません。
- dataの完全性、正確性、最新性、比較可能性を保証しません。
- 就職・転職・報酬交渉・投資判断の根拠として使用できる状態ではありません。
- このrepositoryは履歴保存用の研究snapshotであり、現行製品ではありません。
- manifestは既知の来歴を推測で補完せず、不明項目を`UNKNOWN`として保持します。

## 関連

- README監査の正準: `KAFKA2306/com` Issue #3
- archive integrity: Issue #3
- 現行の企業data基盤候補: `KAFKA2306/investor`
