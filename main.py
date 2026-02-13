import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# 1. 고정 마스터 데이터 (데이터 보존)
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
TARGET = {"cal": 2000, "p": 150, "f": 65, "c": 300, "fiber": 25, "water": 2000}

# 세션 관리
if 'cash' not in st.session_state: st.session_state.cash = 492918
if 'consumed' not in st.session_state: st.session_state.consumed = {"cal": 0, "p": 0, "f": 0, "c": 0, "fiber": 0, "water": 0}
if 'expenses' not in st.session_state: st.session_state.expenses = {cat: 0 for cat in EXPENSE_CATS}
if 'meal_history' not in st.session_state: st.session_state.meal_history = []
if 'log_history' not in st.session_state: st.session_state.log_history = []

def get_live_prices():
    prices = {"crypto": {"KRW-BTC": 95000000, "KRW-ETH": 3800000}, "stocks": {}}
    try:
        res = requests.get("https://api.upbit.com/v1/ticker?markets=KRW-BTC,KRW-ETH", timeout=2).json()
        for c in res: prices["crypto"][c['market']] = int(c['trade_price'])
    except: pass
    for name, code in FIXED_DATA["assets"]["stocks"].items():
        try:
            url = f"https://polling.finance.naver.com/api/realtime?query=SERVICE_ITEM:{code}"
            res = requests.get(url, timeout=2).json()
            prices["stocks"][name] = int(res['result']['areas'][0]['datas'][0]['nv'])
        except: prices["stocks"][name] = 0
    return prices

st.set_page_config(page_title="자비스 v4.2", layout="wide")

# CSS: 폰트 사이즈 최적화(18px) 및 자동 줄바꿈
st.markdown("""
    <style>
    .stTable td, .stTable th { 
        font-size: 18px !important; 
        white-space: normal !important; 
        word-break: break-all !important;
    }
    td:nth-child(2), td:nth-child(3) { text-align: right !important; }
    [data-testid="stMetricValue"] { font-size: 32px !important; font-weight: bold; text-align: right !important; }
    h1 { font-size: 38px !important; }
    h2 { font-size: 28px !important; border-bottom: 2px solid #ddd; padding-bottom: 8px; }
    </style>
    """, unsafe_allow_html=True)

st.title("자비스 : 실시간 통합 매니지먼트")
live = get_live_prices()

# --- 사이드바 ---
with st.sidebar:
    st.header("입력 패널")
    with st.form("input_form"):
        exp_val = st.number_input("지출 금액", min_value=0, step=100)
        pay_method = st.selectbox("수단", PAY_METHODS)
        exp_cat = st.selectbox("카테고리", EXPENSE_CATS)
        st.divider()
        meal_in = st.text_input("음식명")
        if st.form_submit_button("반영"):
            m = {"cal": 0, "p": 0, "f": 0, "c": 0, "fiber": 0, "water": 0}
            if "물" in meal_in: m["water"] = 500
            elif "쿼파치" in meal_in: m = {"cal": 1120, "p": 50, "f": 55, "c": 110, "fiber": 5, "water": 0}
            elif meal_in: m = {"cal": 600, "p": 25, "f": 20, "c": 70, "fiber": 3, "water": 0}
            st.session_state.log_history.append({"cash_diff": exp_val, "exp_cat": exp_cat, "nutri_diff": m, "meal_name": meal_in})
            st.session_state.cash -= exp_val
            st.session_state.expenses[exp_cat] += exp_val
            for k in st.session_state.consumed: st.session_state.consumed[k] += m[k]
            if meal_in: st.session_state.meal_history.append({"시간": datetime.now().strftime('%H:%M'), "메뉴": meal_in, "칼로리": m['cal']})
            st.rerun()
    if st.button("⏪ 직전 기록 취소"):
        if st.session_state.log_history:
            last = st.session_state.log_history.pop()
            st.session_state.cash += last["cash_diff"]
            st.session_state.expenses[last["exp_cat"]] -= last["cash_diff"]
            for k in st.session_state.consumed: st.session_state.consumed[k] -= last["nutri_diff"][k]
            if last["meal_name"] and st.session_state.meal_history: st.session_state.meal_history.pop()
            st.rerun()

