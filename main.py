import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# 1. 마스터 데이터베이스
MY_DATA = {
    "profile": {"항목": ["나이", "거주", "상태", "결혼예정일"], "내용": ["32세", "평택 원평동", "공무원 발령 대기 중", "2026-05-30"]},
    "health": {"항목": ["현재 체중", "목표 체중", "주요 관리", "식단 금기"], "내용": ["125.0kg", "90.0kg", "고지혈증/ADHD", "생굴/멍게"]},
    "assets": {
        "cash": 492918,
        "savings": {"청년도약계좌": 14700000, "주택청약": 2540000, "전세보증금(총액)": 145850000},
        "liabilities": {"전세대출": 100000000, "마이너스통장": 3000000, "학자금대출": 1247270},
        "stocks": {
            "삼성전자": {"code": "005930", "count": 46},
            "SK하이닉스": {"code": "000660", "count": 6},
            "삼성중공업": {"code": "010140", "count": 88},
            "동성화인텍": {"code": "033500", "count": 21}
        },
        "crypto": {"BTC": 0.00181400, "ETH": 0.03417393}
    },
    "lifecycle": {
        "면도날": {"last": "2026-02-06", "period": 21},   # 보스 요청: 3주(21일)로 변경
        "칫솔": {"last": "2026-02-06", "period": 90},     # 권장: 3개월
        "이불세탁": {"last": "2026-01-30", "period": 14}, # 권장: 2주
        "로봇청소기": {"last": "2026-02-12", "period": 2}  # 권장: 2일
    },
    "kitchen": {
        "소스/캔": "토마토페이스트(10), 나시고랭(1), S&B카레, 뚝심(2), 땅콩버터(4/5)",
        "단백질": "냉동삼치(4), 냉동닭다리(4), 관찰레, 북어채, 단백질쉐이크(9)",
        "곡물/면": "파스타면(다수), 소면(1), 쿠스쿠스(1), 라면(12), 우동/소바, 쌀/카무트",
        "신선/기타": "김치4종, 아사이베리, 치아씨드, 각종향신료, 치즈류"
    }
}

# 실시간 주가/코인 시세 엔진
def get_live_prices():
    prices = {"crypto": {}, "stocks": {}}
    # 코인 시세 (업비트)
    try:
        res = requests.get("https://api.upbit.com/v1/ticker?markets=KRW-BTC,KRW-ETH").json()
        prices["crypto"] = {c['market']: c['trade_price'] for c in res}
    except: prices["crypto"] = {"KRW-BTC": 95000000, "KRW-ETH": 3800000}
    
    # 주식 시세 (네이버 금융 API 활용)
    for name, info in MY_DATA["assets"]["stocks"].items():
        try:
            url = f"https://polling.finance.naver.com/api/realtime?query=SERVICE_ITEM:{info['code']}"
            res = requests.get(url, timeout=5).json()
            prices["stocks"][name] = int(res['result']['areas'][0]['datas'][0]['nv'])
        except:
            # 실패 시 최근 종가 기준 (2026-02-13 기준)
            fallbacks = {"삼성전자": 183400, "SK하이닉스": 898000, "삼성중공업": 27800, "동성화인텍": 27550}
            prices["stocks"][name] = fallbacks.get(name, 0)
    return prices

st.set_page_config(page_title="자비스 대시보드 v2.4", layout="wide")
st.title("자비스 : 실시간 통합 관리 시스템")

# CSS: 우측 정렬 및 줄바꿈 보정
st.markdown("""
    <style>
    th {text-align: left !important;}
    td {white-space: pre-wrap !important;} 
    td:nth-child(2), td:nth-child(3), td:nth-child(4) {text-align: right !important;}
    </style>
    """, unsafe_allow_html=True)

# 데이터 업데이트
live = get_live_prices()

# --- 섹션 1: 기본 정보 및 건강 ---
st.header("기본 정보 및 건강 관리")
c1, c2 = st.columns(2)
with c1:
    df_p = pd.DataFrame(MY_DATA["profile"])
    df_p.index = df_p.index + 1
    st.table(df_p)
with c2:
    df_h = pd.DataFrame(MY_DATA["health"])
    df_h.index = df_h.index + 1
    st.table(df_h)

# --- 섹션 2: 재무 정산 (주식/코인 실시간 합산) ---
st.header("재무 관리 매트릭스")
btc_val = int(MY_DATA["assets"]["crypto"]["BTC"] * live["crypto"]["KRW-BTC"])
eth_val = int(MY_DATA["assets"]["crypto"]["ETH"] * live["crypto"]["KRW-ETH"])

# 주식 평가액 계산
stock_rows = []
total_stock_value = 0
for name, info in MY_DATA["assets"]["stocks"].items():
    curr_price = live["stocks"][name]
    val = curr_price * info["count"]
    total_stock_value += val
    stock_rows.append({"종목": name, "수량": info["count"], "현재가": f"{curr_price:,.0f}원", "평가액": f"{val:,.0f}원"})

a1, a2 = st.columns(2)
with a1:
    st.subheader("자산 목록")
    asset_rows = [{"항목": "보유 현금", "금액": MY_DATA['assets']['cash']}]
    for k, v in MY_DATA["assets"]["savings"].items():
        asset_rows.append({"항목": k, "금액": v})
    asset_rows.append({"항목": "주식 총 평가액", "금액": total_stock_value})
    asset_rows.append({"항목": "비트코인 환산", "금액": btc_val})
    asset_rows.append({"항목": "이더리움 환산", "금액": eth_val})
    
    df_a = pd.DataFrame(asset_rows)
    total_a_sum = df_a['금액'].sum()
    df_a_disp = df_a.copy()
    df_a_disp['금액'] = df_a_disp['금액'].apply(lambda x: f"{x:,.0f}원")
    df_a_disp = pd.concat([df_a_disp, pd.DataFrame([{"항목": "총 자산 합계", "금액": f"{total_a_sum:,.0f}원"}])], ignore_index=True)
    df_a_disp.index = df_a_disp.index + 1
    st.table(df_a_disp)

    st.subheader("주식 상세 포트폴리오")
    df_s = pd.DataFrame(stock_rows)
    df_s.index = df_s.index + 1
    st.table(df_s)

with a2:
    st.subheader("부채 목록")
    debt_rows = [{"항목": k, "금액": v} for k, v in MY_DATA["assets"]["liabilities"].items()]
    df_d = pd.DataFrame(debt_rows)
    total_d_sum = df_d['금액'].sum()
    df_d_disp = df_d.copy()
    df_d_disp['금액'] = df_d_disp['금액'].apply(lambda x: f"{x:,.0f}원")
    df_d_disp = pd.concat([df_d_disp, pd.DataFrame([{"항목": "총 부채 합계", "금액": f"{total_d_sum:,.0f}원"}])], ignore_index=True)
    df_d_disp.index = df_d_disp.index + 1
    st.table(df_d_disp)
    
    st.metric("실시간 순자산", f"{total_a_sum - total_d_sum:,.0f}원")

# --- 섹션 3: 생활 관리 및 주방 재고 ---
st.header("생활 주기 및 주방 재고")
l1, l2 = st.columns(2)
with l1:
    life_rows = []
    for item, info in MY_DATA["lifecycle"].items():
        next_d = datetime.strptime(info["last"], "%Y-%m-%d") + timedelta(days=info["period"])
        rem = (next_d - datetime.now()).days
        status = "점검 필요" if rem <= 0 else "정상"
        life_rows.append({"항목
