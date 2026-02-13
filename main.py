import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# 1. 고정 마스터 데이터 (생략 없이 유지)
FIXED_DATA = {
    "profile": {"항목": ["나이", "거주", "상태", "결혼예정일"], "내용": ["32세", "평택 원평동", "공무원 발령 대기 중", "2026-05-30"]},
    "health": {"항목": ["현재 체중", "목표 체중", "주요 관리", "식단 금기"], "내용": ["125.0kg", "90.0kg", "고지혈증/ADHD", "생굴/멍게"]},
    "assets": {
        "savings": {"청년도약계좌": 14700000, "주택청약": 2540000, "전세보증금(총액)": 145850000},
        "liabilities": {"전세대출": 100000000, "마이너스통장": 3000000, "학자금대출": 1247270},
        "stocks": {"삼성전자": "005930", "SK하이닉스": "000660", "삼성중공업": "010140", "동성화인텍": "033500"},
        "crypto": {"BTC": 0.00181400, "ETH": 0.03417393}
    },
    "lifecycle": {
        "면도날": {"last": "2026-02-06", "period": 21}, "칫솔": {"last": "2026-02-06", "period": 90}, "이불세탁": {"last": "2026-01-30", "period": 14}, "로봇청소기": {"last": "2026-02-12", "period": 2}
    },
    "kitchen": {
        "소스/캔": "토마토페이스트, 나시고랭, S&B카레, 뚝심, 땅콩버터",
        "단백질": "냉동삼치, 냉동닭다리, 관찰레, 북어채, 단백질쉐이크",
        "곡물/면": "파스타면, 소면, 쿠스쿠스, 라면, 우동, 쌀/카무트",
        "신선/기타": "김치4종, 아사이베리, 치아씨드, 향신료, 치즈"
    }
}

EXPENSE_CATS = ["식비(집밥)", "식비(배달)", "식비(외식/편의점)", "담배", "생활용품", "주거/통신/이자", "보험/청약", "주식/적금", "주유/교통", "건강/의료", "기타"]
PAY_METHODS = ["하나카드", "우리카드", "국민카드", "현대카드", "지역화폐", "현금"]

# 2. 세션 상태 초기화 (수정을 위한 로그 기록 기능 추가)
if 'cash' not in st.session_state: st.session_state.cash = 492918
if 'consumed' not in st.session_state: st.session_state.consumed = {"cal": 0, "p": 0, "f": 0, "c": 0, "fiber": 0, "water": 0}
if 'expenses' not in st.session_state: st.session_state.expenses = {cat: 0 for cat in EXPENSE_CATS}
if 'meal_history' not in st.session_state: st.session_state.meal_history = []
if 'log_history' not in st.session_state: st.session_state.log_history = [] # 취소용 로그

st.set_page_config(page_title="자비스 v3.9", layout="wide")
st.title("자비스 : 라이프 통합 매니지먼트")

# --- 사이드바 입력 및 수정 기능 ---
with st.sidebar:
    st.header("실시간 기록")
    with st.form("input_form"):
        exp_val = st.number_input("지출 금액(원)", min_value=0, step=100)
        pay_method = st.selectbox("지출 수단", PAY_METHODS)
        exp_cat = st.selectbox("지출 카테고리", EXPENSE_CATS)
        st.divider()
        meal_in = st.text_input("음식명/음료")
        
        if st.form_submit_button("반영"):
            # 영양 분석 데이터 생성
            m = {"cal": 0, "p": 0, "f": 0, "c": 0, "fiber": 0, "water": 0}
            if "물" in meal_in: m["water"] = 500
            elif "쿼파치" in meal_in: m = {"cal": 1120, "p": 50, "f": 55, "c": 110, "fiber": 5, "water": 0}
            elif meal_in: m = {"cal": 600, "p": 25, "f": 20, "c": 70, "fiber": 3, "water": 0}
            
            # 현재 상태 저장 (취소 대비)
            snapshot = {
                "cash_diff": exp_val,
                "exp_cat": exp_cat,
                "nutri_diff": m,
                "meal_name": meal_in
            }
            st.session_state.log_history.append(snapshot)
            
            # 실제 데이터 반영
            st.session_state.cash -= exp_val
            st.session_state.expenses[exp_cat] += exp_val
            for k in st.session_state.consumed: st.session_state.consumed[k] += m[k]
            if meal_in: st.session_state.meal_history.append({"시간": datetime.now().strftime('%H:%M'), "메뉴": meal_in, "칼로리": m['cal']})
            st.rerun()

    st.divider()
    # 수정 기능 버튼들
    if st.button("⏪ 직전 기록 취소"):
        if st.session_state.log_history:
            last = st.session_state.log_history.pop()
            st.session_state.cash += last["cash_diff"]
            st.session_state.expenses[last["exp_cat"]] -= last["cash_diff"]
            for k in st.session_state.consumed: st.session_state.consumed[k] -= last["nutri_diff"][k]
            if last["meal_name"] and st.session_state.meal_history: st.session_state.meal_history.pop()
            st.warning("직전 기록이 취소되었습니다.")
            st.rerun()
        else:
            st.error("취소할 기록이 없습니다.")

    if st.button("🗑️ 오늘 데이터 전체 초기화"):
        st.session_state.cash = 492918
        st.session_state.consumed = {"cal": 0, "p": 0, "f": 0, "c": 0, "fiber": 0, "water": 0}
        st.session_state.expenses = {cat: 0 for cat in EXPENSE_CATS}
        st.session_state.meal_history = []
        st.session_state.log_history = []
        st.info("데이터가 초기화되었습니다.")
        st.rerun()

# (이후 출력 섹션 1~6번은 v3.8과 동일하게 유지 - 생략 없이 모두 출력됩니다)
