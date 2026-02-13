import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# 1. 마스터 데이터 및 환경 설정
BMR = 2000 # 보스의 기초대사량
TARGET = {"단백질": 150, "지방": 65, "탄수화물": 300}

# 2. 세션 상태 (영구 저장을 위해 추후 구글 시트 연동 필수)
if 'cash' not in st.session_state: st.session_state.cash = 492918
if 'consumed' not in st.session_state: 
    st.session_state.consumed = {"cal": 0, "protein": 0, "fat": 0, "carbs": 0}
if 'history' not in st.session_state: st.session_state.history = []

# [지능형 영양 분석 함수] 
# 실제로는 더 방대한 DB와 연동하거나 LLM을 호출할 수 있지만, 우선 대표 식단 로직을 고도화했습니다.
def analyze_meal(meal_name):
    # 식단 사전 (대표적인 것들)
    food_ref = {
        "쿼파치": [1120, 50, 55, 110],
        "삼치": [350, 40, 15, 0],
        "빅맥": [583, 27, 33, 46],
        "제육볶음": [500, 35, 25, 30],
        "단백질쉐이크": [150, 25, 2, 5],
        "치킨": [2000, 120, 150, 80],
        "국밥": [600, 30, 20, 70]
    }
    
    for key, val in food_ref.items():
        if key in meal_name:
            return {"cal": val[0], "p": val[1], "f": val[2], "c": val[3]}
    
    # DB에 없을 경우: 일반적인 한 끼 식사 평균치로 추론
    return {"cal": 650, "p": 25, "f": 20, "c": 80}

st.set_page_config(page_title="자비스 v3.2", layout="wide")
st.title("자비스 : 실시간 통합 라이프 매니저")

# CSS: 정렬 최적화
st.markdown("""<style>td:nth-child(2), td:nth-child(3) {text-align: right !important;} [data-testid="stMetricValue"] {text-align: right !important;}</style>""", unsafe_allow_html=True)

# --- 사이드바: 통합 입력창 ---
with st.sidebar.form("통합 입력"):
    st.header("오늘의 로그")
    exp = st.number_input("지출(원)", min_value=0, step=100)
    meal = st.text_input("섭취 음식명", placeholder="예: 제육볶음")
    
    if st.form_submit_button("시스템 반영"):
        st.session_state.cash -= exp
        m_data = analyze_meal(meal)
        st.session_state.consumed["cal"] += m_data["cal"]
        st.session_state.consumed["protein"] += m_data["p"]
        st.session_state.consumed["fat"] += m_data["f"]
        st.session_state.consumed["carbs"] += m_data["c"]
        st.session_state.history.append(f"{datetime.now().strftime('%H:%M')} - {meal} ({m_data['cal']}kcal)")

# --- 1. 기본정보 ---
# (기존 코드와 동일)

# --- 2. 영양상태 (보스 요청: 분수 형태 표기) ---
st.header("2. 영양상태")
n1, n2 = st.columns([1, 2])
with n1:
    cur_cal = st.session_state.consumed["cal"]
    st.subheader("칼로리 잔량")
    st.title(f"{cur_cal} / {BMR} kcal")
    st.metric("남은 허용치", f"{BMR - cur_cal} kcal", delta_color="inverse")
with n2:
    st.subheader("영양소 밸런스")
    c = st.session_state.consumed
    nutri_table = [
        {"항목": "단백질", "섭취/목표": f"{c['protein']} / {TARGET['단백질']}g", "잔량": f"{TARGET['단백질'] - c['protein']}g"},
        {"항목": "지방", "섭취/목표": f"{c['fat']} / {TARGET['지방']}g", "잔량": f"{TARGET['지방'] - c['fat']}g"},
        {"항목": "탄수화물", "섭취/목표": f"{c['carbs']} / {TARGET['탄수화물']}g", "잔량": f"{TARGET['탄수화물'] - c['carbs']}g"}
    ]
    st.table(pd.DataFrame(nutri_table))

# --- 3. 재무관리 (실시간 순자산 우측 정렬) ---
# (기존 코드와 동일하되, st.session_state.cash 사용)

# (나머지 4. 생활주기, 5. 주방재고 섹션 유지)
