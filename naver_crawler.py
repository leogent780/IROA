"""
네이버 스마트스토어 리뷰 크롤러
사용법:
    pip install requests
    python naver_crawler.py --product_no 13197800272 --out naver_reviews.csv --pages 30
"""
import argparse
import csv
import time
import requests

REVIEW_API = "https://smartstore.naver.com/i/v1/reviews/paged-reviews"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://smartstore.naver.com/",
}
PAGE_SIZE = 20


def fetch_reviews(product_no: str, page: int) -> dict:
    params = {
        "reviewType": "PRODUCT",
        "productNo": product_no,
        "page": page,
        "pageSize": PAGE_SIZE,
        "sortType": "REVIEW_CREATE_DATE_DESC",
    }
    resp = requests.get(REVIEW_API, params=params, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.json()


def crawl(product_no: str, max_pages: int, delay: float) -> list[dict]:
    all_reviews = []

    for page_num in range(1, max_pages + 1):
        print(f"[{page_num}/{max_pages}] 수집 중...")
        try:
            data = fetch_reviews(product_no, page_num)
        except Exception as e:
            print(f"  오류: {e}")
            break

        items = data.get("contents", [])
        if not items:
            print("  리뷰 없음 — 마지막 페이지")
            break

        for item in items:
            all_reviews.append({
                "author": item.get("writerMemberSummary", {}).get("nickName", ""),
                "rating": item.get("reviewScore", ""),
                "date": (item.get("createDate") or "")[:10],
                "content": item.get("reviewContent", ""),
            })

        total = data.get("totalElements", 0)
        print(f"  수집: {len(items)}건 (누계 {len(all_reviews)}건 / 전체 {total}건)")

        if len(all_reviews) >= total:
            print("  전체 수집 완료")
            break

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
    parser = argparse.ArgumentParser(description="네이버 스마트스토어 리뷰 크롤러")
    parser.add_argument("--product_no", required=True, help="상품 번호 (URL의 products/ 뒤 숫자)")
    parser.add_argument("--out", default="naver_reviews.csv")
    parser.add_argument("--pages", type=int, default=30, help="최대 페이지 수 (1페이지=20건)")
    parser.add_argument("--delay", type=float, default=0.5)
    args = parser.parse_args()

    print(f"네이버 스마트스토어 상품 #{args.product_no} 리뷰 수집 시작")
    reviews = crawl(args.product_no, max_pages=args.pages, delay=args.delay)
    save_csv(reviews, args.out)


if __name__ == "__main__":
    main()
