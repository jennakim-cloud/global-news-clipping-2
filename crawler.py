"""
crawler.py - 뉴스 수집 & Google 번역 모듈

[일본] Google News RSS 기반 키워드 검색
  - JS 렌더링 없이 XML 파싱으로 안정적 수집
  - API 키 불필요
  - URL: https://news.google.com/rss/search?q={keyword}&hl=ja&gl=JP&ceid=JP:ja

[중국/대만] 매체별 HTML 크롤링
"""

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
    "무신사":      {"ja": "ムシンサ",        "zh": "MUSINSA",    "tw": "MUSINSA"},
    "한국 패션":   {"ja": "韓国ファッション", "zh": "韩国时尚",   "tw": "韓國時尚"},
    "K-뷰티":      {"ja": "Kビューティー",   "zh": "K美妆",      "tw": "K美妝"},
    "이커머스":    {"ja": "EC",              "zh": "电商",       "tw": "電商"},
    "패션":        {"ja": "ファッション",     "zh": "时尚",       "tw": "時尚"},
    "리테일":      {"ja": "リテール",        "zh": "零售",       "tw": "零售"},
    "뷰티":        {"ja": "ビューティー",     "zh": "美妆",       "tw": "美妝"},
    "SPA":         {"ja": "SPA",             "zh": "SPA",        "tw": "SPA"},
    "럭셔리":      {"ja": "ラグジュアリー",  "zh": "奢侈品",     "tw": "奢侈品"},
    "지속가능성":  {"ja": "サステナビリティ", "zh": "可持续发展", "tw": "永續發展"},
}

# ─── 매체 설정 ────────────────────────────────────────────────────────────────

SOURCES = {
    "japan": [
        {
            "name": "Google News (日本)",
            "url": "https://news.google.com",
            # hl=ja : 일본어 UI / gl=JP : 일본 지역 / ceid=JP:ja : 일본어 에디션
            "search_url": "https://news.google.com/rss/search?q={keyword}&hl=ja&gl=JP&ceid=JP:ja",
            "language": "ja",
            "flag": "🇯🇵",
            "parser": "google_news_rss",
        },
    ],
    "china": [
        {"name": "界面新闻",          "url": "https://www.jiemian.com",     "search_url": "https://www.jiemian.com/search.html?keywords={keyword}",   "language": "zh", "flag": "🇨🇳"},
        {"name": "36氪",              "url": "https://36kr.com",            "search_url": "https://36kr.com/search/articles/{keyword}",               "language": "zh", "flag": "🇨🇳"},
        {"name": "亿邦动力",          "url": "https://www.ebrun.com",       "search_url": "https://www.ebrun.com/search/?q={keyword}",                "language": "zh", "flag": "🇨🇳"},
        {"name": "WWD Greater China", "url": "https://wwdgreaterchina.com", "search_url": "https://wwdgreaterchina.com/?s={keyword}",                 "language": "zh", "flag": "🇨🇳"},
        {"name": "Vogue China",       "url": "https://www.vogue.com.cn",    "search_url": "https://www.vogue.com.cn/search?q={keyword}",              "language": "zh", "flag": "🇨🇳"},
        {"name": "第一财经",          "url": "https://www.yicai.com",       "search_url": "https://www.yicai.com/search/?keys={keyword}",             "language": "zh", "flag": "🇨🇳"},
        {"name": "赢商网",            "url": "https://m.winshang.com",      "search_url": "https://m.winshang.com/search.html?keyword={keyword}",     "language": "zh", "flag": "🇨🇳"},
        {"name": "新浪",              "url": "https://www.sina.com.cn",     "search_url": "https://search.sina.com.cn/?q={keyword}&range=all&c=news", "language": "zh", "flag": "🇨🇳"},
        {"name": "Luxe.co",           "url": "https://luxe.co",             "search_url": "https://luxe.co/?s={keyword}",                             "language": "zh", "flag": "🇨🇳"},
    ],
    "taiwan": [
        {"name": "數位時代", "url": "https://www.bnext.com.tw", "search_url": "https://www.bnext.com.tw/search/{keyword}",  "language": "tw", "flag": "🇹🇼"},
        {"name": "工商時報", "url": "https://www.ctee.com.tw",  "search_url": "https://www.ctee.com.tw/search?q={keyword}", "language": "tw", "flag": "🇹🇼"},
    ],
}

# ─── 날짜 파싱 ────────────────────────────────────────────────────────────────

