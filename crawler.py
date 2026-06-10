"""
경쟁사 홈페이지 리뷰 크롤러
사용법:
    pip install playwright beautifulsoup4
    python -m playwright install chromium
    python crawler.py --url "https://www.well247.co.kr/product/detail.html?product_no=22" --out reviews.csv
"""
import argparse
import csv
import time
import re
from pathlib import Path
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright


REVIEW_SELECTORS = [
    # 카페24 계열 공통
    ".xans-product-review li",
    "#review_list li",
    ".reviewList li",
    ".review-list li",
    ".prd-review li",
    # 일반
    ".review_item",
    ".review-item",
    "[class*='review'] li",
]

STAR_SELECTORS = [
    ".star_score",
    ".rating",
    ".score",
    "[class*='star']",
    "[class*='rating']",
    "[class*='score']",
]

AUTHOR_SELECTORS = [
    ".name",
    ".writer",
    ".author",
    "[class*='name']",
    "[class*='writer']",
    "[class*='author']",
]

DATE_SELECTORS = [
    ".date",
    ".writeday",
    ".regdate",
    "[class*='date']",
    "[class*='day']",
]

CONTENT_SELECTORS = [
    ".cont",
    ".content",
    ".review_cont",
    ".review-content",
    ".memo",
    "[class*='cont']",
    "[class*='content']",
    "p",
]


def _text(el, selectors):
    for sel in selectors:
        found = el.select_one(sel)
        if found:
            return found.get_text(strip=True)
    return ""


def _star_count(el):
    # style="width:80%" → 80/20 = 4점
    for sel in STAR_SELECTORS:
        found = el.select_one(sel)
        if not found:
            continue
        style = found.get("style", "")
        m = re.search(r"width\s*:\s*(\d+(?:\.\d+)?)\s*%", style)
        if m:
            return round(float(m.group(1)) / 20, 1)
        text = found.get_text(strip=True)
        m = re.search(r"(\d+(?:\.\d+)?)", text)
        if m:
            return float(m.group(1))
    return ""


def parse_reviews(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for sel in REVIEW_SELECTORS:
        items = soup.select(sel)
        if items:
            break
    if not items:
        return []

    reviews = []
    for item in items:
        content = _text(item, CONTENT_SELECTORS)
        if not content:
            continue
        reviews.append({
            "author": _text(item, AUTHOR_SELECTORS),
            "rating": _star_count(item),
            "date": _text(item, DATE_SELECTORS),
            "content": content,
        })
    return reviews


def get_review_page_url(base_url: str, page: int) -> str:
    """카페24 계열 리뷰 페이지 URL 패턴"""
    if "?" in base_url:
        return f"{base_url}&review_page={page}"
    return f"{base_url}?review_page={page}"


def crawl(url: str, max_pages: int = 10, delay: float = 1.5) -> list[dict]:
    all_reviews = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"],
        )
        context = browser.new_context(
            ignore_https_errors=True,
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()

        for page_num in range(1, max_pages + 1):
            page_url = get_review_page_url(url, page_num) if page_num > 1 else url
            print(f"[{page_num}/{max_pages}] {page_url}")
            try:
                page.goto(page_url, wait_until="networkidle", timeout=30000)
            except Exception as e:
                print(f"  로드 실패: {e}")
                break

            html = page.content()
            reviews = parse_reviews(html)
            if not reviews:
                print("  리뷰 없음 — 마지막 페이지")
                break

            all_reviews.extend(reviews)
            print(f"  수집: {len(reviews)}건 (누계 {len(all_reviews)}건)")
            time.sleep(delay)

        browser.close()

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
    parser = argparse.ArgumentParser(description="경쟁사 홈페이지 리뷰 크롤러")
    parser.add_argument("--url", required=True, help="상품 페이지 URL")
    parser.add_argument("--out", default="reviews.csv", help="저장할 CSV 파일명")
    parser.add_argument("--pages", type=int, default=10, help="최대 페이지 수 (기본 10)")
    parser.add_argument("--delay", type=float, default=1.5, help="페이지 간 딜레이(초)")
    args = parser.parse_args()

    reviews = crawl(args.url, max_pages=args.pages, delay=args.delay)
    save_csv(reviews, args.out)


if __name__ == "__main__":
    main()
