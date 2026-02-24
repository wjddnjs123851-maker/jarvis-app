import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import json
import re
from datetime import datetime, timedelta

# --- [1. 시스템 설정] ---
st.set_page_config(page_title="JARVIS v70.0", layout="wide")

SPREADSHEET_ID = '12cPPhM68K3SopQJtZyWEq8adDuP98bJ4efoYbjFDDOI'
GID_MAP = {"log": "0", "assets": "1068342666", "inventory": "2138778159", "pharmacy": "347265850"}
API_URL = "https://script.google.com/macros/s/AKfycbzctUtHI2tRtNRoRRfr06xfTp0W9XkxSI1gHj8JPz_E6ftbidN8o8Lz32VbxjAfGLzj/exec"

# --- [2. 시세 및 데이터 엔진] ---
@st.cache_data(ttl=300)
def fetch_market():
    data = {}
    try:
        # 환율 및 금
        yf_data = yf.Tickers("USDKRW=X GC=F")
        rate = yf_data.tickers["USDKRW=X"].fast_info['last_price']
        data['USD_KRW'] = rate
        data['금'] = (yf_data.tickers["GC=F"].fast_info['last_price'] / 31.1035) * rate
        # 주식 (삼성전자, 하이닉스, 삼성중공업, 동성화인텍)
        for n, c in {"삼성전자":"005930.KS", "하이닉스":"000660.KS", "삼성중공업":"010140.KS", "동성화인텍":"033500.KQ"}.items():
            data[n] = yf.Ticker(c).fast_info['last_price']
        # 코인 (업비트)
        c_res = requests.get("https://api.upbit.com/v1/ticker?markets=KRW-BTC,KRW-ETH").json()
        data['비트코인'], data['이더리움'] = c_res[0]['trade_price'], c_res[1]['trade_price']
    except: pass
    return data

def load_data(gid):
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={gid}&t={datetime.now().timestamp()}"
    return pd.read_csv(url).dropna(how='all')

def parse_num(v):
    if pd.isna(v): return 0.0
    found = re.findall(r"[-+]?\d*\.\d+|\d+", str(v))
    return float(found[0]) if found else 0.0

# --- [3. 메인 화면] ---
market = fetch_market()
st.sidebar.title("🛡️ JARVIS v70.0")
user = st.sidebar.radio("사용자", ["정원", "서진"])
menu = st.sidebar.selectbox("메뉴", ["📊 통합 자산", "🥩 식단-재고 차감", "💊 약 보관함", "💾 마스터 편집"])

if menu == "📊 통합 자산":
    df = load_data(GID_MAP["assets"])
    res, total = [], 0.0
    for _, r in df.iterrows():
        name, qty = str(r.iloc[0]), parse_num(r.iloc[1])
        price = market.get(name, 0.0)
        val = price * qty if price > 0 else qty
        res.append({"항목": name, "수량": qty, "현재가": price if price > 0 else "-", "평가금액": val})
        total += val
    st.metric("총 자산", f"{total:,.0f} 원")
    st.dataframe(pd.DataFrame(res), use_container_width=True)

elif menu == "🥩 식단-재고 연동":
    df_i = load_data(GID_MAP["inventory"])
    items = df_i.iloc[:, 1].dropna().unique().tolist()
    with st.form("diet"):
        sel = st.selectbox("재료", items)
        amt = st.number_input("사용량", min_value=0.0)
        if st.form_submit_button("차감"):
            requests.post(API_URL, data=json.dumps({"action":"diet_with_inventory","user":user,"item":sel,"weight":amt,"gid":GID_MAP["inventory"]}))
            st.success("반영됨"); st.rerun()

elif menu == "💊 약 보관함":
    df_p = load_data(GID_MAP["pharmacy"])
    st.dataframe(df_p, use_container_width=True)

elif menu == "💾 마스터 편집":
    target = st.selectbox("시트", ["inventory", "pharmacy", "assets"])
    edited = st.data_editor(load_data(GID_MAP[target]), num_rows="dynamic", use_container_width=True)
    if st.button("저장"):
        requests.post(API_URL, data=json.dumps({"action":"overwrite","gid":GID_MAP[target],"data":[edited.columns.tolist()]+edited.values.tolist()}))
        st.success("동기화 완료"); st.rerun()import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import json
