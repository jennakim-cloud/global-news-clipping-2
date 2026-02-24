import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from urllib.parse import quote, urljoin
import time
import re
import xml.etree.ElementTree as ET

# ─── 헤더 ────────────────────────────────────────────────────────────────────
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,ja;q=0.6,zh-CN;q=0.5",
}

# ─── 키워드 번역 사전 ─────────────────────────────────────────────────────────
KEYWORD_TRANSLATIONS = {
    "무신사":      {"ja": "ムシンサ",              "zh": "MUSINSA",    "tw": "MUSINSA"},
    "한국 패션":   {"ja": "韓国ファッション",       "zh": "韩国时尚",   "tw": "韓國時尚"},
    "K-뷰티":      {"ja": "Kビューティー",          "zh": "K美妆",      "tw": "K美妝"},
    "이커머스":    {"ja": "EC",                    "zh": "电商",       "tw": "電商"},
    "패션":        {"ja": "ファッション",            "zh": "时尚",       "tw": "時尚"},
    "리테일":      {"ja": "リテール",               "zh": "零售",       "tw": "零售"},
    "뷰티":        {"ja": "ビューティー",            "zh": "美妝",       "tw": "美妝"},
    "SPA":         {"ja": "SPA",                   "zh": "SPA",        "tw": "SPA"},
    "패션 브랜드": {"ja": "ファッションブランド",    "zh": "时尚品牌",   "tw": "時尚品牌"},
    "유니클로":    {"ja": "ユニクロ",               "zh": "优衣库",     "tw": "Uniqlo"},
    "무인양품":    {"ja": "無印良品",               "zh": "无印良品",   "tw": "無印良品"},
    "안타":        {"ja": "アン타",                 "zh": "安踏",       "tw": "安踏"},
    "한국 브랜드": {"ja": "韓国ブランド",           "zh": "韩国品牌",   "tw": "韓國品牌"},
    "한국":        {"ja": "韓国",                   "zh": "韩国",       "tw": "韓國"},
    "한국발":      {"ja": "韓国発",                 "zh": "源自韩国",   "tw": "源自韓國"}
}

# ─── 매체 설정 ────────────────────────────────────────────────────────────────
SOURCES = {
    "japan": [
        {
            "name": "Google News (日本)",
            "url": "https://news.google.com",
            "search_url": "https://news.google.com/rss/search?q={keyword}&hl=ja&gl=JP&ceid=JP:ja",
            "language": "ja", "flag": "🇯🇵", "parser": "google_news_rss",
        },
    ],
    "china": [
        {
            "name": "百度新闻",
            "url": "https://news.baidu.com",
            "search_url": "https://news.baidu.com/ns?word={keyword}&tn=news&from=news&ie=utf-8&rn=20",
            "language": "zh", "flag": "🇨🇳", "parser": "baidu_news",
        },
        {"name": "界面新闻", "url": "https://www.jiemian.com", "search_url": "https://www.jiemian.com/search.html?keywords={keyword}", "language": "zh", "flag": "🇨🇳"},
        {"name": "36氪", "url": "https://36kr.com", "search_url": "https://36kr.com/search/articles/{keyword}", "language": "zh", "flag": "🇨🇳"},
        {"name": "Luxe.co", "url": "https://luxe.co", "search_url": "https://luxe.co/?s={keyword}", "language": "zh", "flag": "🇨🇳"},
        {"name": "WWD China", "url": "https://wwdgreaterchina.com", "search_url": "https://wwdgreaterchina.com/?s={keyword}", "language": "zh", "flag": "🇨🇳"},
    ],
    "taiwan": [
        {
            "name": "Google News (台灣)",
            "url": "https://news.google.com",
            "search_url": "https://news.google.com/rss/search?q={keyword}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant",
            "language": "tw", "flag": "🇹🇼", "parser": "google_news_rss",
        },
    ],
}

# ─── 유틸리티 함수 ────────────────────────────────────────────────────────────
def clean_text(text: str) -> str:
    if not text: return ""
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def translate_to_korean(text: str, src_lang: str = "auto") -> str:
    if not text: return ""
    try:
        resp = requests.get(
            "https://translate.googleapis.com/translate_a/single",
            params={"client": "gtx", "sl": src_lang, "tl": "ko", "dt": "t", "q": text},
            timeout=10, headers=HEADERS
        )
        return "".join(seg[0] for seg in resp.json()[0] if seg[0])
    except:
        return text

