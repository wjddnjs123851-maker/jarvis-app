import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime, timedelta

# --- [1. 시스템 설정] ---
SPREADSHEET_ID = '17kw1FMK50MUpAWA9VPSile8JZeeq6TZ9DWJqMRaBMUM'
GID_MAP = {
    "Log": "0", "Assets": "1068342666", "Report": "308599580", "Health": "123456789"
}
API_URL = "https://script.google.com/macros/s/AKfycbzX1w7136qfFsnRb0RMQTZvJ1Q_-GZb5HAwZF6yfKiLTHbchJZq-8H2GXjV2z5WnkmI4A/exec"

COLOR_ASSET = "#4dabf7"  # 파랑
COLOR_DEBT = "#ff922b"   # 주황

# --- [2. 유틸리티 함수] ---
def format_krw(val): return f"{int(val):,}".rjust(15) + " 원"

def to_numeric(val):
    try: 
        if pd.isna(val): return 0
        return int(float(str(val).replace(',', '').replace('원', '').strip()))
    except: return 0

def get_current_time():
    # 한국 표준시(KST) 보정
    now = datetime.utcnow() + timedelta(hours=9)
    return now.strftime('%Y-%m-%d %H:%M:%S')

def get_weather():
    try:
        w_url = "https://api.open-meteo.com/v1/forecast?latitude=36.99&longitude=127.11&current_weather=true&timezone=auto"
        res = requests.get(w_url, timeout=2).json()
        temp = res['current_weather']['temperature']
        code = res['current_weather']['weathercode']
        icon = "☀️" if code <= 3 else "☁️" if code <= 48 else "🌧️" if code <= 80 else "❄️"
        return f"{icon} {temp}°C"
    except: return "날씨 로드 실패"

def send_to_sheet(d_type, cat_main, cat_sub, content, value, corpus="Log"):
    payload = {
        "time": get_current_time().split(' ')[0],
        "corpus": corpus, "type": d_type, "cat_main": cat_main, 
        "cat_sub": cat_sub, "item": content, "value": value, 
        "method": "자비스", "user": "정원"
    }
    try: return requests.post(API_URL, data=json.dumps(payload), timeout=5).status_code == 200
    except: return False

def load_sheet_data(gid):
    # 구글 시트 캐싱 방지를 위해 timestamp 파라미터 추가
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={gid}&t={datetime.now().timestamp()}"
    try: 
        df = pd.read_csv(url)
        return df.dropna(how='all').reset_index(drop=True)
    except: return pd.DataFrame()

# --- [3. 메인 레이아웃 설정] ---
st.set_page_config(page_title="JARVIS v43.0", layout="wide")
st.markdown(f"""
    <style>
    .stApp {{ background-color: #ffffff; color: #212529; }}
    [data-testid="stMetricValue"] {{ text-align: right !important; }}
    [data-testid="stTable"] td {{ text-align: right !important; }}
    .net-box {{ background-color: #f8f9fa; padding: 20px; border-radius: 10px; border: 1px solid {COLOR_ASSET}; margin-bottom: 25px; }}
    </style>
""", unsafe_allow_html=True)

# 헤더 정보
t_c1, t_c2 = st.columns([7, 3])
with t_c1: 
    st.markdown(f"### {get_current_time()} | 평택 {get_weather()}")
with t_c2: 
    st.markdown(f"<div style='text-align:right; color:{COLOR_ASSET}; font-weight:bold;'>JARVIS: ONLINE</div>", unsafe_allow_html=True)

# --- [4. 사이드바 메뉴] ---
with st.sidebar:
    st.title("JARVIS CONTROL")
    menu = st.radio("MENU", ["투자 & 자산", "식단 & 건강", "재고 관리"])
    st.divider()

# --- [5. 메뉴별 화면 구성] ---

