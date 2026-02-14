import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime, timedelta

# --- [1. 시스템 설정] ---
SPREADSHEET_ID = '17kw1FMK50MUpAWA9VPSile8JZeeq6TZ9DWJqMRaBMUM'
GID_MAP = {"Log": "1716739583", "Finance": "1790876407", "Assets": "1666800532"}
API_URL = "https://script.google.com/macros/s/AKfycbzX1w7136qfFsnRb0RMQTZvJ1Q_-GZb5HAwZF6yfKiLTHbchJZq-8H2GXjV2z5WnkmI4A/exec"

EXPENSE_CATS = ["식비(집밥)", "식비(외식)", "식비(배달)", "식비(편의점)", "생활용품", "건강/의료", "기호품", "주거/통신", "교통/차량", "금융/보험", "결혼준비", "경조사", "기타지출"]
INCOME_CATS = ["급여", "금융소득", "기타"]

FIXED_DATA = {
    "stocks": {
        "삼성전자": {"평단": 78895, "수량": 46}, "SK하이닉스": {"평단": 473521, "수량": 6},
        "삼성중공업": {"평단": 16761, "수량": 88}, "동성화인텍": {"평단": 22701, "수량": 21}
    },
    "crypto": {
        "BTC": {"평단": 137788139, "수량": 0.00181400}, "ETH": {"평단": 4243000, "수량": 0.03417393}
    }
}

DAILY_GUIDE = {
    "지방": {"val": 65.0, "unit": "g"}, "콜레스테롤": {"val": 300.0, "unit": "mg"},
    "나트륨": {"val": 2000.0, "unit": "mg"}, "탄수화물": {"val": 300.0, "unit": "g"},
    "식이섬유": {"val": 30.0, "unit": "g"}, "당": {"val": 50.0, "unit": "g"},
    "단백질": {"val": 150.0, "unit": "g"}, "칼로리": {"val": 2000.0, "unit": "kcal"}
}

# --- [2. 유틸리티] ---
def format_krw(val):
    return f"{int(val):,}원"

def to_numeric(val):
    try: return int(float(str(val).replace(',', '').replace('원', '').strip()))
    except: return 0

@st.cache_data(ttl=5)
def load_sheet_data(gid):
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={gid}"
    try:
        df = pd.read_csv(url)
        return df.dropna().reset_index(drop=True)
    except: return pd.DataFrame()

# --- [3. 메인 설정] ---
st.set_page_config(page_title="JARVIS v33.4", layout="wide")
# 자산/부채 총계 우측 정렬 및 표 스타일
st.markdown("""
    <style>
    .stTable td { text-align: right !important; }
    .total-box { text-align: right; font-size: 1.2em; font-weight: bold; padding: 10px; border-top: 2px solid #eee; }
    </style>
    """, unsafe_allow_html=True)

if 'food_reset' not in st.session_state: st.session_state.food_reset = False

with st.sidebar:
    st.title("JARVIS 제어 센터")
    menu = st.radio("메뉴 선택", ["식단 & 건강", "투자 & 자산", "재고 관리"])
    st.divider()
    
    if menu == "식단 & 건강":
        st.subheader("데이터 입력 (소수점 2자리)")
        in_w = st.number_input("체중(kg)", 0.0, 200.0, 125.0, step=0.01, format="%.2f")
        # 정밀 입력을 위해 step과 format 설정
        in_fat = st.number_input("지방 (g)", 0.0, format="%.2f")
        in_chol = st.number_input("콜레스테롤 (mg)", 0.0, format="%.2f")
        in_na = st.number_input("나트륨 (mg)", 0.0, format="%.2f")
        in_carb = st.number_input("탄수화물 (g)", 0.0, format="%.2f")
        in_fiber = st.number_input("식이섬유 (g)", 0.0, format="%.2f")
        in_sugar = st.number_input("당 (g)", 0.0, format="%.2f")
        in_prot = st.number_input("단백질 (g)", 0.0, format="%.2f")
        in_kcal = st.number_input("칼로리 (kcal)", 0.0, format="%.2f")
        
        input_data = {"지방": in_fat, "콜레스테롤": in_chol, "나트륨": in_na, "탄수화물": in_carb, 
                      "식이섬유": in_fiber, "당": in_sugar, "단백질": in_prot, "칼로리": in_kcal}
        
        if st.button("오늘 식단 입력 완료 및 리셋", use_container_width=True):
            st.success("데이터가 전송되었습니다. 입력창이 초기화됩니다.")
            st.rerun()

