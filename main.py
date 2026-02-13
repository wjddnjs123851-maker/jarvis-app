import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# 1. 마스터 데이터 및 목표 설정
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

EXPENSE_CATS = ["식비(집밥)", "식비(배달)", "식비(외식/편의점)", "담배", "생활용품", "주거/통신/이자", "보험/청약", "주식/적금", "주유/교통", "건강/의료", "기타(경조사/문화)"]
PAY_METHODS = ["하나카드", "우리카드", "국민카드", "현대카드", "지역화폐", "현금"]
TARGET = {"cal": 2000, "p": 150, "f": 65, "c": 300, "fiber": 25, "water": 2000}

# 2. 세션 데이터 초기화
if 'cash' not in st.session_state: st.session_state.cash = 492918
if 'consumed' not in st.session_state: st.session_state.consumed = {"cal": 0, "p": 0, "f": 0, "c": 0, "fiber": 0, "water": 0}
if 'expenses' not in st.session_state: st.session_state.expenses = {cat: 0 for cat in EXPENSE_CATS}
if 'meal_history' not in st.session_state: st.session_state.meal_history = []

def get_live_prices():
    prices = {"crypto": {"KRW-BTC": 95000000, "KRW-ETH": 3800000}, "stocks": {}}
    try:
        res = requests.get("https://api.upbit.com/v1/ticker?markets=KRW-BTC,KRW-ETH", timeout=1).json()
        for c in res: prices["crypto"][c['market']] = int(c['trade_price'])
    except: pass
    for name, info in FIXED_DATA["assets"]["stocks"].items():
        try:
            url = f"https://polling.finance.naver.com/api/realtime?query=SERVICE_ITEM:{info['code']}"
            res = requests.get(url, timeout=1).json()
            prices["stocks"][name] = int(res['result']['areas'][0]['datas'][0]['nv'])
        except: prices["stocks"][name] = 0
    return prices

st.set_page_config(page_title="자비스 v3.6", layout="wide")
st.title("자비스 : 라이프 통합 매니지먼트")
st.markdown("""<style>td:nth-child(2), td:nth-child(3) {text-align: right !important;} [data-testid="stMetricValue"] {text-align: right !important;}</style>""", unsafe_allow_html=True)
live = get_live_prices()

# --- 사이드바: 정밀 입력 패널 ---
with st.sidebar.form("데일리 로그 입력"):
    st.header("실시간 기록")
    exp_val = st.number_input("금액(원)", min_value=0, step=100)
    pay_method = st.selectbox("지출 수단", PAY_METHODS)
    exp_cat = st.selectbox("지출 카테고리", EXPENSE_CATS)
    
    st.divider()
    meal_in = st.text_input("음식명/음료", placeholder="예: 쿼파치세트, 물 500ml")
    
    if st.form_submit_button("시스템 반영"):
        if exp_val > 0:
            st.session_state.cash -= exp_val
            st.session_state.expenses[exp_cat] += exp_val
        
        # 지능형 분석 (수분/식이섬유 추가)
        if "물" in meal_in: m_data = {"cal": 0, "p": 0, "f": 0, "c": 0, "fiber": 0, "water": 500}
        elif "쿼파치" in meal_in: m_data = {"cal": 1120, "p": 50, "f": 55, "c": 110, "fiber": 5, "water": 0}
        elif "삼치" in meal_in: m_data = {"cal": 350, "p": 40, "f": 15, "c": 0, "fiber": 0, "water": 0}
        else: m_data = {"cal": 600, "p": 25, "f": 20, "c": 70, "fiber": 3, "water": 0}
        
        for k in st.session_state.consumed: st.session_state.consumed[k] += m_data.get(k, 0)
        st.session_state.meal_history.append({"시간": datetime.now().strftime('%H:%M'), "메뉴": meal_in, "칼로리": m_data['cal']})

# --- 1. 기본정보 ---
st.header("1. 기본정보")
c1, c2 = st.columns(2)
with c1: st.table(pd.DataFrame(FIXED_DATA["profile"]).assign(번호=range(1, 5)).set_index('번호'))
with c2: st.table(pd.DataFrame(FIXED_DATA["health"]).assign(번호=range(1, 5)).set_index('번호'))

