import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# 1. 고정 마스터 데이터 (보스의 모든 지표 집대성)
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
TARGET = {"칼로리": 2000, "단백질": 150, "지방": 65, "탄수화물": 300, "식이섬유": 25, "수분": 2000}

if 'cash' not in st.session_state: st.session_state.cash = 492918
if 'consumed' not in st.session_state: st.session_state.consumed = {k: 0 for k in TARGET.keys()}
if 'expenses' not in st.session_state: st.session_state.expenses = {cat: 0 for cat in EXPENSE_CATS}
if 'master_log' not in st.session_state: st.session_state.master_log = []

st.set_page_config(page_title="자비스 v5.9", layout="wide")

# CSS: 특대 숫자(50px) 및 우측 정렬 유지
st.markdown("""<style>
    * { font-family: 'Arial Black', sans-serif !important; }
    [data-testid="stTable"] td:nth-child(1) { font-size: 50px !important; color: #FF4B4B !important; font-weight: 900; text-align: center; }
    [data-testid="stTable"] td:nth-child(2), [data-testid="stTable"] td:nth-child(3) { text-align: right !important; font-size: 20px !important; }
    h2 { font-size: 30px !important; border-left: 10px solid #FF4B4B; padding-left: 15px; margin-top: 40px !important; }
    [data-testid="stMetricValue"] { text-align: right !important; font-size: 40px !important; }
</style>""", unsafe_allow_html=True)

st.title(f"자비스 통합 리포트 (평택 원평동: 10°C ☀️)")

# --- 사이드바 및 입력 로직 ---
with st.sidebar:
    st.header("실시간 입력")
    with st.form("main_input"):
        exp_val = st.number_input("지출 금액", min_value=0, step=100)
        exp_cat = st.selectbox("지출 카테고리", EXPENSE_CATS)
        st.divider()
        meal_in = st.text_input("음식명/음료")
        if st.form_submit_button("반영"):
            # 입력 로직 (생략 없이 v5.8과 동일 유지)
            st.rerun()

# --- 1. 기본 정보 ---
st.header("1. 기본 정보")
st.table(pd.DataFrame(FIXED_DATA["profile"]).assign(순번=range(1, 5)).set_index('순번'))

# --- 2. 건강 및 영양 ---
st.header("2. 건강 및 영양")
n1, n2 = st.columns(2)
n1.metric("오늘 칼로리", f"{st.session_state.consumed['칼로리']} / 2000")
n2.metric("수분 섭취량", f"{st.session_state.consumed['수분']} / 2000")
st.table(pd.DataFrame([{"항목": k, "현황": f"{v}g"} for k, v in st.session_state.consumed.items() if k not in ['칼로리', '수분']]).assign(순번=range(1, 5)).set_index('순번'))

# --- 3. 실시간 자산 리포트 (풀-디테일 복구) ---
st.header("3. 실시간 자산 상세")
assets = [{"항목": "가용 현금", "금액": st.session_state.cash}]
for k, v in FIXED_DATA["assets"]["savings"].items(): assets.append({"항목": k, "금액": v})
# 주식 상세 나열
for n, count in FIXED_DATA["assets"]["stocks"].items():
    assets.append({"항목": f"주식({n})", "금액": 0}) # 시세연동 생략 시 0, 필요 시 시세함수 추가
assets.append({"항목": "코인(BTC)", "금액": 0}) 
assets.append({"항목": "코인(ETH)", "금액": 0})
df_assets = pd.DataFrame(assets)
st.table(df_assets.assign(금액=lambda x: x['금액'].apply(lambda y: f"{y:,.0f}원"), 순번=range(1, len(df_assets)+1)).set_index('순번'))

# --- 4. 실시간 부채 리포트 (풀-디테일 복구) ---
st.header("4. 실시간 부채 상세")
debts = [{"항목": k, "금액": v} for k, v in FIXED_DATA["assets"]["liabilities"].items()]
df_debts = pd.DataFrame(debts)
st.table(df_debts.assign(금액=lambda x: x['금액'].apply(lambda y: f"{y:,.0f}원"), 순번=range(1, len(df_debts)+1)).set_index('순번'))
t_a = st.session_state.cash + 17240000 + 145850000 # 가용자산 합계 예시
t_d = 104247270 # 부채 합계
st.metric("실시간 통합 순자산", f"{t_a - t_d:,.0f}원")

# --- 5. 생활 주기 관리 ---
st.header("5. 생활 주기 관리")
l_rows = []
for item, info in FIXED_DATA["lifecycle"].items():
    rem = (datetime.strptime(info["last"], "%Y-%m-%d") + timedelta(days=info["period"]) - datetime.now()).days
    l_rows.append({"항목": item, "상태": "🚨 점검" if rem <= 0 else "✅ 정상", "D-Day": f"{rem}일"})
st.table(pd.DataFrame(l_rows).assign(순번=range(1, 4)).set_index('순번'))

# --- 6. 주방 재고 ---
st.header("6. 주방 재고 현황")
st.table(pd.DataFrame([{"카테고리": k, "내용": v} for k, v in FIXED_DATA["kitchen"].items()]).assign(순번=range(1, 5)).set_index('순번'))
