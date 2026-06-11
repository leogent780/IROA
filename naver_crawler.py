"""
네이버 스마트스토어 리뷰 크롤러 (Playwright 기반)
사용법:
    pip install playwright
    python -m playwright install chromium
    python naver_crawler.py --product_no 13197800272 --out naver_reviews.csv
"""
import argparse
import csv
import json
import time
from playwright.sync_api import sync_playwright

STORE_URL = "https://smartstore.naver.com/vilarstore/products/{product_no}#REVIEW"
REVIEW_API = "https://smartstore.naver.com/i/v1/reviews/paged-reviews"
PAGE_SIZE = 20


def fetch_all_reviews(product_no: str, max_pages: int) -> list[dict]:
    all_reviews = []
    api_results = []

    with sync_playwright() as p:
        import os, shutil
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        ]
        chrome_exe = next((p for p in chrome_paths if os.path.exists(p)), None)

        browser = p.chromium.launch(
            headless=False,
            executable_path=chrome_exe,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--start-maximized",
            ],
        )
        context = browser.new_context(
            ignore_https_errors=True,
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="ko-KR",
            timezone_id="Asia/Seoul",
            viewport={"width": 1280, "height": 800},
            extra_http_headers={
                "Accept-Language": "ko-KR,ko;q=0.9",
            },
        )
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['ko-KR','ko']});
            window.chrome = {runtime: {}};
        """)
        page = context.new_page()

        # Intercept review API responses
        def on_response(response):
            if "paged-reviews" in response.url:
                try:
                    data = response.json()
                    api_results.append(data)
                    print(f"  [API] 응답 수신: {response.url[:80]}")
                except Exception:
                    pass

        page.on("response", on_response)

        url = STORE_URL.format(product_no=product_no)
        print(f"페이지 로드 중: {url}")
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(4000)

        # 리뷰 탭 클릭
        for sel in [
            "a[href*='REVIEW']",
            "[data-type='REVIEW']",
            "li:has-text('리뷰')",
            "button:has-text('리뷰')",
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

        page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
        page.wait_for_timeout(5000)

        # Collect page 1 reviews from intercepted API
        if api_results:
            first = api_results[0]
            total = first.get("totalElements", 0)
            print(f"총 리뷰 수: {total}건")
            for item in first.get("contents", []):
                all_reviews.append(_parse_item(item))

            # Get auth cookies/headers for subsequent pages
            cookies = context.cookies()
            cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in cookies)

            # Capture headers from first review request
            captured_headers = {}

            def on_request(request):
                if "paged-reviews" in request.url:
                    captured_headers.update(dict(request.headers))

            page.on("request", on_request)

            # Navigate more pages via API using fetch within the page context
            for page_num in range(2, max_pages + 1):
                if len(all_reviews) >= total:
                    print("전체 수집 완료")
                    break
                print(f"[{page_num}] 페이지 수집 중...")
                params = (
                    f"reviewType=PRODUCT&productNo={product_no}"
                    f"&page={page_num}&pageSize={PAGE_SIZE}"
                    f"&sortType=REVIEW_CREATE_DATE_DESC"
                )
                result = page.evaluate(f"""async () => {{
                    const resp = await fetch(
                        '{REVIEW_API}?{params}',
                        {{credentials: 'include'}}
                    );
                    return await resp.json();
                }}""")
                items = result.get("contents", [])
                if not items:
                    print("  리뷰 없음 — 종료")
                    break
                for item in items:
                    all_reviews.append(_parse_item(item))
                print(f"  수집: {len(items)}건 (누계 {len(all_reviews)}건 / 전체 {total}건)")
                time.sleep(0.5)
        else:
            print("리뷰 API 응답을 찾지 못했습니다.")
            print(f"페이지 타이틀: {page.title()}")

        browser.close()

    return all_reviews


def _parse_item(item: dict) -> dict:
    return {
        "author": item.get("writerMemberSummary", {}).get("nickName", ""),
        "rating": item.get("reviewScore", ""),
        "date": (item.get("createDate") or "")[:10],
        "content": item.get("reviewContent", ""),
    }


def save_csv(reviews: list[dict], path: str):
    if not reviews:
        print("수집된 리뷰가 없습니다.")
        return
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["author", "rating", "date", "content"])
        writer.writeheader()
        writer.writerows(reviews)
    print(f"저장 완료: {path} ({len(reviews)}건)")


def main():
    parser = argparse.ArgumentParser(description="네이버 스마트스토어 리뷰 크롤러")
    parser.add_argument("--product_no", required=True)
    parser.add_argument("--out", default="naver_reviews.csv")
    parser.add_argument("--pages", type=int, default=50)
    args = parser.parse_args()

    print(f"네이버 스마트스토어 상품 #{args.product_no} 리뷰 수집 시작")
    reviews = fetch_all_reviews(args.product_no, max_pages=args.pages)
    save_csv(reviews, args.out)


if __name__ == "__main__":
    main()
