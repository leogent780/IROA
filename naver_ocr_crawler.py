"""
네이버 스마트스토어 리뷰 OCR 크롤러
사용법:
    pip install easyocr playwright pillow
    python -m playwright install chromium
    python naver_ocr_crawler.py --out naver_reviews.csv
"""
import argparse
import csv
import io
import os
import time

import easyocr
from PIL import Image
from playwright.sync_api import sync_playwright

URL = "https://smartstore.naver.com/vilarstore/products/13197800272#REVIEW"
CHROME_PROFILE = os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data")


def get_review_screenshots(max_pages: int) -> list[bytes]:
    screenshots = []

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=CHROME_PROFILE,
            channel="chrome",
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
            no_viewport=True,
        )
        page = context.new_page()
        page.set_viewport_size({"width": 1280, "height": 900})

        print(f"페이지 로드 중...")
        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)

        print(f"페이지 타이틀: {page.title()}")

        # 리뷰 영역으로 스크롤
        for sel in ["a[href*='REVIEW']", "li:has-text('리뷰')", "button:has-text('리뷰')"]:
            try:
                el = page.locator(sel).first
                if el.is_visible(timeout=2000):
                    el.click()
                    page.wait_for_timeout(3000)
                    break
            except Exception:
                continue

        for page_num in range(1, max_pages + 1):
            print(f"[{page_num}/{max_pages}] 스크린샷 촬영...")

            # 리뷰 영역 찾기
            review_area = None
            for sel in ["[class*='review']", "[id*='review']", "section:has([class*='review'])"]:
                try:
                    el = page.locator(sel).first
                    if el.is_visible(timeout=2000):
                        review_area = el
                        break
                except Exception:
                    continue

            if review_area:
                review_area.scroll_into_view_if_needed()
                page.wait_for_timeout(1000)
                shot = review_area.screenshot()
            else:
                shot = page.screenshot(full_page=False)

            screenshots.append(shot)
            print(f"  스크린샷 저장 ({len(shot)//1024}KB)")

            # 다음 페이지 클릭
            if page_num < max_pages:
                clicked = False
                for sel in [
                    f"[aria-label='{page_num + 1}']",
                    f"button:has-text('{page_num + 1}')",
                    "[class*='next']",
                    "[class*='Next']",
                    "button[class*='pagination']:has-text('다음')",
                ]:
                    try:
                        btn = page.locator(sel).first
                        if btn.is_visible(timeout=1500):
                            btn.click()
                            page.wait_for_timeout(3000)
                            clicked = True
                            break
                    except Exception:
                        continue
                if not clicked:
                    print("  다음 페이지 버튼 없음 — 종료")
                    break

        context.close()

    return screenshots


def ocr_screenshots(screenshots: list[bytes]) -> list[str]:
    print("OCR 초기화 중 (처음 실행시 모델 다운로드 필요)...")
    reader = easyocr.Reader(["ko", "en"], gpu=False)
    all_texts = []

    for i, shot in enumerate(screenshots):
        print(f"[{i+1}/{len(screenshots)}] OCR 처리 중...")
        img = Image.open(io.BytesIO(shot))
        results = reader.readtext(img, detail=0, paragraph=True)
        all_texts.extend(results)

    return all_texts


def save_csv(texts: list[str], path: str):
    if not texts:
        print("추출된 텍스트가 없습니다.")
        return
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["content"])
        writer.writeheader()
        for t in texts:
            t = t.strip()
            if len(t) > 10:
                writer.writerow({"content": t})
    print(f"저장 완료: {path} ({len(texts)}개 텍스트)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="naver_reviews.csv")
    parser.add_argument("--pages", type=int, default=10)
    args = parser.parse_args()

    screenshots = get_review_screenshots(max_pages=args.pages)
    if not screenshots:
        print("스크린샷 없음")
        return

    texts = ocr_screenshots(screenshots)
    save_csv(texts, args.out)


if __name__ == "__main__":
    main()
