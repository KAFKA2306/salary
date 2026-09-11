#!/usr/bin/env python3
"""Browser-level completion contract for the current compensation benchmark UI."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from playwright.sync_api import Browser, Page, Route, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data/official_compensation/transport-equipment-fy2026-salary-top20.json"
BENCHMARK_URL_SUFFIX = "/transport-equipment-fy2026-salary-top20.json"


def _load_data() -> dict[str, Any]:
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def _band(value: float, metrics: dict[str, float]) -> str:
    if value < metrics["q1"]:
        return "第1四分位未満"
    if value < metrics["median"]:
        return "第1四分位〜中央値"
    if value < metrics["q3"]:
        return "中央値〜第3四分位"
    return "第3四分位以上"


def _delta(value: float, metrics: dict[str, float]) -> str:
    delta = ((value / metrics["median"]) - 1) * 100
    return f"{delta:+.1f}%"


def _assert_fail_closed(page: Page, expected_fragment: str) -> None:
    page.goto(page.url or "about:blank")
    page.wait_for_function("document.querySelector('#company-select')?.disabled === true")
    assert page.locator("#company-result").is_hidden()
    assert expected_fragment in page.locator("#benchmark-status").inner_text()


def verify_canonical(browser: Browser, base_url: str) -> None:
    data = _load_data()
    observations = data["observations"]
    metrics = data["benchmark"]["metrics"]
    observation = observations[1]

    page = browser.new_page()
    page.goto(base_url)
    page.wait_for_function("document.querySelector('#company-select')?.options.length === 21")
    assert page.locator("#company-select option").count() == 21
    assert page.locator("#benchmark-status").inner_text() == f"{data['verified_at']}確認 / 20社"

    page.select_option("#company-select", "1")
    page.wait_for_function("document.querySelector('#company-result')?.hidden === false")

    expected = {
        "#company-name": observation["company_name"],
        "#salary-value": f"{round(observation['average_annual_salary_jpy']):,}円",
        "#salary-vs-median": _delta(observation["average_annual_salary_jpy"], metrics["average_annual_salary_jpy"]),
        "#salary-band": _band(observation["average_annual_salary_jpy"], metrics["average_annual_salary_jpy"]),
        "#age-value": f"{observation['average_age_years']}歳",
        "#age-vs-median": _delta(observation["average_age_years"], metrics["average_age_years"]),
        "#age-band": _band(observation["average_age_years"], metrics["average_age_years"]),
        "#tenure-value": f"{observation['average_tenure_years']}年",
        "#tenure-vs-median": _delta(observation["average_tenure_years"], metrics["average_tenure_years"]),
        "#tenure-band": _band(observation["average_tenure_years"], metrics["average_tenure_years"]),
        "#fiscal-year": observation["fiscal_year_end"],
    }
    for selector, value in expected.items():
        assert page.locator(selector).inner_text() == value, (selector, page.locator(selector).inner_text(), value)

    source = page.locator("#source-link")
    assert source.get_attribute("href") == observation["source_document"]["url"]
    assert source.inner_text() == (
        f"EDINET {observation['source_document']['doc_id']} / {observation['source_document']['section']}"
    )
    page.close()


def verify_fetch_failure(browser: Browser, base_url: str) -> None:
    page = browser.new_page()

    def reject(route: Route) -> None:
        route.fulfill(status=503, content_type="application/json", body="{}")

    page.route(f"**{BENCHMARK_URL_SUFFIX}", reject)
    page.goto(base_url)
    page.wait_for_function("document.querySelector('#company-select')?.disabled === true")
    assert page.locator("#company-result").is_hidden()
    assert "HTTP 503" in page.locator("#benchmark-status").inner_text()
    page.close()


def verify_missing_metrics(browser: Browser, base_url: str) -> None:
    payload = _load_data()
    del payload["benchmark"]["metrics"]["average_tenure_years"]
    page = browser.new_page()

    def malformed(route: Route) -> None:
        route.fulfill(status=200, content_type="application/json", body=json.dumps(payload, ensure_ascii=False))

    page.route(f"**{BENCHMARK_URL_SUFFIX}", malformed)
    page.goto(base_url)
    page.wait_for_function("document.querySelector('#company-select')?.disabled === true")
    assert page.locator("#company-result").is_hidden()
    assert "three-axis metrics missing" in page.locator("#benchmark-status").inner_text()
    page.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("base_url")
    args = parser.parse_args()
    base_url = args.base_url.rstrip("/") + "/"

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            verify_canonical(browser, base_url)
            verify_fetch_failure(browser, base_url)
            verify_missing_metrics(browser, base_url)
        finally:
            browser.close()
    print("browser compensation benchmark contract: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
