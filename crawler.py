import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from urllib.parse import quote, urljoin
import time
import re

# ... (기존 HEADERS, KEYWORD_TRANSLATIONS 동일)

SOURCES = {
    "japan": [
        {
            "name": "Yahoo Japan News",
            "url": "https://news.yahoo.co.jp",
            # [개선] 기사 탭에서 최신순(pub)으로 검색
            "search_url": "https://news.yahoo.co.jp/search?p={keyword}&ei=utf-8&sort=pub",
            "language": "ja", 
            "flag": "🇯🇵"
        },
    ],
    "china": [
        # ... (기존 중국 소스 유지)
    ],
    "taiwan": [
        # ... (기존 대만 소스 유지)
    ],
}

class NewsCrawler:
    def __init__(self, days: int = 7):
        self.days = days
        self.cutoff = datetime.now() - timedelta(days=days)
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    # [신규] 야후 재팬 전용 상대 시간 파싱 (n시간 전 등)
    def parse_relative_date(self, text: str) -> datetime:
        now = datetime.now()
        if '분 전' in text or '分前' in text:
            m = re.search(r'(\d+)', text)
            return now - timedelta(minutes=int(m.group(1))) if m else now
        if '시간 전' in text or '時間前' in text:
            m = re.search(r'(\d+)', text)
            return now - timedelta(hours=int(m.group(1))) if m else now
        if '어제' in text or '昨日' in text:
            return now - timedelta(days=1)
        
        # 일반 날짜 패턴 시도
        parsed = parse_date(text)
        return parsed if parsed else now

    def is_within_cutoff(self, date_str: str) -> bool:
        dt = self.parse_relative_date(date_str)
        return dt >= self.cutoff

    def parse_yahoo_japan(self, soup: BeautifulSoup) -> list[dict]:
        """야후 재팬 뉴스 검색 결과 전용 파서"""
        results = []
        # 야후 뉴스 검색 결과 카드 셀렉터
        items = soup.select('li.sw-Card') 
        for item in items:
            title_tag = item.select_one('h3.sw-Card__title')
            a_tag = item.select_one('a.sw-Card__titleInner')
            date_tag = item.select_one('span.sw-Card__time')
            source_tag = item.select_one('span.sw-Card__sender') # 원문 매체명 (WWD, Fashionsnap 등)

            if title_tag and a_tag:
                title = clean_text(title_tag.get_text())
                url = a_tag['href']
                date_text = date_tag.get_text() if date_tag else ""
                source_name = source_tag.get_text() if source_tag else "Yahoo News"

                if self.is_within_cutoff(date_text):
                    results.append({
                        "title": title,
                        "url": url,
                        "date": date_text,
                        "source": source_name, # 야후 내 실제 출처 표시
                        "flag": "🇯🇵",
                        "language": "ja"
                    })
        return results

    def search_source(self, source: dict, keyword: str) -> list[dict]:
        print(f"  검색 시도: {source['name']} ({keyword})")
        soup = self.fetch(source["search_url"].format(keyword=quote(keyword)))
        if not soup: return []

        # 일본(야후)인 경우 전용 파서 사용, 나머지는 범용 파서 사용
        if source["name"] == "Yahoo Japan News":
            return self.parse_yahoo_japan(soup)
        
        results = self.parse_generic(soup, source["url"])
        for r in results:
            r.update({"source": source["name"], "source_url": source["url"],
                       "language": source["language"], "flag": source.get("flag", "")})
        return results

# ... (이하 translate_articles, run_pipeline 등 기존 로직 유지)
