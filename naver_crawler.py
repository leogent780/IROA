"""
네이버 스마트스토어 리뷰 크롤러 (curl 직접 실행 방식)

사용법:
  1. Chrome F12 → Network → query-pages 우클릭 → Copy as cURL (bash)
  2. naver_curl.txt 로 저장 (iroa 폴더에)
  3. python naver_crawler.py --out naver_reviews.csv
"""
import argparse
import csv
import json
import re
import subprocess
import time

REVIEW_API = "https://smartstore.naver.com/i/v1/contents/reviews/query-pages"
PAGE_SIZE = 20
CHECKOUT_MERCHANT_NO = 512518077
ORIGIN_PRODUCT_NO = 13139491696


def build_curl_args(curl_text: str, page: int) -> list[str]:
    """cURL 텍스트에서 헤더/쿠키 추출 후 page만 교체해서 args 반환"""
    args = ["curl", "-s", REVIEW_API]

    # 헤더
    for m in re.finditer(r"-H\s+'([^']+)'", curl_text):
        h = m.group(1)
        if not h.lower().startswith("content-length"):
            args += ["-H", h]

    # 쿠키
    m = re.search(r"-b\s+'([^']+)'", curl_text)
    if m:
        args += ["-b", m.group(1)]

    # POST body (page 교체)
    body = {
        "checkoutMerchantNo": CHECKOUT_MERCHANT_NO,
        "originProductNo": ORIGIN_PRODUCT_NO,
        "page": page,
        "pageSize": PAGE_SIZE,
        "reviewSearchSortType": "REVIEW_RANKING",
    }
    args += ["--data-raw", json.dumps(body, ensure_ascii=False)]

    return args


def fetch_page(curl_text: str, page: int) -> dict:
    args = build_curl_args(curl_text, page)
    result = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", timeout=30)
    if not result.stdout.strip():
        raise ValueError(f"빈 응답 (stderr: {result.stderr[:200]})")
    return json.loads(result.stdout)


def crawl(curl_text: str, max_pages: int) -> list[dict]:
    all_reviews = []

    for page_num in range(1, max_pages + 1):
        print(f"[{page_num}/{max_pages}] 수집 중...")
        try:
            data = fetch_page(curl_text, page_num)
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

    with open(args.curl, encoding="utf-8") as f:
        curl_text = f.read()

    reviews = crawl(curl_text, max_pages=args.pages)
    save_csv(reviews, args.out)


if __name__ == "__main__":
    main()
