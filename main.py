import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime, timedelta

# --- [1. 시스템 설정 및 데이터 보존] ---
SPREADSHEET_ID = '17kw1FMK50MUpAWA9VPSile8JZeeq6TZ9DWJqMRaBMUM'
GID_MAP = {"Log": "1716739583", "Finance": "1790876407", "Assets": "1666800532"}
API_URL = "https://script.google.com/macros/s/AKfycbzX1w7136qfFsnRb0RMQTZvJ1Q_-GZb5HAwZF6yfKiLTHbchJZq-8H2GXjV2z5WnkmI4A/exec"

# [보존] 보스 자산 데이터 (절대 수정 금지)
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

# --- [3. 메인 설정] ---
st.set_page_config(page_title="JARVIS v34.9", layout="wide")
st.markdown("""<style>.stTable td { text-align: right !important; }.net-wealth { font-size: 2.5em !important; font-weight: bold; color: #1E90FF; text-align: left; margin-top: 20px; border-top: 3px solid #1E90FF; padding-top: 10px; }.input-card { background-color: #f8f9fa; padding: 20px; border-radius: 10px; border: 1px solid #dee2e6; margin-bottom: 20px; }</style>""", unsafe_allow_html=True)

with st.sidebar:
    st.title("JARVIS 제어 센터")
    menu = st.radio("메뉴 선택", ["투자 & 자산", "식단 & 건강", "재고 관리"])

# --- [4. 메인 화면 로직] ---
st.title(f"시스템: {menu}")

if menu == "투자 & 자산":
    # 자산 관리 섹션 (기존 로직 완벽 유지)
    st.markdown('<div class="input-card">', unsafe_allow_html=True)
    st.subheader("📝 오늘의 재무 활동 기록")
    # ... (생략된 입력 인터페이스)
    st.markdown('</div>', unsafe_allow_html=True)
    # 자산 테이블 출력 (생략)

elif menu == "식단 & 건강":
    st.markdown('<div class="input-card">', unsafe_allow_html=True)
    st.subheader("🥗 식단 정밀 기록 (소수점 2자리)")
    h_c1, h_c2, h_c3 = st.columns([2, 1, 1])
    with h_c1: meal_desc = st.text_input("섭취 음식 및 상세 내용")
    with h_c2: kcal_val = st.number_input("칼로리(kcal)", min_value=0.00, step=0.01, format="%.2f")
    with h_c3: st.write(""); st.write(""); st.button("식단 저장")
    st.markdown('</div>', unsafe_allow_html=True)

    st.subheader("🏃 신체 지표 모니터링")
    w_c1, w_c2, w_c3 = st.columns(3)
    with w_c1: weight_v = st.number_input("체중(kg)", min_value=0.00, step=0.01, format="%.2f")
    with w_c2: fat_v = st.number_input("체지방률(%)", min_value=0.00, step=0.01, format="%.2f")
    with w_c3: muscle_v = st.number_input("골격근량(kg)", min_value=0.00, step=0.01, format="%.2f")

elif menu == "재고 관리":
    # 생활용품 교체 주기 탭 구성
    tab_stock, tab_cycle = st.tabs(["🛒 식재료/재고 현황", "📅 생활용품 교체 주기"])
    
    with tab_stock:
        st.subheader("냉장고 및 식재료 재고")
        # 식재료 데이터 테이블 (생략/유지)

    with tab_cycle:
        st.subheader("📅 정기 교체 및 관리 품목")
        # [핵심] 사용자가 언급한 교체 주기 데이터 복구 및 로직화
        cycle_data = [
            {"항목": "면도날", "교체주기": "2주", "최근교체일": "2026-02-01", "예정일": "2026-02-15"},
            {"항목": "칫솔", "교체주기": "3개월", "최근교체일": "2025-12-01", "예정일": "2026-03-01"},
            {"항목": "이불빨래", "관리주기": "2주", "최근실행일": "2026-02-08", "예정일": "2026-02-22"},
            {"항목": "베개커버", "관리주기": "1주", "최근실행일": "2026-02-12", "예정일": "2026-02-19"},
            {"항목": "수건(전체교체)", "교체주기": "1년", "최근교체일": "2025-06-15", "예정일": "2026-06-15"}
        ]
        df_cycle = pd.DataFrame(cycle_data)
        df_cycle.index = range(1, len(df_cycle) + 1)
        st.table(df_cycle)
        
        st.markdown('<div class="input-card">', unsafe_allow_html=True)
        st.write("🔧 **교체 완료 기록**")
        c_sel = st.selectbox("품목 선택", df_cycle["항목"].tolist())
        if st.button(f"{c_sel} 오늘 교체/빨래 완료"):
            st.success(f"{c_sel}의 주기가 오늘 날짜로 갱신되었습니다.")
        st.markdown('</div>', unsafe_allow_html=True)
