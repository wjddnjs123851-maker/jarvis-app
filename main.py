import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# 1. 마스터 데이터 (보스의 고정 자산)
FIXED_DATA = {
    "savings": {"청년도약계좌": 14700000, "주택청약": 2540000, "전세보증금(총액)": 145850000},
    "liabilities": {"전세대출": 100000000, "마이너스통장": 3000000, "학자금대출": 1247270},
    "stocks": {
        "삼성전자": {"code": "005930", "count": 46},
        "SK하이닉스": {"code": "000660", "count": 6},
        "삼성중공업": {"code": "010140", "count": 88},
        "동성화인텍": {"code": "033500", "count": 21}
    },
    "crypto": {"BTC": 0.00181400, "ETH": 0.03417393}
}

# 2. 실시간 변동 데이터 유지 (세션 상태)
if 'cash' not in st.session_state: st.session_state.cash = 492918
if 'consumed_cal' not in st.session_state: st.session_state.consumed_cal = 0
if 'last_meal' not in st.session_state: st.session_state.last_meal = "미입력"

def get_live_prices():
    prices = {"crypto": {"KRW-BTC": 95000000, "KRW-ETH": 3800000}, "stocks": {}}
    try:
        res = requests.get("https://api.upbit.com/v1/ticker?markets=KRW-BTC,KRW-ETH", timeout=3).json()
        for c in res: prices["crypto"][c['market']] = int(c['trade_price'])
    except: pass
    for name, info in FIXED_DATA["stocks"].items():
        try:
            url = f"https://polling.finance.naver.com/api/realtime?query=SERVICE_ITEM:{info['code']}"
            res = requests.get(url, timeout=3).json()
            prices["stocks"][name] = int(res['result']['areas'][0]['datas'][0]['nv'])
        except: prices["stocks"][name] = 0
    return prices

st.set_page_config(page_title="자비스 v2.8", layout="wide")

# --- 사이드바: 실시간 입력창 ---
with st.sidebar.form("input_panel"):
    st.header("오늘의 기록")
    expense = st.number_input("지출 금액(원)", min_value=0, step=100)
    cal = st.number_input("식사 칼로리(kcal)", min_value=0, step=50)
    meal = st.text_input("식사 메뉴", placeholder="예: 더블쿼터파운더 세트")
    
    if st.form_submit_button("데이터 반영"):
        st.session_state.cash -= expense
        st.session_state.consumed_cal += cal
        st.session_state.last_meal = meal
        st.sidebar.success("성공적으로 반영되었습니다.")

st.title("자비스 : 실시간 통합 관리 시스템")

# CSS: 정렬 및 줄바꿈
st.markdown("""<style>td:nth-child(2), td:nth-child(3), td:nth-child(4) {text-align: right !important;}</style>""", unsafe_allow_html=True)

live = get_live_prices()

# --- 섹션 1: 재무 관리 (복구 완료) ---
st.header("재무 관리 매트릭스")
btc_v = int(FIXED_DATA["crypto"]["BTC"] * live["crypto"]["KRW-BTC"])
eth_v = int(FIXED_DATA["crypto"]["ETH"] * live["crypto"]["KRW-ETH"])

stock_rows = []
total_stock_val = 0
for name, info in FIXED_DATA["stocks"].items():
    p = live["stocks"].get(name, 0)
    v = p * info["count"]
    total_stock_val += v
    stock_rows.append({"종목": name, "수량": info["count"], "현재가": f"{p:,.0f}원", "평가액": f"{v:,.0f}원"})

c1, c2 = st.columns(2)
with c1:
    st.subheader("자산 목록")
    asset_list = [{"항목": "보유 현금", "금액": st.session_state.cash}]
    for k, v in FIXED_DATA["savings"].items(): asset_list.append({"항목": k, "금액": v})
    asset_list.append({"항목": "주식 평가액", "금액": total_stock_val})
    asset_list.append({"항목": "코인 환산액", "금액": btc_v + eth_v})
    
    df_a = pd.DataFrame(asset_list)
    total_a = df_a['금액'].sum()
    df_a_disp = df_a.copy()
    df_a_disp['금액'] = df_a_disp['금액'].apply(lambda x: f"{x:,.0f}원")
    df_a_disp = pd.concat([df_a_disp, pd.DataFrame([{"항목": "총 자산 합계", "금액": f"{total_a:,.0f}원"}])], ignore_index=True)
    df_a_disp.index += 1
    st.table(df_a_disp)

with c2:
    st.subheader("부채 목록")
    debt_list = [{"항목": k, "금액": v} for k, v in FIXED_DATA["liabilities"].items()]
    df_d = pd.DataFrame(debt_list)
    total_d = df_d['금액'].sum()
    df_d_disp = df_d.copy()
    df_d_disp['금액'] = df_d_disp['금액