# --- 2. 영양상태 (식이섬유/물 추가) ---
st.header("2. 영양상태")
n1, n2, n3 = st.columns([1, 2, 1.5])
with n1:
    st.subheader("에너지 잔량")
    st.title(f"{st.session_state.consumed['cal']} / {TARGET['cal']} kcal")
    st.metric("남은 허용량", f"{TARGET['cal'] - st.session_state.consumed['cal']} kcal")
with n2:
    st.subheader("정밀 영양소 밸런스")
    c = st.session_state.consumed
    nutri_df = pd.DataFrame([
        {"항목": "단백질", "섭취/목표": f"{c['p']} / {TARGET['p']}g", "잔량": f"{TARGET['p'] - c['p']}g"},
        {"항목": "지방", "섭취/목표": f"{c['f']} / {TARGET['f']}g", "잔량": f"{TARGET['f'] - c['f']}g"},
        {"항목": "탄수화물", "섭취/목표": f"{c['c']} / {TARGET['c']}g", "잔량": f"{TARGET['c'] - c['c']}g"},
        {"항목": "식이섬유", "섭취/목표": f"{c['fiber']} / {TARGET['fiber']}g", "잔량": f"{TARGET['fiber'] - c['fiber']}g"},
        {"항목": "수분", "섭취/목표": f"{c['water']} / {TARGET['water']}ml", "잔량": f"{TARGET['water'] - c['water']}ml"}
    ]).assign(번호=range(1, 6)).set_index('번호')
    st.table(nutri_df)
with n3:
    st.subheader("오늘의 섭취 목록")
    if st.session_state.meal_history:
        st.table(pd.DataFrame(st.session_state.meal_history).set_index('시간'))
    else: st.info("기록된 식단이 없습니다.")
st.divider()

# --- 3. 재무관리 & 4. 지출관리 ---
st.header("3. 재무 및 지출 관리")
btc_v = int(FIXED_DATA["assets"]["crypto"]["BTC"] * live["crypto"]["KRW-BTC"])
eth_v = int(FIXED_DATA["assets"]["crypto"]["ETH"] * live["crypto"]["KRW-ETH"])
stock_total = sum(live["stocks"].get(n, 0) * i["count"] for n, i in FIXED_DATA["assets"]["stocks"].items())

f1, f2 = st.columns(2)
with f1:
    st.subheader("실시간 순자산 현황")
    total_a = st.session_state.cash + sum(FIXED_DATA['assets']['savings'].values()) + stock_total + btc_v + eth_v
    total_d = sum(FIXED_DATA['assets']['liabilities'].values())
    st.metric("순자산 합계", f"{total_a - total_d:,.0f}원")
    st.table(pd.DataFrame([{"항목": "현금/예적금", "금액": f"{st.session_state.cash + 17240000:,.0f}원"}, {"항목": "주식/코인", "금액": f"{stock_total + btc_v + eth_v:,.0f}원"}, {"항목": "부채 총액", "금액": f"{total_d:,.0f}원"}]).assign(번호=range(1, 4)).set_index('번호'))
with f2:
    st.subheader("카테고리별 누적 지출")
    e_df = pd.DataFrame([{"항목": k, "지출": f"{v:,.0f}원"} for k, v in st.session_state.expenses.items() if v > 0])
    if not e_df.empty: st.table(e_df.assign(번호=range(1, len(e_df)+1)).set_index('번호'))
    else: st.info("이번 세션 지출 내역이 없습니다.")
st.divider()

# --- 5. 생활주기 & 6. 주방재고 ---
st.header("4. 생활 및 주방 관리")
l1, l2 = st.columns(2)
with l1:
    st.subheader("생활주기")
    life_rows = []
    for item, info in FIXED_DATA["lifecycle"].items():
        next_d = datetime.strptime(info["last"], "%Y-%m-%d") + timedelta(days=info["period"])
        rem_d = (next_d - datetime.now()).days
        life_rows.append({"항목": item, "상태": "🚨 점검" if rem_d <= 0 else "✅ 정상", "D-Day": f"{rem_d}일"})
    st.table(pd.DataFrame(life_rows).assign(번호=range(1, 5)).set_index('번호'))
with l2:
    st.subheader("주방재고 요약")
    st.table(pd.DataFrame([{"카테고리": k, "내용": v} for k, v in FIXED_DATA["kitchen"].items()]).assign(번호=range(1, 5)).set_index('번호'))
