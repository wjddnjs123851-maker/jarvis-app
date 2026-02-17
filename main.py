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
    "Health": "123456789"
}
API_URL = "https://script.google.com/macros/s/AKfycbxmlmMqenbvhLiLbUmI2GEd1sUMpM-NIUytaZ6jGjSL_hZ_4bk8rnDT1Td3wxbdJVBA/exec"

COLOR_BG = "#ffffff"
COLOR_TEXT = "#000000"
COLOR_ASSET = "#4dabf7" 
COLOR_DEBT = "#ff922b"  

RECOMMENDED = {
    "칼로리": 2900, "지방": 70, "콜레스테롤": 300, "나트륨": 2300, 
    "탄수화물": 350, "식이섬유": 30, "당": 50, "단백질": 170, "수분(ml)": 2000
}

# --- [2. 유틸리티 및 지능형 추론 함수] ---
def format_krw(val): 
    return f"{int(val):,}".rjust(15) + " 원"

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
        return df.dropna(how='all')
    except: return pd.DataFrame()

def send_to_sheet(d_date, d_hour, d_type, cat_main, content, value, method, corpus="Log"):
    full_time = f"{d_date} {d_hour:02d}시"
    payload = {
        "time": full_time, "corpus": corpus, "type": d_type, 
        "cat_main": cat_main, "cat_sub": "-", 
        "item": content, "value": value, "method": method, "user": "정원"
    }
    try:
        res = requests.post(API_URL, data=json.dumps(payload), timeout=10)
        return res.status_code == 200
    except: return False

def infer_shelf_life(item_name):
    if any(k in item_name for k in ["케일", "잎", "시금치", "루꼴라", "허브", "고수", "샐러드"]): return 7
    elif any(k in item_name for k in ["파스닙", "뿌리", "비트", "마", "연근", "우엉", "감자", "당근", "양파"]): return 21
    elif any(k in item_name for k in ["고기", "살", "닭", "소", "돼지", "삼겹살", "목살", "생선", "해산물"]): return 5
    elif any(k in item_name for k in ["약", "정", "제", "눈물", "시럽"]): return 730
    else: return 10

# --- [3. UI 스타일 및 세션 설정] ---
st.set_page_config(page_title="JARVIS v64.0", layout="wide")

# 세션 상태 초기화
if 'daily_nutri' not in st.session_state:
    st.session_state.daily_nutri = {k: 0.0 for k in RECOMMENDED.keys()}
if 'maintenance' not in st.session_state:
    st.session_state.maintenance = [{"항목": "칫솔", "주기": 90, "마지막": "2025-11-20"}]
if 'food_df_state' not in st.session_state:
    st.session_state.food_df_state = pd.DataFrame([{"품목": "계란", "수량": "15알", "기한": "2026-03-10"}])
if 'med_df_state' not in st.session_state:
    st.session_state.med_df_state = pd.DataFrame([{"품목": "타이레놀", "수량": "8정", "기한": "2027-12-31"}])

st.markdown(f"""
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    * {{ font-family: 'Pretendard', sans-serif !important; }}
    .stApp {{ background-color: {COLOR_BG}; color: {COLOR_TEXT}; }}
    .stButton>button {{
        background-color: #ffffff !important; color: #000000 !important;
        border: 1px solid #dee2e6 !important; border-radius: 8px; font-weight: bold; width: 100%; height: 3.5em;
    }}
    .net-box {{ background-color: #ffffff; padding: 25px; border-radius: 12px; border: 1px solid #dee2e6; border-left: 5px solid {COLOR_ASSET}; margin-bottom: 20px; }}
    .total-card {{ background-color: #ffffff; padding: 20px; border-radius: 10px; border: 1px solid #dee2e6; text-align: right; }}
    </style>
""", unsafe_allow_html=True)
# [전체 백업 및 시간 표시]
now = datetime.utcnow() + timedelta(hours=9)
top_col1, top_col2 = st.columns([3, 1])
with top_col1:
    st.markdown(f"### {now.strftime('%Y-%m-%d %H:%M:%S')} | JARVIS Prime")
with top_col2:
    if st.button("💾 전체 데이터 백업", use_container_width=True):
        backup_log = []
        if 'maintenance' in st.session_state:
            for m in st.session_state.maintenance: backup_log.append(["일정", m['항목'], f"주기:{m['주기']}, 마지막:{m['마지막']}"])
        for _, row in st.session_state.food_df_state.iterrows(): backup_log.append(["식재료", row['품목'], f"{row['수량']} (기한:{row['기한']})"])
        for _, row in st.session_state.med_df_state.iterrows(): backup_log.append(["의약품", row['품목'], f"{row['수량']} (기한:{row['기한']})"])
        success_count = sum([1 for e in backup_log if send_to_sheet(now.date(), now.hour, e[0], "백업", e[1], 0, e[2])])
        if success_count > 0: st.success(f"{success_count}건 백업 완료")

with st.sidebar:
    st.title("JARVIS CONTROL")
    menu = st.radio("SELECT MENU", ["투자 & 자산", "식단 & 건강", "재고 & 교체관리"])

