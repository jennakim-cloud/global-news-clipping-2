"""
app.py - 글로벌 뉴스 클리핑 Streamlit 앱
실행: streamlit run app.py
"""

import streamlit as st
from datetime import datetime
import io

from crawler import run_pipeline, SOURCES, KEYWORD_TRANSLATIONS

# ─────────────────────────────────────────────
# 페이지 설정
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="글로벌 뉴스 클리핑",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# 커스텀 CSS
# ─────────────────────────────────────────────

st.markdown("""
<style>
/* 전체 폰트 */
html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }

/* 헤더 */
.main-header {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    color: white;
    padding: 2rem 2.5rem;
    border-radius: 12px;
    margin-bottom: 1.5rem;
}
.main-header h1 { margin: 0; font-size: 1.8rem; font-weight: 700; }
.main-header p  { margin: 0.4rem 0 0; opacity: 0.75; font-size: 0.9rem; }

/* 섹션 헤더 */
.section-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 1.15rem;
    font-weight: 700;
    padding: 0.6rem 0;
    border-bottom: 2px solid #e0e0e0;
    margin-bottom: 1rem;
}

/* 기사 카드 */
.article-card {
    background: #ffffff;
    border: 1px solid #e8e8e8;
    border-left: 4px solid #0f3460;
    border-radius: 8px;
    padding: 0.85rem 1rem;
    margin-bottom: 0.7rem;
    transition: box-shadow 0.2s;
}
.article-card:hover { box-shadow: 0 3px 12px rgba(0,0,0,0.1); }
.article-title-ko {
    font-size: 0.95rem;
    font-weight: 600;
    color: #1a1a2e;
    margin-bottom: 0.2rem;
}
.article-title-ko a {
    text-decoration: none;
    color: inherit;
}
.article-title-ko a:hover { color: #0f3460; text-decoration: underline; }
.article-title-orig {
    font-size: 0.78rem;
    color: #888;
    margin-bottom: 0.35rem;
}
.article-meta {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
    align-items: center;
}
.badge {
    background: #f0f4ff;
    color: #0f3460;
    border-radius: 4px;
    padding: 1px 8px;
    font-size: 0.72rem;
    font-weight: 500;
}
.badge-date {
    background: #f5f5f5;
    color: #666;
    border-radius: 4px;
    padding: 1px 8px;
    font-size: 0.72rem;
}

/* 무신사 카드 강조색 */
.musinsa-card {
    border-left-color: #e63946;
}

/* 통계 박스 */
.stat-box {
    background: #f8f9ff;
    border: 1px solid #dce3ff;
    border-radius: 8px;
    padding: 0.6rem 1rem;
    text-align: center;
}
.stat-num { font-size: 1.6rem; font-weight: 700; color: #0f3460; }
.stat-label { font-size: 0.75rem; color: #666; }

/* 빈 상태 */
.empty-state {
    text-align: center;
    color: #aaa;
    padding: 2rem;
    font-size: 0.9rem;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 헬퍼
# ─────────────────────────────────────────────

def render_article_card(article: dict, is_musinsa: bool = False):
    title_ko = article.get("title_ko") or article.get("title", "")
    title_orig = article.get("title", "")
    url = article.get("url", "#")
    source = article.get("source", "")
    flag = article.get("flag", "")
    date = article.get("date", "")

    card_class = "article-card musinsa-card" if is_musinsa else "article-card"
    date_badge = f'<span class="badge-date">📅 {date[:10]}</span>' if date else ""

    st.markdown(f"""
    <div class="{card_class}">
        <div class="article-title-ko">
            <a href="{url}" target="_blank">{title_ko}</a>
        </div>
        <div class="article-title-orig">{title_orig}</div>
        <div class="article-meta">
            <span class="badge">{flag} {source}</span>
            {date_badge}
        </div>
    </div>
    """, unsafe_allow_html=True)


def build_markdown_export(result: dict) -> str:
    meta = result["meta"]
    lines = [
        "# 글로벌 뉴스 클리핑 리포트",
        f"**키워드:** {meta['keyword']}　|　**생성일시:** {meta['generated_at']}　|　**수집 기간:** 최근 {meta['days']}일",
        "",
        "---",
        "",
    ]

    def section(title, articles, is_musinsa=False):
        lines.append(f"## {title}")
        lines.append("")
        if not articles:
            lines.append("_수집된 기사가 없습니다._")
        else:
            for a in articles:
                title_ko = a.get("title_ko") or a.get("title", "")
                url = a.get("url", "#")
                source = a.get("source", "")
                flag = a.get("flag", "")
                date = a.get("date", "")[:10] if a.get("date") else ""
                orig = a.get("title", "")
                lines.append(f"### [{title_ko}]({url})")
                if not is_musinsa:
                    lines.append(f"> 원문: {orig}")
                lines.append(f"**출처:** {flag} {source}" + (f"　|　**날짜:** {date}" if date else ""))
                lines.append("")
        lines.append("")

    section("📰 무신사 해외 보도", result["musinsa"], is_musinsa=True)
    section("🇯🇵 일본 산업 이슈", result["japan"])
    section("🇨🇳 중국 산업 이슈", result["china"])
    section("🇹🇼 대만 산업 이슈", result["taiwan"])

    lines.append("---")
    lines.append("*본 리포트는 자동 수집·Google 번역된 내용으로, 원문 확인을 권장합니다.*")
    return "\n".join(lines)


# ─────────────────────────────────────────────
# 사이드바
# ─────────────────────────────────────────────

with st.sidebar:
    st.markdown("## ⚙️ 검색 설정")

    # 키워드
    preset_keywords = list(KEYWORD_TRANSLATIONS.keys()) + ["직접 입력"]
    selected_preset = st.selectbox(
        "키워드 프리셋",
        preset_keywords,
        index=1,  # 기본값: 한국 패션
    )
    if selected_preset == "직접 입력":
        keyword = st.text_input("키워드 직접 입력", placeholder="예: 지속가능성")
    else:
        keyword = selected_preset

    st.divider()

    # 수집 기간
    days = st.slider("수집 기간 (일)", min_value=1, max_value=30, value=7, step=1)

    st.divider()

    # 수집 매체 토글
    st.markdown("**수집 매체 선택**")
    use_japan  = st.checkbox("🇯🇵 일본", value=True)
    use_china  = st.checkbox("🇨🇳 중국", value=True)
    use_taiwan = st.checkbox("🇹🇼 대만", value=True)

    st.divider()

    # 실행 버튼
    run_btn = st.button("🔍 뉴스 수집 시작", type="primary", use_container_width=True)

    st.divider()
    st.markdown("""
    <div style="font-size:0.75rem; color:#999; line-height:1.6;">
    ℹ️ Google 번역(비공식 API)을 사용합니다.<br>
    ⚠️ 일부 매체는 크롤링 제한으로 수집이 안 될 수 있습니다.<br>
    🕒 매체당 약 1~2초 지연이 적용됩니다.
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# 메인 영역 헤더
# ─────────────────────────────────────────────

st.markdown("""
<div class="main-header">
    <h1>📰 글로벌 뉴스 클리핑</h1>
    <p>일본 · 중국 · 대만 패션/리테일 매체 자동 수집 & 한국어 번역</p>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# 실행 & 결과 표시
# ─────────────────────────────────────────────

# 세션 상태 초기화
if "result" not in st.session_state:
    st.session_state.result = None

if run_btn:
    if not keyword or not keyword.strip():
        st.warning("키워드를 입력해주세요.")
        st.stop()

    # 수집할 카테고리 결정
    active_categories = []
    if use_japan:  active_categories.append("japan")
    if use_china:  active_categories.append("china")
    if use_taiwan: active_categories.append("taiwan")
    if not active_categories:
        st.warning("최소 한 개의 매체 국가를 선택해주세요.")
        st.stop()

    # 진행 상태 UI
    status_placeholder = st.empty()
    progress_bar = st.progress(0)
    progress_text = st.empty()

    def on_status(msg):
        status_placeholder.info(f"⏳ {msg}")

    def on_progress(val, text):
        progress_bar.progress(min(val, 1.0))
        progress_text.caption(text)

    try:
        # SOURCES를 active_categories만 남기도록 임시 필터
        from crawler import SOURCES as _SOURCES
        original_sources = {}
        for cat in ["japan", "china", "taiwan"]:
            original_sources[cat] = _SOURCES.get(cat, [])
            if cat not in active_categories:
                _SOURCES[cat] = []

        result = run_pipeline(
            keyword_ko=keyword.strip(),
            days=days,
            on_status=on_status,
            on_progress=on_progress,
        )

        # 복원
        for cat, val in original_sources.items():
            _SOURCES[cat] = val

        st.session_state.result = result
        status_placeholder.empty()
        progress_bar.empty()
        progress_text.empty()
        st.success(f"✅ 수집 완료! — {result['meta']['generated_at']}")

    except Exception as e:
        status_placeholder.error(f"오류 발생: {e}")
        progress_bar.empty()


# ─────────────────────────────────────────────
# 결과 렌더링
# ─────────────────────────────────────────────

if st.session_state.result:
    result = st.session_state.result
    meta = result["meta"]

    # ── 요약 통계 ──────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)
    total = sum(len(result[k]) for k in ["musinsa", "japan", "china", "taiwan"])
    with c1:
        st.markdown(f'<div class="stat-box"><div class="stat-num">{total}</div><div class="stat-label">총 수집 기사</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="stat-box"><div class="stat-num">{len(result["musinsa"])}</div><div class="stat-label">📰 무신사</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="stat-box"><div class="stat-num">{len(result["japan"])}</div><div class="stat-label">🇯🇵 일본</div></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="stat-box"><div class="stat-num">{len(result["china"])}</div><div class="stat-label">🇨🇳 중국</div></div>', unsafe_allow_html=True)
    with c5:
        st.markdown(f'<div class="stat-box"><div class="stat-num">{len(result["taiwan"])}</div><div class="stat-label">🇹🇼 대만</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Markdown 다운로드 버튼 ──────────────────
    md_content = build_markdown_export(result)
    date_str = datetime.now().strftime("%Y%m%d_%H%M")
    st.download_button(
        label="⬇️ 리포트 다운로드 (.md)",
        data=md_content.encode("utf-8"),
        file_name=f"news_clipping_{date_str}.md",
        mime="text/markdown",
    )

    st.divider()

    # ── 탭 구성 ────────────────────────────────
    tab_musinsa, tab_japan, tab_china, tab_taiwan = st.tabs([
        f"📰 무신사 해외 보도 ({len(result['musinsa'])})",
        f"🇯🇵 일본 산업 이슈 ({len(result['japan'])})",
        f"🇨🇳 중국 산업 이슈 ({len(result['china'])})",
        f"🇹🇼 대만 산업 이슈 ({len(result['taiwan'])})",
    ])

    with tab_musinsa:
        if result["musinsa"]:
            for a in result["musinsa"]:
                render_article_card(a, is_musinsa=True)
        else:
            st.markdown('<div class="empty-state">🔍 수집된 무신사 관련 기사가 없습니다.</div>', unsafe_allow_html=True)

    with tab_japan:
        if result["japan"]:
            for a in result["japan"]:
                render_article_card(a)
        else:
            st.markdown('<div class="empty-state">🔍 수집된 일본 기사가 없습니다.</div>', unsafe_allow_html=True)

    with tab_china:
        if result["china"]:
            for a in result["china"]:
                render_article_card(a)
        else:
            st.markdown('<div class="empty-state">🔍 수집된 중국 기사가 없습니다.</div>', unsafe_allow_html=True)

    with tab_taiwan:
        if result["taiwan"]:
            for a in result["taiwan"]:
                render_article_card(a)
        else:
            st.markdown('<div class="empty-state">🔍 수집된 대만 기사가 없습니다.</div>', unsafe_allow_html=True)

else:
    # 초기 안내 화면
    st.markdown("""
    <div style="text-align:center; padding: 4rem 2rem; color: #aaa;">
        <div style="font-size: 3rem; margin-bottom: 1rem;">🌏</div>
        <div style="font-size: 1.1rem; font-weight: 600; color: #555; margin-bottom: 0.5rem;">
            좌측 사이드바에서 키워드와 옵션을 설정한 뒤<br>
            <strong>뉴스 수집 시작</strong> 버튼을 눌러주세요.
        </div>
        <div style="font-size: 0.85rem; margin-top: 1rem;">
            일본 · 중국 · 대만 총 16개 매체에서 기사를 수집하고<br>Google 번역으로 한국어 제목을 자동 생성합니다.
        </div>
    </div>
    """, unsafe_allow_html=True)
