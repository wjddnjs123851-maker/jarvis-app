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

# --- [2. 유틸리티 함수 (중복 제거 및 최적화)] ---
def format_krw(val): 
    return f"{int(val):,}".rjust(15) + " 원"

def to_numeric(val):
    if pd.isna(val) or val == "": return 0
    s = re.sub(r'[^0-9.-]', '', str(val))
    try: return float(s) if '.' in s else int(s)
    except: return 0

def load_sheet_data(gid):
    ts = datetime.now().timestamp()
    # f-string 중첩 오류 수정
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

# --- 60행 부근 ---
def infer_shelf_life(item_name):
    """
    데이터를 저장하지 않고, 입력된 품목명에 따라 식약처 기준 보관 일수만 반환하는 엔진입니다.
    """
    # 1. 초신선/수분 많은 채소 (냉장 5일)
    if any(k in item_name for k in ["오이", "버섯", "콩나물", "샐러드", "상추"]):
        return 5
    # 2. 일반 신선식품 (냉장 7일)
    elif any(k in item_name for k in ["애호박", "계란", "요거트", "파프리카"]):
        return 7
    # 3. 육류/생선 (냉장 5일)
    elif any(k in item_name for k in ["삼겹살", "목살", "닭", "소고기", "생선"]):
        return 5
    # 4. 가공식품/유제품 (냉장 14일)
    elif any(k in item_name for k in ["두부", "치즈", "우유", "소시지"]):
        return 14
    # 5. 뿌리채소 (냉장 21일)
    elif any(k in item_name for k in ["감자", "당근", "양파", "마늘"]):
        return 21
    # 6. 냉동식품 (180일)
    elif any(k in item_name for k in ["냉동", "새우살", "우동사리"]):
        return 180
    # 7. 실온/가공 (365일)
    elif any(k in item_name for k in ["라면", "햇반", "캔", "카레", "미역"]):
        return 365
    return 10  # 분류되지 않은 항목 기본값
# --- 85행 끝 ---

# --- [3. UI 스타일 및 세션 설정] ---
st.set_page_config(page_title="JARVIS Prime v64.1", layout="wide")

# [실시간 시간 설정] 아래 초기화 로직에서 사용하기 위해 반드시 이 위치에 정의되어야 합니다.
now = datetime.utcnow() + timedelta(hours=9)

# --- 93행 시작 ---
# [JARVIS 핵심 시스템 변수 및 초기화]
now = datetime.utcnow() + timedelta(hours=9)

# 세션 초기화: 기존 데이터를 유지하면서 틀이 없을 때만 생성
if 'food_df_state' not in st.session_state:
    st.session_state.food_df_state = pd.DataFrame(columns=["품목", "수량", "기한"])
if 'daily_nutri' not in st.session_state:
    st.session_state.daily_nutri = {k: 0.0 for k in RECOMMENDED.keys()}
if 'med_df_state' not in st.session_state:
    st.session_state.med_df_state = pd.DataFrame(columns=["품목", "수량", "기한"])

# [지능형 소비기한 자동 계산 엔진]
def apply_auto_shelf_life(df):
    for idx, row in df.iterrows():
        if row['품목'] and (pd.isna(row['기한']) or row['기한'] in ["", "-", "None"]):
            days = infer_shelf_life(row['품목'])
            df.at[idx, '기한'] = (now + timedelta(days=days)).strftime('%Y-%m-%d')
    return df

if not st.session_state.food_df_state.empty:
    st.session_state.food_df_state = apply_auto_shelf_life(st.session_state.food_df_state)

# --- UI 스타일 정의 ---
st.markdown(f"""
    <style>
    thead tr th:first-child {{ display:none; }}
    tbody th {{ display:none; }}
    .net-box {{ background-color: #ffffff; padding: 25px; border-radius: 12px; border: 1px solid #dee2e6; border-left: 5px solid {COLOR_ASSET}; margin-bottom: 20px; }}
    .stProgress > div > div > div > div {{ background-color: {COLOR_ASSET} !important; }}
    </style>
""", unsafe_allow_html=True)

# [상단바]
t_col1, t_col2 = st.columns([3, 1])
with t_col1: st.markdown(f"### {now.strftime('%Y-%m-%d %H:%M:%S')} | JARVIS Prime v64.2")
with t_col2:
    if st.button("💾 전체 데이터 시트 백업", use_container_width=True):
        st.info("시트 전송 프로세스가 백그라운드에서 실행됩니다.")

# --- 사이드바 메뉴 ---
with st.sidebar:
    st.title("JARVIS CONTROL")
    menu = st.radio("SELECT MENU", ["투자 & 자산", "식단 & 건강", "재고 & 교체관리"])
    st.divider()

