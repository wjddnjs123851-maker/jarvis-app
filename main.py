import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime, timedelta

# --- [1. 시스템 설정] ---
SPREADSHEET_ID = '17kw1FMK50MUpAWA9VPSile8JZeeq6TZ9DWJqMRaBMUM'
GID_MAP = {"Log": "1716739583", "Finance": "1790876407", "Assets": "1666800532"}
API_URL = "https://script.google.com/macros/s/AKfycbzX1w7136qfFsnRb0RMQTZvJ1Q_-GZb5HAwZF6yfKiLTHbchJZq-8H2GXjV2z5WnkmI4A/exec"

# 일일 권장 섭취 가이드 (체중 감량 목표 반영)
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

def to_numeric(val):
    try:
        return int(float(str(val).replace(',', '').replace('원', '').strip()))
    except: return 0

def send_to_sheet(d_type, item, value):
    now = datetime.utcnow() + timedelta(hours=9)
    payload = {"time": now.strftime('%Y-%m-%d %H:%M:%S'), "type": d_type, "item": item, "value": value}
    try:
        res = requests.post(API_URL, data=json.dumps(payload), timeout=5)
        return res.status_code == 200
    except: return False

@st.cache_data(ttl=5)
def load_sheet_data(gid):
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={gid}"
    try:
        df = pd.read_csv(url)
        return df.dropna().reset_index(drop=True)
    except: return pd.DataFrame()

# --- [3. 메인 인터페이스 설정] ---
st.set_page_config(page_title="JARVIS v32.8", layout="wide")
st.markdown("<style>.stTable td { text-align: right !important; }</style>", unsafe_allow_html=True)

with st.sidebar:
    st.title("JARVIS 제어 센터")
    menu = st.radio("메뉴 선택", ["식단 & 건강", "투자 & 자산", "재고 관리"])
    st.divider()
    
    if menu == "식단 & 건강":
        st.subheader("데이터 입력 및 실시간 분석")
        # 보스 요청 영양소 순서 고정
        in_w = st.number_input("체중(kg)", 0.0, 150.0, 125.0)
        in_fat = st.number_input("지방 (g)", 0)
        in_chol = st.number_input("콜레스테롤 (mg)", 0)
        in_na = st.number_input("나트륨 (mg)", 0)
        in_carb = st.number_input("탄수화물 (g)", 0)
        in_fiber = st.number_input("식이섬유 (g)", 0)
        in_sugar = st.number_input("당 (g)", 0)
        in_prot = st.number_input("단백질 (g)", 0)
        in_kcal = st.number_input("칼로리 (kcal)", 0)
        
        # 실시간 상태 바
        current_inputs = {"지방": in_fat, "콜레스테롤": in_chol, "나트륨": in_na, "탄수화물": in_carb, 
                          "식이섬유": in_fiber, "당": in_sugar, "단백질": in_prot, "칼로리": in_kcal}
        
        for k, v in current_inputs.items():
            if v > 0:
                ratio = min(v / DAILY_GUIDE[k], 1.0)
                st.caption(f"{k} 달성률: {int(ratio*100)}% ({v}/{DAILY_GUIDE[k]})")
                st.progress(ratio)
        
        if st.button("데이터 전송", use_container_width=True):
            send_to_sheet("건강", "체중", in_w)
            for k, v in current_inputs.items():
                if v > 0: send_to_sheet("식단", k, v)
            st.success("시트 업데이트 완료")

# --- [4. 메인 대시보드] ---
st.title(f"시스템: {menu}")

if menu == "투자 & 자산":
    # 자산 데이터 로드
    df_assets = load_sheet_data(GID_MAP["Assets"])
    
    if not df_assets.empty:
        df_assets.columns = ["항목", "금액"]
        df_assets["val"] = df_assets["금액"].apply(to_numeric)
        
        # 총계 계산
        total_a = df_assets[df_assets["val"] > 0]["val"].sum()
        total_l = df_assets[df_assets["val"] < 0]["val"].sum()
        
        # 상단 요약 카드
        c1, c2, c3 = st.columns(3)
        c1.metric("총 자산", format_krw(total_a))
        c2.metric("총 부채", format_krw(total_l))
        c3.metric("순자산", format_krw(total_a + total_l))
        
        # 상세 내역 표 (순번 1부터)
        st.subheader("항목별 상세 현황")
        display_df = df_assets[["항목", "금액"]].copy()
        display_df.index = range(1, len(display_df) + 1)
        st.table(display_df)

elif menu == "식단 & 건강":
    st.info("왼쪽 사이드바에서 데이터를 입력하면 실시간 분석과 시트 전송이 가능합니다.")
    st.divider()
    # 결혼식 목표 강조
    st.warning("목표: 5월 30일 결혼식 전 체중 감량") 

elif menu == "재고 관리":
    # 1. 생활용품 관리주기
    st.subheader("생활용품 관리주기")
    household_data = pd.DataFrame([
        {"품목": "세탁세제", "교체주기": "3개월", "상태": "양호"},
        {"품목": "칫솔", "교체주기": "1개월", "상태": "교체필요"}
    ])
    household_data.index = range(1, len(household_data) + 1)
    st.table(household_data)

    # 2. 식자재 관리
    st.subheader("식자재 재고 관리")
    food_data = pd.DataFrame([
        {"품목": "닭가슴살", "잔량": "12팩", "보관": "냉동"},
        {"품목": "계란", "잔량": "6알", "보관": "냉장"}
    ])
    food_data.index = range(1, len(food_data) + 1)
    st.table(food_data)