import re
from datetime import datetime, timedelta

# --- [1. 시스템 설정] ---
st.set_page_config(page_title="JARVIS v70.0", layout="wide")

SPREADSHEET_ID = '12cPPhM68K3SopQJtZyWEq8adDuP98bJ4efoYbjFDDOI'
GID_MAP = {"log": "0", "assets": "1068342666", "inventory": "2138778159", "pharmacy": "347265850"}
API_URL = "https://script.google.com/macros/s/AKfycbzctUtHI2tRtNRoRRfr06xfTp0W9XkxSI1gHj8JPz_E6ftbidN8o8Lz32VbxjAfGLzj/exec"

# --- [2. 시세 및 데이터 엔진] ---
@st.cache_data(ttl=300)
def fetch_market():
    data = {}
    try:
        # 환율 및 금
        yf_data = yf.Tickers("USDKRW=X GC=F")
        rate = yf_data.tickers["USDKRW=X"].fast_info['last_price']
        data['USD_KRW'] = rate
        data['금'] = (yf_data.tickers["GC=F"].fast_info['last_price'] / 31.1035) * rate
        # 주식 (삼성전자, 하이닉스, 삼성중공업, 동성화인텍)
        for n, c in {"삼성전자":"005930.KS", "하이닉스":"000660.KS", "삼성중공업":"010140.KS", "동성화인텍":"033500.KQ"}.items():
            data[n] = yf.Ticker(c).fast_info['last_price']
        # 코인 (업비트)
        c_res = requests.get("https://api.upbit.com/v1/ticker?markets=KRW-BTC,KRW-ETH").json()
        data['비트코인'], data['이더리움'] = c_res[0]['trade_price'], c_res[1]['trade_price']
    except: pass
    return data

def load_data(gid):
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={gid}&t={datetime.now().timestamp()}"
    return pd.read_csv(url).dropna(how='all')

def parse_num(v):
    if pd.isna(v): return 0.0
    found = re.findall(r"[-+]?\d*\.\d+|\d+", str(v))
    return float(found[0]) if found else 0.0

# --- [3. 메인 화면] ---
market = fetch_market()
st.sidebar.title("🛡️ JARVIS v70.0")
user = st.sidebar.radio("사용자", ["정원", "서진"])
menu = st.sidebar.selectbox("메뉴", ["📊 통합 자산", "🥩 식단-재고 차감", "💊 약 보관함", "💾 마스터 편집"])

if menu == "📊 통합 자산":
    df = load_data(GID_MAP["assets"])
    res, total = [], 0.0
    for _, r in df.iterrows():
        name, qty = str(r.iloc[0]), parse_num(r.iloc[1])
        price = market.get(name, 0.0)
        val = price * qty if price > 0 else qty
        res.append({"항목": name, "수량": qty, "현재가": price if price > 0 else "-", "평가금액": val})
        total += val
    st.metric("총 자산", f"{total:,.0f} 원")
    st.dataframe(pd.DataFrame(res), use_container_width=True)

elif menu == "🥩 식단-재고 연동":
    df_i = load_data(GID_MAP["inventory"])
    items = df_i.iloc[:, 1].dropna().unique().tolist()
    with st.form("diet"):
        sel = st.selectbox("재료", items)
        amt = st.number_input("사용량", min_value=0.0)
        if st.form_submit_button("차감"):
            requests.post(API_URL, data=json.dumps({"action":"diet_with_inventory","user":user,"item":sel,"weight":amt,"gid":GID_MAP["inventory"]}))
            st.success("반영됨"); st.rerun()

elif menu == "💊 약 보관함":
    df_p = load_data(GID_MAP["pharmacy"])
    st.dataframe(df_p, use_container_width=True)

elif menu == "💾 마스터 편집":
    target = st.selectbox("시트", ["inventory", "pharmacy", "assets"])
    edited = st.data_editor(load_data(GID_MAP[target]), num_rows="dynamic", use_container_width=True)
    if st.button("저장"):
        requests.post(API_URL, data=json.dumps({"action":"overwrite","gid":GID_MAP[target],"data":[edited.columns.tolist()]+edited.values.tolist()}))
        st.success("동기화 완료"); st.rerun()
