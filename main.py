import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# 1. 고정 마스터 데이터 (보스의 모든 지표 집대성)
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

if 'cash' not in st.session_state: st.session_state.cash = 492918
if 'consumed' not in st.session_state: st.session_state.consumed = {"cal": 0, "p": 0, "f": 0, "c": 0, "fiber": 0, "water": 0}
if 'expenses' not in st.session_state: st.session_state.expenses = {cat: 0 for cat in EXPENSE_CATS}
if 'meal_history' not in st.session_state: st.session_state.meal_history = []

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

st.set_page_config(page_title="자비스 v3.8", layout="wide")
st.title("자비스 : 라이프 통합 매니지먼트")

st.markdown("""<style>td:nth-child(2), td:nth-child(3) {text-align: right !important;} [data-testid="stMetricValue"] {text-align: right !important;}</style>""", unsafe_allow_html=True)
live = get_live_prices()

# --- 사이드바 ---
with st.sidebar.form("데일리 로그"):
    st.header("실시간 기록")
    exp_val = st.number_input("지출 금액(원)", min_value=0, step=100)
    pay_method = st.selectbox("지출 수단", PAY_METHODS)
    exp_cat = st.selectbox("지출 카테고리", EXPENSE_CATS)
    st.divider()
    meal_in = st.text_input("음식명/음료")
    if st.form_submit_button("반영"):
        if exp_val > 0:
            st.session_state.cash -= exp_val
            st.session_state.expenses[exp_cat] += exp_val
        m = {"cal": 0, "p": 0, "f": 0, "c": 0, "fiber": 0, "water": 0}
        if "물" in meal_in: m["water"] = 500
        elif "쿼파치" in meal_in: m = {"cal": 1120, "p": 50, "f": 55, "c": 110, "fiber": 5, "water": 0}
        elif meal_in: m = {"cal": 600, "p": 25, "f": 20, "c": 70, "fiber": 3, "water": 0}
        for k in st.session_state.consumed: st.session_state.consumed[k] += m.get(k, 0)
        if meal_in: st.session_state.meal_history.append({"시간": datetime.now().strftime('%H:%M'), "메뉴": meal_in, "칼로리": m['cal']})

# --- 1. 기본정보 ---
st.header("1. 기본정보")
c1, c2 = st.columns(2)
with c1: st.table(pd.DataFrame(FIXED_DATA["profile"]).assign(번호=range(1, 5)).set_index('번호'))
with c2: st.table(pd.DataFrame(FIXED_DATA["health"]).assign(번호=range(1, 5)).set_index('번호'))

# --- 2. 영양상태 ---
st.header("2. 영양상태")
n1, n2, n3 = st.columns([1, 1.5, 1.5])
with n1:
    st.subheader("에너지 잔량")
    st.title(f"{st.session_state.consumed['cal']} / {TARGET['cal']} kcal")
    st.metric("남은 허용량", f"{TARGET['cal'] - st.session_state.consumed['cal']} kcal")
with n2:
    st.subheader("영양소 밸런스")
    c = st.session_state.consumed
    nutri_df = pd.DataFrame([
        {"항목": "단백질", "섭취/목표": f"{c['p']} / {TARGET['p']}g", "잔량": f"{max(0, TARGET['p']-c['p'])}g"},
        {"항목": "지방", "섭취/목표": f"{c['f']} / {TARGET['f']}g", "잔량": f"{max(0, TARGET['f']-c['f'])}g"},
        {"항목": "식이섬유", "섭취/목표": f"{c['fiber']} / {TARGET['fiber']}g", "잔량": f"{max(0, TARGET['fiber']-c['fiber'])}g"},
        {"항목": "수분", "섭취/목표": f"{c['water']} / {TARGET['water']}ml", "잔량": f"{max(0, TARGET['water']-c['water'])}ml"}
    ]).assign(번호=range(1, 5)).set_index('번호')
    st.table(nutri_df)
