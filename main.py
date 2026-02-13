import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# 1. 보스의 통합 데이터베이스
MY_DATA = {
    "profile": {"항목": ["나이", "거주", "상태", "결혼예정일"], "내용": ["32세", "평택 원평동", "공무원 발령 대기 중", "2026-05-30"]},
    "health": {"항목": ["현재 체중", "목표 체중", "주요 관리", "식단 금기"], "내용": ["125.0kg", "90.0kg", "고지혈증/ADHD", "생굴/멍게"]},
    "assets": {
        "cash": 492918,
        "savings": {"청년도약계좌": 14700000, "주택청약": 2540000, "전세보증금(총액)": 145850000},
        "liabilities": {"전세대출": 100000000, "마이너스통장": 3000000, "학자금대출": 1247270},
        "stocks": {"삼성전자": 46, "SK하이닉스": 6, "삼성중공업": 88, "동성화인텍": 21},
        "crypto": {"BTC": 0.00181400, "ETH": 0.03417393}
    },
    "lifecycle": {
        "면도기/칫솔": {"last": "2026-02-06", "period": 21},
        "이불세탁": {"last": "2026-01-30", "period": 14},
        "로봇청소기": {"last": "2026-02-12", "period": 2}
    },
    "kitchen": {
        "소스/캔": "토마토페이스트(10), 나시고랭(1), S&B카레, 뚝심(2), 땅콩버터(4/5)",
        "단백질": "냉동삼치(4), 냉동닭다리(4), 관찰레, 북어채, 단백질쉐이크(9)",
        "곡물/면": "파스타면(다수), 소면(1), 쿠스쿠스(1), 라면(12), 우동/소바, 쌀/카무트",
        "신선/기타": "김치4종, 아사이베리, 치아씨드, 각종향신료, 치즈류"
    }
}

def get_live_prices():
    try:
        res = requests.get("https://api.upbit.com/v1/ticker?markets=KRW-BTC,KRW-ETH", timeout=5).json()
        return {c['market']: c['trade_price'] for c in res}
    except: return {"KRW-BTC": 95000000, "KRW-ETH": 3800000}

st.set_page_config(page_title="JARVIS v2.0", layout="wide")
st.title("JARVIS : 실시간 자산 총계 및 정밀 대시보드")

# 금액 우측 정렬을 위한 CSS
st.markdown("""
    <style>
    .stTable td:nth-child(2) {text-align: right !important;}
    .stTable td:nth-child(3) {text-align: right !important;}
    </style>
    """, unsafe_allow_html=True)

# --- [SECTION 1] 프로필 및 건강 ---
st.header("🏁 기본 프로필 및 건강")
c_p1, c_p2 = st.columns(2)
with c_p1:
    df_p = pd.DataFrame(MY_DATA["profile"])
    df_p.index = df_p.index + 1
    st.table(df_p)
with c_p2:
    df_h = pd.DataFrame(MY_DATA["health"])
    df_h.index = df_h.index + 1
    st.table(df_h)

# --- [SECTION 2] 재무 매트릭스 ---
st.header("💰 자산 및 부채 정밀 정산")
prices = get_live_prices()
btc_v = int(MY_DATA["assets"]["crypto"]["BTC"] * prices["KRW-BTC"])
eth_v = int(MY_DATA["assets"]["crypto"]["ETH"] * prices["KRW-ETH"])

a1, a2 = st.columns(2)
with a1:
    st.subheader("🏦 자산 리스트")
    asset_rows = [{"항목": "보유 현금", "금액": MY_DATA['assets']['cash']}]
    for k, v in MY_DATA["assets"]["savings"].items():
        asset_rows.append({"항목": k, "금액": v})
    asset_rows.append({"항목": "비트코인(BTC) 환산", "금액": btc_v})
    asset_rows.append({"항목": "이더리움(ETH) 환산", "금액": eth_v})
    
    df_a = pd.DataFrame(asset_rows)
    total_a = df_a['금액'].sum()
    # 총계 행 추가
    df_a = pd.concat([df_a, pd.DataFrame([{"항목": "✨ 총 자산 합계", "금액": total_a}])], ignore_index=True)
    df_a['금액'] = df_a['금액'].apply(lambda x: f"{x:,.0f}원")
    df_a.index = df_a.index + 1
    st.table(df_a)
    
    st.subheader("📈 주식 포트폴리오")
    df_s = pd.DataFrame(MY_DATA["assets"]["stocks"].items(), columns=['종목', '수량'])
    total_s = df_s['수량'].sum()
    df_s = pd.concat([df_s, pd.DataFrame([{"종목": "✨ 총 보유 주식수", "수량": total_s}])], ignore_index=True)
    df_s.index = df_s.index + 1
    st.table(df_s)

with a2:
    st.subheader("💸 부채 리스트")
    debt_rows = [{"항목": k, "금액": v} for k, v in MY_DATA["assets"]["liabilities"].items()]
    df_d = pd.DataFrame(debt_rows)
    total_d = df_d['금액'].sum()
    # 총계 행 추가
    df_d = pd.concat([df_d, pd.DataFrame([{"항목": "✨ 총 부채 합계", "금액": total_d}])], ignore_index=True)
    df_d['금액'] = df_d['금액'].apply(lambda x: f"{x:,.0f}원")
    df_d.index = df_d.index + 1
    st.table(df_d)
    
    st.metric("💵 최종 순자산 (자산-부채)", f"{total_a - total_d:,.0f}원")

# --- [SECTION 3] 라이프 사이클 및 주방 ---
st.header("🔄 관리 주기 및 📦 주방")
l1, l2 = st.columns(2)
with l1:
    life_rows = []
    for item, info in MY_DATA["lifecycle"].items():
        next_d = datetime.strptime(info["last"], "%Y-%m-%d") + timedelta(days=info["period"])
        rem = (next_d - datetime.now()).days
        life_rows.append({"항목": item, "상태": "🚨 점검
