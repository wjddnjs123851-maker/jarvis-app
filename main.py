import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime, timedelta

# --- [1. 시스템 설정] ---
SPREADSHEET_ID = '17kw1FMK50MUpAWA9VPSile8JZeeq6TZ9DWJqMRaBMUM'
GID_MAP = {
    "Log": "0", "Assets": "1068342666", "Health": "123456789"
}
API_URL = "https://script.google.com/macros/s/AKfycbzX1w7136qfFsnRb0RMQTZvJ1Q_-GZb5HAwZF6yfKiLTHbchJZq-8H2GXjV2z5WnkmI4A/exec"

COLOR_ASSET = "#4dabf7"
COLOR_DEBT = "#ff922b"

# --- [2. 유틸리티] ---
def format_krw(val): return f"{int(val):,}".rjust(15) + " 원"

def to_numeric(val):
    try:
        if pd.isna(val): return 0
        s = str(val).replace(',', '').replace('원', '').replace(' ', '').strip()
        return int(float(s))
    except: return 0

def get_current_time():
    now = datetime.utcnow() + timedelta(hours=9)
    return now.strftime('%Y-%m-%d %H:%M:%S')

def load_sheet_data(gid):
    # 구글 캐시 우회를 위해 매번 주소를 조금씩 바꿈
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={gid}&t={datetime.now().timestamp()}"
    try:
        df = pd.read_csv(url, header=None, skiprows=1) # 제목줄 무시하고 데이터만 가져옴
        return df
    except:
        return pd.DataFrame()

# --- [3. 레이아웃] ---
st.set_page_config(page_title="JARVIS v43.1", layout="wide")
st.markdown(f"<style>.stApp {{ background-color: #ffffff; color: #212529; }} .net-box {{ background-color: #f8f9fa; padding: 20px; border-radius: 10px; border: 1px solid {COLOR_ASSET}; margin-bottom: 25px; }}</style>", unsafe_allow_html=True)

# 헤더
st.markdown(f"### {get_current_time()} | 평택 ONLINE")

# --- [4. 메뉴] ---
menu = st.sidebar.radio("MENU", ["투자 & 자산", "식단 & 건강", "재고 관리"])

# --- [5. 투자 & 자산 화면] ---
if menu == "투자 & 자산":
    st.header("종합 자산 관리")
    
    # 데이터 로드
    df_assets = load_sheet_data(GID_MAP["Assets"])
    df_log = load_sheet_data(GID_MAP["Log"])
    
    cash_diff, card_debt = 0, 0
    if not df_log.empty:
        for _, row in df_log.iterrows():
            try:
                # 시트 구조: 날짜(0), 구분(1), 대분류(2), 소분류(3), 내용(4), 금액(5)
                val = to_numeric(row[5])
                if row[1] == "지출":
                    if row[2] == "자산이동": cash_diff -= val
                    else: card_debt += val
                elif row[1] == "수입":
                    if row[2] != "자산이동": cash_diff += val
            except: continue

    if not df_assets.empty:
        # 무조건 0번 열은 이름, 1번 열은 금액으로 처리
        df_assets = df_assets[[0, 1]].copy()
        df_assets.columns = ["항목", "금액"]
        df_assets["val"] = df_assets["금액"].apply(to_numeric)
        
        # 가용현금 실시간 보정
        cash_idx = df_assets[df_assets['항목'].str.contains('가용현금', na=False)].index
        if not cash_idx.empty: df_assets.at[cash_idx[0], 'val'] += cash_diff
        
        # 순자산 계산
        a_df = df_assets[df_assets["val"] >= 0].copy()
        l_df = df_assets[df_assets["val"] < 0].copy()
        net_worth = a_df["val"].sum() + l_df["val"].sum() - card_debt

        st.markdown(f"""<div class="net-box"><small>통합 순자산 (카드지출 반영)</small><br><span style="font-size:2.5em; color:{COLOR_ASSET}; font-weight:bold;">{format_krw(net_worth)}</span></div>""", unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("보유 자산")
            st.table(a_df.assign(금액=a_df["val"].apply(format_krw))[["항목", "금액"]])
        with c2:
            st.subheader("부채 현황")
            if not l_df.empty: st.table(l_df.assign(금액=l_df["val"].apply(lambda x: format_krw(abs(x))))[["항목", "금액"]])
            st.metric("이번 달 지출 누계", format_krw(card_debt))

# --- [6. 식단 & 건강 화면] ---
elif menu == "식단 & 건강":
    st.header("영양 분석 (FatSecret 순서)")
    # 지방, 콜레스테롤, 나트륨, 탄수화물, 식이섬유, 당, 단백질
    NUTRI_ORDER = ["지방", "콜레스테롤", "나트륨", "탄수화물", "식이섬유", "당", "단백질"]
    df_log = load_sheet_data(GID_MAP["Log"])
    today_str = get_current_time().split(' ')[0]
    
    cur_nutri = {k: 0 for k in NUTRI_ORDER}
    if not df_log.empty:
        df_today = df_log[df_log[0].astype(str).str.contains(today_str)]
        for k in NUTRI_ORDER:
            try: cur_nutri[k] = df_today[(df_today[1] == '식단') & (df_today[3] == k)][5].apply(to_numeric).sum()
            except: continue

    stat_df = pd.DataFrame([{"영양소": k, "현재량": f"{cur_nutri[k]:,.1f}"} for k in NUTRI_ORDER])
    st.table(stat_df.set_index("영양소"))

# --- [7. 재고 관리 화면] ---
elif menu == "재고 관리":
    st.header("창고 재고 목록")
    if 'inventory' not in st.session_state:
        st.session_state.inventory = pd.DataFrame([
            {"구분": "귀중품", "항목": "금(실물)", "수량": "16g"},
            {"구분": "상온", "항목": "올리브유/알룰로스/스테비아", "수량": "보유"},
            {"구분": "냉동", "항목": "삼치/닭다리살/쉐이크", "수량": "보유"}
        ])
    st.data_editor(st.session_state.inventory, num_rows="dynamic", use_container_width=True)

st.sidebar.button("새로고침", on_click=st.cache_data.clear)
