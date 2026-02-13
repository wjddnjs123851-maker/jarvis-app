import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# 1. 고정 마스터 데이터
FIXED_DATA = {
    "profile": {"항목": ["나이", "거주", "상태", "결혼예정일"], "내용": ["32세", "평택 원평동", "공무원 발령 대기 중", "2026-05-30"]},
    "health": {"항목": ["현재 체중", "목표 체중", "주요 관리", "식단 금기"], "내용": ["125.0kg", "90.0kg", "고지혈증/ADHD", "생굴/멍게"]},
    "assets": {
        "savings": {"청년도약계좌": 14700000, "주택청약": 2540000, "전세보증금(총액)": 145850000},
        "liabilities": {"전세대출": 100000000, "마이너스통장": 3000000, "학자금대출": 1247270},
        "stocks": {"삼성전자": {"code": "005930", "count": 46}, "SK하이닉스": {"code": "000660", "count": 6}, "삼성중공업": {"code": "010140", "count": 88}, "동성화인텍": {"code": "033500", "count": 21}},
        "crypto": {"BTC": 0.00181400, "ETH": 0.03417393}
    },
    "lifecycle": {
        "면도날": {"last": "2026-02-06", "period": 21}, "칫솔": {"last": "2026-02-06", "period": 90}, "이불세탁": {"last": "2026-01-30", "period": 14}, "로봇청소기": {"last": "2026-02-12", "period": 2}
    },
    "kitchen": {
        "소스/캔": "토마토페이스트(10), 나시고랭(1), S&B카레, 뚝심(2), 땅콩버터(4/5)",
        "단백질": "냉동삼치(4), 냉동닭다리(4), 관찰레, 북어채, 단백질쉐이크(9)",
        "곡물/면": "파스타면(다수), 소면(1), 쿠스쿠스(1), 라면(12), 우동/소바, 쌀/카무트",
        "신선/기타": "김치4종, 아사이베리, 치아씨드, 각종향신료, 치즈류"
    }
}

# 가계부 기반 지출 카테고리 (xlsx 분석 결과)
EXPENSE_CATS = [
    "식비(집밥)", "식비(배달)", "식비(외식/편의점)", "담배", "생활용품", 
    "주거/통신/이자", "보험/청약", "주식/적금", "주유/교통", "건강/의료", "기타(경조사/문화)"
]

# 2. 세션 데이터
if 'cash' not in st.session_state: st.session_state.cash = 492918
if 'consumed' not in st.session_state: st.session_state.consumed = {"cal": 0, "p": 0, "f": 0, "c": 0}
if 'expenses' not in st.session_state: 
    st.session_state.expenses = {cat: 0 for cat in EXPENSE_CATS}
if 'last_meal' not in st.session_state: st.session_state.last_meal = "기록 없음"

def get_live_prices():
    prices = {"crypto": {"KRW-BTC": 95000000, "KRW-ETH": 3800000}, "stocks": {}}
    try:
        res = requests.get("https://api.upbit.com/v1/ticker?markets=KRW-BTC,KRW-ETH", timeout=2).json()
        for c in res: prices["crypto"][c['market']] = int(c['trade_price'])
    except: pass
    for name, info in FIXED_DATA["assets"]["stocks"].items():
        try:
            url = f"https://polling.finance.naver.com/api/realtime?query=SERVICE_ITEM:{info['code']}"
            res = requests.get(url, timeout=2).json()
            prices["stocks"][name] = int(res['result']['areas'][0]['datas'][0]['nv'])
        except: prices["stocks"][name] = 0
    return prices

st.set_page_config(page_title="자비스 v3.5", layout="wide")
st.title("자비스 : 라이프 통합 대시보드")

st.markdown("""<style>td:nth-child(2), td:nth-child(3) {text-align: right !important;} [data-testid="stMetricValue"] {text-align: right !important;}</style>""", unsafe_allow_html=True)
live = get_live_prices()

# --- 사이드바: 통합 입력 패널 ---
with st.sidebar.form("데일리 통합 입력"):
    st.header("오늘의 로그")
    exp_val = st.number_input("금액(원)", min_value=0, step=100)
    exp_cat = st.selectbox("지출 카테고리", EXPENSE_CATS)
    meal_in = st.text_input("음식명", placeholder="예: 쿼파치")
    
    if st.form_submit_button("시스템 반영"):
        st.session_state.cash -= exp_val
        st.session_state.expenses[exp_cat] += exp_val
        if "쿼파치" in meal_in: m_data = {"cal": 1120, "p": 50, "f": 55, "c": 110}
        elif "삼치" in meal_in: m_data = {"cal": 350, "p": 40, "f": 15, "c": 0}
        else: m_data = {"cal": 600, "p": 25, "f": 20, "c": 70}
        st.session_state.consumed["cal"] += m_data["cal"]
        st.session_state.consumed["p"] += m_data["p"]
        st.session_state.consumed["f"] += m_data["f"]
        st.session_state.consumed["c"] += m_data["c"]
        st.session_state.last_meal = meal_in