# 탭 1: 투자 & 자산
if menu == "투자 & 자산":
    st.header("종합 자산 관리")
    
    with st.sidebar:
        st.subheader("지출/수입 입력")
        t_choice = st.selectbox("구분", ["지출", "수입"])
        c_main = st.selectbox("대분류", ["식비", "생활용품", "주거/통신", "교통", "건강", "금융", "경조사", "자산이동"])
        c_sub = st.text_input("소분류")
        content = st.text_input("상세 내용")
        a_input = st.number_input("금액(원)", min_value=0, step=1000)
        if st.button("전송", use_container_width=True):
            if a_input > 0 and send_to_sheet(t_choice, c_main, c_sub, content, a_input):
                st.success("시트 전송 완료")
                st.rerun()

    df_assets_raw = load_sheet_data(GID_MAP["Assets"])
    df_log = load_sheet_data(GID_MAP["Log"])
    
    cash_diff, card_debt = 0, 0
    if not df_log.empty:
        for _, row in df_log.iterrows():
            try:
                val = to_numeric(row.iloc[5]) 
                if row.iloc[1] == "지출":
                    if row.iloc[2] == "자산이동": cash_diff -= val
                    else: card_debt += val
                elif row.iloc[1] == "수입":
                    if row.iloc[2] != "자산이동": cash_diff += val
            except: continue

    if not df_assets_raw.empty:
        df_assets = df_assets_raw.iloc[:, :2].copy()
        df_assets.columns = ["항목", "금액"]
        df_assets["val"] = df_assets["금액"].apply(to_numeric)
    
        # 가용현금 실시간 보정
        cash_idx = df_assets[df_assets['항목'].str.contains('가용현금', na=False)].index
        if not cash_idx.empty: df_assets.at[cash_idx[0], 'val'] += cash_diff
        
        # 카드 지출 반영
        if card_debt > 0:
            df_assets = pd.concat([df_assets, pd.DataFrame([{"항목": "이번달 카드지출", "val": -card_debt}])], ignore_index=True)

        a_df = df_assets[df_assets["val"] >= 0].copy()
        l_df = df_assets[df_assets["val"] < 0].copy()
        net_worth = a_df["val"].sum() + l_df["val"].sum()

        st.markdown(f"""<div class="net-box"><small>시트 연동 통합 순자산</small><br><span style="font-size:2.5em; color:{COLOR_ASSET}; font-weight:bold;">{format_krw(net_worth)}</span></div>""", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("보유 자산")
            st.table(a_df.assign(금액=a_df["val"].apply(format_krw))[["항목", "금액"]])
        with c2:
            st.subheader("부채 및 지출")
            if not l_df.empty: st.table(l_df.assign(금액=l_df["val"].apply(lambda x: format_krw(abs(x))))[["항목", "금액"]])
            st.metric("실시간 지출 합계", format_krw(card_debt))

# 탭 2: 식단 & 건강
elif menu == "식단 & 건강":
    st.header("영양 섭취 분석")
    
    with st.sidebar:
        st.subheader("영양 기록 (FatSecret 순서)")
        with st.form("health_input"):
            in_w = st.number_input("현재 체중 (kg)", 50.0, 150.0, 125.0, step=0.1)
            st.divider()
            # 지방, 콜레스테롤, 나트륨, 탄수화물, 식이섬유, 당, 단백질
            in_fat = st.number_input("지방 (g)", 0, 500, 0)
            in_chole = st.number_input("콜레스테롤 (mg)", 0, 1000, 0)
            in_na = st.number_input("나트륨 (mg)", 0, 5000, 0)
            in_carb = st.number_input("탄수화물 (g)", 0, 1000, 0)
            in_fiber = st.number_input("식이섬유 (g)", 0, 200, 0)
            in_sugar = st.number_input("당 (g)", 0, 500, 0)
            in_prot = st.number_input("단백질 (g)", 0, 500, 0)
            
            if st.form_submit_button("기록 저장", use_container_width=True):
                send_to_sheet("건강", "기록", "체중", "정원", in_w, corpus="Health")
                nutris = {"지방": in_fat, "콜레스테롤": in_chole, "나트륨": in_na, "탄수화물": in_carb, "식이섬유": in_fiber, "당": in_sugar, "단백질": in_prot}
                for k, v in nutris.items():
                    if v > 0: send_to_sheet("식단", "영양소", k, "정원", v, corpus="Health")
                st.success("기록 완료")
                st.rerun()

    df_log = load_sheet_data(GID_MAP["Log"])
    today_str = get_current_time().split(' ')[0]
    NUTRI_ORDER = ["지방", "콜레스테롤", "나트륨", "탄수화물", "식이섬유", "당", "단백질"]
    
    cur_nutri = {k: 0 for k in NUTRI_ORDER}
    if not df_log.empty:
        df_today = df_log[df_log.iloc[:, 0].astype(str).str.contains(today_str)]
        for k in NUTRI_ORDER:
            try: cur_nutri[k] = df_today[(df_today.iloc[:, 1] == '식단') & (df_today.iloc[:, 3] == k)].iloc[:, 5].apply(to_numeric).sum()
            except: continue

    c_s1, c_s2 = st.columns([5, 5])
    with c_s1:
        st.subheader("오늘의 영양 현황")
        stat_df = pd.DataFrame([{"영양소": k, "현재량": f"{cur_nutri[k]:,.1f}"} for k in NUTRI_ORDER])
        st.table(stat_df.set_index("영양소"))
    with c_s2:
        st.subheader("목표 달성")
        for n, t in {"단백질": 160, "탄수화물": 360, "지방": 90}.items():
            val = cur_nutri[n]
            st.caption(f"{n} ({val:,.1f} / {t}g)")
            st.progress(min(val / t, 1.0) if t > 0 else 0)

# 탭 3: 재고 관리
elif menu == "재고 관리":
    st.header("창고 및 자산 재고 현황")
    
    if 'inventory' not in st.session_state:
        st.session_state.inventory = pd.DataFrame([
            {"구분": "귀중품", "항목": "금(실물)", "수량": "16g", "비고": "자산 연동"},
            {"구분": "상온", "항목": "올리브유/알룰로스/스테비아/사과식초", "수량": "보유", "비고": "-"},
            {"구분": "상온", "항목": "진간장/국간장/맛술/굴소스/저당케찹", "수량": "보유", "비고": "-"},
            {"구분": "곡물", "항목": "카무트/현미/쌀", "수량": "보유", "비고": "-"},
            {"구분": "냉동", "항목": "냉동 삼치/닭다리살/토마토 페이스트", "수량": "보유", "비고": "냉동보관"},
            {"구분": "냉동", "항목": "단백질 쉐이크(9개)", "수량": "보유", "비고": "-"}
        ])

    st.data_editor(st.session_state.inventory, num_rows="dynamic", use_container_width=True, key="inv_editor")

# --- [6. 공통 하단] ---
st.divider()
if st.button("새로고침 및 동기화", use_container_width=True):
    st.cache_data.clear()
    st.rerun()