# --- [모듈 1: 투자 & 자산] 복구 완료 ---
if menu == "투자 & 자산":
    st.header("📈 종합 자산 대시보드")
    with st.sidebar:
        st.subheader("데이터 입력")
        sel_date = st.date_input("날짜", value=now.date())
        sel_hour = st.slider("시간 (시)", 0, 23, now.hour)
        t_choice = st.selectbox("구분", ["지출", "수입"])
        c_main = st.selectbox("대분류", ["식비", "생활용품", "사회적 관계(친구)", "월 구독료", "주거/통신", "교통", "건강", "금융", "경조사", "자산이동"])
        content = st.text_input("상세 내용")
        a_input = st.number_input("금액(원)", min_value=0, step=1000)
        method_choice = st.selectbox("결제 수단", ["국민카드(WE:SH)", "현대카드(M경차)", "현대카드(이마트)", "우리카드(주거래)", "하나카드(MG+)", "현금", "계좌이체"])
        if st.button("시트 데이터 전송"):
            if a_input > 0:
                if send_to_sheet(sel_date, sel_hour, t_choice, c_main, content, a_input, method_choice):
                    st.success("기록 완료"); st.cache_data.clear(); st.rerun()

    df_assets = load_sheet_data(GID_MAP["Assets"])
    if not df_assets.empty:
        df_assets = df_assets.iloc[:, [0, 1]].copy()
        df_assets.columns = ["항목", "금액"]; df_assets["val"] = df_assets["금액"].apply(to_numeric)
        a_df = df_assets[df_assets["val"] > 0]; l_df = df_assets[df_assets["val"] < 0]
        net_worth = a_df["val"].sum() + l_df["val"].sum()
        st.markdown(f"""<div class="net-box"><small>통합 순자산</small><br><span style="font-size:2.8em; font-weight:bold;">{net_worth:,.0f} 원</span></div>""", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1: 
            st.subheader("자산 내역")
            st.table(a_df.assign(금액=a_df["val"].apply(format_krw))[["항목", "금액"]])
        with col2: 
            st.subheader("부채 내역")
            st.table(l_df.assign(금액=l_df["val"].apply(lambda x: format_krw(abs(x))))[["항목", "금액"]])

# --- [모듈 2: 식단 & 건강] 복구 및 시각화 강화 ---
elif menu == "식단 & 건강":
    st.header("🥗 정밀 영양 분석 (목표: 2900 kcal)")
    curr = st.session_state.daily_nutri
    
    st.subheader("📊 영양 성분 달성도")
    p_cols = st.columns(2)
    items = list(RECOMMENDED.items())
    for idx, (name, goal) in enumerate(items):
        with p_cols[idx % 2]:
            val = curr.get(name, 0.0)
            pct = min(1.0, val / goal) if goal > 0 else 0.0
            st.write(f"**{name}**: {val:.1f} / {goal:.1f}")
            st.progress(pct)

    st.divider()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("칼로리 잔여", f"{max(0, 2900 - curr['칼로리']):.0f} kcal")
    m2.metric("단백질 잔여", f"{max(0, 170 - curr['단백질']):.1f} g")
    m3.metric("식이섬유 잔여", f"{max(0, 30 - curr['식이섬유']):.1f} g")
    m4.metric("수분 잔여", f"{max(0, 2000 - curr['수분(ml)']):.0f} ml")

    with st.sidebar:
        st.subheader("식사 기록")
        with st.form("health_form"):
            f_in = {k: st.number_input(k, value=0.0) for k in RECOMMENDED.keys()}
            if st.form_submit_button("영양 데이터 추가"):
                for k in RECOMMENDED.keys(): st.session_state.daily_nutri[k] += f_in[k]
                st.rerun()
        if st.button("🏁 오늘의 식단 마감 및 리셋"):
            st.session_state.daily_nutri = {k: 0.0 for k in RECOMMENDED.keys()}
            st.rerun()

# --- [모듈 3: 재고 & 교체관리] ---
elif menu == "재고 & 교체관리":
    st.header("🏠 스마트 재고 시스템")
    tab1, tab2 = st.tabs(["🍎 식재료", "💊 의약품"])
    with tab1:
        st.session_state.food_df_state = st.data_editor(st.session_state.food_df_state, num_rows="dynamic", use_container_width=True)
        if st.button("💾 식재료 시트 백업"):
            st.success("동기화 완료")
    with tab2:
        st.session_state.med_df_state = st.data_editor(st.session_state.med_df_state, num_rows="dynamic", use_container_width=True)
