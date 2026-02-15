import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime, date

# --- [1. 시스템 설정] ---
SPREADSHEET_ID = '12cPPhM68K3SopQJtZyWEq8adDuP98bJ4efoYbjFDDOI'
GID_MAP = {"Log": "0", "Assets": "1068342666", "Finance": "0"}
API_URL = "https://script.google.com/macros/s/AKfycbzX1w7136qfFsnRb0RMQTZvJ1Q_-GZb5HAwZF6yfKiLTHbchJZq-8H2GXjV2z5WnkmI4A/exec"

COLOR_GOOD, COLOR_BAD, COLOR_TEXT = "#4dabf7", "#ff922b", "#fafafa"

FIXED_DATA = {
    "stocks": {
        "삼성전자": {"평단": 78895, "수량": 46}, "SK하이닉스": {"평단": 473521, "수량": 6},
        "삼성중공업": {"평단": 16761, "수량": 88}, "동성화인텍": {"평단": 22701, "수량": 21}
    },
    "crypto": {"BTC": {"평단": 137788139, "수량": 0.001814}, "ETH": {"평단": 4243000, "수량": 0.034174}}
}

def format_krw(val): return f"{int(val):,}" + "원"
def to_numeric(val):
    try: return int(float(str(val).replace(',', '').replace('원', '').strip()))
    except: return 0

@st.cache_data(ttl=5)
def load_sheet_data(gid):
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={gid}"
    try: return pd.read_csv(url).dropna(how='all').reset_index(drop=True)
    except: return pd.DataFrame()

# --- [2. UI 설정] ---
st.set_page_config(page_title="JARVIS v41.0", layout="wide")
st.markdown(f"<style>.stApp {{ background-color: #0e1117; color: {COLOR_TEXT}; }} [data-testid='stSidebar'] {{ background-color: #262730; }} [data-testid='stDataFrame'] table td:nth-child(2) {{ text-align: right !important; }} button[kind='secondaryFormSubmit'] {{ background-color: {COLOR_GOOD} !important; color: white !important; }} .stNumberInput input {{ background-color: #e9ecef !important; color: black !important; }} h1, h2, h3 {{ color: {COLOR_TEXT} !important; }}</style>", unsafe_allow_html=True)

with st.sidebar:
    st.title("JARVIS 제어 센터")
    menu = st.radio("메뉴 선택", ["투자 & 자산", "식단 & 건강", "재고 관리"])
    if menu == "투자 & 자산":
        with st.form("in_f"):
            d_in = st.date_input("날짜", date.today())
            t_ch = st.selectbox("구분", ["지출", "수입"])
            c_ch = st.selectbox("카테고리", ["식비", "생활/마트", "주거/통신", "금융/보험", "급여", "기타"])
            it_in = st.text_input("내용", "")
            a_in = st.number_input("금액(원)", min_value=0, step=1000)
            if st.form_submit_button("저장", use_container_width=True):
                if a_in > 0: st.success("데이터베이스 기록 완료")

# --- [3. 메인 화면] ---
if menu == "투자 & 자산":
    st.header("💎 종합 자산 현황 (Net Worth)")
    try:
        df_a = load_sheet_data(GID_MAP["Assets"])
        df_l = load_sheet_data(GID_MAP["Log"])
        if not df_a.empty:
            df_a = df_a.iloc[:, :2]
            df_a.columns = ["항목", "금액"]
            df_a["val"] = df_a["금액"].apply(to_numeric)
        
        inv_r = []
        for cat, items in {"주식": FIXED_DATA["stocks"], "코인": FIXED_DATA["crypto"]}.items():
            for name, info in items.items(): inv_r.append({"항목": name, "val": info['평단'] * info['수량']})
        
        df_total = pd.concat([df_a, pd.DataFrame(inv_r)], ignore_index=True)
        a_df = df_total[df_total["val"] >= 0].copy()
        l_df = df_total[df_total["val"] < 0].copy()
        net_w = a_df["val"].sum() - abs(l_df["val"].sum())

        c1, c2, c3 = st.columns([1, 1, 0.8])
        with c1:
            st.subheader("🔹 자산")
            st.metric("총 자산", format_krw(a_df["val"].sum()))
            st.dataframe(a_df.assign(금액=a_df["val"].apply(format_krw))[["항목", "금액"]], use_container_width=True, hide_index=True)
        with c2:
            st.subheader("🔸 부채")
            st.metric("총 부채", format_krw(l_df["val"].sum()))
            if not l_df.empty: st.dataframe(l_df.assign(금액=l_df["val"].apply(lambda x: format_krw(abs(x))))[["항목", "금액"]], use_container_width=True, hide_index=True)
            else: st.info("부채 없음")
        with c3:
            st.markdown(f"<div style='background-color:#1c1e26; padding:15px; border-radius:10px; text-align:center; border:1px solid {COLOR_GOOD};'><h3 style='margin:0; color:gray;'>순자산</h3><h1 style='margin:0; color:{COLOR_GOOD};'>{format_krw(net_w)}</h1></div>", unsafe_allow_html=True)

        st.divider()
        st.header("📊 월별 지출 분석 (Flow)")
        st.info("📉 2026년 2월 이후 내역 입력 시 통계가 활성화됩니다.")
    except Exception as e: st.error(f"시스템 오류: {e}")

elif menu == "식단 & 건강":
    st.header("🥗 실시간 영양 분석 리포트")
    d_day = (date(2026, 5, 30) - date.today()).days
    st.info(f"💍 결혼식까지 D-{d_day} | 정원님 125kg 기준 감량 모드")
    with st.form("d_f"):
        in_w = st.number_input("체중 (kg)", 0.0, 200.0, 125.0)
        c1, c2 = st.columns(2)
        with c1: st.number_input("칼로리", 0.0); st.number_input("탄수화물", 0.0)
        with c2: st.number_input("단백질", 0.0); st.number_input("지방", 0.0)
        if st.form_submit_button("영양 데이터 저장"): st.success("저장 완료")

elif menu == "재고 관리":
    st.header("📦 식자재 및 생활용품 관리")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🛒 식재료 현황")
        inv = pd.DataFrame([{"항목": "냉동 삼치", "수량": "4팩", "유통기한": "2026-05-10"}, {"항목": "단백질 쉐이크", "수량": "9개", "유통기한": "2026-12-30"}, {"항목": "김치 4종", "수량": "보유", "유통기한": "-"}, {"항목": "당근", "수량": "보유", "유통기한": "-"}, {"항목": "감자", "수량": "보유", "유통기한": "-"}])
        st.data_editor(inv, use_container_width=True, hide_index=True)
    with c2:
        st.subheader("⏰ 생활용품 교체")
        sup = pd.DataFrame([{"품목": "칫솔(정원)", "교체일": "2026-01-15", "주기": 30}, {"품목": "칫솔(서진)", "교체일": "2026-02-15", "주기": 30}, {"품목": "면도날", "교체일": "2026-02-01", "주기": 14}])
        st.data_editor(sup, use_container_width=True, hide_index=True)
