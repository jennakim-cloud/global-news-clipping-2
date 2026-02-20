"""
crawler.py - 야후 재팬 뉴스 통합 검색 및 Google 번역 모듈
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from urllib.parse import quote, urljoin
import time
import re

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,ja;q=0.6,zh-CN;q=0.5",
}

# 기존 키워드 맵핑 유지
KEYWORD_TRANSLATIONS = {
    "무신사":      {"ja": "ムシンサ",          "zh": "MUSINSA",   "tw": "MUSINSA"},
    "한국 패션":   {"ja": "韓国ファッション", "zh": "韩国时尚",   "tw": "韓國時尚"},
    "K-뷰티":      {"ja": "Kビューティー",   "zh": "K美妆",     "tw": "K美妝"},
    "이커머스":    {"ja": "EC",              "zh": "电商",      "tw": "電商"},
    "패션":        {"ja": "ファッション",     "zh": "时尚",      "tw": "時尚"},
    "리테일":      {"ja": "リテール",        "zh": "零售",      "tw": "零售"},
    "뷰티":        {"ja": "ビューティー",     "zh": "美妆",      "tw": "美妝"},
    "SPA":         {"ja": "SPA",             "zh": "SPA",       "tw": "SPA"},
    "럭셔리":      {"ja": "ラグジュアリー",  "zh": "奢侈品",    "tw": "奢侈品"},
    "지속가능성":  {"ja": "サステナビリティ", "zh": "可持续发展", "tw": "永續發展"},
}

# 매체 설정 (일본은 야후 뉴스로 통합)
SOURCES = {
    "japan": [
        {
            "name": "Yahoo Japan News", 
            "url": "https://news.yahoo.co.jp", 
            "search_url": "https://news.yahoo.co.jp/search?p={keyword}&ei=utf-8&sort=pub", 
            "language": "ja", 
            "flag": "🇯🇵"
        },
    ],
    "china": [
        {"name": "界面新闻", "url": "https://www.jiemian.com", "search_url": "https://www.jiemian.com/search.html?keywords={keyword}", "language": "zh", "flag": "🇨🇳"},
        {"name": "36氪", "url": "https://36kr.com", "search_url": "https://36kr.com/search/articles/{keyword}", "language": "zh", "flag": "🇨🇳"},
        {"name": "第一财经", "url": "https://www.yicai.com", "search_url": "https://www.yicai.com/search/?keys={keyword}", "language": "zh", "flag": "🇨🇳"},
        {"name": "Luxe.co", "url": "https://luxe.co", "search_url": "https://luxe.co/?s={keyword}", "language": "zh", "flag": "🇨🇳"},
    ],
    "taiwan": [
        {"name": "數位時代", "url": "https://www.bnext.com.tw", "search_url": "https://www.bnext.com.tw/search/{keyword}", "language": "tw", "flag": "🇹🇼"},
        {"name": "工商時報", "url": "https://www.ctee.com.tw", "search_url": "https://www.ctee.com.tw/search?q={keyword}", "language": "tw", "flag": "🇹🇼"},
    ],
}

# 날짜 파싱 유틸리티
def parse_date(text: str):
    if not text: return None
    text = text.strip()
    now = datetime.now()
    # 야후 재팬 전용 상대 시간 처리
    if '分前' in text:
        m = re.search(r'(\d+)', text)
        return now - timedelta(minutes=int(m.group(1))) if m else now
    if '時間前' in text:
        m = re.search(r'(\d+)', text)
        return now - timedelta(hours=int(m.group(1))) if m else now
    if '昨日' in text:
        return now - timedelta(days=1)
    
    patterns = [
        (r"\d{4}-\d{2}-\d{2}", "%Y-%m-%d"),
        (r"\d{4}/\d{2}/\d{2}", "%Y/%m/%d"),
        (r"\d{4}年\d{1,2}월\d{1,2}일", "%Y年%m월%d일"),
    ]
    for pattern, fmt in patterns:
        m = re.search(pattern, text)
        if m:
            try: return datetime.strptime(m.group(0), fmt)
            except: continue
    return None

def clean_text(text: str) -> str:
    if not text: return ""
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()

# Google 번역 API
def translate_to_korean(text: str, src_lang: str = "auto") -> str:
    if not text or not text.strip(): return text
    try:
        resp = requests.get(
            "https://translate.googleapis.com/translate_a/single",
            params={"client": "gtx", "sl": src_lang, "tl": "ko", "dt": "t", "q": text},
            timeout=10, headers=HEADERS
        )
        return "".join(seg[0] for seg in resp.json()[0] if seg[0]).strip()
    except: return text

class NewsCrawler:
    def __init__(self, days: int = 7):
        self.cutoff = datetime.now() - timedelta(days=days)
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