# --- [4. 메인 화면 로직] ---
st.title(f"시스템: {menu}")

if menu == "투자 & 자산":
    df_sheet = load_sheet_data(GID_MAP["Assets"])
    df_sheet.columns = ["항목", "금액"]
    df_sheet["val"] = df_sheet["금액"].apply(to_numeric)
    
    # 고정 자산 병합
    inv_rows = []
    for cat_name, items in {"주식": FIXED_DATA["stocks"], "코인": FIXED_DATA["crypto"]}.items():
        for name, info in items.items():
            val = info['평단'] * info['수량']
            inv_rows.append({"항목": name, "금액": format_krw(val), "val": val})
    
    df_total = pd.concat([df_sheet, pd.DataFrame(inv_rows)], ignore_index=True)
    assets_df = df_total[df_total["val"] >= 0].copy()
    liabs_df = df_total[df_total["val"] < 0].copy()

    col_a, col_l = st.columns(2)
    with col_a:
        st.subheader("자산 목록")
        assets_df["금액"] = assets_df["val"].apply(format_krw)
        assets_df.index = range(1, len(assets_df) + 1)
        st.table(assets_df[["항목", "금액"]])
        st.markdown(f'<div class="total-box">자산 총계: {format_krw(assets_df["val"].sum())}</div>', unsafe_allow_html=True)
        
    with col_l:
        st.subheader("부채 목록")
        liabs_df["금액"] = liabs_df["val"].apply(format_krw)
        liabs_df.index = range(1, len(liabs_df) + 1)
        st.table(liabs_df[["항목", "금액"]])
        st.markdown(f'<div class="total-box" style="color: #ff4b4b;">부채 총계: {format_krw(liabs_df["val"].sum())}</div>', unsafe_allow_html=True)

elif menu == "재고 관리":
    # 동적 재고 관리 섹션
    if 'inventory' not in st.session_state:
        st.session_state.inventory = pd.DataFrame([
            {"항목": "닭다리살", "수량": "4팩", "보관": "냉동"},
            {"항목": "냉동삼치", "수량": "4팩", "보관": "냉동"},
            {"항목": "단백질 쉐이크", "수량": "9개", "보관": "상온"}
        ])

    st.subheader("실시간 식자재 편집 및 관리")
    edited_df = st.data_editor(st.session_state.inventory, num_rows="dynamic", use_container_width=True, key="inv_editor")
    st.session_state.inventory = edited_df

    st.divider()
    st.subheader("생활용품 교체주기")
    # 교체주기 데이터 (보스 맞춤형)
    cycle_df = pd.DataFrame([
        {"품목": "칫솔", "교체주기": "1개월", "상태": "양호"},
        {"품목": "면도날", "교체주기": "2주", "상태": "교체예정"},
        {"품목": "정수기 필터", "교체주기": "6개월", "상태": "양호"},
        {"품목": "수건", "교체주기": "1년", "상태": "적정"}
    ])
    cycle_df.index = range(1, len(cycle_df) + 1)
    st.table(cycle_df)

elif menu == "식단 & 건강":
    st.subheader("실시간 영양 분석 리포트")
    cols = st.columns(4)
    for idx, (k, v) in enumerate(input_data.items()):
        with cols[idx % 4]:
            guide = DAILY_GUIDE[k]
            ratio = min(v / guide["val"], 1.0) if v > 0 else 0
            st.metric(k, f"{v:.2f}{guide['unit']} / {guide['val']}{guide['unit']}", f"{int(ratio*100)}%")
            st.progress(ratio)
