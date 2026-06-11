"""
beaund.com (Snapfit 리뷰 시스템) 크롤러
사용법:
    pip install requests playwright beautifulsoup4
    python -m playwright install chromium
    python beaund_crawler.py --product_no 53 --out beaund_reviews.csv --pages 30
"""
import argparse
import csv
import time
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

BASE_URL = "https://beaund.com"


def parse_reviews_from_html(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    reviews = []

    items = soup.select("review-item")
    for item in items:
        content_el = item.select_one("review-text")
        content = content_el.get_text(strip=True) if content_el else ""
        if not content:
            continue

        rating_el = item.select_one("review-rating")
        rating = ""
        if rating_el:
            rating = rating_el.get("score") or rating_el.get("rating") or rating_el.get_text(strip=True)

        author_el = item.select_one("writer-display")
        author = author_el.get_text(strip=True) if author_el else ""

        date_el = item.select_one("custom-date")
        date = date_el.get_text(strip=True) if date_el else ""

        reviews.append({"author": author, "rating": rating, "date": date, "content": content})

    return reviews


def crawl(product_no: int, max_pages: int, delay: float) -> list[dict]:
    all_reviews = []
    url = f"{BASE_URL}/product/detail.html?product_no={product_no}"

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

        print(f"페이지 로드 중: {url}")
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)

        # 리뷰 iframe 찾기
        frames = page.frames
        print("\n전체 iframe 목록:")
        for frame in frames:
            print(f"  name={frame.name!r}, url={frame.url}")

        review_frame = None
        for frame in frames:
            if "sfre-srcs" in frame.url or ("snapfit" in frame.url and "push" not in frame.url):
                review_frame = frame
                print(f"\n리뷰 iframe 발견: {frame.url}")
                break

        if not review_frame:
            # name에 review_widget 포함된 것 시도
            for frame in frames:
                if "review_widget" in frame.name:
                    review_frame = frame
                    print(f"\n리뷰 iframe 발견 (name): {frame.name}")
                    break

        if not review_frame:
            print("리뷰 iframe을 찾지 못했습니다.")
            browser.close()
            return []

        for page_num in range(1, max_pages + 1):
            print(f"[{page_num}/{max_pages}] 리뷰 수집 중...")

            if page_num == 2:
                # 페이지네이션 구조 출력 (디버깅)
                html_debug = review_frame.content()
                soup_debug = BeautifulSoup(html_debug, "html.parser")
                pag = soup_debug.find("pagination-basic")
                if pag:
                    print(f"  pagination-basic 내용:\n{str(pag)[:800]}")
                else:
                    print("  pagination-basic 없음")
                    # 모든 버튼 출력
                    for btn in soup_debug.find_all("button")[:10]:
                        print(f"  button: {btn}")

            if page_num > 1:
                # 다음 페이지 버튼 클릭 (다양한 셀렉터 시도)
                clicked = False
                for sel in [
                    "pagination-basic button[part='next']",
                    "pagination-basic button[aria-label='next']",
                    "pagination-basic .next",
                    "pagination-basic button:last-child",
                    "[part='next']",
                    "button[aria-label='next']",
                ]:
                    try:
                        btn = review_frame.locator(sel).first
                        if btn.is_visible(timeout=1000):
                            btn.click()
                            review_frame.wait_for_timeout(2000)
                            clicked = True
                            print(f"  클릭 성공: {sel}")
                            break
                    except Exception:
                        continue

                if not clicked:
                    print("  다음 페이지 버튼 없음 — 종료")
                    break

            html = review_frame.content()

            # 첫 페이지 디버깅
            if page_num == 1:
                with open("review_frame.html", "w", encoding="utf-8") as f:
                    f.write(html)
                soup = BeautifulSoup(html, "html.parser")
                tags = sorted(set(t.name for t in soup.find_all()))
                print(f"  iframe 태그 목록: {tags}")
                ol = soup.find("ol")
                if ol:
                    print(f"  <ol> 내용 (첫 300자): {str(ol)[:300]}")

            reviews = parse_reviews_from_html(html)
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
    parser = argparse.ArgumentParser(description="beaund.com 리뷰 크롤러")
    parser.add_argument("--product_no", type=int, default=53, help="상품 번호 (기본 53)")
    parser.add_argument("--out", default="beaund_reviews.csv", help="저장할 CSV 파일명")
    parser.add_argument("--pages", type=int, default=30, help="최대 페이지 수 (기본 30)")
    parser.add_argument("--delay", type=float, default=1.0, help="페이지 간 딜레이(초)")
    args = parser.parse_args()

    print(f"beaund.com 상품 #{args.product_no} 리뷰 수집 시작")
    reviews = crawl(args.product_no, max_pages=args.pages, delay=args.delay)
    save_csv(reviews, args.out)


if __name__ == "__main__":
    main()
