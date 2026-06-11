"""
beaund.com (Snapfit 리뷰 시스템) 크롤러
사용법:
    pip install requests playwright beautifulsoup4
    python -m playwright install chromium
    python beaund_crawler.py --product_no 53 --out beaund_reviews.csv --pages 30
"""
import argparse
import csv
import time
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

DRAW_URL = "https://sfre-srcs-service.snapfit.co.kr/Draw/draw_review_dependent"
BASE_URL = "https://beaund.com"


def get_post_body_and_cookies(product_no: int) -> tuple[dict, dict]:
    """Playwright로 페이지 로드 후 draw_review_dependent POST body와 쿠키 캡처"""
    post_body = {}
    cookies = {}

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

        def on_request(request):
            if "draw_review_dependent" in request.url and request.method == "POST":
                raw = request.post_data or ""
                for pair in raw.split("&"):
                    if "=" in pair:
                        k, v = pair.split("=", 1)
                        post_body[k] = v

        page.on("request", on_request)

        url = f"{BASE_URL}/product/detail.html?product_no={product_no}"
        print(f"페이지 로드 중: {url}")
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)

        # 쿠키 수집
        for c in context.cookies():
            cookies[c["name"]] = c["value"]

        browser.close()

    return post_body, cookies


def fetch_review_html(post_body: dict, cookies: dict, page_num: int) -> str:
    data = dict(post_body)
    data["page"] = str(page_num)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
        "Referer": BASE_URL,
        "Origin": BASE_URL,
        "Content-Type": "application/x-www-form-urlencoded",
    }
    resp = requests.post(DRAW_URL, data=data, headers=headers, cookies=cookies, timeout=15)
    resp.raise_for_status()
    return resp.text


def parse_reviews_from_html(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    reviews = []

    for item in soup.select("review-item"):
        content_el = item.select_one("review-text")
        content = content_el.get_text(strip=True) if content_el else ""
        if not content:
            continue

        rating_el = item.select_one("review-rating")
        rating = ""
        if rating_el:
            rating = (rating_el.get("score") or rating_el.get("rating")
                      or rating_el.get_text(strip=True))

        author_el = item.select_one("writer-display")
        author = author_el.get_text(strip=True) if author_el else ""

        date_el = item.select_one("custom-date")
        date = date_el.get_text(strip=True) if date_el else ""

        reviews.append({"author": author, "rating": rating, "date": date, "content": content})

    return reviews


def crawl(product_no: int, max_pages: int, delay: float) -> list[dict]:
    print("POST body 및 쿠키 획득 중...")
    post_body, cookies = get_post_body_and_cookies(product_no)

    if not post_body:
        print("POST body 획득 실패.")
        return []
    print(f"POST body 획득 완료. 파라미터: {list(post_body.keys())}")

    all_reviews = []
    seen = set()

    for page_num in range(1, max_pages + 1):
        print(f"[{page_num}/{max_pages}] 리뷰 수집 중...")
        try:
            html = fetch_review_html(post_body, cookies, page_num)
        except Exception as e:
            print(f"  오류: {e}")
            break

        reviews = parse_reviews_from_html(html)
        if not reviews:
            print("  리뷰 없음 — 마지막 페이지")
            break

        new_reviews = [r for r in reviews if r["content"] not in seen]
        if not new_reviews:
            print("  중복 페이지 — 종료")
            break
        for r in new_reviews:
            seen.add(r["content"])
        all_reviews.extend(new_reviews)
        print(f"  수집: {len(new_reviews)}건 (누계 {len(all_reviews)}건)")
        time.sleep(delay)

    return all_reviews


def save_csv(reviews: list[dict], path: str):
    if not reviews:
        print("수집된 리뷰가 없습니다.")
        return
    fieldnames = ["author", "rating", "date", "content"]
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(reviews)
    print(f"저장 완료: {path} ({len(reviews)}건)")


def main():
    parser = argparse.ArgumentParser(description="beaund.com 리뷰 크롤러")
    parser.add_argument("--product_no", type=int, default=53, help="상품 번호 (기본 53)")
    parser.add_argument("--out", default="beaund_reviews.csv", help="저장할 CSV 파일명")
    parser.add_argument("--pages", type=int, default=30, help="최대 페이지 수 (기본 30)")
    parser.add_argument("--delay", type=float, default=0.5, help="페이지 간 딜레이(초)")
    args = parser.parse_args()

    print(f"beaund.com 상품 #{args.product_no} 리뷰 수집 시작")
    reviews = crawl(args.product_no, max_pages=args.pages, delay=args.delay)
    save_csv(reviews, args.out)


if __name__ == "__main__":
    main()
