import streamlit as st
import pandas as pd
import requests
import json
import re
from datetime import datetime, timedelta

# --- [1. 시스템 및 권장 섭취량 설정] ---
SPREADSHEET_ID = '12cPPhM68K3SopQJtZyWEq8adDuP98bJ4efoYbjFDDOI'
GID_MAP = {
    "Log": "0", 
    "Assets": "1068342666", 
    "Inventory": "2138778159", 
    "Pharmacy": "347265850"
}
API_URL = "https://script.google.com/macros/s/AKfycbxmlmMqenbvhLiLbUmI2GEd1sUMpM-NIUytaZ6jGjSL_hZ_4bk8rnDT1Td3wxbdJVBA/exec"
COLOR_ASSET = "#4dabf7"

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

def load_sheet_data(gid):
    ts = datetime.now().timestamp()
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={gid}&t={ts}"
    try:
        df = pd.read_csv(url)
        # 데이터가 있으면 빈 행 제거 후 반환
        return df.dropna(how='all')
    except: return pd.DataFrame()

def send_to_sheet(d_date, d_hour, d_type, cat_main, content, value, method, corpus="Log"):
    payload = {
        "time": f"{d_date} {d_hour:02d}시", "corpus": corpus, "type": d_type, 
        "cat_main": cat_main, "cat_sub": "-", "item": content, "value": value, "method": method, "user": "정원"
    }
    try:
        res = requests.post(API_URL, data=json.dumps(payload), timeout=10)
        return res.status_code == 200
    except: return False

def infer_shelf_life(item_name):
    if any(k in item_name for k in ["오이", "버섯", "콩나물", "샐러드", "상추"]): return 5
    elif any(k in item_name for k in ["애호박", "계란", "요거트", "파프리카"]): return 7
    elif any(k in item_name for k in ["삼겹살", "목살", "닭", "소고기", "생선"]): return 5
    elif any(k in item_name for k in ["두부", "치즈", "우유", "소시지"]): return 14
    elif any(k in item_name for k in ["감자", "당근", "양파", "마늘"]): return 21
    elif any(k in item_name for k in ["냉동", "새우살", "우동사리"]): return 180
    elif any(k in item_name for k in ["라면", "햇반", "캔", "카레", "미역"]): return 365
    return 10

# --- [3. 시스템 초기화 및 견고한 복구 로직] ---
st.set_page_config(page_title="JARVIS Prime v65.1", layout="wide")
now = datetime.utcnow() + timedelta(hours=9)

def sync_from_dedicated_sheet(gid):
    try:
        df = load_sheet_data(gid)
        if not df.empty:
            # 컬럼명에 상관없이 1, 2, 3번째 열의 데이터를 가져오고 이름을 강제 지정
            new_df = df.iloc[:, [0, 1, 2]].copy()
            new_df.columns = ["품목", "수량", "기한"]
            return new_df
    except Exception as e:
        st.error(f"시트 로딩 에러 (GID {gid}): {e}")
    return pd.DataFrame(columns=["품목", "수량", "기한"])

# 세션 상태 초기화
if 'food_df_state' not in st.session_state:
    st.session_state.food_df_state = sync_from_dedicated_sheet(GID_MAP["Inventory"])
if 'med_df_state' not in st.session_state:
    st.session_state.med_df_state = sync_from_dedicated_sheet(GID_MAP["Pharmacy"])
if 'daily_nutri' not in st.session_state:
    st.session_state.daily_nutri = {k: 0.0 for k in RECOMMENDED.keys()}

# 자동 소비기한 보정 로직 (기한이 비어있는 경우만)
if not st.session_state.food_df_state.empty:
    for idx, row in st.session_state.food_df_state.iterrows():
        if row['품목'] and (pd.isna(row['기한']) or str(row['기한']).strip() in ["", "-", "None"]):
            st.session_state.food_df_state.at[idx, '기한'] = (now + timedelta(days=infer_shelf_life(row['품목']))).strftime('%Y-%m-%d')

