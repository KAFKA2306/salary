# Pending job candidates

Hard gate未確定の求人を、eligibleへ混ぜずにGitHub上で継続追跡するための保管場所。

- `status: review` の求人は main のeligible件数に含めない。
- 次回の求人ファウンドリーは、mainのeligible・open PRと合わせてこのディレクトリを最初に確認する。
- hard gateをすべて一次情報で確認できた候補だけ `seeds/job_candidates.csv` と `web/job-dashboard.json` へ昇格する。
- 昇格・除外後は該当review記録を更新または削除し、理由をEvidenceに残す。
