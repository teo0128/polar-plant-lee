import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import unicodedata
import io

st.set_page_config(layout="wide", page_title="극지식물 최적 EC 농도 연구")

# ================= 한글 폰트 =================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR&display=swap');
html, body, [class*="css"] {
    font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif;
}
</style>
""", unsafe_allow_html=True)

# ================= 경로 보호 =================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

if not DATA_DIR.exists():
    st.error("❌ data 폴더를 찾을 수 없습니다. GitHub 저장소에 data/ 폴더가 업로드되어 있는지 확인하세요.")
    st.stop()

# ================= 환경 데이터 =================
@st.cache_data
def load_env_data():
    with st.spinner("환경 데이터 로딩 중..."):
        env = {}
        for p in DATA_DIR.iterdir():
            if p.is_file() and p.suffix.lower() == ".csv":
                try:
                    name = unicodedata.normalize("NFC", p.stem.replace("_환경데이터", ""))
                    env[name] = pd.read_csv(p)
                except Exception as e:
                    st.error(f"{p.name} 로딩 실패: {e}")
        return env

# ================= 생육 결과 =================
@st.cache_data
def load_growth_data():
    with st.spinner("생육 결과 데이터 로딩 중..."):
        xlsx_path = None
        for p in DATA_DIR.iterdir():
            if p.is_file() and p.suffix.lower() == ".xlsx":
                xlsx_path = p

        if xlsx_path is None:
            st.error("❌ 생육 결과 XLSX 파일을 찾을 수 없습니다.")
            return {}

        try:
            return pd.read_excel(xlsx_path, sheet_name=None)
        except Exception as e:
            st.error(f"XLSX 로딩 실패: {e}")
            return {}

env_data = load_env_data()
growth_data = load_growth_data()

if not env_data or not growth_data:
    st.stop()

ec_map = {"송도고":1.0,"하늘고":2.0,"아라고":4.0,"동산고":8.0}
schools = ["전체"] + list(env_data.keys())

# ================= 사이드바 =================
selected_school = st.sidebar.selectbox("학교 선택", schools)

# ================= 제목 =================
st.title("🌱 극지식물 최적 EC 농도 연구")

tab1, tab2, tab3 = st.tabs(["📖 실험 개요", "🌡️ 환경 데이터", "📊 생육 결과"])

# ================= TAB 1 =================
with tab1:
    st.subheader("연구 개요")
    info = []
    for s, df in growth_data.items():
        info.append([s, ec_map[s], len(df)])
    info_df = pd.DataFrame(info, columns=["학교","EC","개체수"])
    st.table(info_df)

    st.metric("총 개체수", sum(info_df["개체수"]))
    st.metric("최적 EC", "2.0 (하늘고)")

# ================= TAB 2 =================
with tab2:
    avg = []
    for s, df in env_data.items():
        avg.append([s, df["temperature"].mean(), df["humidity"].mean(),
                    df["ph"].mean(), df["ec"].mean(), ec_map[s]])

    avg_df = pd.DataFrame(avg, columns=["학교","온도","습도","pH","실측EC","목표EC"])

    fig = make_subplots(rows=2, cols=2,
        subplot_titles=["평균 온도","평균 습도","평균 pH","목표 EC vs 실측 EC"])

    fig.add_trace(go.Bar(x=avg_df["학교"], y=avg_df["온도"]),1,1)
    fig.add_trace(go.Bar(x=avg_df["학교"], y=avg_df["습도"]),1,2)
    fig.add_trace(go.Bar(x=avg_df["학교"], y=avg_df["pH"]),2,1)
    fig.add_trace(go.Bar(x=avg_df["학교"], y=avg_df["목표EC"], name="목표EC"),2,2)
    fig.add_trace(go.Bar(x=avg_df["학교"], y=avg_df["실측EC"], name="실측EC"),2,2)

    fig.update_layout(font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"))
    st.plotly_chart(fig, use_container_width=True)

# ================= TAB 3 =================
with tab3:
    result = []
    for s, df in growth_data.items():
        result.append([ec_map[s], df["생중량(g)"].mean()])

    df_r = pd.DataFrame(result, columns=["EC","생중량"])
    best = df_r.loc[df_r["생중량"].idxmax()]
    st.metric("최적 EC", best["EC"], f"{best['생중량']:.2f} g")

    fig2 = go.Figure(go.Bar(x=df_r["EC"], y=df_r["생중량"]))
    fig2.update_layout(font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"))
    st.plotly_chart(fig2, use_container_width=True)

    with st.expander("📥 XLSX 다운로드"):
        buffer = io.BytesIO()
        pd.concat(growth_data.values()).to_excel(buffer, index=False, engine="openpyxl")
        buffer.seek(0)
        st.download_button("다운로드", buffer, "극지식물_생육데이터.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
