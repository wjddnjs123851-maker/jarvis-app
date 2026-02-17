import streamlit as st
import pandas as pd
import requests
import json
import re
from datetime import datetime, timedelta

# --- [1. 시스템 및 권장 섭취량 설정] ---
SPREADSHEET_ID = '12cPPhM68K3SopQJtZyWEq8adDuP98bJ4efoYbjFDDOI'
GID_MAP = {"Log": "0", "Assets": "1068342666", "Health": "123456789"}
API_URL = "https://script.google.com/macros/s/AKfycbxmlmMqenbvhLiLbUmI2GEd1sUMpM-NIUytaZ6jGjSL_hZ_4bk8rnDT1Td3wxbdJVBA/exec"

COLOR_ASSET = "#4dabf7"

# 정원 님 권장 섭취량 이미지 기준 업데이트
RECOMMENDED = {
    "칼로리": 2200,      # 2,150 ~ 2,200kcal
    "단백질": 180,       # 160 ~ 180g
    "탄수화물": 280,     # 250 ~ 280g
    "지방": 85,          # 70 ~ 85g
    "식이섬유": 30,      # 25 ~ 30g
    "나트륨": 2300,      # 2,300mg 미만
    "당류": 50,          # 50g 미만
    "콜레스테롤": 300,   # 300mg 미만
    "수분(ml)": 2000     
}

# --- [2. 핵심 유틸리티] ---
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

# --- [3. 시스템 초기화 및 세션 관리] ---
st.set_page_config(page_title="JARVIS Prime v64.4", layout="wide")
now = datetime.utcnow() + timedelta(hours=9)

for key, default in [('food_df_state', pd.DataFrame(columns=["품목", "수량", "기한"])), 
                     ('daily_nutri', {k: 0.0 for k in RECOMMENDED.keys()}), 
                     ('med_df_state', pd.DataFrame(columns=["품목", "수량", "기한"]))]:
    if key not in st.session_state: st.session_state[key] = default

if not st.session_state.food_df_state.empty:
    df = st.session_state.food_df_state
    for idx, row in df.iterrows():
        if row['품목'] and (pd.isna(row['기한']) or row['기한'] in ["", "-", "None"]):
            df.at[idx, '기한'] = (now + timedelta(days=infer_shelf_life(row['품목']))).strftime('%Y-%m-%d')

# --- [4. UI 스타일] ---
st.markdown(f"""
    <style>
    thead tr th:first-child, tbody th {{ display:none; }}
    .net-box {{ background-color: #ffffff; padding: 25px; border-radius: 12px; border: 1px solid #dee2e6; border-left: 5px solid {COLOR_ASSET}; margin-bottom: 20px; }}
    .stProgress > div > div > div > div {{ background-color: {COLOR_ASSET} !important; }}
    </style>
""", unsafe_allow_html=True)

# --- [5. 메인 레이아웃] ---
t_col1, t_col2 = st.columns([3, 1])
with t_col1: st.markdown(f"### {now.strftime('%Y-%m-%d %H:%M:%S')} | JARVIS Prime")
with t_col2: 
    if st.button("💾 전체 백업", use_container_width=True): st.info("백업 가동")

with st.sidebar:
    st.title("JARVIS CONTROL")
    menu = st.radio("SELECT MENU", ["투자 & 자산", "식단 & 건강", "재고 & 교체관리"])

if menu == "투자 & 자산":
    st.header("📈 종합 자산 대시보드")
    with st.sidebar:
        with st.form("asset_form"):
            sel_date, sel_hour = st.date_input("날짜", value=now.date()), st.slider("시간", 0, 23, now.hour)
            t_choice = st.selectbox("구분", ["지출", "수입"])
            c_main = st.selectbox("분류", ["식비", "생활용품", "사회적 관계(친구)", "월 구독료", "주거/통신", "교통", "건강", "금융", "경조사", "자산이동"])
            content, a_input = st.text_input("상세 내용"), st.number_input("금액", min_value=0, step=1000)
            method = st.selectbox("수단", ["국민카드(WE:SH)", "현대카드(M경차)", "현대카드(이마트)", "우리카드(주거래)", "하나카드(MG+)", "현금", "계좌이체"])
            if st.form_submit_button("시트 전송"):
                if a_input > 0 and send_to_sheet(sel_date, sel_hour, t_choice, c_main, content, a_input, method):
                    st.success("기록 완료"); st.cache_data.clear(); st.rerun()

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
    m = st.columns(4) # 잔여량 Metric
    m[0].metric("칼로리 잔여", f"{max(0, RECOMMENDED['칼로리'] - curr['칼로리']):.0f} kcal")
    m[1].metric("단백질 잔여", f"{max(0, RECOMMENDED['단백질'] - curr['단백질']):.1f} g")
    m[2].metric("탄수화물 잔여", f"{max(0, RECOMMENDED['탄수화물'] - curr['탄수화물']):.1f} g")
    m[3].metric("식이섬유 잔여", f"{max(0, RECOMMENDED['식이섬유'] - curr['식이섬유']):.1f} g")
    with st.sidebar:
        with st.form("health_form"):
            f_in = {k: st.number_input(k, value=0.0) for k in RECOMMENDED.keys()}
            if st.form_submit_button("데이터 추가"):
                for k in RECOMMENDED.keys(): st.session_state.daily_nutri[k] += f_in[k]
                st.rerun()
        if st.button("🏁 식단 마감"): st.session_state.daily_nutri = {k: 0.0 for k in RECOMMENDED.keys()}; st.rerun()

elif menu == "재고 & 교체관리":
    st.header("🏠 스마트 재고 시스템")
    
    # 알림 섹션: 기한 임박 물품 체크
    alert_found = False
    if not st.session_state.food_df_state.empty:
        for _, row in st.session_state.food_df_state.iterrows():
            try:
                due = datetime.strptime(row['기한'], "%Y-%m-%d")
                rem = (due - now).days
                if rem <= 7:
                    st.warning(f"🚨 **{row['품목']}** 소비기한 임박: {rem}일 남음")
                    alert_found = True
            except: continue
    if not alert_found: st.info("✅ 현재 관리 대상 중 기한 임박 항목이 없습니다.")
    st.divider()

    t1, t2 = st.tabs(["🍎 식재료", "💊 의약품"])
    
    with t1:
        # Key를 부여하여 중복 ID 에러 방지
        st.session_state.food_df_state = st.data_editor(
            st.session_state.food_df_state, 
            num_rows="dynamic", 
            use_container_width=True,
            key="food_editor_v1" 
        )
        if st.button("💾 식재료 데이터 동기화", key="btn_food_sync"):
            st.success("식재료 목록이 세션에 저장되었습니다.")

    with t2:
        # 의약품 에디터에도 고유 Key 부여
        st.session_state.med_df_state = st.data_editor(
            st.session_state.med_df_state, 
            num_rows="dynamic", 
            use_container_width=True,
            key="med_editor_v1"
        )
        if st.button("💾 의약품 데이터 저장", key="btn_med_sync"):
            st.success("의약품 목록이 업데이트되었습니다.")
