# 📰 글로벌 뉴스 클리핑 v2

일본·중국·대만 총 16개 패션/리테일 매체에서 기사를 자동 수집하고,  
Google 번역(비공식 무료 API)으로 한국어 제목을 자동 생성하는 Streamlit 웹 앱입니다.

---

## 📁 파일 구성

```
news_clipper_v2/
├── app.py            # Streamlit UI 메인
├── crawler.py        # 크롤링 + Google 번역 로직
├── requirements.txt  # 패키지 목록
└── README.md
```

---

## ⚙️ 로컬 실행

```bash
# 패키지 설치
pip install -r requirements.txt

# 앱 실행
streamlit run app.py
```

브라우저에서 `http://localhost:8501` 접속

---

## ☁️ Streamlit Cloud 배포

1. GitHub에 이 폴더를 레포지토리로 Push
2. [share.streamlit.io](https://share.streamlit.io) 접속 → **New app**
3. 레포지토리 · 브랜치 · 메인 파일(`app.py`) 선택
4. **Deploy** 클릭 → 자동 배포 완료

> `requirements.txt`가 있으면 별도 설정 없이 자동 패키지 설치됩니다.

---

## 🔧 키워드 추가

`crawler.py`의 `KEYWORD_TRANSLATIONS` 딕셔너리에 추가:

```python
"리사이클": {
    "ja": "リサイクル",
    "zh": "回收利用",
    "tw": "回收再利用",
},
```

사전에 없는 키워드는 **Google 번역으로 자동 변환**됩니다.

---

## 🗂️ 수집 매체 (총 16개)

| 국가 | 매체 |
|------|------|
| 🇯🇵 일본 | WWD Japan, Fashionsnap, Yahoo Japan, 日経MJ, 繊研新聞 |
| 🇨🇳 중국 | 界面新闻, 36氪, 亿邦动力, WWD Greater China, Vogue China, 第一财经, 赢商网, 新浪, Luxe.co |
| 🇹🇼 대만 | 數位時代, 工商時報 |

---

## ⚠️ 주의사항

- Google 번역 **비공식 API** 사용 → 과도한 요청 시 일시 차단될 수 있음
- 일부 매체(Nikkei, Vogue China 등)는 로그인/Cloudflare 차단으로 수집 제한 가능
- 상업적 대량 사용 시 Google Cloud Translation 공식 API 전환 권장
