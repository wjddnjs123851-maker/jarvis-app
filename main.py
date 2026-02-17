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

def extract_quantity(text):
    """비고란의 '보유량 0.001814개'에서 숫자 추출"""
    if pd.isna(text): return None
    match = re.search(r"([0-9]*\.[0-9]+|[0-9]+)", str(text))
    return float(match.group(1)) if match else None

@st.cache_data(ttl=15)
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

# --- [3. UI 설정] ---
st.set_page_config(page_title="JARVIS Prime v65.9", layout="wide")
now = datetime.utcnow() + timedelta(hours=9)

st.markdown(f"""<style>thead tr th:first-child, tbody th {{ display:none; }} .status-card {{ background-color: #ffffff; padding: 20px; border-radius: 8px; border: 1px solid #dee2e6; border-left: 5px solid {COLOR_PRIMARY}; margin-bottom: 20px; }}</style>""", unsafe_allow_html=True)

# --- [4. 사이드바 메뉴] ---
with st.sidebar:
    st.title("자비스 제어 센터")
    menu = st.radio("메뉴 선택", ["자산 관리", "식단 및 건강", "재고 관리"])
    st.divider()

# --- [5. 모듈별 로직] ---

# 1. 자산 관리 (입력 탭 복구 완료)
if menu == "자산 관리":
    st.subheader("실시간 통합 자산 현황")
    
    # [사이드바 입력 폼 복구]
    with st.sidebar:
        st.markdown("**💰 지출/수입 기록**")
        with st.form("asset_form"):
            sel_date = st.date_input("날짜", value=now.date())
            sel_hour = st.slider("시간(시)", 0, 23, now.hour)
            t_choice = st.selectbox("구분", ["지출", "수입"])
            c_main = st.selectbox("분류", ["식비", "생활용품", "사회적 관계", "고정지출", "주거/통신", "교통", "건강", "금융", "자산이동"])
            content = st.text_input("상세 내용")
            a_input = st.number_input("금액", min_value=0, step=1000)
            method = st.selectbox("결제수단", ["국민카드", "현대카드", "우리카드", "하나카드", "현금/이체"])
            if st.form_submit_button("전송"):
                payload = {
                    "time": f"{sel_date} {sel_hour:02d}시", "corpus": "Log", "type": t_choice, 
                    "cat_main": c_main, "cat_sub": "-", "item": content, "value": a_input, "method": method, "user": "정원"
                }
                if a_input > 0 and send_to_sheet(payload):
                    st.success("기록 성공"); st.cache_data.clear(); st.rerun()

    # [자산 리스트 및 실시간 연동]
    df_assets = load_sheet_data(GID_MAP["Assets"])
    if not df_assets.empty:
        df_assets.columns = ["항목", "금액", "비고"] + list(df_assets.columns[3:])
        realtime_assets = []
        total_val = 0
        
        for _, row in df_assets.iterrows():
            item, base_val, note = str(row["항목"]), to_numeric(row["금액"]), str(row["비고"])
            qty = extract_quantity(note)
            
            # 코인 실시간 연동
            coin_match = re.search(r'(비트코인|이더리움|BTC|ETH)', item.upper())
            if coin_match and qty:
                symbol = "BTC" if "비트코인" in item or "BTC" in item.upper() else "ETH"
                price = get_upbit_price(symbol)
                if price:
                    current_eval = price * qty
                    realtime_assets.append({"항목": f"{item} (실시간)", "금액": current_eval})
                    total_val += current_eval
                    continue
            
            realtime_assets.append({"항목": item, "금액": base_val})
            total_val += base_val

        st.markdown(f'<div class="status-card"><small>실시간 합산 순자산</small><br><span style="font-size:2.5em; font-weight:bold;">{total_val:,.0f} 원</span></div>', unsafe_allow_html=True)
        
        df_final = pd.DataFrame(realtime_assets)
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**보유 자산**")
            st.table(df_final[df_final["금액"] > 0].assign(금액=lambda x: x["금액"].apply(format_krw)))
        with c2:
            st.markdown("**부채 현황**")
            st.table(df_final[df_final["금액"] < 0].assign(금액=lambda x: x["금액"].apply(lambda v: format_krw(abs(v)))))

# [나머지 식단 및 재고 관리 로직 생략 - 기존 유지]
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
