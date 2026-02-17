import streamlit as st
import pandas as pd
import requests
import json
import re
from datetime import datetime, timedelta

# --- [1. 시스템 설정] ---
SPREADSHEET_ID = '12cPPhM68K3SopQJtZyWEq8adDuP98bJ4efoYbjFDDOI'
GID_MAP = {
    "Log": "0", 
    "Assets": "1068342666", 
    "Inventory": "2138778159", 
    "Pharmacy": "347265850"
}
API_URL = "https://script.google.com/macros/s/AKfycbxmlmMqenbvhLiLbUmI2GEd1sUMpM-NIUytaZ6jGjSL_hZ_4bk8rnDT1Td3wxbdJVBA/exec"
COLOR_ASSET = "#4dabf7"

RECOMMENDED = {
    "칼로리": 2200, "단백질": 180, "탄수화물": 280, "지방": 85,
    "식이섬유": 30, "나트륨": 2300, "당류": 50, "콜레스테롤": 300, "수분(ml)": 2000     
}

# --- [2. 핵심 유틸리티] ---
def format_krw(val): return f"{int(val):,}".rjust(15) + " 원"

def to_numeric(val):
    if pd.isna(val) or val == "": return 0
    s = re.sub(r'[^0-9.-]', '', str(val))
    try: return float(s) if '.' in s else int(s)
    except: return 0

def load_sheet_data(gid):
    ts = datetime.now().timestamp()
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={gid}&t={ts}"
    try:
        df = pd.read_csv(url)
        return df.dropna(how='all')
    except: return pd.DataFrame()

def send_to_sheet(d_date, d_hour, d_type, cat_main, content, value, method, corpus="Log"):
    payload = {
        "time": f"{d_date} {d_hour:02d}시", "corpus": corpus, "type": d_type, 
        "cat_main": cat_main, "cat_sub": "-", "item": content, "value": value, "method": method, "user": "정원"
    }
    try:
        res = requests.post(API_URL, data=json.dumps(payload), timeout=10)
        return res.status_code == 200
    except: return False

# --- [3. 초기화 및 로딩] ---
st.set_page_config(page_title="JARVIS Prime v65.4", layout="wide")
now = datetime.utcnow() + timedelta(hours=9)

def sync_from_dedicated_sheet(gid):
    try:
        df = load_sheet_data(gid)
        if not df.empty:
            new_df = df.iloc[:, [0, 1, 2]].copy()
            new_df.columns = ["품목", "수량", "기한"]
            return new_df
    except: pass
    return pd.DataFrame(columns=["품목", "수량", "기한"])

if 'food_df_state' not in st.session_state:
    st.session_state.food_df_state = sync_from_dedicated_sheet(GID_MAP["Inventory"])
if 'med_df_state' not in st.session_state:
    st.session_state.med_df_state = sync_from_dedicated_sheet(GID_MAP["Pharmacy"])
if 'daily_nutri' not in st.session_state:
    st.session_state.daily_nutri = {k: 0.0 for k in RECOMMENDED.keys()}

# --- [4. UI 스타일] ---
st.markdown(f"""<style>thead tr th:first-child, tbody th {{ display:none; }} .net-box {{ background-color: #ffffff; padding: 25px; border-radius: 12px; border: 1px solid #dee2e6; border-left: 5px solid {COLOR_ASSET}; margin-bottom: 20px; }} .stProgress > div > div > div > div {{ background-color: {COLOR_ASSET} !important; }}</style>""", unsafe_allow_html=True)

