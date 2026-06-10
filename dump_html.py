"""
페이지 HTML 구조 덤프 — 셀렉터 디버깅용
사용법: python dump_html.py --url "https://..."
"""
import argparse
import json
from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    args = parser.parse_args()

    api_calls = []

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

        # 모든 네트워크 요청 캡처
        def on_request(request):
            url = request.url
            if any(k in url for k in ["review", "comment", "후기", "board"]):
                api_calls.append({"type": "REQUEST", "url": url, "method": request.method})

        def on_response(response):
            url = response.url
            if any(k in url for k in ["review", "comment", "후기", "board"]):
                try:
                    body = response.text()
                    api_calls.append({"type": "RESPONSE", "url": url, "status": response.status, "body_preview": body[:500]})
                except Exception:
                    pass

        page.on("request", on_request)
        page.on("response", on_response)

        page.goto(args.url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)

        # 페이지 끝까지 스크롤 (lazy load 트리거)
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(3000)

        html = page.content()
        with open("page_dump.html", "w", encoding="utf-8") as f:
            f.write(html)
        print(f"저장 완료: page_dump.html ({len(html):,} bytes)")

        print("\n=== 리뷰 관련 네트워크 요청 ===")
        if api_calls:
            for c in api_calls:
                print(json.dumps(c, ensure_ascii=False, indent=2))
        else:
            print("리뷰 관련 API 요청 없음")

            # HTML에서 review 키워드 주변 텍스트 출력
            print("\n=== HTML 내 'review' 키워드 위치 ===")
            lower = html.lower()
            idx = 0
            count = 0
            while count < 5:
                idx = lower.find("review", idx)
                if idx == -1:
                    break
                print(f"\n[{idx}]", html[max(0, idx-100):idx+200])
                print("---")
                idx += 6
                count += 1

        browser.close()


if __name__ == "__main__":
    main()
