import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# --- [1. 마스터 데이터: 주식 및 코인 상세 정보 반영] ---
FIXED_DATA = {
    "profile": {"항목": ["나이", "거주", "상태", "결혼예정일"], "내용": ["32세", "평택 원평동", "공무원 발령 대기 중", "2026-05-30"]},
    "health": {"항목": ["현재 체중", "목표 체중", "주요 관리", "식단 금기"], "내용": ["125.0kg", "90.0kg", "고지혈증/ADHD", "생굴/멍게"]},
    "stocks": {
        "동성화인텍": {"평단": 22701, "수량": 21, "코드": "033500"},
        "삼성중공업": {"평단": 16761, "수량": 88, "코드": "010140"},
        "SK하이닉스": {"평단": 473521, "수량": 6, "코드": "000660"},
        "삼성전자": {"평단": 78895, "수량": 46, "코드": "005930"}
    },
    "crypto": {
        "BTC": {"평단": 137788139, "수량": 0.00181400, "마켓": "KRW-BTC"},
        "ETH": {"평단": 4243000, "수량": 0.03417393, "마켓": "KRW-ETH"}
    },
    "assets": {
        "savings": {"청년도약계좌": 14700000, "주택청약": 2540000, "전세보증금": 145850000},
        "liabilities": {"전세대출": 100000000, "마이너스통장": 3000000, "학자금대출": 1247270}
    },
    "lifecycle": {
        "면도날": {"last": "2026-02-06", "period": 21}, 
        "칫솔": {"last": "2026-02-06", "period": 90}, 
        "이불세탁": {"last": "2026-02-04", "period": 14} 
    }
}

TARGET = {"칼로리": 2000, "탄수": 300, "단백": 150, "지방": 65, "수분": 2000}

# --- [2. 실시간 가격 로드 함수] ---
def get_live_prices():
    prices = {"stocks": {}, "crypto": {}}
    # 주식 가격 (네이버 금융)
    for name, info in FIXED_DATA["stocks"].items():
        try:
            res = requests.get(f"https://polling.finance.naver.com/api/realtime?query=SERVICE_ITEM:{info['코드']}", timeout=1).json()
            prices["stocks"][name] = int(res['result']['areas'][0]['datas'][0]['nv'])
        except: prices["stocks"][name] = info['평단']
    # 코인 가격 (업비트)
    try:
        res = requests.get("https://api.upbit.com/v1/ticker?markets=KRW-BTC,KRW-ETH", timeout=1).json()
        for c in res: prices["crypto"][c['market']] = float(c['trade_price'])
    except:
        for k, v in FIXED_DATA["crypto"].items(): prices["crypto"][v['마켓']] = v['평단']
    return prices

# --- [3. 초기화 및 스타일] ---
st.set_page_config(page_title="JARVIS v10.0", layout="wide")
if 'consumed' not in st.session_state: st.session_state.consumed = {k: 0 for k in TARGET.keys()}
if 'weight_log' not in st.session_state: st.session_state.weight_log = [125.0]

st.title("🛡️ JARVIS OS v10.0")

# FatSecret 스타일 하단 탭 (Streamlit Tabs)
tabs = st.tabs(["🏠 홈", "🥗 영양/식단", "📈 자산/투자", "📦 생활/재고"])

# --- [탭 1: 홈] ---
with tabs[0]:
    st.subheader("📍 보스 프로필")
    st.table(pd.DataFrame(FIXED_DATA["profile"]))
    
    st.subheader("⚖️ 데일리 체중 기록")
    curr_w = st.number_input("오늘의 체중 (kg)", value=st.session_state.weight_log[-1], step=0.1)
    if st.button("체중 저장"):
        st.session_state.weight_log.append(curr_w)
        st.success(f"{curr_w}kg 기록 완료. 목표까지 {curr_w - 90:.1f}kg 남았습니다.")

# --- [탭 2: 영양/식단] ---
with tabs[1]:
    st.header("🥗 FatSecret 스타일 영양 관리")
    with st.expander("➕ 식단 추가하기 (FatSecret 수치 입력)", expanded=True):
        cols = st.columns(5)
        c_cal = cols[0].number_input("칼로리", 0)
        c_car = cols[1].number_input("탄수", 0)
        c_pro = cols[2].number_input("단백", 0)
        c_fat = cols[3].number_input("지방", 0)
        c_wat = cols[4].number_input("수분", 0)
        if st.button("기록 합산"):
            vals = [c_cal, c_car, c_pro, c_fat, c_wat]
            for k, v in zip(TARGET.keys(), vals): st.session_state.consumed[k] += v
            st.rerun()

    nut_rows = []
    for k, v in st.session_state.consumed.items():
        nut_rows.append({"항목": k, "현재": f"{v}", "목표": f"{TARGET[k]}", "잔여": f"{TARGET[k]-v}"})
    st.table(pd.DataFrame(nut_rows))

# --- [탭 3: 자산/투자] ---
with tabs[2]:
    st.header("📈 투자 수익률 리포트")
    live = get_live_prices()
    
    # 주식 표
    s_rows = []
    for n, i in FIXED_DATA["stocks"].items():
        curr = live["stocks"].get(n, i['평단'])
        profit = (curr - i['평단']) * i['수량']
        rate = ((curr / i['평단']) - 1) * 100
        s_rows.append({"종목": n, "현재가": f"{curr:,}", "평가손익": f"{int(profit):,}", "수익률": f"{rate:.2f}%"})
    st.subheader("🇰🇷 국내 주식")
    st.table(pd.DataFrame(s_rows))
    
    # 코인 표
    c_rows = []
    for n, i in FIXED_DATA["crypto"].items():
        curr = live["crypto"].get(i['마켓'], i['평단'])
        profit = (curr - i['평단']) * i['수량']
        rate = ((curr / i['평단']) - 1) * 100
        c_rows.append({"코인": n, "현재가": f"{curr:,.0f}", "평가손익": f"{int(profit):,}", "수익률": f"{rate:.2f}%"})
    st.subheader("🪙 가상자산")
    st.table(pd.DataFrame(c_rows))

# --- [탭 4: 생활/재고] ---
with tabs[3]:
    st.header("📦 시스템 교체 주기 및 재고")
    l_rows = []
    for item, info in FIXED_DATA["lifecycle"].items():
        d_day = (datetime.strptime(info["last"], "%Y-%m-%d") + timedelta(days=info["period"]) - datetime.now()).days
        l_rows.append({"항목": item, "마지막 교체": info["last"], "상태": f"{d_day}일 남음"})
    st.table(pd.DataFrame(l_rows))
    
    st.subheader("🍳 주방 재고")
    st.table(pd.DataFrame([{"구분": k, "내역": v} for k, v in FIXED_DATA["kitchen"].items()]))
