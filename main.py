import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime, timedelta

# 1. 마스터 데이터 (주식/코인 평단가 최신화)
FIXED_DATA = {
    "health": {"항목": ["목표 체중", "주요 관리", "식단 금기"], "내용": ["90.0kg", "고지혈증/ADHD", "생굴/멍게"]},
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

# 2. 유틸리티 함수
def send_to_sheet(d_type, item, value):
    # 한국 시간 강제 고정 (UTC+9)
    kr_time = (datetime.utcnow() + timedelta(hours=9)).strftime('%Y-%m-%d %H:%M:%S')
    payload = {"time": kr_time, "type": d_type, "item": item, "value": value}
    try:
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

# 3. 레이아웃
st.set_page_config(page_title="자비스 v12.0", layout="wide")
if 'consumed' not in st.session_state: st.session_state.consumed = {k: 0 for k in TARGET.keys()}

st.title("JARVIS 통합 대시보드")
tabs = st.tabs(["영양/식단/체중", "자산/투자", "재고/생활", "가계부 기록"])

# 탭 1: 영양/식단/체중
with tabs[0]:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("체중 기록")
        weight = st.number_input("현재 체중(kg)", value=125.0, step=0.1)
        if st.button("체중 저장"):
            send_to_sheet("체중", "일일체크", weight)
            st.success("시트 전송 완료")
            
    with col2:
        st.subheader("식단 입력 (FatSecret)")
        kcal = st.number_input("칼로리", 0)
        carb = st.number_input("탄수", 0)
        prot = st.number_input("단백", 0)
        fat = st.number_input("지방", 0)
        if st.button("영양 데이터 전송"):
            send_to_sheet("식단", "칼로리", kcal)
            st.session_state.consumed['칼로리'] += kcal
            st.session_state.consumed['탄수'] += carb
            st.session_state.consumed['단백'] += prot
            st.session_state.consumed['지방'] += fat
            st.rerun()

    st.subheader("오늘의 영양 섭취 현황")
    st.table(pd.DataFrame([{"항목": k, "현재": v, "목표": TARGET[k]} for k, v in st.session_state.consumed.items()]))

# 탭 2: 자산/투자
with tabs[1]:
    live = get_live_prices()
    st.subheader("국내 주식 수익률")
    s_data = []
    for n, i in FIXED_DATA["stocks"].items():
        curr = live["stocks"].get(n, i['평단'])
        profit = (curr - i['평단']) * i['수량']
        rate = ((curr / i['평단']) - 1) * 100
        s_data.append({"종목": n, "현재가": f"{curr:,}", "수익률": f"{rate:.2f}%", "평가손익": f"{int(profit):,}"})
    st.table(pd.DataFrame(s_data))

    st.subheader("가상자산 수익률")
    c_data = []
    for n, i in FIXED_DATA["crypto"].items():
        curr = live["crypto"].get(i['마켓'], i['평단'])
        profit = (curr - i['평단']) * i['수량']
        rate = ((curr / i['평단']) - 1) * 100
        c_data.append({"코인": n, "현재가": f"{curr:,.0f}", "수익률": f"{rate:.2f}%", "평가손익": f"{int(profit):,}"})
    st.table(pd.DataFrame(c_data))

# 탭 3: 재고/생활
with tabs[2]:
    st.subheader("교체 주기")
    l_rows = []
    for item, info in FIXED_DATA["lifecycle"].items():
        d_day = (datetime.strptime(info["last"], "%Y-%m-%d") + timedelta(days=info["period"]) - (datetime.utcnow() + timedelta(hours=9))).days
        l_rows.append({"항목": item, "상태": f"{d_day}일 남음", "최근": info["last"]})
    st.table(pd.DataFrame(l_rows))
    
    st.subheader("주방 재고")
    st.table(pd.DataFrame([{"구분": k, "내용": v} for k, v in FIXED_DATA["kitchen"].items()]))

# 탭 4: 가계부 기록 (지출/수입)
with tabs[3]:
    st.subheader("지출 및 수입 기록")
    t_type = st.selectbox("구분", ["지출", "수입"])
    t_item = st.text_input("항목명 (예: 편의점, 월급 등)")
    t_val = st.number_input("금액", 0)
    if st.button("가계부 시트 전송"):
        if send_to_sheet(t_type, t_item, t_val):
            st.success(f"{t_type} 내역이 Finance 탭에 저장되었습니다.")