# RSS pubDate 형식 (RFC 2822)
RFC2822_PATTERN = re.compile(
    r"(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{4})\s+(\d{2}:\d{2}:\d{2})"
)
MONTH_MAP = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4,  "May": 5,  "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}

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
    """
    날짜 문자열 파싱.
    RSS pubDate (RFC 2822) / ISO 8601 / 일반 날짜 형식 모두 지원.
    """
    if not text:
        return None
    text = text.strip()

    # RFC 2822: "20 Feb 2026 03:00:00 GMT"
    m = RFC2822_PATTERN.search(text)
    if m:
        day, mon_str, year, time_str = m.groups()
        try:
            return datetime(int(year), MONTH_MAP[mon_str], int(day),
                            *map(int, time_str.split(":")))
        except (ValueError, KeyError):
            pass

    # ISO 타임존 제거 후 일반 패턴
    text_clean = re.sub(r"[+Z]\d{2}:?\d{0,2}$", "", text)
    for pattern, fmt in DATE_PATTERNS:
        m = re.search(pattern, text_clean)
        if m:
            try:
                return datetime.strptime(m.group(0), fmt)
            except ValueError:
                continue

    return None


def clean_text(text: str) -> str:
    """HTML 태그·엔티티·과도한 공백 제거"""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = (text.replace("&amp;", "&").replace("&lt;", "<")
                .replace("&gt;", ">").replace("&nbsp;", " ").replace("&quot;", '"'))
    return re.sub(r"\s+", " ", text).strip()


# ─── Google 번역 ──────────────────────────────────────────────────────────────

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
        return "".join(seg[0] for seg in resp.json()[0] if seg[0]).strip() or text
    except Exception:
        return text


def translate_keyword_to_lang(keyword_ko: str, lang: str) -> str:
    """키워드를 대상 언어로 번역 (사전 우선 → Google 번역 fallback)"""
    if keyword_ko in KEYWORD_TRANSLATIONS:
        return KEYWORD_TRANSLATIONS[keyword_ko].get(lang, keyword_ko)
    lang_map = {"ja": "ja", "zh": "zh-CN", "tw": "zh-TW"}
    try:
        resp = requests.get(
            "https://translate.googleapis.com/translate_a/single",
            params={"client": "gtx", "sl": "ko", "tl": lang_map.get(lang, "ja"), "dt": "t", "q": keyword_ko},
            timeout=10, headers=HEADERS,
        )
        return "".join(seg[0] for seg in resp.json()[0] if seg[0]).strip() or keyword_ko
    except Exception:
        return keyword_ko


# ─── 크롤러 ──────────────────────────────────────────────────────────────────

