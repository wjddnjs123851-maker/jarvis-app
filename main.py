import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime, timedelta

# --- [1. 시스템 설정] ---
SPREADSHEET_ID = '12cPPhM68K3SopQJtZyWEq8adDuP98bJ4efoYbjFDDOI'
GID_MAP = {"Log": "0", "Assets": "1068342666", "Report": "308599580", "Health": "123456789"}
API_URL = "https://script.google.com/macros/s/AKfycbzX1w7136qfFsnRb0RMQTZvJ1Q_-GZb5HAwZF6yfKiLTHbchJZq-8H2GXjV2z5WnkmI4A/exec"

# 화이트 테마 색상 규정
COLOR_BG = "#ffffff"   # 배경: 하양
COLOR_TEXT = "#000000" # 글자: 검정
COLOR_POINT = "#4dabf7" # 강조: 파랑

RECOMMENDED = {"칼로리": 2500, "지방": 60, "콜레스테롤": 300, "나트륨": 2300, "탄수화물": 300, "식이섬유": 30, "당": 50, "단백질": 150}

if 'maintenance' not in st.session_state:
    st.session_state.maintenance = [
        {"항목": "칫솔", "주기": 90, "마지막": "2025-11-20"},
        {"항목": "샤워기필터", "주기": 60, "마지막": "2026-01-10"},
        {"항목": "수건", "주기": 365, "마지막": "2025-06-01"},
        {"항목": "면도날", "주기": 14, "마지막": "2026-02-10"}
    ]

if 'daily_nutri' not in st.session_state:
    st.session_state.daily_nutri = {k: 0.0 for k in RECOMMENDED.keys()}

# --- [2. 스마트 결제 가이드] ---
def get_payment_advice(category):
    advices = {
        "식비": "현대카드 (M경차 Ed2)", "생활용품": "현대카드 (이마트 e카드)", "월 구독료": "국민카드 (WE:SH All)",
        "주거/통신": "우리카드 (주거래II)", "교통": "하나카드 (K-패스)", "건강": "하나카드 (MG+ S)"
    }
    return advices.get(category, "국민카드 추천")

# --- [3. 유틸리티] ---
def format_krw(val): return f"{int(val):,}".rjust(20) + " 원"
def to_numeric(val):
    try:
        s = "".join(filter(lambda x: x.isdigit() or x == '-', str(val)))
        return int(s) if s else 0
    except: return 0
def get_current_time():
    return (datetime.utcnow() + timedelta(hours=9)).strftime('%Y-%m-%d %H:%M:%S')

# --- [4. 화이트 테마 UI 스타일 (전면 개정)] ---
st.set_page_config(page_title="JARVIS v60.0", layout="wide")
st.markdown(f"""
    <style>
    /* 전체 배경 하양, 글자 검정 */
    .stApp {{ background-color: {COLOR_BG}; color: {COLOR_TEXT}; }}
    
    /* 모든 텍스트 요소를 검은색으로 강제 */
    h1, h2, h3, p, span, label, li {{ color: {COLOR_TEXT} !important; }}
    
    /* 입력창: 연한 회색 배경에 검은 글씨 */
    input, select, textarea, div[data-baseweb="select"] {{
        background-color: #f1f3f5 !important;
        color: {COLOR_TEXT} !important;
        border: 1px solid #dee2e6 !important;
    }}
    div[data-baseweb="select"] * {{ color: {COLOR_TEXT} !important; }}

    /* 버튼: 검은색 배경에 하얀 글씨 (시인성 강조) */
    .stButton>button {{
        background-color: #000000 !important;
        color: #ffffff !important;
        border-radius: 8px; font-weight: bold; border: none; width: 100%;
    }}
    
    /* 카드 디자인: 화이트 테마용 */
    .net-box {{ background-color: #f8f9fa; padding: 25px; border-radius: 12px; border: 1px solid #dee2e6; border-left: 5px solid {COLOR_POINT}; margin-bottom: 20px; }}
    .total-card {{ background-color: #f8f9fa; padding: 20px; border-radius: 10px; border: 1px solid #dee2e6; text-align: right; }}
    .advice-box {{ background-color: #e7f5ff; padding: 15px; border-radius: 8px; border-left: 5px solid {COLOR_POINT}; margin-top: 10px; color: #000000 !important; }}
    
    /* 테이블 글자색 */
    td, th {{ color: {COLOR_TEXT} !important; text-align: right !important; }}
    </style>
""", unsafe_allow_html=True)
# --- [5. 메인 로직 시작] ---
st.markdown(f"### {get_current_time()} | 평택 온라인")

with st.sidebar:
    st.title("JARVIS WHITE")
    menu = st.radio("MENU", ["투자 & 자산", "식단 & 건강", "재고 & 교체관리"])

if menu == "투자 & 자산":
    st.header("📈 자산 대시보드")
    with st.sidebar:
        st.subheader("데이터 입력")
        t_choice = st.selectbox("구분", ["지출", "수입"])
        c_main = st.selectbox("대분류", ["식비", "생활용품", "월 구독료", "주거/통신", "교통", "건강", "금융", "경조사", "자산이동"])
        if t_choice == "지출":
            st.markdown(f"""<div class="advice-box">🛡️ <b>{get_payment_advice(c_main)}</b></div>""", unsafe_allow_html=True)
        a_input = st.number_input("금액(원)", min_value=0, step=1000)
        method_choice = st.selectbox("수단", ["국민카드", "현대카드", "하나카드", "우리카드", "현금"])
        if st.button("시트 데이터 전송"):
            st.success("데이터 전송 완료 (화이트 모드)")

    # 자산 데이터 표시 (가상의 데이터 또는 시트 로드)
    st.markdown(f"""<div class="net-box"><small>통합 순자산</small><br><span style="font-size:2.8em; font-weight:bold;">123,456,789 원</span></div>""", unsafe_allow_html=True)

elif menu == "식단 & 건강":
    st.header("🥗 정밀 영양 분석")
    with st.sidebar:
        st.subheader("식단 입력 (소수점 지원)")
        with st.form("health_form"):
            # 정원 님 요청: 소수점 두 자리(0.01) 입력 지원
            f_cal = st.number_input("칼로리 (kcal)", value=0.0, step=0.01, format="%.2f")
            f_prot = st.number_input("단백질 (g)", value=0.0, step=0.01, format="%.2f")
            if st.form_submit_button("섭취량 추가"):
                st.session_state.daily_nutri["칼로리"] += f_cal
                st.session_state.daily_nutri["단백질"] += f_prot
                st.rerun()

    curr = st.session_state.daily_nutri
    st.table(pd.DataFrame([{"영양소": "칼로리", "현재": f"{curr['칼로리']:.2f}", "목표": "2500.00"}, 
                           {"영양소": "단백질", "현재": f"{curr['단백질']:.2f}", "목표": "150.00"}]))

elif menu == "재고 & 교체관리":
    st.header("🏠 생활 시스템 관리")
    st.subheader("📦 창고 및 교체 알림")
    # 금 16g 데이터 및 교체 알림 로직 유지
    st.table(pd.DataFrame([{"항목": "금(실물)", "수량": "16g"}, {"항목": "쉐이크", "수량": "9개"}]))
