import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# 1. 자비스 통합 데이터베이스 (보스의 모든 정밀 데이터)
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

# 2. 실시간 시세 엔진
def get_live_prices():
    try:
        res = requests.get("https://api.upbit.com/v1/ticker?markets=KRW-BTC,KRW-ETH").json()
        return {c['market']: c['trade_price'] for c in res}
    except: return {"KRW-BTC": 95000000, "KRW-ETH": 3800000}

st.set_page_config(page_title="JARVIS v1.8", layout="wide")
st.title("🤵 JARVIS : 전지적 보스 시점 (Full-Table)")

# --- [SECTION 1] 프로필 및 건강 (표 형식) ---
st.header("🏁 기본 프로필 및 건강 지표")
c_p1, c_p2 = st.columns(2)
with c_p1:
    st.table(pd.DataFrame(MY_DATA["profile"]))
with c_p2:
    st.table(pd.DataFrame(MY_DATA["health"]))
st.divider()

# --- [SECTION 2] 재무 매트릭스 (자산 리스트에 주식 통합) ---
st.header("💰 자산 및 부채 정밀 표")
prices = get_live_prices()
btc_krw = MY_DATA["assets"]["crypto"]["BTC"] * prices["KRW-BTC"]
eth_krw = MY_DATA["assets"]["crypto"]["ETH"] * prices["KRW-ETH"]

total_assets = MY_DATA["assets"]["cash"] + sum(MY_DATA["assets"]["savings"].values()) + btc_krw + eth_krw
total_debt = sum(MY_DATA["assets"]["liabilities"].values())
st.subheader(f"💵 실시간 순자산: {total_assets - total_debt:,.0f}원")

a1, a2 = st.columns(2)
with a1:
    st.subheader("🏦 자산 리스트")
    # 현금/예금 표
    asset_list = [{"항목": "보유 현금", "금액": f"{MY_DATA['assets']['cash']:,.0f}원"}]
    for k, v in MY_DATA["assets"]["savings"].items():
        asset_list.append({"항목": k, "금액": f"{v:,.0f}원"})
    asset_list.append({"항목": "비트코인(BTC) 환산", "금액": f"{btc_krw:,.0f}원"})
    asset_list.append({"항목": "이더리움(ETH) 환산", "금액": f"{eth_krw:,.0f}원"})
    st.table(pd.DataFrame(asset_list))

    # 주식 포트폴리오 (자산 리스트 하단 배치 및 인덱스 1부터 시작)
    st.write("**[주식 포트폴리오]**")
    stock_df = pd.DataFrame(MY_DATA["assets"]["stocks"].items(), columns=['종목', '수량'])
    stock_df.index = stock_df.index + 1 # 순번 1부터 시작
    st.table(stock_df)

with a2:
    st.subheader("💸 부채 리스트")
    debt_list = []
    for k, v in MY_DATA["assets"]["liabilities"].items():
        debt_list.append({"항목": k, "금액": f"{v:,.0f}원"})
    st.table(pd.DataFrame(debt_list))
st.divider()

# --- [SECTION 3] 라이프 사이클 (표 형식) ---
st.header("🔄 라이프 사이클 관리")
life_list = []
for item, info in MY_DATA["lifecycle"].items():
    next_d = datetime.strptime(info["last"], "%Y-%m-%d") + timedelta(days=info["period"])
    rem = (next_d - datetime.now()).days
    status = "🚨 관리 필요" if rem <= 0 else "✅ 정상"
    life_list.append({"관리 항목": item, "마지막 관리일": info["last"], "남은 일수": f"{rem}일", "상태": status})
st.table(pd.DataFrame(life_list))
st.divider()

# --- [SECTION 4] 주방 재고 (표 형식) ---
st.header("📦 주방 재고 인벤토리")
kitchen_df = pd.DataFrame(MY_DATA["kitchen"].items(), columns=['카테고리', '상세 내용'])
st.table(kitchen_df)