# --- [모듈 1: 투자 & 자산] ---
if menu == "투자 & 자산":
    st.header("📈 종합 자산 대시보드")
    with st.sidebar:
        st.subheader("데이터 입력")
        sel_date = st.date_input("날짜", value=now.date())
        t_choice = st.selectbox("구분", ["지출", "수입"])
        # '외출/약속' 카테고리 추가
        c_main = st.selectbox("대분류", ["식비", "생활용품", "외출/약속", "월 구독료", "주거/통신", "교통", "건강", "금융", "경조사", "자산이동"])
        content = st.text_input("상세 내용")
        a_input = st.number_input("금액(원)", min_value=0, step=1000)
        method_choice = st.selectbox("결제 수단", ["국민카드(WE:SH)", "현대카드(M경차)", "현대카드(이마트)", "우리카드(주거래)", "현금", "계좌이체"])
        
        if st.button("시트 데이터 전송"):
            if a_input > 0 and send_to_sheet(sel_date, now.hour, t_choice, c_main, content, a_input, method_choice):
                # 가계부-재고 연동: 식비/생활용품 시 자동 추가
                if t_choice == "지출" and c_main in ["식비", "생활용품"]:
                    p_days = infer_shelf_life(content)
                    p_date = (now + timedelta(days=p_days)).strftime('%Y-%m-%d')
                    new_item = pd.DataFrame([{"품목": content, "수량": "1(자동)", "기한": p_date}])
                    st.session_state.food_df_state = pd.concat([st.session_state.food_df_state, new_item], ignore_index=True)
                st.success("기록 완료"); st.cache_data.clear(); st.rerun()

    df_assets = load_sheet_data(GID_MAP["Assets"])
    if not df_assets.empty:
        df_assets = df_assets.iloc[:, [0, 1]].copy()
        df_assets.columns = ["항목", "금액"]; df_assets["val"] = df_assets["금액"].apply(to_numeric)
        a_df = df_assets[df_assets["val"] > 0]; l_df = df_assets[df_assets["val"] < 0]
        st.markdown(f"""<div class="net-box"><small>통합 순자산</small><br><span style="font-size:2.8em; font-weight:bold;">{a_df['val'].sum()+l_df['val'].sum():,0f} 원</span></div>""", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        # 인덱스 제거 (hide_index=True)
        with col1: st.subheader("자산 내역"); st.dataframe(a_df.assign(금액=a_df["val"].apply(format_krw))[["항목", "금액"]], hide_index=True, use_container_width=True)
        with col2: st.subheader("부채 내역"); st.dataframe(l_df.assign(금액=l_df["val"].apply(lambda x: format_krw(abs(x))))[["항목", "금액"]], hide_index=True, use_container_width=True)

# --- [모듈 2: 식단 & 건강] ---
elif menu == "식단 & 건강":
    st.header("🥗 정밀 영양 분석")
    curr = st.session_state.daily_nutri
    hc = st.columns(4)
    hc[0].metric("칼로리 잔여", f"{max(0, 2900 - curr.get('칼로리', 0)):.0f} kcal")
    hc[1].metric("단백질 잔여", f"{max(0, 170 - curr.get('단백질', 0)):.1f} g")
    hc[2].metric("식이섬유 잔여", f"{max(0, 30 - curr.get('식이섬유', 0)):.1f} g")
    hc[3].metric("수분 잔여", f"{max(0, 2000 - curr.get('수분(ml)', 0)):.0f} ml")
    
    with st.form("h_form"):
        f_in = {k: st.number_input(k, value=0.0, step=0.1) for k in RECOMMENDED.keys()}
        if st.form_submit_button("영양 추가"):
            for k in RECOMMENDED.keys(): st.session_state.daily_nutri[k] += f_in[k]
            st.rerun()

# --- [모듈 3: 재고 & 교체관리] ---
elif menu == "재고 & 교체관리":
    st.header("🏠 스마트 물품 관리")
    tab1, tab2, tab3 = st.tabs(["🍎 식재료", "💊 의약품", "⚙️ 일정"])
    with tab1:
        ed_f = st.data_editor(st.session_state.food_df_state, num_rows="dynamic", use_container_width=True, key="f_ed")
        if st.button("식재료 저장"): st.session_state.food_df_state = ed_f; st.rerun()
    with tab2:
        ed_m = st.data_editor(st.session_state.med_df_state, num_rows="dynamic", use_container_width=True, key="m_ed")
        if st.button("의약품 저장"): st.session_state.med_df_state = ed_m; st.rerun()
    with tab3:
        if 'maintenance_df' not in st.session_state: st.session_state.maintenance_df = pd.DataFrame(st.session_state.maintenance)
        ed_mt = st.data_editor(st.session_state.maintenance_df, num_rows="dynamic", use_container_width=True, key="mt_ed")
        if st.button("일정 저장"): 
            st.session_state.maintenance = ed_mt.to_dict('records')
            st.session_state.maintenance_df = ed_mt; st.rerun()
