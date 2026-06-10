# IROA 경쟁사 리뷰 크롤러

## 설치

```bash
pip install -r requirements.txt
python -m playwright install chromium
```

## 사용법

```bash
python crawler.py --url "https://www.well247.co.kr/product/detail.html?product_no=22" --out reviews.csv
```

### 옵션

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--url` | 상품 페이지 URL | 필수 |
| `--out` | 저장할 CSV 파일명 | `reviews.csv` |
| `--pages` | 최대 크롤링 페이지 수 | `10` |
| `--delay` | 페이지 간 딜레이(초) | `1.5` |

## 출력 형식 (CSV)

| 컬럼 | 설명 |
|------|------|
| author | 작성자 |
| rating | 별점 |
| date | 작성일 |
| content | 리뷰 내용 |
