import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# 1. 자비스 통합 데이터베이스 (보스의 모든 정밀 데이터)
MY_DATA = {
    "profile": {"나이": 32, "거주": "평택 원평동", "상태": "공무원 발령 대기 중", "결혼일": "2026-05-30"},
    "health": {"현재체중": 125.0, "목표체중": 90.0, "관리": "고지혈증/ADHD", "금기": "생굴/멍게"},
    "assets": {
        "cash": 492918,
        "savings": {
            "청년도약계좌": 14700000, 
            "주택청약": 2540000, 
            "전세보증금(총액)": 145850000 # 1억 4585만원 전체 자산화
        },
        "liabilities": {
            "전세대출": 100000000, # 1억 원 빚
            "마이너스통장": 3000000, 
            "학자금대출": 1247270
        },
        "stocks": {"삼성전자": 46, "SK하이닉스": 6, "삼성중공업": 88, "동성화인텍": 21},
        "crypto": {"BTC": 0.00181400, "ETH": 0.03417393}
    },
    "lifecycle": {
        "면도기/칫솔": {"last": "2026-02-06", "period": 21},
        "이불세탁": {"last": "2026-01-30", "period": 14},
        "로봇청소기": {"last": "2026-02-12", "period": 2}
    },
    "kitchen": {
        "소스/캔": ["토마토페이스트(10)", "나시고랭(1)", "S&B카레", "뚝심(2)", "땅콩버터(4/5)"],
        "단백질": ["냉동삼치(4)", "냉동닭다리(4)", "관찰레", "북어채", "단백질쉐이크(9)"],
        "곡물/면": ["파스타면(다수)", "소면(1)", "쿠스쿠스(1)", "라면(12)", "우동/소바", "쌀/카무트"],
        "기타": ["김치4종(동치미/묵은지/매운/백)", "아사이베리", "치아씨드", "각종향신료", "치즈류"]
    }
}

# 2. 실시간 시세 엔진 (가상자산)
def get_live_prices():
    try:
        res = requests.get("https://api.upbit.com/v1/ticker?markets=KRW-BTC,KRW-ETH").json()
        return {c['market']: c['trade_price'] for c in res}
    except: return {"KRW-BTC": 90000000, "KRW-ETH": 3500000}

# 3. 화면 구성
st.set_page_config(page_title="JARVIS FULL-MATRIX", layout="wide")
st.title("🤵 JARVIS : 전지적 보스 시점 실시간 대시보드")

# --- [SECTION 1] 결혼 및 신체 지표 ---
st.header("🏁 결혼 및 건강 실시간 지표")
target_dt = datetime.strptime(MY_DATA["profile"]["결혼일"], "%Y-%m-%d")
d_day = (target_dt - datetime.now()).days
remain_w = MY_DATA["health"]["현재체중"] - MY_DATA["health"]["목표체중"]

h1, h2, h3 = st.columns(3)
h1.metric("💍 결혼 D-Day", f"D-{d_day}")
h2.metric("⚖️ 현재 체중", f"{MY_DATA['health']['현재체중']}kg")
h3.metric("📉 남은 감량", f"{remain_w}kg", delta_color="inverse")
st.divider()

# --- [SECTION 2] 재무 매트릭스 (자산 보정 완료) ---
st.header("💰 자산/부채 정밀 매트릭스")
prices = get_live_prices()
btc_krw = MY_DATA["assets"]["crypto"]["BTC"] * prices["KRW-BTC"]
eth_krw = MY_DATA["assets"]["crypto"]["ETH"] * prices["KRW-ETH"]

total_assets = MY_DATA["assets"]["cash"] + sum(MY_DATA["assets"]["savings"].values()) + btc_krw + eth_krw
total_debt = sum(MY_DATA["assets"]["liabilities"].values())
net_worth = total_assets - total_debt

st.subheader(f"💵 실시간 순자산: {net_worth:,.0f}원")
a1, a2 = st.columns(2)
with a1:
    st.write("**[내 자산 리스트]**")
    st.write(f"- 현금: {MY_DATA['assets']['cash']:,.0f}원")
    st.write(f"- 청년도약계좌: 1,470만원")
    st.write(f"- 주택청약: 254만원")
    st.info(f"- 전세보증금(총액): {MY_DATA['assets']['savings']['전세보증금(총액)']:,.0f}원 (내돈 4,585만 포함)")
    st.write(f"- 비트코인 가치: {btc_krw:,.0f}원")
    st.write(f"- 이더리움 가치: {eth_krw:,.0f}원")
with a2:
    st.write("**[내 부채 리스트]**")
    st.error(f"- 전세보증금대출: {MY_DATA['assets']['liabilities']['전세대출']:,.0f}원")
    st.write(f"- 마이너스 통장: {MY_DATA['assets']['liabilities']['마이너스통장']:,.0f}원")
    st.write(f"- 학자금 대출: {MY_DATA['assets']['liabilities']['학자금대출']:,.0f}원")
    st.write("**[주식 포트폴리오]**")
    st.table(pd.DataFrame(MY_DATA["assets"]["stocks"].items(), columns=['종목', '수량']))
st.divider()

# --- [SECTION 3] 라이프 사이클 ---
st.header("🔄 주기적 관리 스케줄")
l_cols = st.columns(3)
for i, (item, info) in enumerate(MY_DATA["lifecycle"].items()):
    next_d = datetime.strptime(info["last"], "%Y-%m-%d") + timedelta(days=info["period"])
    rem = (next_d - datetime.now()).days
    with l_cols[i % 3]:
        if rem <= 0: st.error(f"🚨 {item}: 관리 기한 초과!")
        else: st.success(f"✅ {item}: {rem}일 뒤 관리")
st.divider()

# --- [SECTION 4] 주방 인벤토리 ---
st.header("📦 주방 재고 매트릭스")
i_cols = st.columns(4)
for i, (cat, items) in enumerate(MY_DATA["kitchen"].items()):
    with i_cols[i]:
        st.write(f"**[{cat}]**")
        for item in items:
            st.write(f"- {item}")

st.markdown("---")
st.caption(f"JARVIS Real-time Data Mapping... Last Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
