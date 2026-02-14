import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime, timedelta

# --- [1. 마스터 데이터: 보스의 투자 및 프로필 정보] ---
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
    "kitchen": {
        "단백질": "냉동삼치, 냉동닭다리, 관찰레, 북어채, 단백질쉐이크",
        "곡물/면": "파스타면, 소면, 쿠스쿠스, 라면, 우동, 쌀/카무트",
        "신선/기타": "김치4종, 아사이베리, 치아씨드, 향신료, 치즈"
    },
    "lifecycle": {
        "면도날": {"last": "2026-02-06", "period": 21},
        "칫솔": {"last": "2026-02-06", "period": 90},
        "이불세탁": {"last": "2026-02-04", "period": 14}
    }
}

API_URL = "https://script.google.com/macros/s/AKfycbzX1w7136qfFsnRb0RMQTZvJ1Q_-GZb5HAwZF6yfKiLTHbchJZq-8H2GXjV2z5WnkmI4A/exec"
TARGET = {"칼로리": 2000, "탄수": 300, "단백": 150, "지방": 65, "수분": 2000}

# --- [2. 시스템 유틸리티 함수] ---
def send_to_sheet(data_type, item, value):
    try:
        payload = {"type": data_type, "item": item, "value": value}
        requests.post(API_URL, data=json.dumps(payload), timeout=5)
        return True
    except: return False

def get_live_prices():
    prices = {"stocks": {}, "crypto": {}}
    for name, info in FIXED_DATA["stocks"].items():
        try:
            res = requests.get(f"https://polling.finance.naver.com/api/realtime?query=SERVICE_ITEM:{info['코드']}", timeout=1).json()
            prices["stocks"][name] = int(res['result']['areas'][0]['datas'][0]['nv'])
        except: prices["stocks"][name] = info['평단']
    try:
        res = requests.get("https://api.upbit.com/v1/ticker?markets=KRW-BTC,KRW-ETH", timeout=1).json()
        for c in res: prices["crypto"][c['market']] = float(c['trade_price'])
    except:
        for k, v in FIXED_DATA["crypto"].items(): prices["crypto"][v['마켓']] = v['평단']
    return prices

# --- [3. 초기화 및 레이아웃] ---
st.set_page_config(page_title="JARVIS v11.0", layout="wide")
if 'consumed' not in st.session_state: st.session_state.consumed = {k: 0 for k in TARGET.keys()}

st.title("🛡️ JARVIS OS v11.0")
tabs = st.tabs(["🏠 홈/체중", "🥗 영양/식단", "📈 자산/투자", "📦 재고/생활"])

# --- [탭 1: 홈/체중 기록] ---
with tabs[0]:
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("📍 보스 프로필")
        st.table(pd.DataFrame(FIXED_DATA["profile"]))
    with col_b:
        st.subheader("⚖️ 체중 관리")
        weight = st.number_input("오늘 체중(kg)", value=125.0, step=0.1)
        if st.button("체중 시트 전송"):
            if send_to_sheet("Weight", "Daily_Check", weight):
                st.success(f"{weight}kg 기록이 구글 시트에 저장되었습니다.")
            else: st.error("시트 전송 실패")

# --- [탭 2: 영양/식단] ---
with tabs[1]:
    st.header("🥗 영양 섭취 및 기록")
    with st.expander("➕ 식단 입력 (FatSecret 수치)", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        kcal = c1.number_input("칼로리", 0)
        carb = c2.number_input("탄수", 0)
        prot = c3.number_input("단백", 0)
        fat = c4.number_input("지방", 0)
        if st.button("영양 데이터 시트 전송"):
            send_to_sheet("Diet", "Calories", kcal)
            st.session_state.consumed['칼로리'] += kcal
            st.session_state.consumed['탄수'] += carb
            st.session_state.consumed['단백'] += prot
            st.session_state.consumed['지방'] += fat
            st.success("시트 저장 및 앱 합산 완료")

    st.subheader("📊 오늘의 영양 표")
    nut_df = pd.DataFrame([{"항목": k, "현재": v, "목표": TARGET[k]} for k, v in st.session_state.consumed.items()])
    st.table(nut_df)

# --- [탭 3: 자산/투자] ---
with tabs[2]:
    st.header("📈 투자 실시간 리포트")
    live = get_live_prices()
    
    # 주식 리스트
    s_data = []
    for n, i in FIXED_DATA["stocks"].items():
        curr = live["stocks"].get(n, i['평단'])
        profit = (curr - i['평단']) * i['수량']
        rate = ((curr / i['평단']) - 1) * 100
        s_data.append({"종목": n, "수량": i['수량'], "현재가": f"{curr:,}", "수익률": f"{rate:.2f}%", "평가손익": f"{int(profit):,}"})
    st.table(pd.DataFrame(s_data))
    
    # 코인 리스트
    c_data = []
    for n, i in FIXED_DATA["crypto"].items():
        curr = live["crypto"].get(i['마켓'], i['평단'])
        profit = (curr - i['평단']) * i['수량']
        rate = ((curr / i['평단']) - 1) * 100
        c_data.append({"코인": n, "현재가": f"{curr:,.0f}", "수익률": f"{rate:.2f}%", "평가손익": f"{int(profit):,}"})
    st.table(pd.DataFrame(c_data))

# --- [탭 4: 재고/생활] ---
with tabs[3]:
    st.header("📦 시스템 재고 및 주기")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🔄 교체 주기")
        l_rows = []
        for item, info in FIXED_DATA["lifecycle"].items():
            d_day = (datetime.strptime(info["last"], "%Y-%m-%d") + timedelta(days=info["period"]) - datetime.now()).days
            l_rows.append({"항목": item, "상태": f"D-{d_day}", "최근": info["last"]})
        st.table(pd.DataFrame(l_rows))
    with col2:
        st.subheader("🍳 주방 재고")
        st.table(pd.DataFrame([{"카테고리": k, "내용": v} for k, v in FIXED_DATA["kitchen"].items()]))
