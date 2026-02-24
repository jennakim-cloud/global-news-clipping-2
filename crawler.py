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

# ─── 키워드 번역 사전 (업데이트 버전) ─────────────────────────────────────────
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
    "안타":        {"ja": "安踏",                   "zh": "安踏",       "tw": "安踏"},
}

# ─── 매체 설정 (중국 & 대만 통합) ─────────────────────────────────────────────
SOURCES = {
    "china": [
        # 검색 엔진: 바이두
        {
            "name": "百度新闻",
            "url": "https://news.baidu.com",
            "search_url": "https://news.baidu.com/ns?word={keyword}&tn=news&from=news&ie=utf-8&rn=20",
            "language": "zh", "flag": "🇨🇳", "parser": "baidu_news",
        },
        # 개별 매체 리스트
        {"name": "界面新闻",          "url": "https://www.jiemian.com",     "search_url": "https://www.jiemian.com/search.html?keywords={keyword}",    "language": "zh", "flag": "🇨🇳"},
        {"name": "36氪",              "url": "https://36kr.com",            "search_url": "https://36kr.com/search/articles/{keyword}",                "language": "zh", "flag": "🇨🇳"},
        {"name": "亿邦动力",          "url": "https://www.ebrun.com",       "search_url": "https://www.ebrun.com/search/?q={keyword}",                 "language": "zh", "flag": "🇨🇳"},
        {"name": "新浪",              "url": "https://www.sina.com.cn",     "search_url": "https://search.sina.com.cn/?q={keyword}&range=all&c=news",  "language": "zh", "flag": "🇨🇳"},
        {"name": "Luxe.co",           "url": "https://luxe.co",             "search_url": "https://luxe.co/?s={keyword}",                              "language": "zh", "flag": "🇨🇳"},
        {"name": "WWD Greater China", "url": "https://wwdgreaterchina.com", "search_url": "https://wwdgreaterchina.com/?s={keyword}",                  "language": "zh", "flag": "🇨🇳"},
        {"name": "Vogue China",       "url": "https://www.vogue.com.cn",    "search_url": "https://www.vogue.com.cn/search?q={keyword}",               "language": "zh", "flag": "🇨🇳"},
    ],
    "taiwan": [
        # 대만 구글 뉴스 RSS
        {
            "name": "Google News (台灣)",
            "url": "https://news.google.com",
            "search_url": "https://news.google.com/rss/search?q={keyword}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant",
            "language": "tw",
            "flag": "🇹🇼",
            "parser": "google_news_rss",
        },
    ],
}

# ─── 유틸리티 함수 (날짜, 텍스트, 번역) ───────────────────────────────────────
DATE_PATTERNS = [
    (r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", "%Y-%m-%dT%H:%M:%S"),
    (r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", "%Y-%m-%d %H:%M:%S"),
    (r"\d{4}/\d{2}/\d{2}", "%Y/%m/%d"),
    (r"\d{4}-\d{2}-\d{2}", "%Y-%m-%d"),
    (r"\d{4}年\d{1,2}월\d{1,2}일", "%Y年%m월%d일"),
]

def parse_date(text: str):
    if not text: return None
    text = text.strip()
    for pattern, fmt in DATE_PATTERNS:
        m = re.search(pattern, text)
        if m:
            try: return datetime.strptime(m.group(0), fmt)
            except: continue
    return None

def clean_text(text: str) -> str:
    if not text: return ""
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def translate_to_korean(text: str, src_lang: str = "auto") -> str:
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
class IntegratedNewsCrawler:
    def __init__(self, days: int = 7):
        self.days = days
        self.cutoff = datetime.now() - timedelta(days=days)
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def is_within_cutoff(self, date_str: str, is_china: bool = False) -> bool:
        if not date_str: return False
        if is_china:
            now = datetime.now()
            if "小时前" in date_str:
                h = int(re.search(r"(\d+)", date_str).group(1))
                return (now - timedelta(hours=h)) >= self.cutoff
            if "分钟前" in date_str or "刚刚" in date_str or "今天" in date_str:
                return True
        
        dt = parse_date(date_str)
        return dt >= self.cutoff if dt else False

    # RSS 파서 (대만용)
    def parse_google_news_rss(self, raw_xml: str) -> list:
        results = []
        try:
            root = ET.fromstring(raw_xml.encode("utf-8"))
            for item in root.iter("item"):
                title = clean_text(item.findtext("title"))
                url = item.findtext("link")
                date = item.findtext("pubDate")
                if self.is_within_cutoff(date):
                    results.append({"title": title, "url": url, "date": date, "media": "Google News"})
        except: pass
        return results[:15]

    # 바이두 파서 (중국용)
    def parse_baidu_news(self, soup: BeautifulSoup) -> list:
        results = []
        for item in soup.select("div.result"):
            a_tag = item.select_one("h3.c-title a")
            if not a_tag: continue
            title = clean_text(a_tag.get_text())
            url = a_tag.get("href")
            date_tag = item.select_one("span.c-author")
            date_str = date_tag.get_text() if date_tag else ""
            if self.is_within_cutoff(date_str, is_china=True):
                results.append({"title": title, "url": url, "date": date_str, "media": "Baidu"})
        return results[:15]

    def crawl(self, category: str, keyword_ko: str):
        all_articles = []
        sources = SOURCES.get(category, [])
        for src in sources:
            # 키워드 변역
            kw = KEYWORD_TRANSLATIONS.get(keyword_ko, {}).get(src["language"], keyword_ko)
            search_url = src["search_url"].format(keyword=quote(kw))
            
            try:
                resp = self.session.get(search_url, timeout=15)
                if src.get("parser") == "google_news_rss":
                    articles = self.parse_google_news_rss(resp.text)
                elif src.get("parser") == "baidu_news":
                    articles = self.parse_baidu_news(BeautifulSoup(resp.text, "html.parser"))
                else:
                    # 일반 매체 범용 파서 (단순화)
                    articles = [] 
                
                for a in articles:
                    a.update({"source": src["name"], "flag": src["flag"], "lang": src["language"]})
                    all_articles.append(a)
                time.sleep(1)
            except: continue
        return all_articles

# ─── 실행 파이프라인 ─────────────────────────────────────────────────────────
def run_integrated_pipeline(keyword: str, days: int = 7):
    crawler = IntegratedNewsCrawler(days=days)
    results = {}
    
    for region in ["china", "taiwan"]:
        print(f"--- {region} 수집 시작 ---")
        articles = crawler.crawl(region, keyword)
        
        # 한국어 번역 추가
        for a in articles:
            a["title_ko"] = translate_to_korean(a["title"], a["lang"])
        
        results[region] = articles
    
    return results

# 실행 예시
# final_data = run_integrated_pipeline("무신사", days=3)
