"""네이버 스마트스토어 리뷰 API 헤더/쿠키 캡처"""
import json
from playwright.sync_api import sync_playwright

URL = "https://smartstore.naver.com/vilarstore/products/13197800272#REVIEW"

def main():
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

        captured = {}

        def on_request(request):
            if "paged-reviews" in request.url:
                captured["url"] = request.url
                captured["headers"] = dict(request.headers)
                print(f"\n[리뷰 API 요청 발견]\nURL: {request.url}")
                print("Headers:", json.dumps(dict(request.headers), indent=2, ensure_ascii=False))

        page.on("request", on_request)

        print(f"페이지 로드 중: {URL}")
        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(3000)

        # 리뷰 탭 클릭 시도
        for sel in [
            "a[href*='REVIEW']",
            "[data-type='REVIEW']",
            "li:has-text('리뷰')",
            "button:has-text('리뷰')",
            "a:has-text('리뷰')",
            "[class*='review'] a",
        ]:
            try:
                el = page.locator(sel).first
                if el.is_visible(timeout=2000):
                    print(f"리뷰 탭 클릭: {sel}")
                    el.click()
                    page.wait_for_timeout(3000)
                    break
            except Exception:
                continue

        # 스크롤해서 리뷰 영역 활성화
        page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
        page.wait_for_timeout(5000)

        # 쿠키 출력
        cookies = {c["name"]: c["value"] for c in context.cookies()}
        print(f"\n쿠키 수: {len(cookies)}")
        print("쿠키 키:", list(cookies.keys()))

        browser.close()

if __name__ == "__main__":
    main()