# ─── 크롤러 클래스 ───────────────────────────────────────────────────────────
class NewsCrawler:
    def __init__(self, days: int = 7):
        self.days = days
        self.cutoff = datetime.now() - timedelta(days=days)
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def is_within_cutoff(self, date_str: str) -> bool:
        if not date_str: return False
        # 중국어 상대 시간 처리
        now = datetime.now()
        if "小时前" in date_str:
            h = int(re.search(r"(\d+)", date_str).group(1))
            return (now - timedelta(hours=h)) >= self.cutoff
        if any(x in date_str for x in ["分钟前", "刚刚", "今天", "今日"]):
            return True
        
        # 일반 날짜 파싱 시도
        try:
            clean_date = re.search(r"\d{4}[-/년]\d{1,2}[-/월]\d{1,2}", date_str).group(0)
            fmt = "%Y-%m-%d" if "-" in clean_date else "%Y/%m/%d"
            dt = datetime.strptime(clean_date.replace("년","-").replace("월","-").replace("일",""), "%Y-%m-%d")
            return dt >= self.cutoff
        except:
            return True # 파싱 실패 시 일단 포함

    def parse_google_news_rss(self, raw_xml: str) -> list:
        results = []
        try:
            root = ET.fromstring(raw_xml.encode("utf-8"))
            for item in root.iter("item"):
                title = clean_text(item.findtext("title"))
                url = item.findtext("link")
                date = item.findtext("pubDate")
                results.append({"title": title, "url": url, "date": date})
        except: pass
        return results

    def parse_baidu_news(self, soup: BeautifulSoup) -> list:
        results = []
        for item in soup.select("div.result"):
            a = item.select_one("h3.c-title a")
            author = item.select_one("span.c-author")
            if a:
                results.append({
                    "title": clean_text(a.get_text()),
                    "url": a.get("href"),
                    "date": author.get_text() if author else "",
                    "media": author.get_text().split()[0] if author else "Baidu"
                })
        return results

    def search_source(self, source: dict, keyword: str) -> list:
        kw_translated = KEYWORD_TRANSLATIONS.get(keyword, {}).get(source["language"], keyword)
        url = source["search_url"].format(keyword=quote(kw_translated))
        try:
            resp = self.session.get(url, timeout=15)
            if source.get("parser") == "google_news_rss":
                articles = self.parse_google_news_rss(resp.text)
            elif source.get("parser") == "baidu_news":
                articles = self.parse_baidu_news(BeautifulSoup(resp.text, "html.parser"))
            else:
                articles = [] # 개별 매체 로직은 범용 파서 필요 시 추가
            
            # 메타데이터 주입 및 날짜 필터링
            valid = []
            for a in articles:
                if self.is_within_cutoff(a.get("date", "")):
                    a.update({"source": source["name"], "flag": source["flag"], "language": source["language"]})
                    valid.append(a)
            return valid
        except:
            return []

# ─── 파이프라인 (app.py 연결용) ────────────────────────────────────────────────
def run_pipeline(keyword_ko: str, days: int = 7, active_categories: list = None, on_status=None, on_progress=None) -> dict:
    crawler = NewsCrawler(days=days)
    if active_categories is None: active_categories = ["japan", "china", "taiwan"]
    
    collected = {cat: [] for cat in ["japan", "china", "taiwan"]}
    total_steps = sum(len(SOURCES[c]) for c in active_categories)
    current_step = 0

    for cat in active_categories:
        if on_status: on_status(f"{cat.upper()} 수집 중...")
        for src in SOURCES[cat]:
            current_step += 1
            if on_progress: on_progress(current_step / total_steps * 0.7, f"{src['name']} 수집 중")
            collected[cat].extend(crawler.search_source(src, keyword_ko))
            time.sleep(0.5)

    # 중복 제거 및 번역
    all_articles = []
    for cat in active_categories:
        seen = set()
        deduped = []
        for a in collected[cat]:
            if a["url"] not in seen:
                seen.add(a["url"])
                deduped.append(a)
                all_articles.append(a)
        collected[cat] = deduped

    if on_status: on_status("번역 처리 중...")
    for i, a in enumerate(all_articles):
        if on_progress: on_progress(0.7 + (i / len(all_articles) * 0.3), f"번역 중: {a['source']}")
        src_lang = "ja" if a["language"] == "ja" else ("zh-CN" if a["language"] == "zh" else "zh-TW")
        a["title_ko"] = translate_to_korean(a["title"], src_lang)
        time.sleep(0.2)

    if on_progress: on_progress(1.0, "수집 완료")
    
    return {
        **collected,
        "meta": {
            "keyword": keyword_ko,
            "days": days,
            "generated_at": datetime.now().strftime("%Y.%m.%d %H:%M")
        }
    }