class NewsCrawler:
    def __init__(self, days: int = 7):
        self.days = days
        self.cutoff = datetime.now() - timedelta(days=days)
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def fetch_raw(self, url: str, timeout: int = 15) -> str | None:
        """원시 텍스트 반환 (RSS XML 파싱용)"""
        try:
            resp = self.session.get(url, timeout=timeout)
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding or "utf-8"
            return resp.text
        except Exception:
            return None

    def fetch(self, url: str, timeout: int = 15) -> BeautifulSoup | None:
        """BeautifulSoup 반환 (HTML 크롤링용)"""
        raw = self.fetch_raw(url, timeout)
        return BeautifulSoup(raw, "html.parser") if raw else None

    def is_within_cutoff(self, date_str: str) -> bool:
        """날짜를 명확히 파싱한 경우에만 포함 (날짜 불명 → False)"""
        dt = parse_date(date_str)
        if dt is None:
            return False
        return dt >= self.cutoff

    # ── Google News RSS 파서 ──────────────────────────────────────────────────

    def parse_google_news_rss(self, raw_xml: str, source_flag: str = "🇯🇵") -> list[dict]:
        """
        Google News RSS XML을 파싱해 기사 목록 반환.

        RSS <item> 구조:
          <title>기사 제목 - 매체명</title>
          <link>https://news.google.com/rss/articles/...</link>
          <pubDate>Thu, 20 Feb 2026 03:00:00 GMT</pubDate>
          <source url="...">매체명</source>
        """
        results = []
        try:
            root = ET.fromstring(raw_xml.encode("utf-8"))
        except ET.ParseError:
            return []

        # XML 네임스페이스 처리
        ns = {"media": "http://search.yahoo.com/mrss/"}

        for item in root.iter("item"):
            # 제목 (Google News RSS는 "기사제목 - 매체명" 형식)
            title_el = item.find("title")
            if title_el is None or not title_el.text:
                continue
            raw_title = clean_text(title_el.text)

            # "제목 - 매체명" 에서 매체명 분리
            media_name = ""
            if " - " in raw_title:
                parts      = raw_title.rsplit(" - ", 1)
                title      = parts[0].strip()
                media_name = parts[1].strip()
            else:
                title = raw_title

            if len(title) < 5:
                continue

            # URL
            link_el = item.find("link")
            # Google News RSS의 <link>는 텍스트가 아니라 다음 요소 앞에 위치
            # 대안: <guid>
            url = ""
            if link_el is not None and link_el.text:
                url = link_el.text.strip()
            if not url:
                guid_el = item.find("guid")
                if guid_el is not None and guid_el.text:
                    url = guid_el.text.strip()

            # <source> 태그에서 매체명 보완
            source_el = item.find("source")
            if source_el is not None and source_el.text:
                media_name = media_name or clean_text(source_el.text)

            # 날짜
            pub_el = item.find("pubDate")
            date_str = pub_el.text.strip() if pub_el is not None and pub_el.text else ""

            if not self.is_within_cutoff(date_str):
                continue

            results.append({
                "title":   title,
                "url":     url,
                "date":    date_str,
                "media":   media_name,   # 원본 매체명 보존
            })

        return results[:20]

    # ── 범용 HTML 파서 ────────────────────────────────────────────────────────

    def _find_date_in_tag(self, tag) -> str:
        t = tag.find("time")
        if t:
            candidate = t.get("datetime") or t.get_text(strip=True)
            if parse_date(candidate):
                return candidate
        d = tag.find(True, class_=re.compile(r"\b(date|time|pub|posted|created|updated)\b", re.I))
        if d:
            candidate = d.get("datetime") or d.get_text(strip=True)
            if parse_date(candidate):
                return candidate
        raw = tag.get_text(" ", strip=True)
        for pattern, _ in DATE_PATTERNS:
            m = re.search(pattern, raw)
            if m:
                return m.group(0)
        return ""

    def parse_generic(self, soup: BeautifulSoup, base_url: str) -> list[dict]:
        candidates = []
        seen = set()

        for article in soup.find_all("article"):
            title_tag = article.find(["h1", "h2", "h3", "h4"])
            a_tag     = article.find("a", href=True)
            if not title_tag or not a_tag:
                continue
            title = clean_text(title_tag.get_text())
            url   = urljoin(base_url, a_tag["href"])
            date  = self._find_date_in_tag(article)
            if url not in seen and len(title) > 5:
                seen.add(url)
                candidates.append({"title": title, "url": url, "date": date})

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

        return [c for c in candidates if self.is_within_cutoff(c["date"])][:12]

    # ── 매체 검색 (파서 분기) ─────────────────────────────────────────────────

    def search_source(self, source: dict, keyword: str) -> list[dict]:
        search_url  = source["search_url"].format(keyword=quote(keyword))
        parser_name = source.get("parser", "generic")

        if parser_name == "google_news_rss":
            # RSS는 raw XML로 가져와서 ET로 파싱
            raw = self.fetch_raw(search_url)
            results = self.parse_google_news_rss(raw, source.get("flag", "🇯🇵")) if raw else []
        else:
            soup    = self.fetch(search_url)
            results = self.parse_generic(soup, source["url"]) if soup else []

        # URL 패턴 필터 (카테고리·태그 링크 제거)
        exclude_patterns   = source.get("exclude_url_patterns", [])
        exclude_exact_urls = set(source.get("exclude_exact_urls", []))
        if exclude_patterns or exclude_exact_urls:
            before  = len(results)
            results = [
                r for r in results
                if r.get("url", "") not in exclude_exact_urls
                and not any(p in r.get("url", "") for p in exclude_patterns)
            ]
            if before - len(results):
                print(f"  [{source['name']}] 비기사 링크 {before - len(results)}건 제외")

        # 공통 메타 세팅
        for r in results:
            r.setdefault("source",     source["name"])
            r.setdefault("source_url", source["url"])
            r.setdefault("language",   source["language"])
            r.setdefault("flag",       source.get("flag", ""))

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

    crawler       = NewsCrawler(days=days)
    collected     = {cat: [] for cat in ["japan", "china", "taiwan"]}
    total_sources = sum(len(SOURCES[c]) for c in active_categories)
    done          = 0

    for cat in active_categories:
        label = {"japan": "🇯🇵 일본", "china": "🇨🇳 중국", "taiwan": "🇹🇼 대만"}[cat]
        _s(f"{label} 매체 수집 중...")

        def _cb(name, kw, _label=label):
            nonlocal done
            done += 1
            _p(done / total_sources * 0.6, f"{_label} · {name} ({kw})")

        collected[cat] = crawler.crawl_category(cat, keyword_ko, _cb)

    # 무신사 기사 분리
    musinsa     = []
    musinsa_kws = ["무신사", "musinsa", "ムシンサ"]
    for cat in active_categories:
        flagged = [
            a for a in collected[cat]
            if any(k in a.get("title", "").lower() for k in musinsa_kws)
        ]
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
