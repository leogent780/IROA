"""API 응답 필드명 확인용"""
import requests
import json

resp = requests.get(
    "https://review-widget.alphwidget.com/v2/api-widget",
    params={
        "page": 1,
        "page_size": 2,
        "sort": "-created_at",
        "media_only": "false",
        "product_no": 22,
        "widget_code": "80831c03",
        "device": "w",
    },
    headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
        "Referer": "https://www.well247.co.kr/",
        "Origin": "https://www.well247.co.kr",
    },
    timeout=15,
)
print("Status:", resp.status_code)
data = resp.json()
if data:
    print("\n=== 첫 번째 리뷰 전체 필드 ===")
    print(json.dumps(data[0], ensure_ascii=False, indent=2))
