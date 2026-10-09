# Pending job candidates

Hard gate未確定の求人は `status: review` で保持し、eligibleへ混ぜない。

- 一次情報で確定できない給与・職務条件は `seeds/job_candidates.csv` の該当欄を空欄（NULL）にし、`verified` を未確定のまま保持する。
- `evidence/pending/*.json` は調査根拠・未確認項目の正本。値を推測で埋めない。
- dbtのhard gateとdecision traceで `REVIEW` と判断した求人だけdashboardの「要確認」に出す。
- 一次情報でゲートをすべて確認できた求人だけ eligible に昇格する。明確な不適合が出た求人は FAIL にする。
- 次回調査は eligible / FAIL / REVIEW とopen PRを確認し、重複登録しない。
