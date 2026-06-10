"""
페이지 HTML 구조 덤프 — 셀렉터 디버깅용
사용법: python dump_html.py --url "https://..."
"""
import argparse
from playwright.sync_api import sync_playwright

REVIEW_TAB_SELECTORS = [
    "a[href*='review']",
    "li a[onclick*='review']",
    ".review_tab",
    "#review_tab",
    "a:text('상품후기')",
    "a:text('리뷰')",
    "a:text('Review')",
    "[class*='tab'] a:text('후기')",
    "[class*='tab'] a:text('리뷰')",
]

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

        # 리뷰 탭 클릭 시도
        clicked = False
        for sel in REVIEW_TAB_SELECTORS:
            try:
                el = page.locator(sel).first
                if el.is_visible(timeout=2000):
                    print(f"리뷰 탭 클릭: {sel}")
                    el.click()
                    page.wait_for_timeout(3000)
                    clicked = True
                    break
            except Exception:
                continue

        if not clicked:
            print("리뷰 탭 자동 클릭 실패 — 탭 없이 덤프")

        html = page.content()
        with open("page_dump.html", "w", encoding="utf-8") as f:
            f.write(html)
        print(f"저장 완료: page_dump.html ({len(html):,} bytes)")

        # 페이지에서 탭 관련 요소 목록 출력 (디버깅용)
        print("\n=== 탭/메뉴 관련 요소 ===")
        tabs = page.locator("ul li a, .tab a, [class*='tab'] a").all()
        for t in tabs[:20]:
            try:
                print(f"  [{t.get_attribute('href') or ''}] {t.inner_text().strip()[:50]}")
            except Exception:
                pass

        browser.close()

if __name__ == "__main__":
    main()
