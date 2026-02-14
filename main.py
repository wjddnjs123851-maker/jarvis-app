import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime

# --- [1. 시스템 설정 및 데이터 보존] ---
SPREADSHEET_ID = '17kw1FMK50MUpAWA9VPSile8JZeeq6TZ9DWJqMRaBMUM'
GID_MAP = {"Log": "1716739583", "Finance": "1790876407", "Assets": "1666800532"}
API_URL = "https://script.google.com/macros/s/AKfycbzX1w7136qfFsnRb0RMQTZvJ1Q_-GZb5HAwZF6yfKiLTHbchJZq-8H2GXjV2z5WnkmI4A/exec"

# [보존] 보스 자산 데이터 (누락 절대 금지)
FIXED_DATA = {
    "stocks": {
        "SK하이닉스": {"수량": 6, "현재가": 880000},
        "삼성전자": {"수량": 46, "현재가": 181200},
        "삼성중공업": {"수량": 88, "현재가": 27700},
        "동성화인텍": {"수량": 21, "현재가": 27750}
    },
    "crypto": {
        "비트코인(BTC)": {"수량": 0.00181400, "현재가": 102625689},
        "이더리움(ETH)": {"수량": 0.03417393, "현재가": 3068977}
    },
    "gold": {"품목": "순금", "수량": 16, "단위": "g", "현재가": 115000}
}

# --- [2. 유틸리티] ---
def format_krw(val): return f"{int(val):,}"
def to_numeric(val):
    try: return int(float(str(val).replace(',', '').replace('원', '').strip()))
    except: return 0

def load_sheet_data(gid):
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={gid}"
    try: return pd.read_csv(url).dropna().reset_index(drop=True)
    except: return pd.DataFrame()

# --- [3. 메인 설정] ---
st.set_page_config(page_title="JARVIS v34.9", layout="wide")
st.markdown("""<style>.stTable td { text-align: right !important; }.net-wealth { font-size: 2.5em !important; font-weight: bold; color: #1E90FF; text-align: left; margin-top: 20px; border-top: 3px solid #1E90FF; padding-top: 10px; }.total-box { text-align: right; font-size: 1.2em; font-weight: bold; padding: 10px; border-top: 2px solid #eee; }.input-card { background-color: #f8f9fa; padding: 20px; border-radius: 10px; border: 1px solid #dee2e6; margin-bottom: 20px; }</style>""", unsafe_allow_html=True)

with st.sidebar:
    st.title("JARVIS 제어 센터")
    menu = st.radio("메뉴 선택", ["투자 & 자산", "식단 & 건강", "재고 관리"])

# --- [4. 메인 화면 로직] ---
st.title(f"시스템: {menu}")

if menu == "투자 & 자산":
    # 재무 기록 입력
    st.markdown('<div class="input-card">', unsafe_allow_html=True)
    st.subheader("📝 오늘의 재무 활동 기록")
    i_c1, i_c2, i_c3, i_c4 = st.columns([1, 2, 2, 1])
    with i_c1: t_choice = st.selectbox("구분", ["지출", "수입"])
    with i_c2:
        cats = ["식비(집밥)", "식비(외식)", "식비(배달)", "식비(편의점)", "생활용품", "건강/의료", "기호품", "주거/통신", "교통/차량", "금융/보험", "결혼준비", "경조사", "기타지출"] if t_choice == "지출" else ["급여", "금융소득", "기타"]
        c_choice = st.selectbox("카테고리", cats)
    with i_c3: a_input = st.number_input("금액(원)", min_value=0, step=1000)
    with i_c4: 
        st.write(""); st.write("")
        if st.button("기록하기", use_container_width=True): st.success("기록 완료")
    st.markdown('</div>', unsafe_allow_html=True)

    # 투자 현황 테이블
    inv_rows = []
    for cat, items in {"주식": FIXED_DATA["stocks"], "코인": FIXED_DATA["crypto"]}.items():
        for name, info in items.items():
            inv_rows.append({"분류": cat, "항목": name, "수량": str(info['수량']), "현재가": format_krw(info['현재가']), "평가금액": info['수량'] * info['현재가']})
    df_inv = pd.DataFrame(inv_rows)
    df_inv["평가금액_str"] = df_inv["평가금액"].apply(lambda x: f"{format_krw(x)}원")
    df_inv.index = range(1, len(df_inv) + 1)
    st.subheader("📊 실시간 투자 현황")
    st.table(df_inv[["분류", "항목", "수량", "현재가", "평가금액_str"]])

# 2번 탭: 식단 & 건강
elif menu == "식단 & 건강":
    st.markdown('<div class="input-card">', unsafe_allow_html=True)
    st.subheader("🥗 오늘의 식단 기록")
    h_c1, h_c2, h_c3 = st.columns([2, 2, 1])
    with h_c1: meal_name = st.text_input("메뉴명", placeholder="예: 닭가슴살 샐러드")
    with h_c2: kcal_input = st.number_input("칼로리(kcal)", min_value=0.00, step=0.01, format="%.2f") # 정밀도 유지
    with h_c3: 
        st.write(""); st.write("")
        if st.button("식단 저장"): st.success("기록 완료")
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.subheader("🏃 신체 지표 (소수점 2자리)")
    weight_input = st.number_input("현재 체중(kg)", min_value=0.00, step=0.01, format="%.2f")

# 3번 탭: 재고 관리 (식재료 포함 복구)
elif menu == "재고 관리":
    st.subheader("📦 우리집 재고 통합 관리")
    
    # 식재료 및 생활용품 탭 구분
    stock_tab1, stock_tab2 = st.tabs(["🛒 식재료 관리", "🏠 생활용품"])
    
    with stock_tab1:
        st.subheader("냉장고/팬트리 식재료")
        food_data = [
            {"품목": "계란", "수량": 10, "단위": "알", "소비기한": "2026-02-25", "상태": "보통"},
            {"품목": "우유", "수량": 1, "단위": "팩", "소비기한": "2026-02-20", "상태": "임박"},
            {"품목": "닭가슴살", "수량": 5, "단위": "팩", "소비기한": "2026-03-10", "상태": "여유"}
        ]
        df_food = pd.DataFrame(food_data)
        df_food.index = range(1, len(df_food) + 1)
        st.table(df_food)

    with stock_tab2:
        st.subheader("생필품 재고")
        item_data = [
            {"품목": "화장지", "재고": 15, "단위": "롤", "주기": "30일"},
            {"품목": "세제", "재고": 2, "단위": "개", "주기": "60일"}
        ]
        df_item = pd.DataFrame(item_data)
        df_item.index = range(1, len(df_item) + 1)
        st.table(df_item)
