import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime, timedelta

# --- [1. 시스템 설정] ---
SPREADSHEET_ID = '17kw1FMK50MUpAWA9VPSile8JZeeq6TZ9DWJqMRaBMUM'
GID_MAP = {"Log": "1716739583", "Finance": "1790876407", "Assets": "1666800532"}
API_URL = "https://script.google.com/macros/s/AKfycbzX1w7136qfFsnRb0RMQTZvJ1Q_-GZb5HAwZF6yfKiLTHbchJZq-8H2GXjV2z5WnkmI4A/exec"

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

DAILY_GUIDE = {
    "지방": {"val": 65, "unit": "g"}, "콜레스테롤": {"val": 300, "unit": "mg"},
    "나트륨": {"val": 2000, "unit": "mg"}, "탄수화물": {"val": 300, "unit": "g"},
    "식이섬유": {"val": 30, "unit": "g"}, "당": {"val": 50, "unit": "g"},
    "단백질": {"val": 150, "unit": "g"}, "칼로리": {"val": 2000, "unit": "kcal"}
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
st.set_page_config(page_title="JARVIS v33.2", layout="wide")
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
    df_sheet = load_sheet_data(GID_MAP["Assets"])
    df_sheet.columns = ["항목", "금액"]
    df_sheet["val"] = df_sheet["금액"].apply(to_numeric)
    
    inv_rows = []
    for cat, items in {"주식": FIXED_DATA["stocks"], "코인": FIXED_DATA["crypto"]}.items():
        for name, info in items.items():
            val = info['평단'] * info['수량']
            inv_rows.append({"항목": name, "금액": format_krw(val), "val": val})
    
    df_total = pd.concat([df_sheet, pd.DataFrame(inv_rows)], ignore_index=True)
    assets_df = df_total[df_total["val"] >= 0].copy()
    liabs_df = df_total[df_total["val"] < 0].copy()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("총 자산", f"{format_krw(assets_df['val'].sum())}원")
    c2.metric("총 부채", f"{format_krw(liabs_df['val'].sum())}원")
    c3.metric("순자산", f"{format_krw(assets_df['val'].sum() + liabs_df['val'].sum())}원")
    
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
    st.subheader("보스 실시간 식자재 재고 현황")
    
    # 데이터 섹션별 구성
    col1, col2 = st.columns(2)
    
    with col1:
        st.info("1. 주요 단백질류 (Protein)")
        p_df = pd.DataFrame([
            {"품목": "닭다리살", "수량": "4팩", "보관": "냉동", "비고": "-"},
            {"품목": "냉동삼치", "수량": "4팩", "보관": "냉동", "비고": "구매 권장"},
            {"품목": "단백질 쉐이크", "수량": "9개", "보관": "상온", "비고": "-"}
        ])
        p_df.index = range(1, len(p_df) + 1)
        st.table(p_df)

        st.info("3. 소스 및 기타 (Others)")
        o_df = pd.DataFrame([
            {"품목": "토마토 페이스트", "수량": "10캔", "보관": "상온", "비고": "사용 중"},
            {"품목": "나시고랭 소스", "수량": "1팩", "보관": "상온", "비고": "사용 중"},
            {"품목": "치아씨드", "수량": "약 200g", "보관": "상온", "비고": "-"},
            {"품목": "아사이베리 파우더", "수량": "약 200g", "보관": "상온", "비고": "-"},
            {"품목": "김치 4종", "수량": "각 1포기 내외", "보관": "냉장", "비고": "-"}
        ])
        o_df.index = range(1, len(o_df) + 1)
        st.table(o_df)

    with col2:
        st.info("2. 곡물 및 면류 (Grains & Noodles)")
        g_df = pd.DataFrame([
            {"품목": "카무트/쌀 혼합", "수량": "약 2kg", "보관": "상온", "비고": "-"},
            {"품목": "파스타면", "수량": "2kg", "보관": "상온", "비고": "-"},
            {"품목": "쿠스쿠스", "수량": "약 500g", "보관": "상온", "비고": "-"},
            {"품목": "우동사리", "수량": "200g x 3봉", "보관": "상온/냉장", "비고": "-"},
            {"품목": "기타 라면", "수량": "9봉", "보관": "상온", "비고": "-"}
        ])
        g_df.index = range(1, len(g_df) + 1)
        st.table(g_df)
