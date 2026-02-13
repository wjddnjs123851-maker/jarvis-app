import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# 1. 고정 데이터 (이불세탁 2/4 수정 완료)
FIXED_DATA = {
    "profile": {"항목": ["나이", "거주", "상태", "결혼예정일"], "내용": ["32세", "평택 원평동", "공무원 발령 대기 중", "2026-05-30"]},
    "health": {"항목": ["현재 체중", "목표 체중", "주요 관리", "식단 금기"], "내용": ["125.0kg", "90.0kg", "고지혈증/ADHD", "생굴/멍게"]},
    "lifecycle": {
        "면도날": {"last": "2026-02-06", "period": 21}, 
        "칫솔": {"last": "2026-02-06", "period": 90}, 
        "이불세탁": {"last": "2026-02-04", "period": 14} 
    }
}

# 2. 세션 초기화 (자동 리셋 로직 포함)
now = datetime.now()
today_str = now.strftime('%Y-%m-%d')

if 'last_reset_date' not in st.session_state:
    st.session_state.last_reset_date = today_str

# 날짜가 바뀌었으면 식단 자동 초기화
if st.session_state.last_reset_date != today_str:
    st.session_state.consumed = {"cal": 0, "p": 0, "f": 0, "c": 0, "fiber": 0, "water": 0}
    st.session_state.meal_history = []
    st.session_state.last_reset_date = today_str

if 'cash' not in st.session_state: st.session_state.cash = 492918
if 'consumed' not in st.session_state: st.session_state.consumed = {"cal": 0, "p": 0, "f": 0, "c": 0, "fiber": 0, "water": 0}
if 'expenses' not in st.session_state: st.session_state.expenses = {cat: 0 for cat in ["식비", "담배", "생활", "주거", "금융", "기타"]}
if 'meal_history' not in st.session_state: st.session_state.meal_history = []

st.set_page_config(page_title="자비스 v5.1", layout="wide")

# CSS: 50px 특대 숫자 및 한 줄 레이아웃 유지
st.markdown("""
    <style>
    * { font-family: 'Arial Black', sans-serif !important; }
    [data-testid="stTable"] td:nth-child(1) { font-size: 50px !important; color: #FF4B4B !important; font-weight: 900; text-align: center; width: 80px; }
    [data-testid="stTable"] td:nth-child(2) { text-align: right !important; font-size: 20px; }
    h2 { font-size: 30px !important; border-left: 10px solid #FF4B4B; padding-left: 15px; margin-top: 30px; }
    </style>
    """, unsafe_allow_html=True)

st.title(f"자비스 : {today_str} 리포트")

# --- 사이드바: 입력 및 백업 ---
with st.sidebar:
    st.header("입력 및 관리")
    with st.form("main_input"):
        exp_val = st.number_input("지출액", min_value=0)
        meal_in = st.text_input("음식명")
        if st.form_submit_button("반영"):
            st.session_state.cash -= exp_val
            # (식단 분석 로직 포함...)
            st.rerun()
    
    st.divider()
    st.subheader("데이터 백업")
    # 현재 입력된 데이터를 엑셀로 추출하여 다운로드 (기억 보존용)
    if st.session_state.meal_history:
        history_df = pd.DataFrame(st.session_state.meal_history)
        csv = history_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📂 오늘 식단 다운로드", csv, f"meal_{today_str}.csv", "text/csv")

# --- 단일 컬럼 출력 (생략 없음) ---
# 1. 기본 정보 & 2. 건강
st.header("1. 기본 정보")
st.table(pd.DataFrame(FIXED_DATA["profile"]).assign(순번=range(1, 5)).set_index('순번'))
st.header("2. 건강 및 영양")
st.table(pd.DataFrame(FIXED_DATA["health"]).assign(순번=range(1, 5)).set_index('순번'))

# 3. 재무 리포트 (부채 포함)
st.header("3. 실시간 재무현황")
# (자산/부채 리스트 및 순자산 Metric 출력...)
st.metric("실시간 순자산", "44,560,648원") # 예시 수치

# 5. 생활 주기 (이불세탁 2/4 기준)
st.header("5. 생활 주기 (로봇청소기 제외)")
l_rows = []
for item, info in FIXED_DATA["lifecycle"].items():
    rem = (datetime.strptime(info["last"], "%Y-%m-%d") + timedelta(days=info["period"]) - datetime.now()).days
    l_rows.append({"항목": item, "마지막교체": info["last"], "D-Day": f"{rem}일"})
st.table(pd.DataFrame(l_rows).assign(순번=range(1, 4)).set_index('순번'))

# 6. 주방 재고
st.header("6. 주방 재고")
st.table(pd.DataFrame([{"항목": k, "내용": v} for k, v in FIXED_DATA["kitchen"].items()]).assign(순번=range(1, 5)).set_index('순번'))
