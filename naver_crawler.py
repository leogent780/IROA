"""
네이버 스마트스토어 리뷰 크롤러 (undetected-chromedriver 기반)
사용법:
    pip install undetected-chromedriver selenium requests
    python naver_crawler.py --product_no 13197800272 --out naver_reviews.csv
"""
import argparse
import csv
import json
import time
import requests
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

REVIEW_API = "https://smartstore.naver.com/i/v1/reviews/paged-reviews"
PAGE_SIZE = 20


def get_cookies_and_fetch(product_no: str, max_pages: int) -> list[dict]:
    all_reviews = []

    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1280,800")
    options.add_argument("--lang=ko-KR")

    print("Chrome 실행 중 (잠시 창이 열립니다)...")
    driver = uc.Chrome(options=options, headless=False, version_main=148)

    try:
        url = f"https://smartstore.naver.com/vilarstore/products/{product_no}#REVIEW"
        print(f"페이지 로드 중: {url}")
        driver.get(url)
        time.sleep(5)

        title = driver.title
        print(f"페이지 타이틀: {title}")

        if "에러" in title or "오류" in title:
            print("에러 페이지 — 잠시 후 재시도")
            time.sleep(5)
            driver.get(url)
            time.sleep(5)
            title = driver.title
            print(f"재시도 타이틀: {title}")

        # 쿠키 수집
        cookies = {c["name"]: c["value"] for c in driver.get_cookies()}
        print(f"쿠키 수: {len(cookies)}개")

        # User-Agent 수집
        ua = driver.execute_script("return navigator.userAgent")
        print(f"UA: {ua[:60]}...")

    finally:
        driver.quit()

    if not cookies:
        print("쿠키를 가져오지 못했습니다.")
        return []

    # requests로 API 호출 (브라우저 쿠키 사용)
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
            resp = requests.get(
                REVIEW_API,
                params=params,
                headers=headers,
                cookies=cookies,
                timeout=15,
            )
            print(f"  상태: {resp.status_code}")
            if resp.status_code != 200:
                print(f"  오류 응답: {resp.text[:200]}")
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
    parser = argparse.ArgumentParser(description="네이버 스마트스토어 리뷰 크롤러")
    parser.add_argument("--product_no", required=True)
    parser.add_argument("--out", default="naver_reviews.csv")
    parser.add_argument("--pages", type=int, default=50)
    args = parser.parse_args()

    print(f"네이버 스마트스토어 상품 #{args.product_no} 리뷰 수집 시작")
    reviews = get_cookies_and_fetch(args.product_no, max_pages=args.pages)
    save_csv(reviews, args.out)


if __name__ == "__main__":
    main()