# --- 1. 기본정보 ---
st.header("1. 기본정보")
c1, c2 = st.columns(2)
with c1: st.table(pd.DataFrame(FIXED_DATA["profile"]).assign(번호=range(1, 5)).set_index('번호'))
with c2: st.table(pd.DataFrame(FIXED_DATA["health"]).assign(번호=range(1, 5)).set_index('번호'))
st.divider()

# --- 2. 영양상태 ---
st.header("2. 영양상태")
n1, n2 = st.columns([1, 2])
with n1:
    st.subheader(f"에너지: {st.session_state.consumed['cal']} / 2000 kcal")
    st.metric("남은 칼로리", f"{2000 - st.session_state.consumed['cal']} kcal")
with n2:
    st.subheader("영양소 밸런스")
    c = st.session_state.consumed
    nutri_table = pd.DataFrame([
        {"항목": "단백질", "섭취/목표": f"{c['p']} / 150g", "잔량": f"{150 - c['p']}g"},
        {"항목": "지방", "섭취/목표": f"{c['f']} / 65g", "잔량": f"{65 - c['f']}g"},
        {"항목": "탄수화물", "섭취/목표": f"{c['c']} / 300g", "잔량": f"{300 - c['c']}g"}
    ]).assign(번호=range(1, 4)).set_index('번호')
    st.table(nutri_table)
st.divider()

# --- 3. 재무관리 ---
st.header("3. 재무관리")
btc_v = int(FIXED_DATA["assets"]["crypto"]["BTC"] * live["crypto"]["KRW-BTC"])
eth_v = int(FIXED_DATA["assets"]["crypto"]["ETH"] * live["crypto"]["KRW-ETH"])
stock_total = sum(live["stocks"].get(n, 0) * i["count"] for n, i in FIXED_DATA["assets"]["stocks"].items())
a1, a2 = st.columns(2)
with a1:
    assets = [{"항목": "현금", "금액": st.session_state.cash}]
    for k, v in FIXED_DATA["assets"]["savings"].items(): assets.append({"항목": k, "금액": v})
    assets.append({"항목": "주식/코인", "금액": stock_total + btc_v + eth_v})
    df_a = pd.DataFrame(assets)
    df_a['금액'] = df_a['금액'].apply(lambda x: f"{x:,.0f}원")
    st.table(df_a.assign(번호=range(1, len(df_a)+1)).set_index('번호'))
with a2:
    debts = [{"항목": k, "금액": v} for k, v in FIXED_DATA["assets"]["liabilities"].items()]
    df_d = pd.DataFrame(debts)
    total_d = df_d['금액'].sum()
    df_d['금액'] = df_d['금액'].apply(lambda x: f"{x:,.0f}원")
    st.table(df_d.assign(번호=range(1, len(df_d)+1)).set_index('번호'))
    st.metric("실시간 순자산", f"{st.session_state.cash + sum(FIXED_DATA['assets']['savings'].values()) + stock_total + btc_v + eth_v - total_d:,.0f}원")
st.divider()

# --- 4. 지출관리 (가계부 기반 신설) ---
st.header("4. 지출관리")
e_data = [{"카테고리": k, "누적 지출액": f"{v:,.0f}원"} for k, v in st.session_state.expenses.items()]
df_e = pd.DataFrame(e_data)
st.table(df_e.assign(번호=range(1, len(df_e)+1)).set_index('번호'))
st.divider()

# --- 5. 생활주기 & 6. 주방재고 ---
st.header("5. 생활주기")
life_rows = []
for item, info in FIXED_DATA["lifecycle"].items():
    next_d = datetime.strptime(info["last"], "%Y-%m-%d") + timedelta(days=info["period"])
    rem_d = (next_d - datetime.now()).days
    life_rows.append({"항목": item, "상태": "🚨 점검" if rem_d <= 0 else "✅ 정상", "남은일수": f"{rem_d}일"})
st.table(pd.DataFrame(life_rows).assign(번호=range(1, 5)).set_index('번호'))

st.header("6. 주방재고")
k_rows = [{"카테고리": k, "내용": v} for k, v in FIXED_DATA["kitchen"].items()]
st.table(pd.DataFrame(k_rows).assign(번호=range(1, 5)).set_index('번호'))