st.markdown("---")
st.caption(f"JARVIS Matrix Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# 1. 자비스 통합 데이터베이스 (보스의 모든 정밀 데이터)
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

# 2. 실시간 시세 엔진
def get_live_prices():
    try:
        res = requests.get("https://api.upbit.com/v1/ticker?markets=KRW-BTC,KRW-ETH").json()
        return {c['market']: c['trade_price'] for c in res}
    except: return {"KRW-BTC": 95000000, "KRW-ETH": 3800000}

st.set_page_config(page_title="JARVIS v1.8", layout="wide")
st.title("🤵 JARVIS : 전지적 보스 시점 (Full-Table)")

# --- [SECTION 1] 프로필 및 건강 (표 형식) ---
st.header("🏁 기본 프로필 및 건강 지표")
c_p1, c_p2 = st.columns(2)
with c_p1:
    st.table(pd.DataFrame(MY_DATA["profile"]))
with c_p2:
    st.table(pd.DataFrame(MY_DATA["health"]))
st.divider()

# --- [SECTION 2] 재무 매트릭스 (자산 리스트에 주식 통합) ---
st.header("💰 자산 및 부채 정밀 표")
prices = get_live_prices()
btc_krw = MY_DATA["assets"]["crypto"]["BTC"] * prices["KRW-BTC"]
eth_krw = MY_DATA["assets"]["crypto"]["ETH"] * prices["KRW-ETH"]

total_assets = MY_DATA["assets"]["cash"] + sum(MY_DATA["assets"]["savings"].values()) + btc_krw + eth_krw
total_debt = sum(MY_DATA["assets"]["liabilities"].values())
st.subheader(f"💵 실시간 순자산: {total_assets - total_debt:,.0f}원")

a1, a2 = st.columns(2)
with a1:
    st.subheader("🏦 자산 리스트")
    # 현금/예금 표
    asset_list = [{"항목": "보유 현금", "금액": f"{MY_DATA['assets']['cash']:,.0f}원"}]
    for k, v in MY_DATA["assets"]["savings"].items():
        asset_list.append({"항목": k, "금액": f"{v:,.0f}원"})
    asset_list.append({"항목": "비트코인(BTC) 환산", "금액": f"{btc_krw:,.0f}원"})
    asset_list.append({"항목": "이더리움(ETH) 환산", "금액": f"{eth_krw:,.0f}원"})
    st.table(pd.DataFrame(asset_list))

    # 주식 포트폴리오 (자산 리스트 하단 배치 및 인덱스 1부터 시작)
    st.write("**[주식 포트폴리오]**")
    stock_df = pd.DataFrame(MY_DATA["assets"]["stocks"].items(), columns=['종목', '수량'])
    stock_df.index = stock_df.index + 1 # 순번 1부터 시작
    st.table(stock_df)

with a2:
    st.subheader("💸 부채 리스트")
    debt_list = []
    for k, v in MY_DATA["assets"]["liabilities"].items():
        debt_list.append({"항목": k, "금액": f"{v:,.0f}원"})
    st.table(pd.DataFrame(debt_list))
st.divider()

# --- [SECTION 3] 라이프 사이클 (표 형식) ---
st.header("🔄 라이프 사이클 관리")
life_list = []
for item, info in MY_DATA["lifecycle"].items():
    next_d = datetime.strptime(info["last"], "%Y-%m-%d") + timedelta(days=info["period"])
    rem = (next_d - datetime.now()).days
    status = "🚨 관리 필요" if rem <= 0 else "✅ 정상"
    life_list.append({"관리 항목": item, "마지막 관리일": info["last"], "남은 일수": f"{rem}일", "상태": status})
st.table(pd.DataFrame(life_list))
st.divider()

# --- [SECTION 4] 주방 재고 (표 형식) ---
st.header("📦 주방 재고 인벤토리")
kitchen_df = pd.DataFrame(MY_DATA["kitchen"].items(), columns=['카테고리', '상세 내용'])
st.table(kitchen_df)

st.markdown("---")
st.caption(f"JARVIS Matrix Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
