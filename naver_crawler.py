"""
네이버 스마트스토어 리뷰 크롤러

사용법:
  1. Chrome에서 스마트스토어 리뷰 페이지 방문 후 F12 → Network
  2. query-pages 요청 우클릭 → Copy → Copy as cURL (bash)
  3. 복사한 내용을 naver_curl.txt 로 저장
  4. python naver_crawler.py --out naver_reviews.csv
"""
import argparse
import csv
import re
import time
import requests

REVIEW_API = "https://smartstore.naver.com/i/v1/contents/reviews/query-pages"
PAGE_SIZE = 20
CHECKOUT_MERCHANT_NO = 512518077
ORIGIN_PRODUCT_NO = 13139491696


def parse_curl(path="naver_curl.txt") -> tuple[dict, dict]:
    """cURL 파일에서 헤더와 쿠키 파싱"""
    with open(path, encoding="utf-8") as f:
        text = f.read()

    headers = {}
    for m in re.finditer(r"-H\s+'([^']+)'", text):
        line = m.group(1)
        if ": " in line:
            k, v = line.split(": ", 1)
            headers[k.lower()] = v

    cookies = {}
    m = re.search(r"-b\s+'([^']+)'", text)
    if m:
        for part in m.group(1).split(";"):
            part = part.strip()
            if "=" in part:
                k, v = part.split("=", 1)
                cookies[k.strip()] = v.strip()

    print(f"헤더 수: {len(headers)}개, 쿠키 수: {len(cookies)}개")
    return headers, cookies


def fetch_reviews(headers: dict, cookies: dict, max_pages: int) -> list[dict]:
    all_reviews = []

    for page_num in range(1, max_pages + 1):
        print(f"[{page_num}/{max_pages}] 수집 중...")
        body = {
            "checkoutMerchantNo": CHECKOUT_MERCHANT_NO,
            "originProductNo": ORIGIN_PRODUCT_NO,
            "page": page_num,
            "pageSize": PAGE_SIZE,
            "reviewSearchSortType": "REVIEW_RANKING",
        }
        try:
            resp = requests.post(REVIEW_API, json=body, headers=headers, cookies=cookies, timeout=15)
            print(f"  상태: {resp.status_code}")
            if resp.status_code != 200:
                print(f"  응답: {resp.text[:300]}")
                break
            data = resp.json()
        except Exception as e:
            print(f"  오류: {e}")
            break

        contents = data.get("contents", [])
        if not contents:
            print("  리뷰 없음 — 마지막 페이지")
            break

        total = data.get("totalElements", 0)
        for item in contents:
            all_reviews.append({
                "author": item.get("writerMemberSummary", {}).get("nickName", ""),
                "rating": item.get("reviewScore", ""),
                "date": (item.get("createDate") or "")[:10],
                "content": item.get("reviewContent", ""),
            })

        print(f"  수집: {len(contents)}건 (누계 {len(all_reviews)}건 / 전체 {total}건)")
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
    parser.add_argument("--out", default="naver_reviews.csv")
    parser.add_argument("--pages", type=int, default=50)
    parser.add_argument("--curl", default="naver_curl.txt")
    args = parser.parse_args()

    headers, cookies = parse_curl(args.curl)
    reviews = fetch_reviews(headers=headers, cookies=cookies, max_pages=args.pages)
    save_csv(reviews, args.out)


if __name__ == "__main__":
    main()
