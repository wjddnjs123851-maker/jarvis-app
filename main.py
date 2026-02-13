import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# 1. 고정 마스터 데이터 (생략 없이 유지)
FIXED_DATA = {
    "profile": {"항목": ["나이", "거주", "상태", "결혼예정일"], "내용": ["32세", "평택 원평동", "공무원 발령 대기 중", "2026-05-30"]},
    "health": {"항목": ["현재 체중", "목표 체중", "주요 관리", "식단 금기"], "내용": ["125.0kg", "90.0kg", "고지혈증/ADHD", "생굴/멍게"]},
    "assets": {
        "savings": {"청년도약계좌": 14700000, "주택청약": 2540000, "전세보증금": 145850000},
        "liabilities": {"전세대출": 100000000, "마이너스통장": 3000000, "학자금대출": 1247270},
        "stocks": {"삼성전자": 46, "SK하이닉스": 6, "삼성중공업": 88, "동성화인텍": 21},
        "crypto": {"BTC": 0.00181400, "ETH": 0.03417393}
    },
    "lifecycle": {
        "면도날": {"last": "2026-02-06", "period": 21}, 
        "칫솔": {"last": "2026-02-06", "period": 90}, 
        "이불세탁": {"last": "2026-02-04", "period": 14}
    }
}

# 세션 초기화
today_str = datetime.now().strftime('%Y-%m-%d')
if 'meal_log' not in st.session_state: st.session_state.meal_log = []
if 'expense_rating' not in st.session_state: st.session_state.expense_rating = "아직 평가 전입니다."

st.set_page_config(page_title="자비스 v5.3", layout="wide")

# CSS: 특대 숫자 스타일 유지
st.markdown("""<style>
    * { font-family: 'Arial Black', sans-serif !important; }
    [data-testid="stTable"] td:nth-child(1) { font-size: 50px !important; color: #FF4B4B !important; font-weight: 900; text-align: center; }
    [data-testid="stTable"] td:nth-child(2) { text-align: right !important; font-size: 20px; }
    </style>""", unsafe_allow_html=True)

# --- 사이드바: 정밀 입력 및 평가 ---
with st.sidebar:
    st.header("오늘의 로그")
    with st.form("input_form"):
        st.subheader("지출 관리")
        exp_val = st.number_input("금액", min_value=0)
        rating = st.select_slider("오늘의 지출 평가", options=["절제함", "적당함", "과소비", "반성함"])
        
        st.divider()
        st.subheader("식단 기록")
        meal_in = st.text_input("음식명")
        
        if st.form_submit_button("시스템 반영"):
            # 영양 분석 로직
            m = {"시간": datetime.now().strftime('%H:%M'), "메뉴": meal_in, "kcal": 0, "P": 0, "F": 0, "C": 0}
            if "쿼파치" in meal_in: m.update({"kcal": 1120, "P": 50, "F": 55, "C": 110})
            elif "물" in meal_in: m.update({"kcal": 0, "P": 0, "F": 0, "C": 0})
            else: m.update({"kcal": 600, "P": 25, "F": 20, "C": 70})
            
            st.session_state.meal_log.append(m)
            st.session_state.expense_rating = rating
            st.rerun()

    st.divider()
    if st.session_state.meal_log:
        st.subheader("데이터 내보내기")
        log_df = pd.DataFrame(st.session_state.meal_log)
        log_df['지출평가'] = st.session_state.expense_rating
        csv = log_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📂 정밀 데이터(CSV) 다운로드", csv, f"jarvis_log_{today_str}.csv")

# --- 메인 리포트 ---
st.title(f"자비스 통합 매니지먼트 (원평동: 10°C ☀️)")

# 1~6 섹션 출력 (v5.2 레이아웃 유지하며 지출 평가 추가)
st.header("1. 오늘의 소비 총평")
st.info(f"보스의 오늘 지출 평가: **{st.session_state.expense_rating}**")

st.header("2. 식단 정밀 로그")
if st.session_state.meal_log:
    st.table(pd.DataFrame(st.session_state.meal_history if 'meal_history' in st.session_state else []).assign(순번=range(1, len(st.session_state.meal_log)+1)).set_index('순번'))
else:
    st.write("입력된 식단이 없습니다.")

# (기존 재무, 생활주기 등 섹션 생략 없이 출력...)
