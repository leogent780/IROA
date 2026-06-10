"""
경쟁사 홈페이지 리뷰 크롤러 (alphwidget API 직접 호출)
사용법:
    pip install requests
    python crawler.py --product_no 22 --out reviews.csv
    python crawler.py --product_no 22 --out reviews.csv --pages 30
"""
import argparse
import csv
import time
import requests

API_BASE = "https://review-widget.alphwidget.com/v2/api-widget"
MALL_ID = "hlbgswell247"
SHOP_NO = 1
WIDGET_CODE = "80831c03"
PAGE_SIZE = 50

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.well247.co.kr/",
    "Origin": "https://www.well247.co.kr",
}


def fetch_reviews(product_no: int, page: int) -> list[dict]:
    params = {
        "page": page,
        "page_size": PAGE_SIZE,
        "sort": "-created_at",
        "media_only": "false",
        "product_no": product_no,
        "widget_code": WIDGET_CODE,
        "device": "w",
    }
    resp = requests.get(API_BASE, params=params, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    items = resp.json()
    if not isinstance(items, list):
        return []

    reviews = []
    for item in items:
        reviews.append({
            "author": item.get("user_info", ""),
            "rating": item.get("ratings", ""),
            "date": (item.get("created_at") or "")[:10],
            "content": item.get("content", ""),
        })
    return reviews


def crawl(product_no: int, max_pages: int, delay: float) -> list[dict]:
    all_reviews = []
    for page_num in range(1, max_pages + 1):
        print(f"[{page_num}/{max_pages}] 페이지 수집 중...")
        try:
            reviews = fetch_reviews(product_no, page_num)
        except Exception as e:
            print(f"  오류: {e}")
            break

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
    parser = argparse.ArgumentParser(description="well247 리뷰 크롤러")
    parser.add_argument("--product_no", type=int, default=22, help="상품 번호 (기본 22)")
    parser.add_argument("--out", default="reviews.csv", help="저장할 CSV 파일명")
    parser.add_argument("--pages", type=int, default=30, help="최대 페이지 수 (기본 30, 1페이지=50건)")
    parser.add_argument("--delay", type=float, default=0.5, help="페이지 간 딜레이(초)")
    args = parser.parse_args()

    print(f"상품 #{args.product_no} 리뷰 수집 시작 (최대 {args.pages * PAGE_SIZE}건)")
    reviews = crawl(args.product_no, max_pages=args.pages, delay=args.delay)
    save_csv(reviews, args.out)


if __name__ == "__main__":
    main()