# --- [5. 메인 레이아웃 및 사이드바 메뉴] ---
t_col1, t_col2 = st.columns([3, 1])
with t_col1: st.markdown(f"### {now.strftime('%Y-%m-%d %H:%M:%S')} | JARVIS Prime")
with t_col2: 
    if st.button("🔄 시트 데이터 동기화", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

with st.sidebar:
    st.title("JARVIS CONTROL")
    menu = st.radio("SELECT MENU", ["투자 & 자산", "식단 & 건강", "재고 & 교체관리"])

# --- [6. 모듈별 기능 로직] ---

# 1. 투자 & 자산 모듈
if menu == "투자 & 자산":
    st.header("📈 종합 자산 대시보드")
    with st.sidebar:
        st.subheader("💰 지출/수입 입력")
        with st.form("asset_form"):
            sel_date, sel_hour = st.date_input("날짜", value=now.date()), st.slider("시간", 0, 23, now.hour)
            t_choice = st.selectbox("구분", ["지출", "수입"])
            c_main = st.selectbox("분류", ["식비", "생활용품", "사회적 관계(친구)", "월 구독료", "주거/통신", "교통", "건강", "금융", "경조사", "자산이동"])
            content, a_input = st.text_input("상세 내용"), st.number_input("금액", min_value=0, step=1000)
            method = st.selectbox("결제수단", ["국민카드(WE:SH)", "현대카드(M경차)", "현대카드(이마트)", "우리카드(주거래)", "하나카드(MG+)", "현금", "계좌이체"])
            if st.form_submit_button("전송"):
                if a_input > 0 and send_to_sheet(sel_date, sel_hour, t_choice, c_main, content, a_input, method):
                    st.success("기록 완료"); st.cache_data.clear(); st.rerun()

    df_assets = load_sheet_data(GID_MAP["Assets"])
    if not df_assets.empty:
        df_assets = df_assets.iloc[:, [0, 1]].copy()
        df_assets.columns = ["항목", "금액"]; df_assets["val"] = df_assets["금액"].apply(to_numeric)
        a_df, l_df = df_assets[df_assets["val"] > 0], df_assets[df_assets["val"] < 0]
        st.markdown(f'<div class="net-box"><small>통합 순자산</small><br><span style="font-size:2.8em; font-weight:bold;">{a_df["val"].sum() + l_df["val"].sum():,.0f} 원</span></div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1: st.subheader("자산 내역"); st.table(a_df.assign(금액=a_df["val"].apply(format_krw))[["항목", "금액"]])
        with c2: st.subheader("부채 내역"); st.table(l_df.assign(금액=l_df["val"].apply(lambda x: format_krw(abs(x))))[["항목", "금액"]])

# 2. 식단 & 건강 모듈
elif menu == "식단 & 건강":
    st.header(f"🥗 정밀 영양 분석 (목표: {RECOMMENDED['칼로리']} kcal)")
    curr = st.session_state.daily_nutri
    cols = st.columns(2)
    for idx, (name, goal) in enumerate(RECOMMENDED.items()):
        with cols[idx % 2]:
            val = curr.get(name, 0.0)
            st.write(f"**{name}**: {val:.1f} / {goal:.1f}")
            st.progress(min(1.0, val / goal) if goal > 0 else 0.0)
    
    st.divider()
    with st.sidebar:
        st.subheader("🍴 식사 기록 입력")
        with st.form("diet_form"):
            f_in = {k: st.number_input(k, value=0.0) for k in RECOMMENDED.keys()}
            if st.form_submit_button("데이터 추가"):
                for k in RECOMMENDED.keys(): st.session_state.daily_nutri[k] += f_in[k]
                st.rerun()
        if st.button("🏁 식단 마감"):
            st.session_state.daily_nutri = {k: 0.0 for k in RECOMMENDED.keys()}; st.rerun()

# 3. 재고 관리 모듈
elif menu == "재고 & 교체관리":
    st.header("🏠 스마트 재고 시스템 (전용 시트)")
    t1, t2 = st.tabs(["🍎 식재료", "💊 의약품"])
    with t1:
        st.session_state.food_df_state = st.data_editor(st.session_state.food_df_state, num_rows="dynamic", use_container_width=True, key="food_final")
        if st.button("💾 식재료 백업"): st.success("임시 저장 완료")
    with t2:
        st.session_state.med_df_state = st.data_editor(st.session_state.med_df_state, num_rows="dynamic", use_container_width=True, key="med_final")
        if st.button("💾 의약품 백업"): st.success("임시 저장 완료")
