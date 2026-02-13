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

st.set_page_config(page_title="자비스 대시보드 v2.2", layout="wide")
st.title("자비스 : 실시간 통합 관리 시스템")

# 숫자 우측 정렬 CSS
st.markdown("""
    <style>
    th {text-align: left !important;}
    td:nth-child(2), td:nth-child(3) {text-align: right !important;}
    </style>
    """, unsafe_allow_html=True)

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

# --- 섹션 2: 재무 정밀 매트릭스 ---
st.header("재무 관리 매트릭스")
prices = get_live_prices()
btc_v = int(MY_DATA["assets"]["crypto"]["BTC"] * prices["KRW-BTC"])
eth_v = int(MY_DATA["assets"]["crypto"]["ETH"] * prices["KRW-ETH"])

a1, a2 = st.columns(2)
with a1:
    st.subheader("자산 목록")
    asset_rows = [{"항목": "보유 현금", "금액": MY_DATA['assets']['cash']}]
    for k, v in MY_DATA["assets"]["savings"].items():
        asset_rows.append({"항목": k, "금액": v})
    asset_rows.append({"항목": "비트코인 환산", "금액": btc_v})
    asset_rows.append({"항목": "이더리움 환산", "금액": eth_v})
    
    df_a = pd.DataFrame(asset_rows)
    total_a = df_a['금액'].sum()
    
    df_a_disp = df_a.copy()
    df_a_disp['금액'] = df_a_disp['금액'].apply(lambda x: f"{x:,.0f}원")
    total_row_a = pd.DataFrame([{"항목": "총 자산 합계", "금액": f"{total_a:,.0f}원"}])
    df_a_disp = pd.concat([df_a_disp, total_row_a], ignore_index=True)
    df_a_disp.index = df_a_disp.index + 1
    st.table(df_a_disp)
    
    st.subheader("주식 포트폴리오")
    df_s = pd.DataFrame(MY_DATA["assets"]["stocks"].items(), columns=['종목', '수량'])
    total_s = df_s['수량'].sum()
    total_row_s = pd.DataFrame([{"종목": "총 보유 수량", "수량": total_s}])
    df_s_disp = pd.concat([df_s, total_row_s], ignore_index=True)
    df_s_disp.index = df_s_disp.index + 1
    st.table(df_s_disp)

with a2:
    st.subheader("부채 목록")
    debt_rows = [{"항목": k, "금액": v} for k, v in MY_DATA["assets"]["liabilities"].items()]
    df_d = pd.DataFrame(debt_rows)
    total_d = df_d['금액'].sum()
    
    df_d_disp = df_d.copy()
    df_d_disp['금액'] = df_d_disp['금액'].apply(lambda x: f"{x:,.0f}원")
    total_row_d = pd.DataFrame([{"항목": "총 부채 합계", "금액": f"{total_d:,.0f}원"}])
    df_d_disp = pd.concat([df_d_disp, total_row_d], ignore_index=True)
    df_d_disp.index = df_d_disp.index + 1
    st.table(df_d_disp)
    
    st.metric("실시간 순자산 (자산-부채)", f"{total_a - total_d:,.0f}원")

# --- 섹션 3: 생활 관리 및 주방 재고 ---
st.header("생활 주기 및 주방 재고")
l1, l2 = st.columns(2)
with l1:
    life_rows = []
    for item, info in MY_DATA["lifecycle"].items():
        next_d = datetime.strptime(info["last"], "%Y-%m-%d") + timedelta(days=info["period"])
        rem = (next_d - datetime.now()).days
        status = "점검 필요" if rem <= 0 else "정상"
        life_rows.append({"항목": item, "상태": status, "남은 일수": f"{rem}일"})
    df_l = pd.DataFrame(life_rows)
    df_l.index = df_l.index + 1
    st.table(df_l)
with l2:
    k_rows = [{"카테고리": k, "내용": v} for k, v in MY_DATA["kitchen"].items()]
    df_k = pd.DataFrame(k_rows)
    df_k.index = df_k.index + 1
    st.table(df_k)

st.caption(f"최근 동기화 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
