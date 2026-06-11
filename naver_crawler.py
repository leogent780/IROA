"""
네이버 스마트스토어 리뷰 크롤러
사용법:
    python naver_crawler.py --out naver_reviews.csv
    (naver_cookies.txt 에 쿠키값, naver_headers.txt 에 x-client-rtk 값 저장 필요)
"""
import argparse
import csv
import time
import requests

REVIEW_API = "https://smartstore.naver.com/i/v1/contents/reviews/query-pages"
PAGE_SIZE = 20

# fetch에서 확인한 고정값
CHECKOUT_MERCHANT_NO = 512518077
ORIGIN_PRODUCT_NO = 13139491696


def load_cookies(path="naver_cookies.txt") -> dict:
    with open(path, encoding="utf-8") as f:
        cookie_str = f.read().strip()
    cookies = {}
    for part in cookie_str.split(";"):
        part = part.strip()
        if "=" in part:
            k, v = part.split("=", 1)
            cookies[k.strip()] = v.strip()
    print(f"쿠키 수: {len(cookies)}개")
    return cookies


def fetch_reviews(rtk: str, rts: str, version: str, cookies: dict, max_pages: int) -> list[dict]:
    all_reviews = []
    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "ko-KR,ko;q=0.9",
        "content-type": "application/json",
        "origin": "https://smartstore.naver.com",
        "referer": "https://smartstore.naver.com/vilarstore/products/13197800272",
        "sec-ch-ua": '"Google Chrome";v="149", "Chromium";v="149", "Not)A;Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
        "x-client-lct": "/vilarstore/products/13197800272",
        "x-client-rtk": rtk,
        "x-client-rts": rts,
        "x-client-version": version,
        "x-service-type": "NONE",
    }

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
    parser.add_argument("--rtk", default="t21:LC8C42aZ1Og6MVgyystUAHolr2PEZhEviekadcxT1Xo")
    parser.add_argument("--rts", default="1781157489226")
    parser.add_argument("--version", default="20260611104631")
    args = parser.parse_args()

    cookies = load_cookies()
    reviews = fetch_reviews(
        rtk=args.rtk,
        rts=args.rts,
        version=args.version,
        cookies=cookies,
        max_pages=args.pages,
    )
    save_csv(reviews, args.out)


if __name__ == "__main__":
    main()
