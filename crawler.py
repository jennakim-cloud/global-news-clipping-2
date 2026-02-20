"""
crawler.py - 뉴스 수집 & Google 번역 모듈
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from urllib.parse import quote, urljoin
import time
import re

# ─────────────────────────────────────────────
# 헤더
# ─────────────────────────────────────────────

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,ja;q=0.6,zh-CN;q=0.5",
}

# ─────────────────────────────────────────────
# 키워드 번역 사전
# ─────────────────────────────────────────────

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

# ─────────────────────────────────────────────
# 매체 설정
# ─────────────────────────────────────────────

SOURCES = {
    "japan": [
        {
            "name": "WWD Japan",
            "url": "https://www.wwdjapan.com",
            "search_url": "https://www.wwdjapan.com/search?q={keyword}",
            "language": "ja",
            "flag": "🇯🇵",
        },
        {
            "name": "Fashionsnap",
            "url": "https://www.fashionsnap.com",
            "search_url": "https://www.fashionsnap.com/?s={keyword}",
            "language": "ja",
            "flag": "🇯🇵",
        },
        {
            "name": "Yahoo Japan ニュース",
            "url": "https://news.yahoo.co.jp",
            "search_url": "https://news.yahoo.co.jp/search?p={keyword}&ei=UTF-8",
            "language": "ja",
            "flag": "🇯🇵",
        },
        {
            "name": "日経MJ",
            "url": "https://www.nikkei.com",
            "search_url": "https://www.nikkei.com/search?keyword={keyword}",
            "language": "ja",
            "flag": "🇯🇵",
        },
        {
            "name": "繊研新聞",
            "url": "https://senken.co.jp",
            "search_url": "https://senken.co.jp/?s={keyword}",
            "language": "ja",
            "flag": "🇯🇵",
        },
    ],
    "china": [
        {
            "name": "界面新闻",
            "url": "https://www.jiemian.com",
            "search_url": "https://www.jiemian.com/search.html?keywords={keyword}",
            "language": "zh",
            "flag": "🇨🇳",
        },
        {
            "name": "36氪",
            "url": "https://36kr.com",
            "search_url": "https://36kr.com/search/articles/{keyword}",
            "language": "zh",
            "flag": "🇨🇳",
        },
        {
            "name": "亿邦动力",
            "url": "https://www.ebrun.com",
            "search_url": "https://www.ebrun.com/search/?q={keyword}",
            "language": "zh",
            "flag": "🇨🇳",
        },
        {
            "name": "WWD Greater China",
            "url": "https://wwdgreaterchina.com",
            "search_url": "https://wwdgreaterchina.com/?s={keyword}",
            "language": "zh",
            "flag": "🇨🇳",
        },
        {
            "name": "Vogue China",
            "url": "https://www.vogue.com.cn",
            "search_url": "https://www.vogue.com.cn/search?q={keyword}",
            "language": "zh",
            "flag": "🇨🇳",
        },
        {
            "name": "第一财经",
            "url": "https://www.yicai.com",
            "search_url": "https://www.yicai.com/search/?keys={keyword}",
            "language": "zh",
            "flag": "🇨🇳",
        },
        {
            "name": "赢商网",
            "url": "https://m.winshang.com",
            "search_url": "https://m.winshang.com/search.html?keyword={keyword}",
            "language": "zh",
            "flag": "🇨🇳",
        },
        {
            "name": "新浪",
            "url": "https://www.sina.com.cn",
            "search_url": "https://search.sina.com.cn/?q={keyword}&range=all&c=news",
            "language": "zh",
            "flag": "🇨🇳",
        },
        {
            "name": "Luxe.co",
            "url": "https://luxe.co",
            "search_url": "https://luxe.co/?s={keyword}",
            "language": "zh",
            "flag": "🇨🇳",
        },
    ],
    "taiwan": [
        {
            "name": "數位時代",
            "url": "https://www.bnext.com.tw",
            "search_url": "https://www.bnext.com.tw/search/{keyword}",
            "language": "tw",
            "flag": "🇹🇼",
        },
        {
            "name": "工商時報",
            "url": "https://www.ctee.com.tw",
            "search_url": "https://www.ctee.com.tw/search?q={keyword}",
            "language": "tw",
            "flag": "🇹🇼",
        },
    ],
}

# ─────────────────────────────────────────────
# Google 번역 (비공식 무료 API)
# ─────────────────────────────────────────────

def translate_to_korean(text: str, src_lang: str = "auto") -> str:
    """
    Google 번역 비공식 API를 이용한 한국어 번역.
    실패 시 원문 반환.
    """
    if not text or not text.strip():
        return text
    try:
        url = "https://translate.googleapis.com/translate_a/single"
        params = {
            "client": "gtx",
            "sl": src_lang,
            "tl": "ko",
            "dt": "t",
            "q": text,
        }
        resp = requests.get(url, params=params, timeout=10, headers=HEADERS)
        resp.raise_for_status()
        data = resp.json()
        # 번역 결과 조각들을 합침
        translated = "".join(seg[0] for seg in data[0] if seg[0])
        return translated.strip() or text
    except Exception:
        return text


def translate_keyword_to_lang(keyword_ko: str, lang: str) -> str:
    """키워드를 대상 언어로 번역 (사전 → Google 번역 순)"""
    # 사전에 있으면 우선 사용
    if keyword_ko in KEYWORD_TRANSLATIONS:
        return KEYWORD_TRANSLATIONS[keyword_ko].get(lang, keyword_ko)
    # 없으면 Google 번역 사용
    lang_map = {"ja": "ja", "zh": "zh-CN", "tw": "zh-TW"}
    tl = lang_map.get(lang, "ja")
    url = "https://translate.googleapis.com/translate_a/single"
    params = {"client": "gtx", "sl": "ko", "tl": tl, "dt": "t", "q": keyword_ko}
    try:
        resp = requests.get(url, params=params, timeout=10, headers=HEADERS)
        data = resp.json()
        return "".join(seg[0] for seg in data[0] if seg[0]).strip() or keyword_ko
    except Exception:
        return keyword_ko


# ─────────────────────────────────────────────
# 크롤러
# ─────────────────────────────────────────────

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
        except Exception as e:
            return None, str(e)

    def _parse_date(self, text: str):
        if not text:
            return None
        text = text.strip()
        patterns = [
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S+09:00",
            "%Y-%m-%d %H:%M:%S",
            "%Y/%m/%d %H:%M",
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%Y年%m月%d日",
        ]
        for fmt in patterns:
            try:
                dt = datetime.strptime(text[:len(fmt) + 2], fmt)
                if dt.year < 2000:
                    dt = dt.replace(year=datetime.now().year)
                return dt
            except ValueError:
                continue
        return None

    def is_recent(self, date_str: str) -> bool:
        dt = self._parse_date(date_str)
        if dt is None:
            return True
        return dt >= self.cutoff

    def parse_generic(self, soup, base_url: str) -> list[dict]:
        articles = []
        seen = set()
        candidates = []

        for tag in soup.find_all("article"):
            a = tag.find("a", href=True)
            title_tag = tag.find(["h1", "h2", "h3", "h4"])
            date_tag = tag.find(["time", "span"], class_=re.compile(r"date|time|pub", re.I))
            if a and title_tag:
                candidates.append({
                    "title": title_tag.get_text(strip=True),
                    "url": urljoin(base_url, a["href"]),
                    "date": (date_tag.get("datetime") or date_tag.get_text(strip=True)) if date_tag else "",
                })

        if not candidates:
            for tag in soup.find_all(["h2", "h3"]):
                a = tag.find("a", href=True) or tag.find_parent("a", href=True)
                if a:
                    candidates.append({
                        "title": tag.get_text(strip=True),
                        "url": urljoin(base_url, a["href"]),
                        "date": "",
                    })

        for c in candidates:
            if c["url"] in seen:
                continue
            seen.add(c["url"])
            if self.is_recent(c["date"]) and len(c["title"]) > 5:
                articles.append(c)

        return articles[:12]

    def search_source(self, source: dict, keyword: str) -> list[dict]:
        kw_encoded = quote(keyword)
        search_url = source["search_url"].format(keyword=kw_encoded)
        soup = self.fetch(search_url)
        if not soup or isinstance(soup, tuple):
            return []
        results = self.parse_generic(soup, source["url"])
        for r in results:
            r["source"] = source["name"]
            r["source_url"] = source["url"]
            r["language"] = source["language"]
            r["flag"] = source.get("flag", "")
        return results

    def crawl_category(
        self,
        category: str,
        keyword_ko: str,
        progress_callback=None,
    ) -> list[dict]:
        sources = SOURCES.get(category, [])
        all_articles = []

        for i, source in enumerate(sources):
            lang = source["language"]
            keyword = translate_keyword_to_lang(keyword_ko, lang)

            if progress_callback:
                progress_callback(source["name"], keyword)

            articles = self.search_source(source, keyword)
            all_articles.extend(articles)
            time.sleep(0.8)

        return all_articles


# ─────────────────────────────────────────────
# 번역 일괄 처리
# ─────────────────────────────────────────────

def translate_articles(
    articles: list[dict],
    progress_callback=None,
) -> list[dict]:
    """기사 제목을 한국어로 일괄 번역"""
    lang_map = {"ja": "ja", "zh": "zh-CN", "tw": "zh-TW"}
    for i, a in enumerate(articles):
        if progress_callback:
            progress_callback(i + 1, len(articles), a.get("source", ""))
        src = lang_map.get(a.get("language", "ja"), "auto")
        a["title_ko"] = translate_to_korean(a["title"], src_lang=src)
        time.sleep(0.3)  # Google 번역 rate limit 방지
    return articles


# ─────────────────────────────────────────────
# 전체 파이프라인
# ─────────────────────────────────────────────

def run_pipeline(
    keyword_ko: str,
    days: int = 7,
    on_status=None,       # 상태 메시지 콜백: fn(msg: str)
    on_progress=None,     # 진행률 콜백: fn(value: float, text: str)
) -> dict:
    """
    수집 → 번역 파이프라인 실행.
    반환: {
        "musinsa": [...],
        "japan": [...],
        "china": [...],
        "taiwan": [...],
        "meta": {"keyword": ..., "days": ..., "generated_at": ...}
    }
    """
    def _status(msg):
        if on_status:
            on_status(msg)

    def _prog(val, text=""):
        if on_progress:
            on_progress(val, text)

    crawler = NewsCrawler(days=days)
    all_collected = {"japan": [], "china": [], "taiwan": []}
    total_sources = sum(len(SOURCES[c]) for c in ["japan", "china", "taiwan"])
    done = 0

    for category in ["japan", "china", "taiwan"]:
        cat_label = {"japan": "🇯🇵 일본", "china": "🇨🇳 중국", "taiwan": "🇹🇼 대만"}[category]
        _status(f"{cat_label} 매체 수집 중...")

        def _prog_cb(name, kw, _cat=category, _label=cat_label):
            nonlocal done
            done += 1
            _prog(done / total_sources * 0.6, f"{_label} · {name} ({kw})")

        articles = crawler.crawl_category(category, keyword_ko, progress_callback=_prog_cb)
        all_collected[category] = articles

    # 무신사 필터링
    musinsa_kws = {"무신사", "musinsa", "ムシンサ"}
    musinsa_articles = []
    for cat in ["japan", "china", "taiwan"]:
        flagged = [
            a for a in all_collected[cat]
            if any(k in a.get("title", "").lower() for k in musinsa_kws)
        ]
        musinsa_articles.extend(flagged)
        all_collected[cat] = [a for a in all_collected[cat] if a not in flagged]

    # 전체 번역
    all_to_translate = (
        musinsa_articles
        + all_collected["japan"]
        + all_collected["china"]
        + all_collected["taiwan"]
    )
    total_translate = len(all_to_translate)
    _status(f"Google 번역 처리 중 (총 {total_translate}건)...")

    def _trans_cb(cur, total, source):
        _prog(0.6 + (cur / total) * 0.4, f"번역 중 {cur}/{total} · {source}")

    translate_articles(all_to_translate, progress_callback=_trans_cb)
    _prog(1.0, "완료!")

    return {
        "musinsa": musinsa_articles,
        "japan": all_collected["japan"],
        "china": all_collected["china"],
        "taiwan": all_collected["taiwan"],
        "meta": {
            "keyword": keyword_ko,
            "days": days,
            "generated_at": datetime.now().strftime("%Y.%m.%d %H:%M"),
        },
    }
