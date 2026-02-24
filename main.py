import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import json
import re
from datetime import datetime, timedelta

# --- [1. 시스템 설정] ---
SPREADSHEET_ID = '12cPPhM68K3SopQJtZyWEq8adDuP98bJ4efoYbjFDDOI'
GID_MAP = {
    "log": "0", "assets": "1068342666", "inventory": "2138778159", "pharmacy": "347265850"
}
# 배포된 최신 URL을 사용하세요!
API_URL = "https://script.google.com/macros/s/AKfycbzctUtHI2tRtNRoRRfr06xfTp0W9XkxSI1gHj8JPz_E6ftbidN8o8Lz32VbxjAfGLzj/exec"

NUTRITION_DB = {
    "닭가슴살": {"cal": 165, "prot": 31}, "소고기(우둔살)": {"cal": 137, "prot": 22},
    "계란": {"cal": 150, "prot": 12}, "햇반": {"cal": 145, "prot": 3},
    "돼지고기(뒷다리)": {"cal": 185, "prot": 20}
}
RECOMMENDED = {"칼로리": 2200, "단백질": 180, "탄수화물": 280, "지방": 85}

# --- [2. 핵심 유틸리티] ---
def to_numeric(val):
    if pd.isna(val) or val == "": return 0.0
    try: return float(re.sub(r'[^0-9.-]', '', str(val)))
    except: return 0.0

@st.cache_data(ttl=60)
def fetch_realtime_prices():
    prices = {}
    try: # 코인
        btc = requests.get("https://api.upbit.com/v1/ticker?markets=KRW-BTC", timeout=2).json()[0]['trade_price']
        eth = requests.get("https://api.upbit.com/v1/ticker?markets=KRW-ETH", timeout=2).json()[0]['trade_price']
        prices.update({'비트코인': btc, '이더리움': eth})
    except: pass
    
    tickers = {"삼성전자": "005930.KS", "하이닉스": "000660.KS", "삼성중공업": "010140.KS", "동성화인텍": "033500.KQ", "금": "GC=F"}
    for name, code in tickers.items():
        try:
            curr = yf.Ticker(code).history(period='1d')['Close'].iloc[-1]
            prices[name] = curr if name != "금" else curr * 1350 / 31.1035
        except: prices[name] = 0.0
    return prices

def load_sheet_data(gid):
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={gid}&t={datetime.now().timestamp()}"
    try: return pd.read_csv(url).dropna(how='all')
    except: return pd.DataFrame()

def send_to_sheet(payload):
    try: return requests.post(API_URL, data=json.dumps(payload), timeout=10).status_code == 200
    except: return False

# --- [3. UI 설정] ---
st.set_page_config(page_title="JARVIS v69.2 Final", layout="wide")
now = datetime.utcnow() + timedelta(hours=9)
rt_prices = fetch_realtime_prices()

with st.sidebar:
    st.title("🛡️ JARVIS Final")
    user_name = st.radio("사용자", ["정원", "서진"])
    menu = st.radio("메뉴", ["📈 실시간 자산현황", "🏦 매수/매도 기록", "🍴 스마트 식단", "📦 재고 관리"])
    st.divider()
    st.write(f"비트코인: {rt_prices.get('비트코인', 0):,.0f}원")

# --- [4. 메뉴별 구현] ---
if menu == "📈 실시간 자산현황":
    st.subheader(f"📊 {user_name} & 서진 통합 자산")
    df_assets = load_sheet_data(GID_MAP["assets"])
    if not df_assets.empty:
        total_sum, final_list = 0.0, []
        for _, row in df_assets.iterrows():
            item, qty = str(row.iloc[0]), to_numeric(row.iloc[1])
            price = rt_prices.get(item, 0.0)
            val = price * qty if price > 0 else qty
            if item != "nan":
                final_list.append({"항목": item, "수량/금액": qty, "평가금액": val})
                total_sum += val
        st.metric("실시간 총 자산", f"{total_sum:,.0f} 원")
        st.table(pd.DataFrame(final_list).style.format({"수량/금액": "{:,.2f}", "평가금액": "{:,.0f} 원"}))

elif menu == "🏦 매수/매도 기록":
    st.subheader("🏦 자산 이동 기록")
    with st.form("trade_form"):
        t_type = st.selectbox("구분", ["매수", "매도"])
        t_item = st.selectbox("종목", ["삼성전자", "하이닉스", "삼성중공업", "동성화인텍", "비트코인", "이더리움", "금"])
        t_qty = st.number_input("거래 수량", min_value=0.0, step=0.01)
        t_price = st.number_input("거래 단가", min_value=0)
        if st.form_submit_button("거래 전송"):
            payload = {"action": "trade", "user": user_name, "type": t_type, "item": t_item, "qty": t_qty, "price": t_price, "asset_gid": GID_MAP["assets"]}
            if send_to_sheet(payload):
                st.success("거래가 반영되었습니다!"); st.cache_data.clear(); st.rerun()

elif menu == "🍴 스마트 식단":
    st.subheader("🍴 식단 및 재고 연동")
    df_inv = load_sheet_data(GID_MAP["inventory"])
    if not df_inv.empty:
        col1, col2 = st.columns(2)
        with col1:
            with st.form("diet_form"):
                food = st.selectbox("품목 선택", df_inv.iloc[:, 0].tolist())
                weight = st.number_input("사용량 (g)", min_value=0, step=10)
                if st.form_submit_button("식사 완료"):
                    info = NUTRITION_DB.get(food, {"cal": 0, "prot": 0})
                    cal_t, prot_t = (info["cal"]/100)*weight, (info["prot"]/100)*weight
                    payload = {"action": "diet_with_inventory", "user": user_name, "item": food, "weight": weight, "cal": cal_t, "prot": prot_t, "gid": GID_MAP["inventory"]}
                    if send_to_sheet(payload):
                        st.success("식단 기록 및 재고 차감 완료!"); st.cache_data.clear(); st.rerun()
        with col2:
            st.write("#### 오늘의 단백질 목표")
            # 시트에서 오늘 기록된 단백질 합계를 읽어오는 로직으로 보강 가능
            st.progress(min(1.0, 0.5)) # 시각적 피드백 유지

elif menu == "📦 재고 관리":
    st.subheader("📦 실시간 재고 편집")
    df_i = load_sheet_data(GID_MAP["inventory"])
    if not df_i.empty:
        ed_i = st.data_editor(df_i, num_rows="dynamic", use_container_width=True, key="inv_ed_final")
        if st.button("변경사항 시트에 최종 저장"):
            if send_to_sheet({"action": "overwrite", "gid": GID_MAP["inventory"], "data": [ed_i.columns.tolist()] + ed_i.values.tolist()}):
                st.success("재고 데이터 동기화 완료!"); st.cache_data.clear(); st.rerun()
