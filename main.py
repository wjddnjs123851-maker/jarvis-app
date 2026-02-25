import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import json
import re
from datetime import datetime

# --- [1. 시스템 설정] ---
st.set_page_config(page_title="JARVIS v76.0", layout="wide")

API_URL = "https://script.google.com/macros/s/AKfycbw93B0RE2aeYBMDKKL0kyKHKc7c1mmUAe2QkSo-rENECvGD7xHS-0uSBwaOttyFLuwy/exec"
SPREADSHEET_ID = '12cPPhM68K3SopQJtZyWEq8adDuP98bJ4efoYbjFDDOI'
GID_MAP = {"log": "0", "assets": "1068342666", "inventory": "2138778159", "pharmacy": "347265850"}

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
        df = pd.read_csv(url).dropna(how='all')
        df.index = range(1, len(df) + 1) # 모든 메뉴 순번 1번부터 시작
        return df
    except: return pd.DataFrame()

def safe_float(v):
    if pd.isna(v) or v == "": return 0.0
    try:
        if isinstance(v, str):
            nums = re.findall(r"[-+]?\d*\.\d+|\d+", v.replace(',', ''))
            return float(nums[0]) if nums else 0.0
        return float(v)
    except: return 0.0

def get_nutri(food, weight):
    db = {"냉동큐브닭가슴살": [165, 0, 31, 3.6, 0, 45, 85, 0], "계란": [150, 1, 12, 10, 1, 130, 370, 0], "햇반": [145, 33, 3, 0.5, 0, 5, 0, 1]}
    base = db.get(food, [120, 15, 10, 5, 2, 150, 20, 1])
    return [round((v * weight / 100), 1) for v in base]

# --- [3. 사이드바 메뉴 및 통합 입력창] ---
market = fetch_market()
with st.sidebar:
    st.title("🛡️ JARVIS v76.0")
    menu = st.radio("메뉴 선택", ["📊 자산 현황", "🥩 식단/재고 관리", "💸 가계부 내역", "💊 의약품 보관함"])
    st.divider()
    st.subheader("➕ 통합 입력창")
    if menu == "🥩 식단/재고 관리":
        df_inv_list = load_data(GID_MAP["inventory"])
        food_sel = st.selectbox("식재료 선택", df_inv_list.iloc[:, 1].tolist())
        weight_in = st.number_input("섭취량(g/개)", min_value=0.0, step=10.0)
        if st.button("섭취 기록"):
            nutri = get_nutri(food_sel, weight_in)
            requests.post(API_URL, data=json.dumps({"action":"diet_with_inventory","gid":GID_MAP["inventory"],"item":food_sel,"weight":weight_in,"user":"정원"}))
            st.success(f"{food_sel} 반영됨"); st.rerun()
    else:
        st.info("각 메뉴 하단 편집기에서 데이터를 직접 수정/추가하세요.")

# --- [4. 메인 기능 구현] ---
def show_editor(gid):
    df = load_data(gid)
    edited = st.data_editor(df, num_rows="dynamic", use_container_width=True, key=f"editor_{gid}")
    if st.button("💾 변경사항 저장", key=f"btn_{gid}"):
        data = [edited.columns.tolist()] + edited.values.tolist()
        requests.post(API_URL, data=json.dumps({"action":"overwrite","gid":gid,"data":data}))
        st.success("시트 동기화 완료"); st.rerun()

if menu == "📊 자산 현황":
    st.header("📊 실시간 자산 및 부채 리포트")
    df_a = load_data(GID_MAP["assets"])
    if not df_a.empty:
        total_a, total_d = 0.0, 0.0
        res = []
        for _, r in df_a.iterrows():
            name, qty = str(r.iloc[0]), safe_float(r.iloc[1])
            price = market.get(name, 0.0)
            val = price * qty if price > 0 else qty
            if val >= 0: total_a += val
            else: total_d += val
            res.append({"항목": name, "수량/금액": qty, "평가액": val})
        
        c1, c2, c3 = st.columns(3)
        c1.metric("총 자산", f"{total_a:,.0f}원")
        c2.metric("총 부채", f"{abs(total_d):,.0f}원")
        c3.metric("순자산", f"{(total_a + total_d):,.0f}원")
        st.dataframe(pd.DataFrame(res), use_container_width=True)
    st.divider(); st.subheader("⚙️ 데이터 편집"); show_editor(GID_MAP["assets"])

elif menu == "🥩 식단/재고 관리":
    st.header("🥩 식재료 재고 및 영양분 섭취 현황")
    df_inv = load_data(GID_MAP["inventory"])
    st.write("### 📦 현재 재고 목록")
    st.dataframe(df_inv.iloc[:, [1, 2, 4]], use_container_width=True)
    st.divider(); st.subheader("⚙️ 재고 마스터 편집"); show_editor(GID_MAP["inventory"])

elif menu == "💸 가계부 내역":
    st.header("💸 가계부 지출/수입 내역")
    show_editor(GID_MAP["log"])

elif menu == "💊 의약품 보관함":
    st.header("💊 상비약 유효기한 관리")
    df_p = load_data(GID_MAP["pharmacy"])
    # 날짜 정렬 후 순번 재부여
    df_p['유통/소비기한'] = pd.to_datetime(df_p.iloc[:, 3], errors='coerce')
    df_p = df_p.sort_values('유통/소비기한').reset_index(drop=True)
    df_p.index = range(1, len(df_p) + 1)
    st.dataframe(df_p, use_container_width=True)
    st.divider(); st.subheader("⚙️ 의약품 데이터 편집"); show_editor(GID_MAP["pharmacy"])
