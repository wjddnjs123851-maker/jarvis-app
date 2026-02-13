import streamlit as st
import pandas as pd
from datetime import datetime

# 기초대사량 및 영양소 권장량 설정
BMR = 2000
RECOMMENDED = {"단백질": 150, "지방": 65, "탄수화물": 300, "식이섬유": 25}

# 세션 상태 초기화 (데이터 휘발 방지 기초)
if 'cash' not in st.session_state: st.session_state.cash = 492918
if 'consumed_cal' not in st.session_state: st.session_state.consumed_cal = 0

st.set_page_config(page_title="자비스 v2.7", layout="wide")
st.title("자비스 : 실시간 자산 및 영양 관리 시스템")

# --- 사이드바 입력창 ---
with st.sidebar.form("daily_log"):
    st.subheader("💳 지출 및 식단 입력")
    amt = st.number_input("지출 금액(원)", min_value=0, step=100)
    meal_cal = st.number_input("식사 칼로리(kcal)", min_value=0, step=50)
    meal_name = st.text_input("메뉴 이름")
    
    if st.form_submit_button("장부 기록"):
        st.session_state.cash -= amt
        st.session_state.consumed_cal += meal_cal
        st.success(f"기록 완료: {meal_name}")

# --- 섹션 1: 자산 현황 ---
st.header("💰 실시간 자산 상태")
col_a1, col_a2 = st.columns(2)
with col_a1:
    st.metric("가용 현금", f"{st.session_state.cash:,.0f}원", delta=f"-{amt}원" if amt > 0 else None)

# --- 섹션 2: 영양 매트릭스 (보스 요청 스타일) ---
st.header("🥗 에너지 및 영양 잔량")
rem_cal = BMR - st.session_state.consumed_cal

# 칼로리 게이지 및 수치
c1, c2 = st.columns([1, 2])
with c1:
    st.subheader("에너지 잔량")
    st.title(f"{st.session_state.consumed_cal} / {BMR} kcal")
    if rem_cal > 0:
        st.write(f"🤵 보스, 오늘 **{rem_cal} kcal** 더 드실 수 있습니다.")
    else:
        st.error(f"🚨 기초대사량을 {abs(rem_cal)} kcal 초과했습니다!")

with c2:
    st.subheader("주요 영양소 밸런스")
    # 예시 데이터 (더블쿼터파운더 반영)
    nutri_data = [
        {"항목": "단백질", "섭취/권장": "50 / 150 g", "잔량": "100 g", "상태": "양호"},
        {"항목": "지방", "섭취/권장": "55 / 65 g", "잔량": "10 g", "상태": "위험"},
        {"항목": "식이섬유", "섭취/권장": "4 / 25 g", "잔량": "21 g", "상태": "부족"}
    ]
    st.table(pd.DataFrame(nutri_data))

# --- 섹션 3: 주방 재고 연동 ---
st.header("📦 추천 저녁 식재료 (인벤토리 기반)")
st.info("현재 지방 섭취가 높습니다. 냉장고에 있는 **냉동삼치(단백질)**와 **백김치(식이섬유)**를 추천합니다.")
