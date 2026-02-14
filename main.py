import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime, timedelta

# --- [1. 시스템 설정] ---
SPREADSHEET_ID = '17kw1FMK50MUpAWA9VPSile8JZeeq6TZ9DWJqMRaBMUM'
GID_MAP = {"Log": "1716739583", "Finance": "1790876407", "Assets": "1666800532"}
API_URL = "https://script.google.com/macros/s/AKfycbzX1w7136qfFsnRb0RMQTZvJ1Q_-GZb5HAwZF6yfKiLTHbchJZq-8H2GXjV2z5WnkmI4A/exec"

# 일일 권장 섭취량 가이드라인 (보스 전용)
DAILY_GUIDE = {
    "지방": 65, "콜레스테롤": 300, "나트륨": 2000, 
    "탄수화물": 300, "식이섬유": 30, "당": 50, "단백질": 150, "칼로리": 2000
}

# --- [2. 유틸리티] ---
def format_krw(val):
    try:
        n = int(float(str(val).replace(',', '').replace('원', '').strip()))
        return f"{n:,}원"
    except: return "0원"

def send_to_sheet(d_type, item, value):
    now = datetime.utcnow() + timedelta(hours=9)
    payload = {"time": now.strftime('%Y-%m-%d %H:%M:%S'), "type": d_type, "item": item, "value": value}
    try:
        res = requests.post(API_URL, data=json.dumps(payload), timeout=5)
        return res.status_code == 200
    except: return False

@st.cache_data(ttl=5)
def load_assets():
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={GID_MAP['Assets']}"
    try:
        df = pd.read_csv(url)
        return df.dropna().reset_index(drop=True)
    except: return pd.DataFrame()

# --- [3. 메인 인터페이스 스타일] ---
st.set_page_config(page_title="JARVIS v32.7", layout="wide")
st.markdown("<style>.stTable td { text-align: right !important; }</style>", unsafe_allow_html=True)

with st.sidebar:
    st.title("JARVIS 제어 센터")
    menu = st.radio("메뉴 선택", ["식단 & 건강", "투자 & 자산", "재고 관리"])
    st.divider()
    
    if menu == "식단 & 건강":
        st.subheader("실시간 섭취 분석")
        in_fat = st.number_input("지방 (g)", 0)
        in_chol = st.number_input("콜레스테롤 (mg)", 0)
        in_na = st.number_input("나트륨 (mg)", 0)
        in_carb = st.number_input("탄수화물 (g)", 0)
        in_fiber = st.number_input("식이섬유 (g)", 0)
        in_sugar = st.number_input("당 (g)", 0)
        in_prot = st.number_input("단백질 (g)", 0)
        in_kcal = st.number_input("칼로리 (kcal)", 0)
        
        # 실시간 상태 표시
        input_data = {"지방": in_fat, "콜레스테롤": in_chol, "나트륨": in_na, "탄수화물": in_carb, 
                      "식이섬유": in_fiber, "당": in_sugar, "단백질": in_prot, "칼로리": in_kcal}
        
        for k, v in input_data.items():
            if v > 0:
                ratio = min(v / DAILY_GUIDE[k], 1.0)
                st.caption(f"{k}: {v} / {DAILY_GUIDE[k]}")
                st.progress(ratio)
        
        if st.button("시트로 전송", use_container_width=True):
            for k, v in input_data.items():
                if v > 0: send_to_sheet("식단", k, v)
            st.success("전송 완료")

# --- [4. 메인 화면] ---
st.title(f"시스템: {menu}")

if menu == "투자 & 자산":
    df_raw = load_assets()
    if not df_raw.empty:
        # 데이터 정리 및 총계 계산
        df_raw.columns = ["항목", "금액"]
        df_raw["numeric"] = df_raw["금액"].apply(lambda x: int(float(str(x).replace(',', '').replace('원', '').strip())))
        
        # 자산/부채 분리 (금액이 마이너스면 부채로 간주하거나 항목 이름으로 판별 가능)
        assets = df_raw[df_raw["numeric"] >= 0]
        liabilities = df_raw[df_raw["numeric"] < 0]
        
        total_asset = assets["numeric"].sum()
        total_liab = liabilities["numeric"].sum()
        
        st.subheader("자산 및 부채 상세")
        df_display = df_raw[["항목", "금액"]].copy()
        df_display.index = range(1, len(df_display) + 1) # 순번 1부터 시작
        st.table(df_display)
        
        # 하단 총계 요약
        st.divider()
        c1, c2, c3 = st.columns(3)
        c1.metric("자산 총계", format_krw(total_asset))
        c2.metric("부채 총계", format_krw(total_liab))
        c3.metric("순자산", format_krw(total_asset + total_liab))

elif menu == "재고 관리":
    # 1. 생활용품 관리주기
    st.subheader("생활용품 관리주기")
    household_df = pd.DataFrame([
        {"품목": "세탁세제", "교체/구매주기": "3개월", "최근교체": "2026-01-10", "상태": "양호"},
        {"품목": "칫솔", "교체/구매주기": "1개월", "최근교체": "2026-01-25", "상태": "교체예정"},
    ])
    household_df.index = range(1, len(household_df) + 1)
    st.table(household_df)

    # 2. 식자재 관리
    st.subheader("식자재 재고 현황")
    food_df = pd.DataFrame([
        {"품목": "닭가슴살", "유통기한": "2026-05-30", "잔량": "10팩", "보관": "냉동"},
        {"품목": "계란", "유통기한": "2026-02-25", "잔량": "5알", "보관": "냉장"},
    ])
    food_df.index = range(1, len(food_df) + 1)
    st.table(food_df)