# --- 1. 기본 정보 & 2. 영양 식단 ---
col1, col2 = st.columns([1, 1.2]) # 비율 조정으로 잘림 방지
with col1:
    st.header("1. 기본 정보")
    st.table(pd.DataFrame(FIXED_DATA["profile"]).assign(번호=range(1, 5)).set_index('번호'))
    st.table(pd.DataFrame(FIXED_DATA["health"]).assign(번호=range(1, 5)).set_index('번호'))
with col2:
    st.header("2. 영양 및 식단")
    n_col1, n_col2 = st.columns(2)
    n_col1.metric("에너지 섭취", f"{st.session_state.consumed['cal']}/{TARGET['cal']}kcal")
    n_col2.metric("남은 허용량", f"{TARGET['cal'] - st.session_state.consumed['cal']}kcal")
    c = st.session_state.consumed
    nut_df = pd.DataFrame([
        {"항목": "단백질", "섭취/목표": f"{c['p']}/{TARGET['p']}g", "잔여": f"{max(0, TARGET['p']-c['p'])}g"},
        {"항목": "지방", "섭취/목표": f"{c['f']}/{TARGET['f']}g", "잔여": f"{max(0, TARGET['f']-c['f'])}g"},
        {"항목": "식이섬유", "섭취/목표": f"{c['fiber']}/{TARGET['fiber']}g", "잔여": f"{max(0, TARGET['fiber']-c['fiber'])}g"},
        {"항목": "수분", "섭취/목표": f"{c['water']}/{TARGET['water']}ml", "잔여": f"{max(0, TARGET['water']-c['water'])}ml"}
    ]).assign(번호=range(1, 5)).set_index('번호')
    st.table(nut_df)

st.divider()

# --- 3. 재무 & 4. 지출 ---
st.header("3 & 4. 재무 및 지출 통합")
s_cnt = {"삼성전자": 46, "SK하이닉스": 6, "삼성중공업": 88, "동성화인텍": 21}
s_val = sum(live["stocks"].get(n, 0) * s_cnt[n] for n in FIXED_DATA["assets"]["stocks"])
b_val = int(FIXED_DATA["assets"]["crypto"]["BTC"] * live["crypto"]["KRW-BTC"])
e_val = int(FIXED_DATA["assets"]["crypto"]["ETH"] * live["crypto"]["KRW-ETH"])

f_col1, f_col2 = st.columns([1.3, 1])
with f_col1:
    assets = [{"항목": "현금", "금액": st.session_state.cash}]
    for k, v in FIXED_DATA["assets"]["savings"].items(): assets.append({"항목": k, "금액": v})
    for n in FIXED_DATA["assets"]["stocks"]: assets.append({"항목": f"주식({n})", "금액": live["stocks"].get(n, 0) * s_cnt[n]})
    assets.append({"항목": "코인(BTC/ETH)", "금액": b_val + e_val})
    df_a = pd.DataFrame(assets)
    t_a = df_a['금액'].sum()
    t_d = sum(FIXED_DATA["assets"]["liabilities"].values())
    st.metric("실시간 총 순자산", f"{t_a - t_d:,.0f}원")
    df_a['금액'] = df_a['금액'].apply(lambda x: f"{x:,.0f}원")
    st.table(df_a.assign(번호=range(1, len(df_a)+1)).set_index('번호'))

with f_col2:
    e_rows = [{"항목": k, "지출": f"{v:,.0f}원"} for k, v in st.session_state.expenses.items() if v > 0]
    if e_rows: st.table(pd.DataFrame(e_rows).assign(번호=range(1, len(e_rows)+1)).set_index('번호'))
    else: st.info("이번 세션 지출 내역이 없습니다.")

st.divider()

# --- 5. 생활 & 6. 주방 ---
st.header("5 & 6. 생활 및 주방 재고")
l_col1, l_col2 = st.columns(2)
with l_col1:
    l_rows = []
    for item, info in FIXED_DATA["lifecycle"].items():
        r = (datetime.strptime(info["last"], "%Y-%m-%d") + timedelta(days=info["period"]) - datetime.now()).days
        l_rows.append({"항목": item, "상태": "🚨 점검" if r <= 0 else "✅ 정상", "D-Day": f"{r}일"})
    st.table(pd.DataFrame(l_rows).assign(번호=range(1, 5)).set_index('번호'))
with l_col2:
    st.table(pd.DataFrame([{"카테고리": k, "내용": v} for k, v in FIXED_DATA["kitchen"].items()]).assign(번호=range(1, 5)).set_index('번호'))
