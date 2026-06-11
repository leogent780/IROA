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

        for c in context.cookies():
            captured["cookies"][c["name"]] = c["value"]
        browser.close()

    print("\n완료.")


if __name__ == "__main__":
    main()
