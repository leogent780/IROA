"""
beaund.com (Snapfit 리뷰 시스템) 크롤러
사용법:
    pip install requests playwright beautifulsoup4
    python -m playwright install chromium
    python beaund_crawler.py --product_no 53 --out beaund_reviews.csv --pages 30
"""
import argparse
import csv
import json
import time
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

DRAW_URL = "https://sfre-srcs-service.snapfit.co.kr/Draw/draw_review_dependent"
INIT_URL = "https://sfre-srcs-service.snapfit.co.kr/Datainit/init_detail_page"
STORE = "beaund"
BASE_URL = "https://beaund.com"


def get_tokens(product_no: int) -> dict:
    """Playwright로 페이지 로드 후 init_detail_page 토큰 캡처"""
    tokens = {}

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

        def on_response(response):
            if "init_detail_page" in response.url:
                try:
                    data = response.json()
                    wcd = data.get("data", {}).get("widgetCommonDatas", {})
                    wi = data.get("data", {}).get("review", {}).get("widgetinfo", {})
                    # 첫 번째 위젯 정보 사용
                    first_widget = next(iter(wi.values()), {})
                    tokens.update({
                        "a": wcd.get("a", ""),
                        "b": wcd.get("b", ""),
                        "c": wcd.get("c", "pc"),
                        "d": wcd.get("d", str(product_no)),
                        "e": wcd.get("e", ""),
                        "h": first_widget.get("h", ""),
                        "f": first_widget.get("f", ""),
                    })
                except Exception as e:
                    print(f"토큰 파싱 오류: {e}")

        page.on("response", on_response)
        url = f"{BASE_URL}/product/detail.html?product_no={product_no}"
        print(f"페이지 로드 중: {url}")
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)
        browser.close()

    return tokens


def fetch_review_html(tokens: dict, page: int) -> str:
    data = {
        "e": tokens["e"],
        "c": tokens["c"],
        "a": tokens["a"],
        "d": tokens["d"],
        "b": tokens["b"],
        "h": tokens["h"],
        "f": tokens["f"],
        "i": "tiaa",
        "j": "0",
        "page": str(page),
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
        "Referer": BASE_URL,
        "Origin": BASE_URL,
        "Content-Type": "application/x-www-form-urlencoded",
    }
    resp = requests.post(DRAW_URL, data=data, headers=headers, timeout=15)
    resp.raise_for_status()
    return resp.text


def parse_review_html(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    reviews = []

    # Snapfit 리뷰 아이템 셀렉터
    items = (
        soup.select("review-item")
        or soup.select(".review-item")
        or soup.select("[class*='review_item']")
        or soup.select("li[class*='review']")
    )

    for item in items:
        # 리뷰 내용
        content_el = (
            item.select_one("review-text")
            or item.select_one(".review-text")
            or item.select_one("[class*='review_text']")
            or item.select_one("p")
        )
        content = content_el.get_text(strip=True) if content_el else ""
        if not content:
            continue

        # 별점
        rating_el = (
            item.select_one("review-rating")
            or item.select_one(".review-rating")
            or item.select_one("[class*='rating']")
        )
        rating = ""
        if rating_el:
            # data-score 속성 우선
            rating = rating_el.get("score") or rating_el.get("data-score") or rating_el.get_text(strip=True)

        # 작성자
        author_el = (
            item.select_one("writer-display")
            or item.select_one(".writer-display")
            or item.select_one("[class*='writer']")
            or item.select_one("[class*='author']")
        )
        author = author_el.get_text(strip=True) if author_el else ""

        # 날짜
        date_el = (
            item.select_one("custom-date")
            or item.select_one(".custom-date")
            or item.select_one("[class*='date']")
        )
        date = date_el.get_text(strip=True) if date_el else ""

        reviews.append({
            "author": author,
            "rating": rating,
            "date": date,
            "content": content,
        })

    return reviews


def crawl(product_no: int, max_pages: int, delay: float) -> list[dict]:
    print("토큰 획득 중...")
    tokens = get_tokens(product_no)
    if not tokens.get("a"):
        print("토큰 획득 실패. 페이지가 정상 로드되었는지 확인하세요.")
        return []
    print(f"토큰 획득 완료: product_no={tokens['d']}")

    all_reviews = []
    for page_num in range(1, max_pages + 1):
        print(f"[{page_num}/{max_pages}] 리뷰 수집 중...")
        try:
            html = fetch_review_html(tokens, page_num)
        except Exception as e:
            print(f"  오류: {e}")
            break

        # 첫 페이지 HTML 저장 (디버깅용)
        if page_num == 1:
            with open("review_page1.html", "w", encoding="utf-8") as f:
                f.write(html)
            print(f"  첫 페이지 HTML 저장: review_page1.html ({len(html):,} bytes)")

            # 태그 종류 확인
            from bs4 import BeautifulSoup as BS
            soup = BS(html, "html.parser")
            tags = set(t.name for t in soup.find_all())
            print(f"  HTML 내 태그 목록: {sorted(tags)}")

        reviews = parse_review_html(html)
        if not reviews:
            print("  리뷰 없음 — 마지막 페이지")
            break

        all_reviews.extend(reviews)
        print(f"  수집: {len(reviews)}건 (누계 {len(all_reviews)}건)")
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
