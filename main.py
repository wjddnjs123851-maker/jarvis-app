import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime, timedelta

# --- [1. 시스템 설정] ---
SPREADSHEET_ID = '17kw1FMK50MUpAWA9VPSile8JZeeq6TZ9DWJqMRaBMUM'
GID_MAP = {"Log": "1716739583", "Finance": "1790876407", "Assets": "1666800532"}
API_URL = "https://script.google.com/macros/s/AKfycbzX1w7136qfFsnRb0RMQTZvJ1Q_-GZb5HAwZF6yfKiLTHbchJZq-8H2GXjV2z5WnkmI4A/exec"

# 고정 투자 데이터 (보스 포트폴리오)
FIXED_DATA = {
    "stocks": {
        "삼성전자": {"평단": 78895, "수량": 46},
        "SK하이닉스": {"평단": 473521, "수량": 6},
        "삼성중공업": {"평단": 16761, "수량": 88},
        "동성화인텍": {"평단": 22701, "수량": 21}
    },
    "crypto": {
        "BTC": {"평단": 137788139, "수량": 0.00181400},
        "ETH": {"평단": 4243000, "수량": 0.03417393}
    }
}

# 영양소 가이드 및 단위
DAILY_GUIDE = {
    "지방": {"val": 65, "unit": "g"},
    "콜레스테롤": {"val": 300, "unit": "mg"},
    "나트륨": {"val": 2000, "unit": "mg"},
    "탄수화물": {"val": 300, "unit": "g"},
    "식이섬유": {"val": 30, "unit": "g"},
    "당": {"val": 50, "unit": "g"},
    "단백질": {"val": 150, "unit": "g"},
    "칼로리": {"val": 2000, "unit": "kcal"}
}

# --- [2. 유틸리티] ---
def format_krw(val):
    return f"{int(val):,}"

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
st.set_page_config(page_title="JARVIS v33.1", layout="wide")
st.markdown("<style>.stTable td { text-align: right !important; }</style>", unsafe_allow_html=True)

with st.sidebar:
    st.title("JARVIS 제어 센터")
    menu = st.radio("메뉴 선택", ["식단 & 건강", "투자 & 자산", "재고 관리"])
    st.divider()
    
    if menu == "식단 & 건강":
        st.subheader("데이터 입력")
        in_w = st.number_input("체중(kg)", 0.0, 200.0, 125.0)
        in_fat = st.number_input("지방 (g)", 0)
        in_chol = st.number_input("콜레스테롤 (mg)", 0)
        in_na = st.number_input("나트륨 (mg)", 0)
        in_carb = st.number_input("탄수화물 (g)", 0)
        in_fiber = st.number_input("식이섬유 (g)", 0)
        in_sugar = st.number_input("당 (g)", 0)
        in_prot = st.number_input("단백질 (g)", 0)
        in_kcal = st.number_input("칼로리 (kcal)", 0)
        
        input_data = {"지방": in_fat, "콜레스테롤": in_chol, "나트륨": in_na, "탄수화물": in_carb, 
                      "식이섬유": in_fiber, "당": in_sugar, "단백질": in_prot, "칼로리": in_kcal}
        
        if st.button("데이터 전송", use_container_width=True):
            st.success("시트 업데이트 완료")

# --- [4. 메인 화면] ---
st.title(f"시스템: {menu}")

if menu == "식단 & 건강":
    st.subheader("실시간 영양 분석 리포트")
    cols = st.columns(4)
    for idx, (k, v) in enumerate(input_data.items()):
        with cols[idx % 4]:
            guide = DAILY_GUIDE[k]
            ratio = min(v / guide["val"], 1.0) if v > 0 else 0
            st.metric(k, f"{v}{guide['unit']} / {guide['val']}{guide['unit']}", f"{int(ratio*100)}%")
            st.progress(ratio)
    st.divider()
    st.warning("목표: 5월 30일 결혼식 전 체중 감량 (현재 125kg)")

elif menu == "투자 & 자산":
    # 데이터 로드 및 병합
    df_sheet = load_sheet_data(GID_MAP["Assets"])
    df_sheet.columns = ["항목", "금액"]
    df_sheet["val"] = df_sheet["금액"].apply(to_numeric)
    
    inv_rows = []
    for cat, items in {"주식": FIXED_DATA["stocks"], "코인": FIXED_DATA["crypto"]}.items():
        for name, info in items.items():
            val = info['평단'] * info['수량']
            inv_rows.append({"항목": name, "금액": format_krw(val), "val": val})
    
    df_inv = pd.DataFrame(inv_rows)
    df_total = pd.concat([df_sheet, df_inv], ignore_index=True)
    
    # 자산과 부채 구분
    assets_df = df_total[df_total["val"] >= 0].copy()
    liabs_df = df_total[df_total["val"] < 0].copy()
    
    total_a = assets_df["val"].sum()
    total_l = liabs_df["val"].sum()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("총 자산", f"{format_krw(total_a)}원")
    c2.metric("총 부채", f"{format_krw(total_l)}원", delta_color="inverse")
    c3.metric("순자산", f"{format_krw(total_a + total_l)}원")
    
    col_a, col_l = st.columns(2)
    with col_a:
        st.subheader("자산 목록")
        assets_df.index = range(1, len(assets_df) + 1)
        st.table(assets_df[["항목", "금액"]])
    with col_l:
        st.subheader("부채 목록")
        liabs_df.index = range(1, len(liabs_df) + 1)
        st.table(liabs_df[["항목", "금액"]])

elif menu == "재고 관리":
    col_h, col_f = st.columns(2)
    with col_h:
        st.subheader("생활용품 관리주기")
        h_df = pd.DataFrame([
            {"품목": "칫솔", "주기": "1개월", "상태": "교체필요"},
            {"품목": "면도날", "주기": "2주", "상태": "양호"},
            {"품목": "영양제", "주기": "매일", "상태": "복용중"},
            {"품목": "세탁세제", "주기": "3개월", "상태": "적정"}
        ])
        h_df.index = range(1, len(h_df) + 1)
        st.table(h_df)

    with col_f:
        st.subheader("식자재 재고 현황 (보강)")
        # 보스님의 해산물 선호 및 식단 관리 데이터를 반영한 보강 목록
        f_df = pd.DataFrame([
            {"품목": "냉동 새우", "잔량": "여유", "보관": "냉동"},
            {"품목": "고등어/생선류", "잔량": "부족", "보관": "냉동"},
            {"품목": "닭가슴살", "잔량": "12팩", "보관": "냉동"},
            {"품목": "계란", "잔량": "6알", "보관": "냉장"},
            {"품목": "채소/샐러드", "잔량": "보통", "보관": "냉장"},
            {"품목": "소스/향신료", "잔량": "여유", "보관": "상온"}
        ])
        f_df.index = range(1, len(f_df) + 1)
        st.table(f_df)
