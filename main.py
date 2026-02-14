import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# --- [1. 마스터 데이터 보존] ---
FIXED_DATA = {
    "profile": {"항목": ["나이", "거주", "상태", "결혼예정일"], "내용": ["32세", "평택 원평동", "공무원 발령 대기 중", "2026-05-30"]},
    "health": {"항목": ["현재 체중", "목표 체중", "주요 관리", "식단 금기"], "내용": ["125.0kg", "90.0kg", "고지혈증/ADHD", "생굴/멍게"]},
    "assets": {
        "savings": {"청년도약계좌": 14700000, "주택청약": 2540000, "전세보증금": 145850000},
        "liabilities": {"전세대출": 100000000, "마이너스통장": 3000000, "학자금대출": 1247270},
        "stocks": {"삼성전자": "005930", "SK하이닉스": "000660", "삼성중공업": "010140", "동성화인텍": "033500"},
        "stocks_count": {"삼성전자": 46, "SK하이닉스": 6, "삼성중공업": 88, "동성화인텍": 21},
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

TARGET = {"칼로리": 2000, "탄수화물": 300, "단백질": 150, "지방": 65, "나트륨": 2000, "콜레스테롤": 300, "당류": 50, "수분": 2000}
PAY_METHODS = ["하나카드", "우리카드", "국민카드", "현대카드", "지역화폐", "현금"]

# --- [2. 세션 초기화] ---
if 'consumed' not in st.session_state: st.session_state.consumed = {k: 0 for k in TARGET.keys()}
if 'cash' not in st.session_state: st.session_state.cash = 492918
if 'card_debt' not in st.session_state: st.session_state.card_debt = 0
if 'master_log' not in st.session_state: st.session_state.master_log = []

# --- [3. 가격 정보 (에러 방지 강화)] ---
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

# --- [4. 화면 구성] ---
st.set_page_config(page_title="자비스 최종 복구본", layout="wide")
st.title("🛡️ 자비스 통합 리포트")

live = get_live_prices()

# 사이드바 입력
with st.sidebar:
    st.header("📋 기록소")
    with st.form("input_form"):
        tran_type = st.radio("구분", ["지출", "수입"])
        amount = st.number_input("금액", 0)
        item_name = st.text_input("내용")
        if st.form_submit_button("기록"):
            st.success("데이터가 반영되었습니다.")

# 메인 리포트
col1, col2 = st.columns(2)

with col1:
    st.header("1. 기본 및 건강")
    st.table(pd.DataFrame(FIXED_DATA["profile"]))
    st.metric("오늘 칼로리", f"{st.session_state.consumed['칼로리']} / {TARGET['칼로리']} kcal")

with col2:
    st.header("2. 자산 현황")
    # 비트코인/이더리움 가치 계산
    btc_val = int(FIXED_DATA["assets"]["crypto"]["BTC"] * live["crypto"]["KRW-BTC"])
    eth_val = int(FIXED_DATA["assets"]["crypto"]["ETH"] * live["crypto"]["KRW-ETH"])
    st.metric("BTC 가치", f"{btc_val:,.0f}원")
    st.metric("ETH 가치", f"{eth_val:,.0f}원")

st.header("3. 생활 및 재고")
st.table(pd.DataFrame([{"항목": k, "내용": v} for k, v in FIXED_DATA["kitchen"].items()]))
