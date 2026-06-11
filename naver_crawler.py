"""
네이버 스마트스토어 리뷰 크롤러 (browser-cookie3 방식)

사전 준비:
  1. Chrome에서 https://smartstore.naver.com/vilarstore/products/13197800272 방문
  2. python naver_crawler.py --product_no 13197800272 --out naver_reviews.csv
"""
import argparse
import csv
import time
import requests

REVIEW_API = "https://smartstore.naver.com/i/v1/reviews/paged-reviews"
PAGE_SIZE = 20
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/148.0.0.0 Safari/537.36"
)
COOKIE_FILE = "naver_cookies.txt"


def get_naver_cookies() -> dict:
    """naver_cookies.txt 파일에서 쿠키 읽기"""
    try:
        with open(COOKIE_FILE, encoding="utf-8") as f:
            cookie_str = f.read().strip()
    except FileNotFoundError:
        print(f"[오류] {COOKIE_FILE} 파일이 없습니다.")
        print()
        print("다음 순서로 쿠키를 복사하세요:")
        print("  1. Chrome에서 https://smartstore.naver.com/vilarstore/products/13197800272 방문")
        print("  2. F12 → Network 탭 → F5 새로고침")
        print("  3. 왼쪽 목록에서 '13197800272' 클릭")
        print("  4. Headers → Request Headers → cookie: 값 전체 복사")
        print(f"  5. 복사한 값을 {COOKIE_FILE} 파일로 저장")
        raise SystemExit(1)

    cookies = {}
    for part in cookie_str.split(";"):
        part = part.strip()
        if "=" in part:
            k, v = part.split("=", 1)
            cookies[k.strip()] = v.strip()
    print(f"쿠키 수: {len(cookies)}개")
    return cookies


def fetch_reviews(product_no: str, max_pages: int, cookies: dict) -> list[dict]:
    all_reviews = []
    headers = {
        "User-Agent": UA,
        "Referer": f"https://smartstore.naver.com/vilarstore/products/{product_no}",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "ko-KR,ko;q=0.9",
    }

    for page_num in range(1, max_pages + 1):
        print(f"[{page_num}/{max_pages}] 수집 중...")
        params = {
            "reviewType": "PRODUCT",
            "productNo": product_no,
            "page": page_num,
            "pageSize": PAGE_SIZE,
            "sortType": "REVIEW_CREATE_DATE_DESC",
        }
        try:
            resp = requests.get(REVIEW_API, params=params, headers=headers, cookies=cookies, timeout=15)
            print(f"  상태: {resp.status_code}")
            if resp.status_code != 200:
                print(f"  응답: {resp.text[:200]}")
                break
            data = resp.json()
        except Exception as e:
            print(f"  오류: {e}")
            break

        items = data.get("contents", [])
        if not items:
            print("  리뷰 없음 — 마지막 페이지")
            break

        total = data.get("totalElements", 0)
        for item in items:
            all_reviews.append({
                "author": item.get("writerMemberSummary", {}).get("nickName", ""),
                "rating": item.get("reviewScore", ""),
                "date": (item.get("createDate") or "")[:10],
                "content": item.get("reviewContent", ""),
            })

        print(f"  수집: {len(items)}건 (누계 {len(all_reviews)}건 / 전체 {total}건)")
        if len(all_reviews) >= total:
            print("  전체 수집 완료")
            break

        time.sleep(0.5)

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
    parser = argparse.ArgumentParser()
    parser.add_argument("--product_no", required=True)
    parser.add_argument("--out", default="naver_reviews.csv")
    parser.add_argument("--pages", type=int, default=50)
    args = parser.parse_args()

    print(f"네이버 스마트스토어 상품 #{args.product_no} 리뷰 수집 시작")
    cookies = get_naver_cookies()
    reviews = fetch_reviews(args.product_no, max_pages=args.pages, cookies=cookies)
    save_csv(reviews, args.out)


if __name__ == "__main__":
    main()
