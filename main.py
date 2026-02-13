import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# 1. 고정 마스터 데이터 (이불세탁 2/4 수정 및 로봇청소기 제외)
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
    },
    "kitchen": {
        "소스/캔": "토마토페이스트, 나시고랭, S&B카레, 뚝심, 땅콩버터",
        "단백질": "냉동삼치, 냉동닭다리, 관찰레, 북어채, 단백질쉐이크",
        "곡물/면": "파스타면, 소면, 쿠스쿠스, 라면, 우동, 쌀/카무트",
        "신선/기타": "김치4종, 아사이베리, 치아씨드, 향신료, 치즈"
    }
}

EXPENSE_CATS = ["식비(집밥)", "식비(배달)", "식비(외식/편의점)", "담배", "생활용품", "주거/통신/이자", "보험/청약", "주식/적금", "주유/교통", "건강/의료", "기타"]

# 2. 자동 초기화 및 세션 관리 로직
now = datetime.now()
today_str = now.strftime('%Y-%m-%d')
this_month_str = now.strftime('%Y-%m')

if 'last_run_date' not in st.session_state: st.session_state.last_run_date = today_str
if 'last_run_month' not in st.session_state: st.session_state.last_run_month = this_month_str

# [날짜 변경 시 식단 초기화]
if st.session_state.last_run_date != today_str:
    st.session_state.consumed = {"cal": 0, "p": 0, "f": 0, "c": 0, "fiber": 0, "water": 0}
    st.session_state.meal_history = []
    st.session_state.last_run_date = today_str

# [달 변경 시 가계부 초기화]
if st.session_state.last_run_month != this_month_str:
    st.session_state.expenses = {cat: 0 for cat in EXPENSE_CATS}
    st.session_state.last_run_month = this_month_str

# 초기 세션 값 설정
if 'cash' not in st.session_state: st.session_state.cash = 492918
if 'consumed' not in st.session_state: st.session_state.consumed = {"cal": 0, "p": 0, "f": 0, "c": 0, "fiber": 0, "water": 0}
if 'expenses' not in st.session_state: st.session_state.expenses = {cat: 0 for cat in EXPENSE_CATS}
if 'meal_history' not in st.session_state: st.session_state.meal_history = []

st.set_page_config(page_title="자비스 v5.2", layout="wide")

# CSS: 50px 특대 숫자 및 우측 정렬
st.markdown("""
    <style>
    * { font-family: 'Arial Black', sans-serif !important; }
    [data-testid="stTable"] td:nth-child(1) { font-size: 50px !important; color: #FF4B4B !important; font-weight: 900; text-align: center; width: 80px; }
    [data-testid="stTable"] td:nth-child(2) { text-align: right !important; font-size: 20px !important; }
    h2 { font-size: 30px !important; border-left: 10px solid #FF4B4B; padding-left: 15px; margin-top: 40px !important; }
    [data-testid="stMetricValue"] { text-align: right !important; font-size: 40px !important; }
    </style>
    """, unsafe_allow_html=True)

st.title(f"자비스 통합 리포트 : {today_str}")

# --- 사이드바: 입력 및 백업 ---
with st.sidebar:
    st.header("실시간 입력")
    with st.form("input_panel"):
        exp_val = st.number_input("지출액", min_value=0)
        exp_cat = st.selectbox("카테고리", EXPENSE_CATS)
        meal_in = st.text_input("음식/음료")
        if st.form_submit_button("반영"):
            st.session_state.cash -= exp_val
            st.session_state.expenses[exp_cat] += exp_val
            # (식단 분석 로직 수행...)
            if meal_in: st.session_state.meal_history.append({"시간": datetime.now().strftime('%H:%M'), "메뉴": meal_in})
            st.rerun()
    
    st.divider()
    st.subheader("데이터 백업 (CSV)")
    # 기록이 있을 경우 다운로드 버튼 활성화
    if st.session_state.meal_history:
        m_df = pd.DataFrame(st.session_state.meal_history)
        st.download_button("📂 오늘 식단 백업", m_df.to_csv(index=False).encode('utf-8-sig'), f"meal_{today_str}.csv")
    
    e_df = pd.DataFrame([{"항목": k, "금액": v} for k, v in st.session_state.expenses.items() if v > 0])
    if not e_df.empty:
        st.download_button("📂 이번 달 가계부 백업", e_df.to_csv(index=False).encode('utf-8-sig'), f"expense_{this_month_str}.csv")

# --- 단일 컬럼 출력 (전체 항목) ---
st.header("1. 기본 정보")
st.table(pd.DataFrame(FIXED_DATA["profile"]).assign(순번=range(1, 5)).set_index('순번'))

st.header("2. 건강 및 영양")
st.table(pd.DataFrame(FIXED_DATA["health"]).assign(순번=range(1, 5)).set_index('순번'))
st.metric("오늘의 에너지", f"{st.session_state.consumed['cal']} / 2000 kcal")

st.header("3. 실시간 자산 리포트")
assets = [{"항목": "가용 현금", "금액": st.session_state.cash}]
for k, v in FIXED_DATA["assets"]["savings"].items(): assets.append({"항목": k, "금액": v})
# (주식/코인 시세 연동 로직 포함...)
st.table(pd.DataFrame(assets).assign(금액=lambda x: x['금액'].apply(lambda y: f"{y:,.0f}원"), 순번=range(1, len(assets)+1)).set_index('순번'))

st.header("4. 실시간 부채 현황")
debts = [{"항목": k, "금액": v} for k, v in FIXED_DATA["assets"]["liabilities"].items()]
st.table(pd.DataFrame(debts).assign(금액=lambda x: x['금액'].apply(lambda y: f"{y:,.0f}원"), 순번=range(1, 4)).set_index('순번'))

st.header("5. 생활 주기 관리")
l_rows = []
for item, info in FIXED_DATA["lifecycle"].items():
    rem = (datetime.strptime(info["last"], "%Y-%m-%d") + timedelta(days=info["period"]) - datetime.now()).days
    l_rows.append({"항목": item, "최근수행": info["last"], "D-Day": f"{rem}일"})
st.table(pd.DataFrame(l_rows).assign(순번=range(1, 4)).set_index('순번'))

st.header("6. 주방 재고")
st.table(pd.DataFrame([{"카테고리": k, "내용": v} for k, v in FIXED_DATA["kitchen"].items()]).assign(순번=range(1, 5)).set_index('순번'))
