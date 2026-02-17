import streamlit as st
import pandas as pd
import requests
import json
import re
from datetime import datetime, timedelta

# --- [1. 시스템 설정] ---
SPREADSHEET_ID = '12cPPhM68K3SopQJtZyWEq8adDuP98bJ4efoYbjFDDOI'
GID_MAP = {
    "Log": "0", 
    "Assets": "1068342666", 
    "Inventory": "2138778159", 
    "Pharmacy": "347265850"
}
API_URL = "https://script.google.com/macros/s/AKfycbxmlmMqenbvhLiLbUmI2GEd1sUMpM-NIUytaZ6jGjSL_hZ_4bk8rnDT1Td3wxbdJVBA/exec"
COLOR_PRIMARY = "#4dabf7"

RECOMMENDED = {
    "칼로리": 2200, "단백질": 180, "탄수화물": 280, "지방": 85,
    "식이섬유": 30, "나트륨": 2300, "당류": 50, "콜레스테롤": 300, "수분(ml)": 2000     
}

# --- [2. 핵심 유틸리티] ---
def format_krw(val): 
    return f"{int(val):,}".rjust(15) + " 원"

def to_numeric(val):
    if pd.isna(val) or val == "": return 0
    s = re.sub(r'[^0-9.-]', '', str(val))
    try: return float(s) if '.' in s else int(s)
    except: return 0

# 실시간 코인 시세 획득 (업비트 API)
@st.cache_data(ttl=10) # 10초마다 시세 갱신
def get_upbit_price(ticker):
    try:
        url = f"https://api.upbit.com/v1/ticker?markets=KRW-{ticker}"
        res = requests.get(url, timeout=2)
        return float(res.json()[0]['trade_price'])
    except: return None

@st.cache_data(ttl=600)
def load_sheet_data(gid):
    ts = datetime.now().timestamp()
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={gid}&t={ts}"
    try:
        df = pd.read_csv(url)
        return df.dropna(how='all')
    except: return pd.DataFrame()

def send_to_sheet(payload):
    try:
        res = requests.post(API_URL, data=json.dumps(payload), timeout=10)
        return res.status_code == 200
    except: return False

# --- [3. 초기화 및 UI 설정] ---
st.set_page_config(page_title="JARVIS Prime v65.7", layout="wide")
now = datetime.utcnow() + timedelta(hours=9)

# 데이터 로드 생략 (이전 버전과 동일)
if 'daily_nutri' not in st.session_state:
    st.session_state.daily_nutri = {k: 0.0 for k in RECOMMENDED.keys()}

st.markdown(f"""<style>thead tr th:first-child, tbody th {{ display:none; }} .status-card {{ background-color: #ffffff; padding: 20px; border-radius: 8px; border: 1px solid #dee2e6; border-left: 5px solid {COLOR_PRIMARY}; margin-bottom: 20px; }}</style>""", unsafe_allow_html=True)

# --- [4. 메인 로직] ---
with st.sidebar:
    st.title("자비스 제어 센터")
    menu = st.radio("메뉴 선택", ["자산 관리", "식단 및 건강", "재고 관리"])
    st.divider()
    st.info("사용자: 정원 (실시간 시세 연동 활성화)")

# 1. 자산 관리 모듈 (실시간 연동 강화)
if menu == "자산 관리":
    st.subheader("종합 자산 현황 (실시간 연동)")
    
    df_assets = load_sheet_data(GID_MAP["Assets"])
    if not df_assets.empty:
        df_assets = df_assets.iloc[:, [0, 1]].copy()
        df_assets.columns = ["항목", "금액"]
        
        # 실시간 자산 계산 로직
        realtime_assets = []
        total_val = 0
        
        for _, row in df_assets.iterrows():
            item = row["항목"]
            val_str = str(row["금액"])
            
            # 항목 이름에 코인 심볼이 포함된 경우 (예: BTC, ETH, XRP)
            # 시트에는 'BTC', 금액란에는 보유 수량(예: 0.5)을 적어두면 작동합니다.
            coin_match = re.search(r'(BTC|ETH|XRP|SOL|DOGE)', item.upper())
            if coin_match:
                symbol = coin_match.group(1)
                price = get_upbit_price(symbol)
                qty = to_numeric(val_str)
                if price:
                    current_eval = price * qty
                    realtime_assets.append({"항목": f"{item} (실시간)", "금액": current_eval, "유형": "코인"})
                    total_val += current_eval
                    continue
            
            # 일반 자산/부채
            num_val = to_numeric(val_str)
            realtime_assets.append({"항목": item, "금액": num_val, "유형": "일반"})
            total_val += num_val

        # 상단 대시보드 출력
        st.markdown(f'<div class="status-card"><small>실시간 순자산</small><br><span style="font-size:2.5em; font-weight:bold;">{total_val:,.0f} 원</span></div>', unsafe_allow_html=True)
        
        # 상세 내역 테이블
        df_final = pd.DataFrame(realtime_assets)
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**보유 자산 및 코인 평가액**")
            pos_df = df_final[df_final["금액"] > 0].copy()
            pos_df["금액"] = pos_df["금액"].apply(format_krw)
            st.table(pos_df[["항목", "금액"]])
        with c2:
            st.markdown("**부채 현황**")
            neg_df = df_final[df_final["금액"] < 0].copy()
            neg_df["금액"] = neg_df["금액"].apply(lambda v: format_krw(abs(v)))
            st.table(neg_df[["항목", "금액"]])

# --- [중략: 식단 및 재고 관리 로직은 이전과 동일] ---
# 2. 식단 및 건강 모듈
elif menu == "식단 및 건강":
    st.subheader(f"오늘의 영양 분석 (목표: {RECOMMENDED['칼로리']} kcal)")
    curr = st.session_state.daily_nutri
    
    # 영양소 게이지 출력 (2열 구성)
    items = list(RECOMMENDED.items())
    for i in range(0, len(items), 2):
        cols = st.columns(2)
        for j in range(2):
            if i + j < len(items):
                name, goal = items[i + j]
                val = curr.get(name, 0.0)
                with cols[j]:
                    st.write(f"**{name}**: {val:.1f} / {goal:.1f}")
                    st.progress(min(1.0, val / goal) if goal > 0 else 0.0)
    
    st.divider()
    with st.sidebar:
        st.markdown("**식사 내용 입력**")
        with st.form("diet_form"):
            f_in = {k: st.number_input(k, value=0.0, format="%.1f") for k in RECOMMENDED.keys()}
            if st.form_submit_button("데이터 추가"):
                for k in RECOMMENDED.keys(): st.session_state.daily_nutri[k] += f_in[k]
                st.rerun()
        if st.button("일일 기록 초기화"):
            st.session_state.daily_nutri = {k: 0.0 for k in RECOMMENDED.keys()}; st.rerun()

# 3. 재고 관리 모듈
elif menu == "재고 관리":
    st.subheader("물품 및 재고 관리")
    t1, t2 = st.tabs(["식재료 재고", "상비약 관리"])
    with t1:
        st.session_state.food_df_state = st.data_editor(st.session_state.food_df_state, num_rows="dynamic", use_container_width=True, key="food_editor")
        if st.button("식재료 상태 저장"): st.info("현재 세션에 반영되었습니다.")
    with t2:
        st.session_state.med_df_state = st.data_editor(st.session_state.med_df_state, num_rows="dynamic", use_container_width=True, key="med_editor")
        if st.button("의약품 상태 저장"): st.info("현재 세션에 반영되었습니다.")
