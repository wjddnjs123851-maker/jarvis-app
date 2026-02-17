import streamlit as st
import pandas as pd
import requests
import json
import re
from datetime import datetime, timedelta

# --- [1. 시스템 설정] ---
SPREADSHEET_ID = '12cPPhM68K3SopQJtZyWEq8adDuP98bJ4efoYbjFDDOI'
GID_MAP = {
    "log": "0",          
    "assets": "1068342666", 
    "inventory": "2138778159",
    "pharmacy": "347265850"
}
API_URL = "https://script.google.com/macros/s/AKfycbxmlmMqenbvhLiLbUmI2GEd1sUMpM-NIUytaZ6jGjSL_hZ_4bk8rnDT1Td3wxbdJVBA/exec"
COLOR_PRIMARY = "#4dabf7"

RECOMMENDED = {
    "칼로리": 2200, "단백질": 180, "탄수화물": 280, "지방": 85,
    "식이섬유": 30, "나트륨": 2300, "당류": 50, "콜레스테롤": 300, "수분(ml)": 2000     
}

# --- [2. 핵심 유틸리티] ---
def format_krw(val): return f"{int(val):,}".rjust(15) + " 원"

def to_numeric(val):
    if pd.isna(val) or val == "": return 0
    s = re.sub(r'[^0-9.-]', '', str(val))
    try: return float(s) if '.' in s else int(s)
    except: return 0

def extract_quantity(text):
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
st.set_page_config(page_title="JARVIS Prime v66.2", layout="wide")
now = datetime.utcnow() + timedelta(hours=9)

st.markdown(f"""<style>thead tr th:first-child, tbody th {{ display:none; }} .status-card {{ background-color: #ffffff; padding: 20px; border-radius: 8px; border: 1px solid #dee2e6; border-left: 5px solid {COLOR_PRIMARY}; margin-bottom: 20px; }}</style>""", unsafe_allow_html=True)

with st.sidebar:
    st.title("자비스 제어 센터")
    menu = st.radio("메뉴 선택", ["자산 관리", "식단 및 건강", "재고 관리"])
    st.divider()
    st.info("사용자: 정원 (185cm / 자산 분리 모드)")

# --- [4. 메뉴별 기능 구현] ---

