import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from urllib.parse import quote, urljoin
import time
import re

# 1. HEADERS 설정
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,ja;q=0.6,zh-CN;q=0.5",
}

# 2. KEYWORD_TRANSLATIONS 설정 (app.py에서 임포트함)
KEYWORD_TRANSLATIONS = {
    "무신사":      {"ja": "ムシンサ",          "zh": "MUSINSA",   "tw": "MUSINSA"},
    "한국 패션":   {"ja": "韓国ファッション", "zh": "韩国时尚",   "tw": "韓國時尚"},
    "K-뷰티":      {"ja": "K뷰ティー",   "zh": "K美妆",     "tw": "K美妝"},
    "이커머스":    {"ja": "EC",              "zh": "电商",      "tw": "電商"},
    "패션":        {"ja": "ファッション",     "zh": "时尚",      "tw": "時尚"},
    "리테일":      {"ja": "リテール",        "zh": "零售",      "tw": "零售"},
}

# 3. SOURCES 설정 (app.py에서 임포트함 - 일본은 야후 뉴스로 통합)
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
    ],
    "taiwan": [
        {"name": "數位時代", "url": "https://www.bnext.com.tw", "search_url": "https://www.bnext.com.tw/search/{keyword}", "language": "tw", "flag": "🇹🇼"},
        {"name": "工商時報", "url": "https://www.ctee.com.tw", "search_url": "https://www.ctee.com.tw/search?q={keyword}", "language": "tw", "flag": "🇹🇼"},
    ],
}

# --- 날짜 및 텍스트 처리 함수 ---
def parse_date(text: str):
    if not text: return None
    text = text.strip()
    now = datetime.now()
    if '分前' in text:
        m = re.search(r'(\d+)', text); return now - timedelta(minutes=int(m.group(1))) if m else now
    if '時間前' in text:
        m = re.search(r'(\d+)', text); return now - timedelta(hours=int(m.group(1))) if m else now
    if '昨日' in text: return now - timedelta(days=1)
    
    patterns = [(r"\d{4}-\d{2}-\d{2}", "%Y-%m-%d"), (r"\d{4}/\d{2}/\d{2}", "%Y/%m/%d")]
    for pattern, fmt in patterns:
        m = re.search(pattern, text)
        if m:
            try: return datetime.strptime(m.group(0), fmt)
            except: continue
    return None

def clean_text(text: str):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text or "")).strip()

def translate_to_korean(text: str, src_lang: str = "auto"):
    if not text or not text.strip(): return text
    try:
        resp = requests.get("https://translate.googleapis.com/translate_a/single",
                            params={"client": "gtx", "sl": src_lang, "tl": "ko", "dt": "t", "q": text}, timeout=10)
        return "".join(seg[0] for seg in resp.json()[0] if seg[0]).strip()
    except: return text

# --- 크롤러 클래스 ---
class NewsCrawler:
    def __init__(self, days=7):
        self.cutoff = datetime.now() - timedelta(days=days)
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def fetch(self, url):
        try:
            resp = self.session.get(url, timeout=15)
            resp.encoding = resp.apparent_encoding
            return BeautifulSoup(resp.text, "html.parser")
        except: return None

    def parse_yahoo_japan(self, soup):
        results = []
        for item in soup.select('li.sw-Card'):
            title_tag = item.select_one('h3.sw-Card__title')
            a_tag = item.select_one('a.sw-Card__titleInner')
            date_tag = item.select_one('span.sw-Card__time')
            source_tag = item.select_one('span.sw-Card__sender')
            if title_tag and a_tag:
                dt = parse_date(date_tag.get_text() if date_tag else "")
                if dt and dt >= self.cutoff:
                    results.append({
                        "title": clean_text(title_tag.get_text()), "url": a_tag['href'],
                        "date": date_tag.get_text() if date_tag else "",
                        "source": source_tag.get_text() if source_tag else "Yahoo Japan",
                        "flag": "🇯🇵", "language": "ja"
                    })
        return results

    def parse_generic(self, soup, base_url):
        candidates = []
        for h in soup.find_all(["h2", "h3"]):
            a = h.find("a", href=True) or h.find_parent("a", href=True)
            if a: candidates.append({"title": clean_text(h.get_text()), "url": urljoin(base_url, a["href"]), "date": ""})
        return candidates

    def crawl_category(self, category, keyword_ko, progress_callback=None):
        all_articles = []
        for src in SOURCES.get(category, []):
            kw = KEYWORD_TRANSLATIONS.get(keyword_ko, {}).get(src["language"], keyword_ko)
            if progress_callback: progress_callback(src["name"], kw)
            soup = self.fetch(src["search_url"].format(keyword=quote(kw)))
            if soup:
