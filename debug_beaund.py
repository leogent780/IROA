"""
beaund.com 디버그: POST body 캡처 후 page=1,2 직접 비교
"""
import re
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

BASE_URL = "https://beaund.com"
DRAW_URL = "https://sfre-srcs-service.snapfit.co.kr/Draw/draw_review_dependent"


def main():
    captured = {"body": b"", "cookies": {}}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = browser.new_context(
            ignore_https_errors=True,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
        )
        page = context.new_page()

        # context 레벨에서 모든 프레임의 응답 캡처
        def on_response(response):
            url = response.url
            if "snapfit" not in url and "sfre" not in url:
                return
            ct = response.headers.get("content-type", "")
            try:
                body = response.text()
            except Exception:
                return
            # review 관련 JSON 탐색
            if ("review" in body.lower() or "content" in body.lower()) and len(body) > 200:
                if body.strip().startswith(("[", "{")):
                    print(f"\n[JSON API] {url}")
                    print(f"  Preview: {body[:400]}")
                elif "draw_review_dependent" in url:
                    captured["body"] = response.request.post_data_buffer or b""

        context.on("response", on_response)

        page.goto(f"{BASE_URL}/product/detail.html?product_no=53",
                  wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(8000)

        # iframe 내부 전역변수 및 review-content 컴포넌트 탐색
        for frame in page.frames:
            if "sfre-srcs" in frame.url:
                print("\n=== iframe 내부 전역변수 (snap 관련) ===")
                keys = frame.evaluate("""() => {
                    return Object.keys(window).filter(k =>
                        k.toLowerCase().includes('snap') ||
                        k.toLowerCase().includes('review') ||
                        k.toLowerCase().includes('data')
                    );
                }""")
                print(keys)

                print("\n=== review-content 속성 ===")
                info = frame.evaluate("""() => {
                    const el = document.querySelector('review-content');
                    if (!el) return 'not found';
                    const attrs = {};
                    for (const a of el.attributes) attrs[a.name] = a.value;
                    const props = ['page', 'totalCount', 'pageSize', 'currentPage'];
                    const propVals = {};
                    for (const p of props) propVals[p] = el[p];
                    return {attrs, props: propVals, tagName: el.tagName};
                }""")
                print(info)

                print("\n=== pagination-basic 속성 ===")
                pag = frame.evaluate("""() => {
                    const el = document.querySelector('pagination-basic');
                    if (!el) return 'not found';
                    const attrs = {};
                    for (const a of el.attributes) attrs[a.name] = a.value;
                    const props = ['page', 'totalCount', 'limit'];
                    const propVals = {};
                    for (const p of props) propVals[p] = el[p];
                    return {attrs, props: propVals};
                }""")
                print(pag)
                break

        browser.close()

    print("\n완료.")


if __name__ == "__main__":
    main()
