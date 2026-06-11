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

        def intercept(route):
            request = route.request
            if "draw_review_dependent" in request.url and request.method == "POST":
                buf = request.post_data_buffer or b""
                if buf and not captured["body"]:
                    captured["body"] = buf
                    print(f"POST body 캡처: {buf[:200]}")
            route.continue_()

        context.route("**/*", intercept)
        page.goto(f"{BASE_URL}/product/detail.html?product_no=53",
                  wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(6000)

        for c in context.cookies():
            captured["cookies"][c["name"]] = c["value"]
        browser.close()

    if not captured["body"]:
        print("POST body 캡처 실패")
        return

    raw = captured["body"].decode("utf-8", errors="ignore")
    print(f"\n원본 POST body:\n{raw}\n")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
        "Referer": BASE_URL,
        "Origin": BASE_URL,
        "Content-Type": "application/x-www-form-urlencoded",
    }

    for pg in [1, 2]:
        body = re.sub(r"page=\d+", f"page={pg}", raw)
        print(f"\n--- page={pg} 요청 ---")
        resp = requests.post(DRAW_URL, data=body, headers=headers,
                             cookies=captured["cookies"], timeout=15)
        print(f"상태: {resp.status_code}")
        soup = BeautifulSoup(resp.text, "html.parser")
        items = soup.select("review-item")
        print(f"review-item 개수: {len(items)}")
        if items:
            first = items[0].select_one("review-text")
            print(f"첫 번째 리뷰: {first.get_text(strip=True)[:80] if first else 'N/A'}")


if __name__ == "__main__":
    main()
