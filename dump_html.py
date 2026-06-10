"""
페이지 HTML 구조 덤프 — 셀렉터 디버깅용
사용법: python dump_html.py --url "https://..."
"""
import argparse
from playwright.sync_api import sync_playwright

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    args = parser.parse_args()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = browser.new_context(
            ignore_https_errors=True,
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()
        page.goto(args.url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(3000)

        html = page.content()
        with open("page_dump.html", "w", encoding="utf-8") as f:
            f.write(html)
        print(f"저장 완료: page_dump.html ({len(html):,} bytes)")
        browser.close()

if __name__ == "__main__":
    main()
