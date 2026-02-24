import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import json
import re
from datetime import datetime, timedelta

# --- [1. 시스템 및 보안 설정] ---
SPREADSHEET_ID = '12cPPhM68K3SopQJtZyWEq8adDuP98bJ4efoYbjFDDOI'
GID_MAP = {
    "log": "0", "assets": "1068342666", "inventory": "2138778159", "pharmacy": "347265850"
}
# Apps Script API URL (기존 URL 유지)
API_URL = "https://script.google.com/macros/s/AKfycbzctUtHI2tRtNRoRRfr06xfTp0W9XkxSI1gHj8JPz_E6ftbidN8o8Lz32VbxjAfGLzj/exec"

# 영양 데이터: 팩트 기반 (인수인계서 원칙 반영)
NUTRITION_DB = {
    "닭가슴살": {"cal": 165, "prot": 31}, "소고기(우둔살)": {"cal": 137, "prot": 22},
    "계란": {"cal": 150, "prot": 12}, "햇반": {"cal": 145, "prot": 3},
    "돼지고기(뒷다리)": {"cal": 185, "prot": 20}
}

# --- [2. 핵심 엔진: 속도 및 정합성 최적화] ---
def to_numeric(val):
    if pd.isna(val) or val == "": return 0.0
    try: return float(re.sub(r'[^0-9.-]', '', str(val)))
    except: return 0.0

@st.cache_data(ttl=300) # 시세 캐시 5분으로 연장 (속도 개선)
def fetch_realtime_prices():
    prices = {}
    # 1. 환율 (금 및 해외 자산 계산용)
    try:
        usdkrw = yf.Ticker("USDKRW=X").fast_info['last_price']
        prices['USD_KRW'] = usdkrw
    except:
        prices['USD_KRW'] = 1350.0 # 폴백
        
    # 2. 코인 (Upbit)
    try:
        coins = requests.get("https://api.upbit.com/v1/ticker?markets=KRW-BTC,KRW-ETH", timeout=2).json()
        for c in coins:
            name = '비트코인' if c['market'] == 'KRW-BTC' else '이더리움'
            prices[name] = c['trade_price']
    except: pass
    
    # 3. 주식 및 금 (yfinance)
    tickers = {
        "삼성전자": "005930.KS", "하이닉스": "000660.KS", 
        "삼성중공업": "010140.KS", "동성화인텍": "033500.KQ", "금": "GC=F"
    }
    for name, code in tickers.items():
        try:
            curr = yf.Ticker(code).fast_info['last_price']
            # 금 시세 계산: (온스당 달러 / 31.1035) * 환율 = g당 한화
            prices[name] = curr if name != "금" else (curr / 31.1035) * prices['USD_KRW']
        except: prices[name] = 0.0
    return prices

def load_sheet_data(gid):
    # 캐시 방지를 위한 타임스탬프 쿼리 포함
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={gid}&t={datetime.now().timestamp()}"
    try: 
        df = pd.read_csv(url)
        return df.dropna(how='all')
    except: return pd.DataFrame()

def send_to_sheet(payload):
    try:
        resp = requests.post(API_URL, data=json.dumps(payload), timeout=10)
        return resp.status_code == 200
    except: return False

# --- [3. 메인 UI 구조] ---
st.set_page_config(page_title="JARVIS v69.5", layout="wide")
rt_prices = fetch_realtime_prices()

with st.sidebar:
    st.title("🛡️ JARVIS v69.5")
    user_name = st.radio("관리자", ["정원", "서진"])
    menu = st.radio("기능 선택", ["📊 통합 자산현황", "📝 자산 거래기록", "🥩 식단/재고 연동", "📦 재고 마스터 편집"])
    st.divider()
    # 핵심 시세 실시간 표시
    st.metric("BTC", f"{rt_prices.get('비트코인', 0):,.0f}원")
    st.metric("환율(USD)", f"{rt_prices.get('USD_KRW', 0):,.2f}원")

# --- [4. 메뉴별 상세 구현] ---

if menu == "📊 통합 자산현황":
    st.subheader("📊 실시간 자산 관리 시스템")
    df_assets = load_sheet_data(GID_MAP["assets"])
    
    if not df_assets.empty:
        # A열: 자산명, B열: 보유량
        final_list = []
        total_sum = 0.0
        
        for _, row in df_assets.iterrows():
            item = str(row.iloc[0])
            qty = to_numeric(row.iloc[1])
            price = rt_prices.get(item, 0.0)
            
            # 현금성 자산인 경우 price가 없으므로 qty 자체가 가치임
            val = price * qty if price > 0 else qty
            final_list.append({"항목": item, "보유량": qty, "현재가/환율": price if price > 0 else 1.0, "평가금액": val})
            total_sum += val
            
        st.metric("총 합계 자산", f"{total_sum:,.0f} 원")
        st.dataframe(pd.DataFrame(final_list), use_container_width=True)

elif menu == "🥩 식단/재고 연동":
    st.subheader("🥩 식단 입력 및 재고 자동 차감")
    df_inv = load_sheet_data(GID_MAP["inventory"])
    
    if not df_inv.empty:
        # 인수인계서 원칙: 고추장/된장 등 엄격 구분 위해 selectbox 사용
        col1, col2 = st.columns([1, 1])
        with col1:
            with st.form("diet_form"):
                # A열(품목) 기반으로 선택
                food_list = df_inv.iloc[:, 0].dropna().unique().tolist()
                selected_food = st.selectbox("사용 식재료", food_list)
                weight = st.number_input("사용량 (g 또는 개)", min_value=0.0, step=1.0)
                
                if st.form_submit_button("식사 기록 및 재고 차감"):
                    info = NUTRITION_DB.get(selected_food, {"cal": 0, "prot": 0})
                    payload = {
                        "action": "diet_with_inventory",
                        "user": user_name,
                        "item": selected_food,
                        "weight": weight,
                        "cal": (info["cal"]/100)*weight,
                        "prot": (info["prot"]/100)*weight,
                        "gid": GID_MAP["inventory"]
                    }
                    if send_to_sheet(payload):
                        st.success(f"✅ {selected_food} {weight} 차감 완료!")
                        st.cache_data.clear()
                        st.rerun()

elif menu == "📦 재고 마스터 편집":
    st.subheader("📦 재고 데이터 직접 수정")
    st.info("⚠️ 이곳의 수정사항은 시트에 즉시 반영됩니다. '환각' 데이터 입력을 주의하세요.")
    df_i = load_sheet_data(GID_MAP["inventory"])
    
    if not df_i.empty:
        # 직접 수정 가능하게 data_editor 사용
        edited_df = st.data_editor(df_i, num_rows="dynamic", use_container_width=True)
        
        if st.button("💾 시트에 최종 저장"):
            # 헤더 포함 전체 데이터 전송
            payload = {
                "action": "overwrite",
                "gid": GID_MAP["inventory"],
                "data": [edited_df.columns.tolist()] + edited_df.values.tolist()
            }
            if send_to_sheet(payload):
                st.success("데이터가 성공적으로 동기화되었습니다.")
                st.cache_data.clear()
                st.rerun()