with n3:
    st.subheader("식단 히스토리")
    if st.session_state.meal_history: st.table(pd.DataFrame(st.session_state.meal_history).set_index('시간'))
    else: st.info("기록 없음")

# --- 3. 재무관리 (전 항목 공개) ---
st.header("3. 재무관리")
# 투자 자산 상세 계산
s_counts = {"삼성전자": 46, "SK하이닉스": 6, "삼성중공업": 88, "동성화인텍": 21}
stock_list = []
total_stock_val = 0
for n, code in FIXED_DATA["assets"]["stocks"].items():
    p = live["stocks"].get(n, 0)
    val = p * s_counts[n]
    total_stock_val += val
    stock_list.append({"항목": f"주식: {n}", "금액": val})

btc_val = int(FIXED_DATA["assets"]["crypto"]["BTC"] * live["crypto"]["KRW-BTC"])
eth_val = int(FIXED_DATA["assets"]["crypto"]["ETH"] * live["crypto"]["KRW-ETH"])

a1, a2 = st.columns(2)
with a1:
    st.subheader("전체 자산 리포트")
    # 모든 자산 항목 나열
    all_assets = [{"항목": "가용 현금", "금액": st.session_state.cash}]
    for k, v in FIXED_DATA["assets"]["savings"].items():
        all_assets.append({"항목": k, "금액": v})
    all_assets.extend(stock_list)
    all_assets.append({"항목": "가상자산: BTC", "금액": btc_val})
    all_assets.append({"항목": "가상자산: ETH", "금액": eth_val})
    
    df_assets = pd.DataFrame(all_assets)
    t_asset = df_assets['금액'].sum()
    df_assets_disp = df_assets.copy()
    df_assets_disp['금액'] = df_assets_disp['금액'].apply(lambda x: f"{x:,.0f}원")
    df_assets_disp = pd.concat([df_assets_disp, pd.DataFrame([{"항목": "총 자산 합계", "금액": f"{t_asset:,.0f}원"}])], ignore_index=True)
    df_assets_disp.index += 1
    st.table(df_assets_disp)
with a2:
    st.subheader("전체 부채 리포트")
    all_debts = [{"항목": k, "금액": v} for k, v in FIXED_DATA["assets"]["liabilities"].items()]
    df_debts = pd.DataFrame(all_debts)
    t_debt = df_debts['금액'].sum()
    df_debts_disp = df_debts.copy()
    df_debts_disp['금액'] = df_debts_disp['금액'].apply(lambda x: f"{x:,.0f}원")
    df_debts_disp = pd.concat([df_debts_disp, pd.DataFrame([{"항목": "총 부채 합계", "금액": f"{t_debt:,.0f}원"}])], ignore_index=True)
    df_debts_disp.index += 1
    st.table(df_debts_disp)
    st.metric("실시간 순자산", f"{t_asset - t_debt:,.0f}원")

# --- 4. 지출관리 / 5. 생활주기 / 6. 주방재고 ---
# (이전 v3.7과 동일하게 섹션 유지 - 생략 없이 출력)
st.header("4. 지출관리")
e_rows = [{"카테고리": k, "지출": f"{v:,.0f}원"} for k, v in st.session_state.expenses.items() if v > 0]
if e_rows: st.table(pd.DataFrame(e_rows).assign(번호=range(1, len(e_rows)+1)).set_index('번호'))
else: st.info("내역 없음")

st.header("5. 생활주기")
l_rows = []
for item, info in FIXED_DATA["lifecycle"].items():
    rem = (datetime.strptime(info["last"], "%Y-%m-%d") + timedelta(days=info["period"]) - datetime.now()).days
    l_rows.append({"항목": item, "상태": "🚨 점검" if rem <= 0 else "✅ 정상", "D-Day": f"{rem}일"})
st.table(pd.DataFrame(l_rows).assign(번호=range(1, 5)).set_index('번호'))

st.header("6. 주방재고")
st.table(pd.DataFrame([{"카테고리": k, "내용": v} for k, v in FIXED_DATA["kitchen"].items()]).assign(번호=range(1, 5)).set_index('번호'))
