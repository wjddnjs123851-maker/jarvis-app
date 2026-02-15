import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime

# --- [1. 시스템 설정] ---
SPREADSHEET_ID = '17kw1FMK50MUpAWA9VPSile8JZeeq6TZ9DWJqMRaBMUM'
GID_MAP = {
    "Log": "0", "Assets": "1068342666", "Report": "308599580", "Health": "123456789"
}
API_URL = "https://script.google.com/macros/s/AKfycbzX1w7136qfFsnRb0RMQTZvJ1Q_-GZb5HAwZF6yfKiLTHbchJZq-8H2GXjV2z5WnkmI4A/exec"

COLOR_ASSET = "#4dabf7"  
COLOR_DEBT = "#ff922b"   

# --- [2. 유틸리티] ---
def format_krw(val): return f"{int(val):,}".rjust(15) + " 원"
def to_numeric(val):
    try: 
        if pd.isna(val): return 0
        return int(float(str(val).replace(',', '').replace('원', '').strip()))
    except: return 0

def get_weather():
    try:
        # 평택 좌표 기반 실시간 날씨
        w_url = "https://api.open-meteo.com/v1/forecast?latitude=36.99&longitude=127.11&current_weather=true&timezone=auto"
        res = requests.get(w_url, timeout=2).json()
        temp = res['current_weather']['temperature']
        code = res['current_weather']['weathercode']
        icon = "☀️" if code <= 3 else "☁️" if code <= 48 else "🌧️" if code <= 80 else "❄️"
        return f"{icon} {temp}°C"
    except: return "날씨 로드 실패"

def send_to_sheet(d_type, cat_main, cat_sub, content, value, corpus="Log"):
    payload = {
        "time": datetime.now().strftime('%Y-%m-%d'),
        "corpus": corpus, "type": d_type, "cat_main": cat_main, 
        "cat_sub": cat_sub, "item": content, "value": value, 
        "method": "자비스", "user": "정원"
    }
    try: return requests.post(API_URL, data=json.dumps(payload), timeout=5).status_code == 200
    except: return False

@st.cache_data(ttl=5)
def load_sheet_data(gid):
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={gid}"
    try: return pd.read_csv(url).dropna(how='all').reset_index(drop=True)
    except: return pd.DataFrame()

# --- [3. 메인 레이아웃] ---
st.set_page_config(page_title="JARVIS v42.6", layout="wide")
st.markdown(f"""
    <style>
    .stApp {{ background-color: #ffffff; color: #212529; }}
    [data-testid="stMetricValue"] {{ text-align: right !important; }}
    [data-testid="stTable"] td {{ text-align: right !important; }}
    .net-box {{ background-color: #f8f9fa; padding: 20px; border-radius: 10px; border: 1px solid {COLOR_ASSET}; margin-bottom: 25px; }}
    </style>
""", unsafe_allow_html=True)

# 헤더 (시간 및 날씨 연동 완료)
t_c1, t_c2 = st.columns([7, 3])
with t_c1: 
    st.markdown(f"### {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 평택 {get_weather()}")
with t_c2: 
    st.markdown(f"<div style='text-align:right; color:{COLOR_ASSET}; font-weight:bold;'>JARVIS: ONLINE</div>", unsafe_allow_html=True)

# --- [4. 사이드바: 통합 제어 센터] ---
with st.sidebar:
    st.title("JARVIS CONTROL")
    menu = st.radio("MENU", ["투자 & 자산", "식단 & 건강", "재고 관리"])
    st.divider()
    
    if menu == "투자 & 자산":
        st.subheader("지출/수입 입력")
        t_choice = st.selectbox("구분", ["지출", "수입"])
        c_main = st.selectbox("대분류", ["식비", "생활용품", "주거/통신", "교통", "건강", "금융", "경조사", "자산이동"])
        c_sub = st.text_input("소분류")
        content = st.text_input("상세 내용")
        a_input = st.number_input("금액(원)", min_value=0, step=1000)
        if st.button("전송", use_container_width=True):
            if a_input > 0 and send_to_sheet(t_choice, c_main, c_sub, content, a_input):
                st.cache_data.clear(); st.rerun()

