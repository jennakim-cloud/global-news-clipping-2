"""
crawler.py - 뉴스 수집 & Google 번역 모듈
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from urllib.parse import quote, urljoin
import time
import re

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,ja;q=0.6,zh-CN;q=0.5",
}

KEYWORD_TRANSLATIONS = {
    "무신사":      {"ja": "무신사",          "zh": "MUSINSA",   "tw": "MUSINSA"},
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

SOURCES = {
    "japan": [
        {"name": "WWD Japan",        "url": "https://www.wwdjapan.com",      "search_url": "https://www.wwdjapan.com/search?q={keyword}",              "language": "ja", "flag": "🇯🇵"},
        {"name": "Fashionsnap",      "url": "https://www.fashionsnap.com",   "search_url": "https://www.fashionsnap.com/?s={keyword}",                  "language": "ja", "flag": "🇯🇵"},
        {"name": "Yahoo Japan",      "url": "https://news.yahoo.co.jp",      "search_url": "https://news.yahoo.co.jp/search?p={keyword}&ei=UTF-8",      "language": "ja", "flag": "🇯🇵"},
        {"name": "日経MJ",           "url": "https://www.nikkei.com",        "search_url": "https://www.nikkei.com/search?keyword={keyword}",           "language": "ja", "flag": "🇯🇵"},
        {"name": "繊研新聞",         "url": "https://senken.co.jp",          "search_url": "https://senken.co.jp/?s={keyword}",                         "language": "ja", "flag": "🇯🇵"},
    ],
    "china": [
        {"name": "界面新闻",         "url": "https://www.jiemian.com",       "search_url": "https://www.jiemian.com/search.html?keywords={keyword}",    "language": "zh", "flag": "🇨🇳"},
        {"name": "36氪",             "url": "https://36kr.com",              "search_url": "https://36kr.com/search/articles/{keyword}",                "language": "zh", "flag": "🇨🇳"},
        {"name": "亿邦动力",         "url": "https://www.ebrun.com",         "search_url": "https://www.ebrun.com/search/?q={keyword}",                 "language": "zh", "flag": "🇨🇳"},
        {"name": "WWD Greater China","url": "https://wwdgreaterchina.com",   "search_url": "https://wwdgreaterchina.com/?s={keyword}",                  "language": "zh", "flag": "🇨🇳"},
        {"name": "Vogue China",      "url": "https://www.vogue.com.cn",      "search_url": "https://www.vogue.com.cn/search?q={keyword}",               "language": "zh", "flag": "🇨🇳"},
        {"name": "第一财经",         "url": "https://www.yicai.com",         "search_url": "https://www.yicai.com/search/?keys={keyword}",              "language": "zh", "flag": "🇨🇳"},
        {"name": "赢商网",           "url": "https://m.winshang.com",        "search_url": "https://m.winshang.com/search.html?keyword={keyword}",      "language": "zh", "flag": "🇨🇳"},
        {"name": "新浪",             "url": "https://www.sina.com.cn",       "search_url": "https://search.sina.com.cn/?q={keyword}&range=all&c=news",  "language": "zh", "flag": "🇨🇳"},
        {"name": "Luxe.co",          "url": "https://luxe.co",               "search_url": "https://luxe.co/?s={keyword}",                              "language": "zh", "flag": "🇨🇳"},
    ],
    "taiwan": [
        {"name": "數位時代",         "url": "https://www.bnext.com.tw",      "search_url": "https://www.bnext.com.tw/search/{keyword}",                 "language": "tw", "flag": "🇹🇼"},
        {"name": "工商時報",         "url": "https://www.ctee.com.tw",       "search_url": "https://www.ctee.com.tw/search?q={keyword}",                "language": "tw", "flag": "🇹🇼"},
    ],
}

# ─── 날짜 파싱 ───────────────────────────────────────────────────────────────

DATE_PATTERNS = [
    (r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", "%Y-%m-%dT%H:%M:%S"),
    (r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", "%Y-%m-%d %H:%M:%S"),
    (r"\d{4}/\d{2}/\d{2} \d{2}:\d{2}",        "%Y/%m/%d %H:%M"),
    (r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}",        "%Y-%m-%d %H:%M"),
    (r"\d{4}-\d{2}-\d{2}",                    "%Y-%m-%d"),
    (r"\d{4}/\d{2}/\d{2}",                    "%Y/%m/%d"),
    (r"\d{4}年\d{1,2}月\d{1,2}日",            "%Y年%m月%d日"),
]

def parse_date(text: str):
    if not text:
        return None
    text = text.strip()
    # ISO 타임존 제거
    text = re.sub(r"[+Z]\d{2}:?\d{0,2}$", "", text)
    for pattern, fmt in DATE_PATTERNS:
        m = re.search(pattern, text)
        if m:
            try:
                return datetime.strptime(m.group(0), fmt)
            except ValueError:
                continue
    return None

def clean_text(text: str) -> str:
    """HTML 태그 및 불필요한 공백 제거"""
    if not text:
        return ""
    # HTML 태그 완전 제거
    text = re.sub(r"<[^>]+>", " ", text)
    # HTML 엔티티 치환
    text = (text.replace("&amp;", "&").replace("&lt;", "<")
                .replace("&gt;", ">").replace("&nbsp;", " ").replace("&quot;", '"'))
    # 연속 공백/줄바꿈 정리
    text = re.sub(r"\s+", " ", text).strip()
    return text

# ─── Google 번역 ─────────────────────────────────────────────────────────────

def translate_to_korean(text: str, src_lang: str = "auto") -> str:
    if not text or not text.strip():
        return text
    try:
        resp = requests.get(
            "https://translate.googleapis.com/translate_a/single",
            params={"client": "gtx", "sl": src_lang, "tl": "ko", "dt": "t", "q": text},
            timeout=10, headers=HEADERS,
        )
        resp.raise_for_status()
        data = resp.json()
        return "".join(seg[0] for seg in data[0] if seg[0]).strip() or text
    except Exception:
        return text

def translate_keyword_to_lang(keyword_ko: str, lang: str) -> str:
    if keyword_ko in KEYWORD_TRANSLATIONS:
        return KEYWORD_TRANSLATIONS[keyword_ko].get(lang, keyword_ko)
    lang_map = {"ja": "ja", "zh": "zh-CN", "tw": "zh-TW"}
    try:
        resp = requests.get(
            "https://translate.googleapis.com/translate_a/single",
            params={"client": "gtx", "sl": "ko", "tl": lang_map.get(lang, "ja"), "dt": "t", "q": keyword_ko},
            timeout=10, headers=HEADERS,
        )
        data = resp.json()
        return "".join(seg[0] for seg in data[0] if seg[0]).strip() or keyword_ko
    except Exception:
        return keyword_ko

# ─── 크롤러 ──────────────────────────────────────────────────────────────────

class NewsCrawler:
    def __init__(self, days: int = 7):
        self.days = days
        self.cutoff = datetime.now() - timedelta(days=days)
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def fetch(self, url: str, timeout: int = 15):
        try:
            resp = self.session.get(url, timeout=timeout)
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding or "utf-8"
            return BeautifulSoup(resp.text, "html.parser")
        except Exception:
            return None

    def is_within_cutoff(self, date_str: str) -> bool:
        """
        [Fix 1] 날짜를 명확히 파싱한 경우에만 포함.
        날짜 불명(파싱 실패) → False (기간 외 기사 오염 방지 우선).
        """
        dt = parse_date(date_str)
        if dt is None:
            return False
        return dt >= self.cutoff

    def _find_date_in_tag(self, tag) -> str:
        """태그 내에서 날짜 문자열 추출 (여러 방법 순차 시도)"""
        # 1) <time datetime="">
        t = tag.find("time")
        if t:
            candidate = t.get("datetime") or t.get_text(strip=True)
            if parse_date(candidate):
                return candidate

        # 2) class에 date/time/pub 포함 태그
        d = tag.find(True, class_=re.compile(r"\b(date|time|pub|posted|created|updated)\b", re.I))
        if d:
            candidate = d.get("datetime") or d.get_text(strip=True)
            if parse_date(candidate):
                return candidate

        # 3) 텍스트 패턴 직접 탐색
        raw = tag.get_text(" ", strip=True)
        for pattern, _ in DATE_PATTERNS:
            m = re.search(pattern, raw)
            if m:
                return m.group(0)

        return ""

    def parse_generic(self, soup: BeautifulSoup, base_url: str) -> list[dict]:
        candidates = []
        seen = set()

        # (A) <article> 기반
        for article in soup.find_all("article"):
            title_tag = article.find(["h1", "h2", "h3", "h4"])
            a_tag = article.find("a", href=True)
            if not title_tag or not a_tag:
                continue
            title = clean_text(title_tag.get_text())
            url   = urljoin(base_url, a_tag["href"])
            date  = self._find_date_in_tag(article)
            if url not in seen and len(title) > 5:
                seen.add(url)
                candidates.append({"title": title, "url": url, "date": date})

        # (B) h2/h3 기반 (article 없을 때)
        if not candidates:
            for h in soup.find_all(["h2", "h3"]):
                a_tag = h.find("a", href=True) or h.find_parent("a", href=True)
                if not a_tag:
                    continue
                title  = clean_text(h.get_text())
                url    = urljoin(base_url, a_tag["href"])
                parent = h.find_parent(["li", "div", "section"])
                date   = self._find_date_in_tag(parent) if parent else ""
                if url not in seen and len(title) > 5:
                    seen.add(url)
                    candidates.append({"title": title, "url": url, "date": date})

        # [Fix 1] 엄격한 날짜 필터 적용
        return [c for c in candidates if self.is_within_cutoff(c["date"])][:12]

    def search_source(self, source: dict, keyword: str) -> list[dict]:
        soup = self.fetch(source["search_url"].format(keyword=quote(keyword)))
        if not soup:
            return []
        results = self.parse_generic(soup, source["url"])
        for r in results:
            r.update({"source": source["name"], "source_url": source["url"],
                       "language": source["language"], "flag": source.get("flag", "")})
        return results

    def crawl_category(self, category: str, keyword_ko: str, progress_callback=None) -> list[dict]:
        all_articles = []
        for source in SOURCES.get(category, []):
            keyword = translate_keyword_to_lang(keyword_ko, source["language"])
            if progress_callback:
                progress_callback(source["name"], keyword)
            all_articles.extend(self.search_source(source, keyword))
            time.sleep(0.8)
        return all_articles

# ─── 번역 일괄 처리 ──────────────────────────────────────────────────────────

def translate_articles(articles: list[dict], progress_callback=None) -> list[dict]:
    lang_map = {"ja": "ja", "zh": "zh-CN", "tw": "zh-TW"}
    for i, a in enumerate(articles):
        if progress_callback:
            progress_callback(i + 1, len(articles), a.get("source", ""))
        src = lang_map.get(a.get("language", "ja"), "auto")
        a["title_ko"] = translate_to_korean(a["title"], src_lang=src)
        time.sleep(0.3)
    return articles

# ─── 전체 파이프라인 ─────────────────────────────────────────────────────────

def run_pipeline(
    keyword_ko: str,
    days: int = 7,
    active_categories: list = None,
    on_status=None,
    on_progress=None,
) -> dict:
    if active_categories is None:
        active_categories = ["japan", "china", "taiwan"]

    def _s(msg):
        if on_status: on_status(msg)
    def _p(val, text=""):
        if on_progress: on_progress(min(val, 1.0), text)

    crawler = NewsCrawler(days=days)
    collected = {cat: [] for cat in ["japan", "china", "taiwan"]}
    total_sources = sum(len(SOURCES[c]) for c in active_categories)
    done = 0

    for cat in active_categories:
        label = {"japan": "🇯🇵 일본", "china": "🇨🇳 중국", "taiwan": "🇹🇼 대만"}[cat]
        _s(f"{label} 매체 수집 중...")

        def _cb(name, kw, _label=label):
            nonlocal done
            done += 1
            _p(done / total_sources * 0.6, f"{_label} · {name} ({kw})")

        collected[cat] = crawler.crawl_category(cat, keyword_ko, _cb)

    # 무신사 분리
    musinsa = []
    musinsa_kws = ["무신사", "musinsa", "ムシンサ"]
    for cat in active_categories:
        flagged = [a for a in collected[cat] if any(k in a.get("title","").lower() for k in musinsa_kws)]
        musinsa.extend(flagged)
        collected[cat] = [a for a in collected[cat] if a not in flagged]

    # 번역
    all_t = musinsa + collected["japan"] + collected["china"] + collected["taiwan"]
    _s(f"Google 번역 처리 중 (총 {len(all_t)}건)...")

    def _tcb(cur, total, source):
        _p(0.6 + (cur / max(total, 1)) * 0.4, f"번역 중 {cur}/{total} · {source}")

    translate_articles(all_t, _tcb)
    _p(1.0, "완료!")

    return {
        "musinsa": musinsa,
        "japan":   collected["japan"],
        "china":   collected["china"],
        "taiwan":  collected["taiwan"],
        "meta": {
            "keyword":      keyword_ko,
            "days":         days,
            "generated_at": datetime.now().strftime("%Y.%m.%d %H:%M"),
        },
    }
