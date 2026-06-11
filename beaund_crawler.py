"""
beaund.com (Snapfit 리뷰 시스템) 크롤러
사용법:
    pip install playwright beautifulsoup4
    python -m playwright install chromium
    python beaund_crawler.py --product_no 53 --out beaund_reviews.csv --pages 30
"""
import argparse
import csv
import re
import time
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

BASE_URL = "https://beaund.com"
DRAW_URL = "https://sfre-srcs-service.snapfit.co.kr/Draw/draw_review_dependent"


def scrape_page(product_no: int, target_page: int) -> str:
    """페이지 route 인터셉트로 draw_review_dependent의 page 파라미터를 교체"""
    html_result = {"content": ""}

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

        def intercept(route):
            request = route.request
            if "draw_review_dependent" in request.url and request.method == "POST":
                try:
                    raw = request.post_data_buffer or b""
                    body = raw.decode("utf-8", errors="ignore")
                except Exception:
                    body = ""
                # page 파라미터 교체
                body = re.sub(r"page=\d+", f"page={target_page}", body)
                if "page=" not in body:
                    body += f"&page={target_page}"
                route.continue_(post_data=body)
            else:
                route.continue_()

        context.route("**/*", intercept)

        url = f"{BASE_URL}/product/detail.html?product_no={product_no}"
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(6000)

        # 리뷰 iframe 찾기
        for frame in page.frames:
            if "sfre-srcs" in frame.url:
                frame.wait_for_timeout(2000)
                html_result["content"] = frame.content()
                break

        browser.close()

    return html_result["content"]


def parse_reviews(html: str) -> list[dict]:
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
            rating = rating_el.get("score") or rating_el.get("rating") or rating_el.get_text(strip=True)
        author_el = item.select_one("writer-display")
        author = author_el.get_text(strip=True) if author_el else ""
        date_el = item.select_one("custom-date")
        date = date_el.get_text(strip=True) if date_el else ""
        reviews.append({"author": author, "rating": rating, "date": date, "content": content})
    return reviews


def crawl(product_no: int, max_pages: int, delay: float) -> list[dict]:
    all_reviews = []
    seen = set()

    for page_num in range(1, max_pages + 1):
        print(f"[{page_num}/{max_pages}] 페이지 로드 중...")
        html = scrape_page(product_no, page_num)

        reviews = parse_reviews(html)
        if not reviews:
            print("  리뷰 없음 — 마지막 페이지")
            break

        new_reviews = [r for r in reviews if r["content"] not in seen]
        if not new_reviews:
            print("  중복 — 종료")
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
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["author", "rating", "date", "content"])
        writer.writeheader()
        writer.writerows(reviews)
    print(f"저장 완료: {path} ({len(reviews)}건)")


def main():
    parser = argparse.ArgumentParser(description="beaund.com 리뷰 크롤러")
    parser.add_argument("--product_no", type=int, default=53)
    parser.add_argument("--out", default="beaund_reviews.csv")
    parser.add_argument("--pages", type=int, default=30)
    parser.add_argument("--delay", type=float, default=1.0)
    args = parser.parse_args()

    print(f"beaund.com 상품 #{args.product_no} 리뷰 수집 시작")
    reviews = crawl(args.product_no, max_pages=args.pages, delay=args.delay)
    save_csv(reviews, args.out)


if __name__ == "__main__":
    main()