# --- [4. UI 스타일 및 메인 레이아웃] ---
st.markdown(f"""<style>thead tr th:first-child, tbody th {{ display:none; }} .net-box {{ background-color: #ffffff; padding: 25px; border-radius: 12px; border: 1px solid #dee2e6; border-left: 5px solid {COLOR_ASSET}; margin-bottom: 20px; }} .stProgress > div > div > div > div {{ background-color: {COLOR_ASSET} !important; }}</style>""", unsafe_allow_html=True)

t_col1, t_col2 = st.columns([3, 1])
with t_col1: st.markdown(f"### {now.strftime('%Y-%m-%d %H:%M:%S')} | JARVIS Prime")
with t_col2: 
    if st.button("💾 전체 백업", use_container_width=True, key="main_backup"):
        st.cache_data.clear()
        st.rerun()

with st.sidebar:
    st.title("JARVIS CONTROL")
    menu = st.radio("SELECT MENU", ["투자 & 자산", "식단 & 건강", "재고 & 교체관리"])

# --- [모듈별 기능 분기] ---
if menu == "투자 & 자산":
    st.header("📈 종합 자산 대시보드")
    df_assets = load_sheet_data(GID_MAP["Assets"])
    if not df_assets.empty:
        df_assets = df_assets.iloc[:, [0, 1]].copy()
        df_assets.columns = ["항목", "금액"]; df_assets["val"] = df_assets["금액"].apply(to_numeric)
        a_df, l_df = df_assets[df_assets["val"] > 0], df_assets[df_assets["val"] < 0]
        st.markdown(f'<div class="net-box"><small>통합 순자산</small><br><span style="font-size:2.8em; font-weight:bold;">{a_df["val"].sum() + l_df["val"].sum():,.0f} 원</span></div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1: st.subheader("자산 내역"); st.table(a_df.assign(금액=a_df["val"].apply(format_krw))[["항목", "금액"]])
        with c2: st.subheader("부채 내역"); st.table(l_df.assign(금액=l_df["val"].apply(lambda x: format_krw(abs(x))))[["항목", "금액"]])

elif menu == "식단 & 건강":
    st.header(f"🥗 정밀 영양 분석 (목표: {RECOMMENDED['칼로리']} kcal)")
    curr = st.session_state.daily_nutri
    cols = st.columns(2)
    for idx, (name, goal) in enumerate(RECOMMENDED.items()):
        with cols[idx % 2]:
            val = curr.get(name, 0.0)
            st.write(f"**{name}**: {val:.1f} / {goal:.1f}"); st.progress(min(1.0, val / goal) if goal > 0 else 0.0)
    st.divider()
    m = st.columns(4)
    m[0].metric("칼로리 잔여", f"{max(0, RECOMMENDED['칼로리'] - curr['칼로리']):.0f} kcal")
    m[1].metric("단백질 잔여", f"{max(0, RECOMMENDED['단백질'] - curr['단백질']):.1f} g")
    m[2].metric("탄수화물 잔여", f"{max(0, RECOMMENDED['탄수화물'] - curr['탄수화물']):.1f} g")
    m[3].metric("식이섬유 잔여", f"{max(0, RECOMMENDED['식이섬유'] - curr['식이섬유']):.1f} g")

elif menu == "재고 & 교체관리":
    st.header("🏠 스마트 재고 시스템 (전용 시트)")
    t1, t2 = st.tabs(["🍎 식재료", "💊 의약품"])
    with t1:
        st.session_state.food_df_state = st.data_editor(st.session_state.food_df_state, num_rows="dynamic", use_container_width=True, key="food_v651")
    with t2:
        st.session_state.med_df_state = st.data_editor(st.session_state.med_df_state, num_rows="dynamic", use_container_width=True, key="med_v651")
