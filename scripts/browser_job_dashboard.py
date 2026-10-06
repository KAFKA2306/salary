#!/usr/bin/env python3
from __future__ import annotations

import argparse
from playwright.sync_api import sync_playwright

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("base_url")
    args = parser.parse_args()
    url = args.base_url.rstrip("/") + "/"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1365, "height": 1000})
            page.goto(url)
            page.wait_for_function("document.querySelectorAll('.job-card').length === 3")
            assert page.locator(".job-card").count() == 3
            assert page.locator(".reject-card").count() == 2
            assert page.locator("body").inner_text().find("応募状態") == -1
            assert "バフェットコード" in page.locator(".job-card").first.inner_text()
            assert "基本給" in page.locator(".job-card").first.inner_text()
            assert "退職者" in page.locator("body").inner_text()

            page.locator('button[data-filter="ai"]').click()
            page.wait_for_function("document.querySelectorAll('.job-card').length === 2")
            assert page.locator(".job-card").count() == 2

            page.locator('button[data-filter="all"]').click()
            page.wait_for_function("document.querySelectorAll('.job-card').length === 3")
        finally:
            browser.close()

    print("browser job dashboard contract: PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
