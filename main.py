import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import json
import re
from datetime import datetime, timedelta

# --- [1. 시스템 설정 및 영양 DB] ---
SPREADSHEET_ID = '12cPPhM68K3SopQJtZyWEq8adDuP98bJ4efoYbjFDDOI'
GID_MAP = {
    "log": "0", "assets": "1068342666", "inventory": "2138778159", "pharmacy": "347265850"
}
API_URL = "https://script.google.com/macros/s/AKfycbzctUtHI2tRtNRoRRfr06xfTp0W9XkxSI1gHj8JPz_E6ftbidN8o8Lz32VbxjAfGLzj/exec"

# 정원 님 맞춤 영양 DB (100g 기준)
NUTRITION_DB = {
    "닭가슴살": {"cal": 165, "prot": 31}, "소고기(우둔살)": {"cal": 137, "prot": 22},
    "계란": {"cal": 150, "prot": 12}, "햇반": {"cal": 145, "prot": 3},
    "돼지고기(뒷다리)": {"cal": 185, "prot": 20}, "고등어": {"cal": 167, "prot": 19}
}

RECOMMENDED = {"칼로리": 2200, "단백질": 180, "탄수화물": 280, "지방": 85}

# --- [2. 핵심 엔진: 시세 및 데이터] ---
@st.cache_data(ttl=60)
def fetch_realtime_prices():
    prices = {}
    # 코인 (업비트)
    try:
        btc = requests.get("https://api.upbit.com/v1/ticker?markets=KRW-BTC").json()[0]['trade_price']
        eth = requests.get("https://api.upbit.com/v1/ticker?markets=KRW-ETH").json()[0]['trade_price']
        prices.update({'비트코인': btc, '이더리움': eth})
    except: pass
    # 주식/금 (야후 파이낸스)
    tickers = {"삼성전자": "005930.KS", "하이닉스": "000660.KS", "삼성중공업": "010140.KS", "동성화인텍": "033500.KQ", "금": "GC=F"}
    for name, code in tickers.items():
        try:
            curr = yf.Ticker(code).history(period='1d')['Close'].iloc[-1]
            prices[name] = curr if name != "금" else curr * 1350 / 31.1035 # 금 g당 환산
        except: prices[name] = 0
    return prices

def load_sheet_data(gid):
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={gid}"
    try: return pd.read_csv(url).dropna(how='all')
    except: return pd.DataFrame()

def send_to_sheet(payload):
    try: return requests.post(API_URL, data=json.dumps(payload), timeout=10).status_code == 200
    except: return False

def to_numeric(val):
    if pd.isna(val) or val == "": return 0
    try: return float(re.sub(r'[^0-9.-]', '', str(val)))
    except: return 0

# --- [3. 메인 UI 레이아웃] ---
st.set_page_config(page_title="JARVIS v69.0 Multi", layout="wide")
now = datetime.utcnow() + timedelta(hours=9)
rt_prices = fetch_realtime_prices()

with st.sidebar:
    st.title("🛡️ JARVIS v69.0")
    user_name = st.radio("사용자", ["정원", "서진"])
    menu = st.radio("메뉴", ["📈 실시간 자산현황", "🏦 매수/매도 기록", "🍴 스마트 식단", "📦 재고 관리"])
    st.divider()
    st.caption("실시간 주요 시세")
    st.write(f"삼성전자: {rt_prices.get('삼성전자', 0):,.0f}")
    st.write(f"비트코인: {rt_prices.get('비트코인', 0):,.0f}")

# --- [4. 기능 구현] ---

if menu == "📈 실시간 자산현황":
    st.subheader(f"📊 {user_name} & 서진 통합 자산")
    df_assets = load_sheet_data(GID_MAP["assets"])
    if not df_assets.empty:
        total_sum, final_list = 0, []
        for _, row in df_assets.iterrows():
            item, qty = str(row[0]), to_numeric(row[1])
            price = rt_prices.get(item, 0)
            val = price * qty if price > 0 else qty
            final_list.append({"항목": item, "수량": qty, "평가금액": val})
            total_sum += val
        st.metric("실시간 총 자산", f"{total_sum:,.0f} 원")
        st.table(pd.DataFrame(final_list).assign(평가금액=lambda x: x["평가금액"].apply(lambda v: f"{int(v):,} 원")))

elif menu == "🏦 매수/매도 기록":
    st.subheader("주식/코인 트레이딩")
    with st.form("trade_form"):
        t_type = st.selectbox("구분", ["매수", "매도"])
        t_item = st.selectbox("종목", ["삼성전자", "하이닉스", "삼성중공업", "동성화인텍", "비트코인", "이더리움", "금"])
        t_qty = st.number_input("수량", min_value=0.0, step=0.01)
        if st.form_submit_button("기록 전송"):
            if send_to_sheet({"action": "trade", "user": user_name, "type": t_type, "item": t_item, "qty": t_qty, "asset_gid": GID_MAP["assets"]}):
                st.success("거래 완료!"); st.rerun()

elif menu == "🍴 스마트 식단":
    st.subheader("🍴 영양 분석 및 재고 연동")
    df_inv = load_sheet_data(GID_MAP["inventory"])
    if not df_inv.empty:
        col1, col2 = st.columns(2)
        with col1:
            with st.form("diet_form"):
                food = st.selectbox("품목 선택", df_inv.iloc[:, 0].tolist())
                weight = st.number_input("사용량 (g)", min_value=0, step=10)
                if st.form_submit_button("식사 기록"):
                    info = NUTRITION_DB.get(food, {"cal": 0, "prot": 0})
                    cal_t, prot_t = (info["cal"]/100)*weight, (info["prot"]/100)*weight
                    payload = {"action": "diet_with_inventory", "user": user_name, "item": food, "weight": weight, "cal": cal_t, "prot": prot_t, "gid": GID_MAP["inventory"]}
                    if send_to_sheet(payload):
                        st.success(f"{food} 차감 & 단백질 {prot_t:.1f}g 추가!"); st.rerun()
        with col2:
            st.write("#### 오늘의 목표")
            st.progress(0.6) # 예시 데이터
            st.caption("단백질 180g 목표 진행 중...")

elif menu == "📦 재고 관리":
    st.subheader("📦 재고 편집")
    tab1, tab2 = st.tabs(["식재료", "상비약"])
    with tab1:
        df_i = load_sheet_data(GID_MAP["inventory"])
        if not df_i.empty:
            ed_i = st.data_editor(df_i, num_rows="dynamic", key="inv_ed")
            if st.button("식재료 저장"):
                if send_to_sheet({"action": "overwrite", "gid": GID_MAP["inventory"], "data": [ed_i.columns.tolist()] + ed_i.values.tolist()}):
                    st.success("저장 완료!"); st.rerun()
    with tab2:
        df_p = load_sheet_data(GID_MAP["pharmacy"])
        if not df_p.empty:
            ed_p = st.data_editor(df_p, num_rows="dynamic", key="pha_ed")
            if st.button("상비약 저장"):
                if send_to_sheet({"action": "overwrite", "gid": GID_MAP["pharmacy"], "data": [ed_p.columns.tolist()] + ed_p.values.tolist()}):
                    st.success("저장 완료!"); st.rerun()