if menu == "자산 관리":
    st.subheader("실시간 통합 자산 및 가계부")
    
    # 1. 입력 폼 (기존 동일)
    with st.sidebar:
        st.markdown("**💰 지출/수입 기록**")
        with st.form("asset_form"):
            sel_date = st.date_input("날짜", value=now.date())
            sel_hour = st.slider("시간(시)", 0, 23, now.hour)
            t_choice = st.selectbox("구분", ["지출", "수입"])
            c_main = st.selectbox("분류", ["식비", "생활용품", "사회적 관계", "고정지출", "주거/통신", "교통", "건강", "금융", "자산이동"])
            content = st.text_input("상세 내용")
            a_input = st.number_input("금액", min_value=0, step=1000)
            method = st.selectbox("결제수단", ["국민카드(WE:SH)", "하나카드(MG+)", "우리카드(주거래)", "현대카드(이마트)", "현금", "계좌이체"])
            if st.form_submit_button("전송"):
                payload = {"time": f"{sel_date} {sel_hour:02d}시", "corpus": "log", "type": t_choice, "cat_main": c_main, "item": content, "value": a_input, "method": method, "user": "정원"}
                if a_input > 0 and send_to_sheet(payload):
                    st.success("데이터 기록 성공"); st.cache_data.clear(); st.rerun()

    # 2. 데이터 로드 및 강제 보정
    df_assets = load_sheet_data(GID_MAP["assets"])
    
    if not df_assets.empty:
        # 데이터가 있는 행부터 읽기 위해 불필요한 헤더 정리
        # 정원 님 시트 구조: A열(항목), B열(금액), C열(비고)
        realtime_list = []
        total_val = 0
        
        # DataFrame의 실제 데이터를 순회 (컬럼명 무시하고 인덱스로 접근)
        for i in range(len(df_assets)):
            try:
                # 첫 번째 열(항목)과 두 번째 열(금액)을 직접 추출
                item = str(df_assets.iloc[i, 0])
                raw_val = df_assets.iloc[i, 1]
                note = str(df_assets.iloc[i, 2]) if len(df_assets.columns) > 2 else ""
                
                # 금액 숫자로 변환
                val = to_numeric(raw_val)
                
                # '항목'이 비어있으면 건너뜀
                if not item or item == "nan" or item == "항목":
                    continue
                
                # 코인 실시간 시세 처리
                qty = extract_quantity(note)
                coin_match = re.search(r'(BTC|ETH)', item.upper())
                if coin_match and qty:
                    symbol = coin_match.group(1)
                    price = get_upbit_price(symbol)
                    if price:
                        val = price * qty
                        item = f"{item} (실시간)"
                
                realtime_list.append({"항목": item, "금액": val})
                total_val += val
            except Exception as e:
                continue

        # 3. 화면 출력
        st.markdown(f'<div class="status-card"><small>현재 실시간 통합 순자산</small><br><span style="font-size:2.5em; font-weight:bold;">{total_val:,.0f} 원</span></div>', unsafe_allow_html=True)

        df_final = pd.DataFrame(realtime_list)
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 🟢 보유 자산")
            # 1원이라도 있는 자산 출력
            df_pos = df_final[df_final["금액"] > 0].copy()
            if not df_pos.empty:
                st.table(df_pos.assign(금액=lambda x: x["금액"].apply(format_krw)))
            else:
                st.info("표시할 자산이 없습니다.")

        with col2:
            st.markdown("#### 🔴 부채 및 카드값")
            # 0보다 작은 모든 항목 출력 (카드값 등)
            df_neg = df_final[df_final["금액"] < 0].copy()
            if not df_neg.empty:
                st.table(df_neg.assign(금액=lambda x: x["금액"].apply(lambda v: format_krw(abs(v)))))
            else:
                st.warning("부채 내역이 없습니다. (시트의 B열 금액이 마이너스인지 확인하세요)")
elif menu == "식단 및 건강":
    # (v66.1과 동일한 식단 코드)
    st.subheader(f"오늘의 영양 분석 (목표: {RECOMMENDED['칼로리']} kcal)")
    if 'daily_nutri' not in st.session_state:
        st.session_state.daily_nutri = {k: 0.0 for k in RECOMMENDED.keys()}
    curr = st.session_state.daily_nutri
    items = list(RECOMMENDED.items())
    for i in range(0, len(items), 2):
        cols = st.columns(2)
        for j in range(2):
            if i + j < len(items):
                name, goal = items[i + j]; val = curr.get(name, 0.0)
                with cols[j]:
                    st.write(f"**{name}**: {val:.1f} / {goal:.1f}")
                    st.progress(min(1.0, val / goal) if goal > 0 else 0.0)
    with st.sidebar:
        st.markdown("**🍴 식단 입력**")
        with st.form("diet_form"):
            f_in = {k: st.number_input(k, value=0.0) for k in RECOMMENDED.keys()}
            if st.form_submit_button("영양 데이터 전송"):
                for k in RECOMMENDED.keys(): st.session_state.daily_nutri[k] += f_in[k]
                payload = {"time": now.strftime('%Y-%m-%d %H시'), "corpus": "log", "type": "식단", "cat_main": "식단", "item": "일일섭취", "value": f_in["칼로리"], "method": "앱입력", "user": "정원"}
                send_to_sheet(payload); st.success("식단 기록 완료"); st.rerun()

elif menu == "재고 관리":
    # (v66.1과 동일한 재고 코드)
    st.subheader("물품 재고 및 소비기한 관리")
    t1, t2 = st.tabs(["식재료 재고", "상비약 현황"])
    with t1:
        df_inv = load_sheet_data(GID_MAP["inventory"])
        if not df_inv.empty: st.data_editor(df_inv, num_rows="dynamic", use_container_width=True, key="inv_editor")
    with t2:
        df_pharma = load_sheet_data(GID_MAP["pharmacy"])
        if not df_pharma.empty: st.data_editor(df_pharma, num_rows="dynamic", use_container_width=True, key="pharma_editor")
