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

        # context 레벨에서 sfre-srcs 도메인의 모든 요청 캡처
        def on_request(request):
            url = request.url
            if "sfre-srcs" in url:
                try:
                    pb = request.post_data_buffer
                    pd = pb.decode("utf-8", errors="ignore") if pb else ""
                except Exception:
                    pd = ""
                print(f"\n[REQUEST] {request.method} {url}")
                if pd:
                    print(f"  POST: {pd[:200]}")

        def on_response(response):
            url = response.url
            if "sfre-srcs" not in url:
                return
            try:
                body = response.text()
            except Exception:
                return
            if body.strip().startswith(("[", "{")):
                print(f"\n[JSON RESPONSE] {url}")
                print(f"  {body[:400]}")
            if "draw_review_dependent" in url and not captured["body"]:
                captured["body"] = response.request.post_data_buffer or b""

        context.on("request", on_request)
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

                print("\n=== snapData 내용 ===")
                snap = frame.evaluate("""() => {
                    try {
                        return JSON.stringify(window.snapData).slice(0, 1000);
                    } catch(e) { return String(e); }
                }""")
                print(snap)

                print("\n=== snapApp.request 메서드 ===")
                req_methods = frame.evaluate("""() => {
                    try {
                        const r = window.snapApp.request;
                        return Object.keys(r).map(k => k + ':' + typeof r[k]);
                    } catch(e) { return String(e); }
                }""")
                print(req_methods)

                print("\n=== 리뷰 API 직접 호출 시도 (page=2) ===")
                result = frame.evaluate("""async () => {
                    try {
                        const d = window.snapData;
                        const url = d.serverUrl + '/Review/list';
                        const params = new URLSearchParams({
                            store_id: d.storeId,
                            widget_id: d.widgetId,
                            item_id: d.itemId,
                            page: 2,
                            page_size: 10,
                        });
                        const resp = await fetch(url + '?' + params);
                        const text = await resp.text();
                        return text.slice(0, 500);
                    } catch(e) { return String(e); }
                }""")
                print(result)
                break

        browser.close()

    print("\n완료.")


if __name__ == "__main__":
    main()