# --- [5. 메인 화면: 투자 & 자산 대시보드 (KeyError 해결 버전)] ---
if menu == "투자 & 자산":
    st.header("종합 자산 관리")
    df_assets_raw = load_sheet_data(GID_MAP["Assets"])
    df_log = load_sheet_data(GID_MAP["Log"])
    
    cash_diff, card_debt = 0, 0
    if not df_log.empty:
        for _, row in df_log.iterrows():
            val = to_numeric(row.iloc[5]) 
            if row.iloc[1] == "지출":
                if row.iloc[2] == "자산이동": cash_diff -= val
                else: card_debt += val
            elif row.iloc[1] == "수입":
                if row.iloc[2] != "자산이동": cash_diff += val

    if not df_assets_raw.empty:
        # 에러 방지를 위해 열 이름을 강제로 지정
        df_assets = df_assets_raw.iloc[:, :2].copy()
        df_assets.columns = ["항목", "금액"]
        df_assets["val"] = df_assets["금액"].apply(to_numeric)
    
        # 가용현금 보정
        cash_idx = df_assets[df_assets['항목'] == '가용현금'].index
        if not cash_idx.empty: df_assets.at[cash_idx[0], 'val'] += cash_diff
        
        # 카드 미결제액 추가
        if card_debt > 0:
            df_assets = pd.concat([df_assets, pd.DataFrame([{"항목": "카드 미결제액(지출)", "val": -card_debt}])], ignore_index=True)

        a_df = df_assets[df_assets["val"] >= 0].copy()
        l_df = df_assets[df_assets["val"] < 0].copy()
        net_worth = a_df["val"].sum() + l_df["val"].sum()

        st.markdown(f"""<div class="net-box"><small>시트 연동 통합 순자산</small><br><span style="font-size:2.5em; color:{COLOR_ASSET}; font-weight:bold;">{format_krw(net_worth)}</span></div>""", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("보유 자산")
            st.table(a_df.assign(금액=a_df["val"].apply(format_krw))[["항목", "금액"]])
        with c2:
            st.subheader("부채 현황")
            if not l_df.empty: st.table(l_df.assign(금액=l_df["val"].apply(lambda x: format_krw(abs(x))))[["항목", "금액"]])
            st.metric("이번 달 지출 누계", format_krw(card_debt))
    else:
        st.warning("Assets 시트에 데이터를 입력해 주세요.")
        # --- [6. 사이드바: 건강 및 재고 입력 섹션] ---
with st.sidebar:
    if menu == "식단 & 건강":
        st.subheader("영양 기록 (FatSecret 순서)")
        with st.form("health_input"):
            in_w = st.number_input("현재 체중 (kg)", 50.0, 150.0, 125.0, step=0.1)
            st.divider()
            # 팻시크릿 순서: 지방, 콜레스테롤, 나트륨, 탄수화물, 식이섬유, 당, 단백질
            in_kcal = st.number_input("칼로리 (kcal)", 0, 5000, 0)
            in_fat = st.number_input("지방 (g)", 0, 200, 0)
            in_chole = st.number_input("콜레스테롤 (mg)", 0, 1000, 0)
            in_na = st.number_input("나트륨 (mg)", 0, 5000, 0)
            in_carb = st.number_input("탄수화물 (g)", 0, 500, 0)
            in_fiber = st.number_input("식이섬유 (g)", 0, 100, 0)
            in_sugar = st.number_input("당 (g)", 0, 200, 0)
            in_prot = st.number_input("단백질 (g)", 0, 300, 0)
            
            if st.form_submit_button("기록 저장", use_container_width=True):
                send_to_sheet("건강", "기록", "체중", "정원", in_w, corpus="Health")
                nutris = {"칼로리": in_kcal, "지방": in_fat, "콜레스테롤": in_chole, "나트륨": in_na, "탄수화물": in_carb, "식이섬유": in_fiber, "당": in_sugar, "단백질": in_prot}
                for k, v in nutris.items():
                    if v > 0: send_to_sheet("식단", "영양소", k, "정원", v, corpus="Health")
                st.cache_data.clear(); st.rerun()

# --- [7. 메인 화면: 식단 & 건강 대시보드] ---
if menu == "식단 & 건강":
    st.header("영양 분석")
    df_log = load_sheet_data(GID_MAP["Log"])
    today_str = datetime.now().strftime('%Y-%m-%d')
    NUTRI_ORDER = ["칼로리", "지방", "콜레스테롤", "나트륨", "탄수화물", "식이섬유", "당", "단백질"]
    
    cur_nutri = {k: 0 for k in NUTRI_ORDER}
    if not df_log.empty:
        df_log['날짜'] = df_log.iloc[:, 0].astype(str)
        df_today = df_log[df_log['날짜'].str.contains(today_str)]
        for k in NUTRI_ORDER:
            # 시트의 2번째 컬럼(구분)이 식단, 4번째 컬럼(소분류)이 영양소명인 행 합산
            cur_nutri[k] = df_today[(df_today.iloc[:, 1] == '식단') & (df_today.iloc[:, 3] == k)].iloc[:, 5].apply(to_numeric).sum()

    col_stat, col_vis = st.columns([5, 5])
    with col_stat:
        st.subheader("오늘의 섭취 현황")
        stat_data = [{"영양소": k, "현재량": f"{cur_nutri[k]:,.1f}"} for k in NUTRI_ORDER]
        st.table(pd.DataFrame(stat_data).set_index("영양소"))
    with col_vis:
        st.subheader("목표 달성도")
        for name in ["칼로리", "단백질", "탄수화물", "지방"]:
            val, target = cur_nutri[name], (2900 if name == "칼로리" else 160)
            st.caption(f"{name} ({val:,.1f} / {target:,.1f})")
            st.progress(min(val / target, 1.0) if target > 0 else 0)

# --- [8. 메인 화면: 재고 관리 (전수조사)] ---
elif menu == "재고 관리":
    st.header("창고 재고 관리")
    if 'inventory' not in st.session_state:
        st.session_state.inventory = pd.DataFrame([
            {"구분": "상온", "항목": "올리브유/알룰로스/스테비아/사과식초", "수량": "보유"},
            {"구분": "상온", "항목": "진간장/국간장/맛술/굴소스/저당케찹", "수량": "보유"},
            {"구분": "상온", "항목": "하이라이스 가루/황설탕/고춧가루/후추", "수량": "보유"},
            {"구분": "상온", "항목": "소금/통깨/김", "수량": "보유"},
            {"구분": "곡물", "항목": "카무트/현미/쌀", "수량": "보유"},
            {"구분": "냉장", "항목": "계란/대파/양파/마늘/청양고추", "수량": "보유"},
            {"구분": "냉동", "항목": "냉동 삼치(4팩)/닭다리살(3팩)", "수량": "보유"},
            {"구분": "냉동", "항목": "토마토 페이스트(10캔)", "수량": "보유"},
            {"구분": "냉동", "항목": "단백질 쉐이크(9개)", "수량": "보유"},
            {"구분": "냉동", "항목": "닭가슴살 스테이크", "수량": "보유"}
        ])
    st.session_state.inventory = st.data_editor(st.session_state.inventory, num_rows="dynamic", use_container_width=True)

st.divider()
if st.button("시스템 리프레시", use_container_width=True):
    st.cache_data.clear(); st.rerun()
