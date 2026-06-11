"""
네이버 스마트스토어 리뷰 크롤러 (기존 Chrome 연결 방식)

사전 준비:
  1. Chrome을 모두 닫기
  2. 아래 명령어로 Chrome 실행:
     "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222
  3. 열린 Chrome에서 아무 네이버 페이지나 방문 (쿠키 생성용)
  4. 그 상태에서 이 스크립트 실행:
     python naver_crawler.py --product_no 13197800272 --out naver_reviews.csv
"""
import argparse
import csv
import time
import requests
from playwright.sync_api import sync_playwright

REVIEW_API = "https://smartstore.naver.com/i/v1/reviews/paged-reviews"
PAGE_SIZE = 20


def get_cookies_via_existing_chrome(product_no: str) -> tuple[dict, str]:
    """기존 Chrome에 연결해서 쿠키와 UA 수집"""
    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp("http://localhost:9222")
        except Exception as e:
            print(f"\n[오류] Chrome에 연결할 수 없습니다: {e}")
            print("\n다음 순서로 진행하세요:")
            print('  1. Chrome을 모두 닫기')
            print('  2. 실행: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" --remote-debugging-port=9222')
            print("  3. 열린 Chrome에서 https://naver.com 방문")
            print("  4. 다시 이 스크립트 실행")
            raise SystemExit(1)

        context = browser.contexts[0] if browser.contexts else browser.new_context()
        page = context.new_page()

        url = f"https://smartstore.naver.com/vilarstore/products/{product_no}#REVIEW"
        print(f"페이지 로드 중: {url}")
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)

        title = page.title()
        print(f"페이지 타이틀: {title}")

        cookies = {c["name"]: c["value"] for c in context.cookies()}
        ua = page.evaluate("() => navigator.userAgent")
        print(f"쿠키 수: {len(cookies)}개")

        page.close()
        browser.close()

    return cookies, ua


def fetch_reviews(product_no: str, max_pages: int, cookies: dict, ua: str) -> list[dict]:
    all_reviews = []
    headers = {
        "User-Agent": ua,
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
    cookies, ua = get_cookies_via_existing_chrome(args.product_no)

    if not cookies:
        print("쿠키 없음 — Chrome에서 네이버 로그인 후 다시 시도하세요")
        return

    reviews = fetch_reviews(args.product_no, max_pages=args.pages, cookies=cookies, ua=ua)
    save_csv(reviews, args.out)


if __name__ == "__main__":
    main()
