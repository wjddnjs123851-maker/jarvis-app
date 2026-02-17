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

# 정원 님 맞춤 영양 목표 (185cm / 결혼식 대비 식단)
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

@st.cache_data(ttl=600)
def load_sheet_data(gid):
    ts = datetime.now().timestamp()
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={gid}&t={ts}"
    try:
        df = pd.read_csv(url)
        return df.dropna(how='all')
    except Exception as e:
        st.error(f"데이터 로드 오류: {e}")
        return pd.DataFrame()

def send_to_sheet(payload):
    try:
        res = requests.post(API_URL, data=json.dumps(payload), timeout=10)
        return res.status_code == 200
    except: return False

# --- [3. 초기화 및 로딩] ---
st.set_page_config(page_title="JARVIS Prime v65.6", layout="wide")
now = datetime.utcnow() + timedelta(hours=9)

def sync_from_dedicated_sheet(gid):
    df = load_sheet_data(gid)
    if not df.empty:
        try:
            # 시트의 1, 2, 3열을 품목, 수량, 기한으로 매핑
            new_df = df.iloc[:, [0, 1, 2]].copy()
            new_df.columns = ["품목", "수량", "소비기한"]
            return new_df
        except: pass
    return pd.DataFrame(columns=["품목", "수량", "소비기한"])

if 'food_df_state' not in st.session_state:
    st.session_state.food_df_state = sync_from_dedicated_sheet(GID_MAP["Inventory"])
if 'med_df_state' not in st.session_state:
    st.session_state.med_df_state = sync_from_dedicated_sheet(GID_MAP["Pharmacy"])
if 'daily_nutri' not in st.session_state:
    st.session_state.daily_nutri = {k: 0.0 for k in RECOMMENDED.keys()}

# --- [4. UI 스타일링] ---
st.markdown(f"""
<style>
    thead tr th:first-child, tbody th {{ display:none; }}
    .status-card {{ background-color: #ffffff; padding: 20px; border-radius: 8px; border: 1px solid #dee2e6; border-left: 5px solid {COLOR_PRIMARY}; margin-bottom: 20px; }}
    .stProgress > div > div > div > div {{ background-color: {COLOR_PRIMARY} !important; }}
</style>
""", unsafe_allow_html=True)

# --- [5. 상단 헤더] ---
t_col1, t_col2 = st.columns([3, 1])
with t_col1: 
    st.markdown(f"### {now.strftime('%Y-%m-%d %H:%M:%S')} | JARVIS Prime 시스템")
with t_col2: 
    if st.button("데이터 새로고침", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

with st.sidebar:
    st.title("자비스 제어 센터")
    menu = st.radio("메뉴 선택", ["자산 관리", "식단 및 건강", "재고 관리"])
    st.divider()
    st.info("사용자: 정원 (185cm / 목표 체중 감량)")

# --- [6. 모듈별 로직] ---

# 1. 자산 관리 모듈
if menu == "자산 관리":
    st.subheader("종합 자산 현황")
    with st.sidebar:
        st.markdown("**내역 입력**")
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
                    st.success("기록되었습니다."); st.cache_data.clear(); st.rerun()

    df_assets = load_sheet_data(GID_MAP["Assets"])
    if not df_assets.empty:
        df_assets = df_assets.iloc[:, [0, 1]].copy()
        df_assets.columns = ["항목", "금액"]
        df_assets["val"] = df_assets["금액"].apply(to_numeric)
        net_val = df_assets["val"].sum()
        
        st.markdown(f'<div class="status-card"><small>현재 순자산</small><br><span style="font-size:2.5em; font-weight:bold;">{net_val:,.0f} 원</span></div>', unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        with c1: 
            st.markdown("**보유 자산**")
            st.table(df_assets[df_assets["val"] > 0].assign(금액=lambda x: x["val"].apply(format_krw))[["항목", "금액"]])
        with c2: 
            st.markdown("**부채 현황**")
            st.table(df_assets[df_assets["val"] < 0].assign(금액=lambda x: x["val"].apply(lambda v: format_krw(abs(v))))[["항목", "금액"]])

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
