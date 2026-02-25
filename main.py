import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import json
import re
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- [1. 시스템 설정] ---
st.set_page_config(page_title="JARVIS v75.1 Pro", layout="wide")

API_URL = "https://script.google.com/macros/s/AKfycbw93B0RE2aeYBMDKKL0kyKHKc7c1mmUAe2QkSo-rENECvGD7xHS-0uSBwaOttyFLuwy/exec"
SPREADSHEET_ID = '12cPPhM68K3SopQJtZyWEq8adDuP98bJ4efoYbjFDDOI'
GID_MAP = {"log": "0", "assets": "1068342666", "inventory": "2138778159", "pharmacy": "347265850"}

# 2000kcal 기준 정원님 맞춤 목표
GOALS = {"칼로리": 2000, "탄수화물": 150, "단백질": 150, "지방": 60, "당류": 30, "나트륨": 2000, "콜레스테롤": 300, "식이섬유": 25}

# --- [2. 핵심 엔진] ---
@st.cache_data(ttl=300)
def fetch_market():
    data = {}
    try:
        yf_data = yf.Tickers("USDKRW=X GC=F 005930.KS 000660.KS 010140.KS 033500.KQ")
        rate = yf_data.tickers["USDKRW=X"].fast_info['last_price']
        data.update({'USD_KRW': rate, '금(16g)': (yf_data.tickers["GC=F"].fast_info['last_price'] / 31.1035) * rate})
        stocks = {"삼성전자":"005930.KS", "SK하이닉스":"000660.KS", "삼성중공업":"010140.KS", "동성화인텍":"033500.KQ"}
        for n, c in stocks.items(): data[n] = yf_data.tickers[c].fast_info['last_price']
        c_res = requests.get("https://api.upbit.com/v1/ticker?markets=KRW-BTC,KRW-ETH", timeout=5).json()
        data.update({'비트코인(BTC)': c_res[0]['trade_price'], '이더리움(ETH)': c_res[1]['trade_price']})
    except: pass
    return data

def load_data(gid):
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={gid}&t={datetime.now().timestamp()}"
    try:
        df = pd.read_csv(url)
        return df.dropna(how='all').reset_index(drop=True)
    except: return pd.DataFrame()

def safe_float(v):
    if pd.isna(v) or v == "": return 0.0
    try:
        if isinstance(v, str):
            nums = re.findall(r"[-+]?\d*\.\d+|\d+", v.replace(',', ''))
            return float(nums[0]) if nums else 0.0
        return float(v)
    except: return 0.0

# --- [3. 메인 인터페이스] ---
market = fetch_market()
st.sidebar.title("🛡️ JARVIS v75.1")
active_user = st.sidebar.radio("사용자", ["정원", "서진"])
menu = st.sidebar.selectbox("메뉴", ["📊 통합 자산 리포트", "🥩 99kg 다이어트 보드", "💸 가계부 내역", "💊 상비약 관리", "⚙️ 시스템 관리"])

if menu == "📊 통합 자산 리포트":
    st.subheader(f"📊 {active_user}님 재무 상태 분석")
    df_a = load_data(GID_MAP["assets"])
    
    if not df_a.empty:
        asset_list, debt_list = [], []
        total_asset, total_debt = 0.0, 0.0
        
        for _, r in df_a.iterrows():
            name, qty = str(r.iloc[0]), safe_float(r.iloc[1])
            price = market.get(name, 0.0)
            val = price * qty if price > 0 else qty
            
            if val >= 0:
                asset_list.append({"항목": name, "평가액": val})
                total_asset += val
            else:
                debt_list.append({"항목": name, "금액": val})
                total_debt += val
        
        # 상단 요약 지표
        c1, c2, c3 = st.columns(3)
        c1.metric("총 자산", f"{total_asset:,.0f} 원")
        c2.metric("총 부채", f"{abs(total_debt):,.0f} 원", delta_color="inverse")
        c3.metric("순자산", f"{(total_asset + total_debt):,.0f} 원")
        
        # 시각화
        st.write("### 📈 자산 vs 부채 구성")
        fig = go.Figure(data=[
            go.Bar(name='자산', x=['금액'], y=[total_asset], marker_color='blue'),
            go.Bar(name='부채', x=['금액'], y=[abs(total_debt)], marker_color='red')
        ])
        fig.update_layout(barmode='group', height=350)
        st.plotly_chart(fig, use_container_width=True)
        
        col_left, col_right = st.columns(2)
        with col_left:
            st.write("🔵 **자산 상세**")
            st.dataframe(pd.DataFrame(asset_list), use_container_width=True)
        with col_right:
            st.write("🔴 **부채 상세**")
            st.dataframe(pd.DataFrame(debt_list), use_container_width=True)

elif menu == "🥩 99kg 다이어트 보드":
    st.subheader("🔥 결혼식 목표 99kg 추적")
    # (식단 로직 생략 - v75.0과 동일)
    st.info("오늘 섭취한 영양 성분과 재고를 연동합니다.")

elif menu == "💸 가계부 내역":
    st.subheader("💸 수입/지출 로그")
    st.table(load_data(GID_MAP["log"]).tail(10))

elif menu == "💊 상비약 관리":
    st.subheader("💊 의약품 안전 관리")
    df_p = load_data(GID_MAP["pharmacy"])
    if not df_p.empty:
        df_p['유통/소비기한'] = pd.to_datetime(df_p.iloc[:, 3], errors='coerce')
        st.dataframe(df_p.sort_values('유통/소비기한'), use_container_width=True)

elif menu == "⚙️ 시스템 관리":
    st.subheader("⚙️ 데이터베이스 편집")
    target = st.selectbox("편집 대상", ["assets", "inventory", "pharmacy", "log"])
    df_m = load_data(GID_MAP[target])
    edited = st.data_editor(df_m, num_rows="dynamic", use_container_width=True)
    if st.button("💾 클라우드 저장"):
        payload = {"action": "overwrite", "gid": GID_MAP[target], "data": [edited.columns.tolist()] + edited.values.tolist()}
        requests.post(API_URL, data=json.dumps(payload))
        st.success("저장 완료!"); st.rerun()
