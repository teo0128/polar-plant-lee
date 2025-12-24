import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import unicodedata
import io

st.set_page_config(layout="wide", page_title="극지식물 최적 EC 농도 연구")

# ================= 한글 폰트 CSS =================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR&display=swap');
html, body, [class*="css"] {
    font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif;
}
</style>
""", unsafe_allow_html=True)

# ================= 경로 =================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

# ================= 한글 파일 탐색 =================
def find_korean_file(target_name: str):
    for p in DATA_DIR.iterdir():
        if unicodedata.normalize("NFC", p.name) == unicodedata.normalize("NFC", target_name) or \
           unicodedata.normalize("NFD", p.name) == unicodedata.normalize("NFD", target_name):
            return p
    return None

# ================= 데이터 로딩 =================
@st.cache_data
def load_env_data():
    with st.spinner("환경 데이터 로딩 중..."):
        env = {}
        for p in DATA_DIR.iterdir():
            if p.suffix.lower() == ".csv":
                name = p.stem.replace("_환경데이터", "")
                env[name] = pd.read_csv(p)
        if not env:
            st.error("환경 CSV 파일을 찾을 수 없습니다.")
        return env

@st.cache_data
def load_growth_data():
    with st.spinner("생육 결과 데이터 로딩 중..."):
        xlsx_path = None
        for p in DATA_DIR.iterdir():
            if p.suffix.lower() == ".xlsx":
                xlsx_path = p
        if xlsx_path is None:
            st.error("생육 결과 XLSX 파일을 찾을 수 없습니다.")
            return {}

        sheets = pd.read_excel(xlsx_path, sheet_name=None)
        return sheets

env_data = load_env_data()
growth_data = load_growth_data()

schools = ["전체"] + list(env_data.keys())

ec_map = {
    "송도고": 1.0,
    "하늘고": 2.0,
    "아라고": 4.0,
    "동산고": 8.0
}

# ================= 사이드바 =================
selected_school = st.sidebar.selectbox("학교 선택", schools)

# ================= 제목 =================
st.title("🌱 극지식물 최적 EC 농도 연구")

tab1, tab2, tab3 = st.tabs(["📖 실험 개요", "🌡️ 환경 데이터", "📊 생육 결과"])

# ================= TAB 1 =================
with tab1:
    st.subheader("연구 배경 및 목적")
    st.write("극지식물 재배에서 EC 농도가 생육에 미치는 영향을 분석하여 최적 EC 조건을 도출한다.")

    info_rows = []
    total_count = 0
    for s, df in growth_data.items():
        info_rows.append([s, ec_map.get(s, None), len(df)])
        total_count += len(df)

    info_df = pd.DataFrame(info_rows, columns=["학교명", "EC 목표", "개체수"])
    st.table(info_df)

    avg_temp = pd.concat(env_data.values())["temperature"].mean()
    avg_hum = pd.concat(env_data.values())["humidity"].mean()

    st.metric("총 개체수", total_count)
    st.metric("평균 온도", f"{avg_temp:.2f} ℃")
    st.metric("평균 습도", f"{avg_hum:.2f} %")
    st.metric("최적 EC", "2.0 (하늘고)")

# ================= TAB 2 =================
with tab2:
    st.subheader("학교별 환경 평균 비교")

    avg_df = []
    for s, df in env_data.items():
        avg_df.append([
            s,
            df["temperature"].mean(),
            df["humidity"].mean(),
            df["ph"].mean(),
            df["ec"].mean(),
            ec_map.get(s, None)
        ])

    avg_df = pd.DataFrame(avg_df, columns=["학교","온도","습도","pH","실측EC","목표EC"])

    fig = make_subplots(rows=2, cols=2,
                        subplot_titles=["평균 온도","평균 습도","평균 pH","목표 EC vs 실측 EC"])

    fig.add_trace(go.Bar(x=avg_df["학교"], y=avg_df["온도"]), row=1,col=1)
    fig.add_trace(go.Bar(x=avg_df["학교"], y=avg_df["습도"]), row=1,col=2)
    fig.add_trace(go.Bar(x=avg_df["학교"], y=avg_df["pH"]), row=2,col=1)
    fig.add_trace(go.Bar(x=avg_df["학교"], y=avg_df["목표EC"], name="목표EC"), row=2,col=2)
    fig.add_trace(go.Bar(x=avg_df["학교"], y=avg_df["실측EC"], name="실측EC"), row=2,col=2)

    fig.update_layout(font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"))
    st.plotly_chart(fig, use_container_width=True)

# ================= TAB 3 =================
with tab3:
    st.subheader("EC별 평균 생중량")

    weight_avg = []
    for s, df in growth_data.items():
        weight_avg.append([ec_map.get(s, None), df["생중량(g)"].mean()])

    weight_df = pd.DataFrame(weight_avg, columns=["EC","생중량"])

    best_ec = weight_df.loc[weight_df["생중량"].idxmax()]

    st.metric("최적 EC", best_ec["EC"], f"{best_ec['생중량']:.2f} g")

    fig2 = go.Figure()
    fig2.add_trace(go.Bar(x=weight_df["EC"], y=weight_df["생중량"]))
    fig2.update_layout(font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"))
    st.plotly_chart(fig2, use_container_width=True)

    with st.expander("📥 생육 데이터 다운로드"):
        buffer = io.BytesIO()
        pd.concat(growth_data.values()).to_excel(buffer, index=False, engine="openpyxl")
        buffer.seek(0)
        st.download_button("XLSX 다운로드", data=buffer,
                           file_name="극지식물_생육데이터.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

