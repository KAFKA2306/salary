#!/usr/bin/env python3
from pathlib import Path
import csv
import duckdb

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "warehouse" / "job_search.duckdb"
OUT = ROOT / "artifacts" / "job_ranking.csv"

def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB), read_only=True)
    rows = con.execute("select * from job_ranking order by rank").fetchall()
    cols = [d[0] for d in con.description]
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        w.writerows(rows)
    print(f"wrote {len(rows)} rows to {OUT}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
