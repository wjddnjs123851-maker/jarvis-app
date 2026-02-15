import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime, timedelta

# --- [1. 시스템 설정 및 원칙 준수] ---
SPREADSHEET_ID = '12cPPhM68K3SopQJtZyWEq8adDuP98bJ4efoYbjFDDOI'
GID_MAP = {
    "Log": "0", 
    "Assets": "1068342666", 
    "Report": "308599580",
    "Health": "123456789"
}
API_URL = "https://script.google.com/macros/s/AKfycbzX1w7136qfFsnRb0RMQTZvJ1Q_-GZb5HAwZF6yfKiLTHbchJZq-8H2GXjV2z5WnkmI4A/exec"

# 디자인 원칙: 다크모드 및 자산/부채 색상 규정 준수
COLOR_BG = "#0e1117"
COLOR_ASSET = "#4dabf7"  # 자산/수입 (파랑)
COLOR_DEBT = "#ff922b"   # 부채/지출 (주황)

# --- [2. 유틸리티 함수] ---
def format_krw(val): 
    # 원칙: 숫자는 3자리 콤마 + 우측 정렬 필수
    return f"{int(val):,}".rjust(20) + " 원"

def to_numeric(val):
    try:
        if pd.isna(val): return 0
        s = "".join(filter(lambda x: x.isdigit() or x == '-', str(val)))
        return int(s) if s else 0
    except: return 0

def get_current_time():
    now = datetime.utcnow() + timedelta(hours=9)
    return now.strftime('%Y-%m-%d %H:%M:%S')

def get_weather():
    try:
        w_url = "https://api.open-meteo.com/v1/forecast?latitude=36.99&longitude=127.11&current_weather=true&timezone=auto"
        res = requests.get(w_url, timeout=2).json()
        temp = res['current_weather']['temperature']
        return f"☀️ {temp}°C"
    except: return "날씨 로드 실패"

def load_sheet_data(gid):
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={gid}&t={datetime.now().timestamp()}"
    try:
        df = pd.read_csv(url)
        return df.dropna(how='all')
    except: return pd.DataFrame()

def send_to_sheet(d_type, cat_main, cat_sub, content, value, method, corpus="Log"):
    # 지출 수단(method) 매개변수 추가 적용
    payload = {
        "time": get_current_time().split(' ')[0],
        "corpus": corpus, "type": d_type, "cat_main": cat_main, 
        "cat_sub": cat_sub, "item": content, "value": value, 
        "method": method, "user": "정원"
    }
    try: return requests.post(API_URL, data=json.dumps(payload), timeout=5).status_code == 200
    except: return False

# --- [3. 메인 레이아웃 및 디자인] ---
st.set_page_config(page_title="JARVIS v47.0", layout="wide")
st.markdown(f"""
    <style>
    .stApp {{ background-color: {COLOR_BG}; color: #ffffff; }}
    [data-testid="stMetricValue"] {{ text-align: right !important; }}
    [data-testid="stTable"] {{ background-color: #1d2129; }}
    th {{ color: #ffffff !important; text-align: center !important; }}
    td {{ color: #ffffff !important; text-align: right !important; }}
    .net-box {{ background-color: #1d2129; padding: 25px; border-radius: 12px; border-left: 5px solid {COLOR_ASSET}; margin-bottom: 20px; }}
    .stat-card {{ background-color: #1d2129; padding: 15px; border-radius: 10px; text-align: right; }}
    </style>
""", unsafe_allow_html=True)

# 헤더 정보
t_c1, t_c2 = st.columns([7, 3])
with t_c1: 
    st.markdown(f"### {get_current_time()} | 평택 {get_weather()}")
with t_c2: 
    st.markdown(f"<div style='text-align:right; color:{COLOR_ASSET}; font-weight:bold;'>JARVIS v47.0 ONLINE</div>", unsafe_allow_html=True)

# --- [4. 사이드바: 입력 제어] ---
with st.sidebar:
    st.title("JARVIS CONTROL")
    menu = st.radio("MENU", ["투자 & 자산", "식단 & 건강", "재고 관리"])
    st.divider()
    
    if menu == "투자 & 자산":
        st.subheader("데이터 입력")
        t_choice = st.selectbox("구분", ["지출", "수입"])
        c_main = st.selectbox("대분류", ["식비", "생활용품", "주거/통신", "교통", "건강", "금융", "경조사", "자산이동"])
        c_sub = st.text_input("소분류 (항목)")
        content = st.text_input("상세 내용")
        a_input = st.number_input("금액(원)", min_value=0, step=1000)
        # 신규 추가: 지출 수단 (결제 수단)
        method_choice = st.selectbox("지출 수단", ["현금", "신용카드", "체크카드", "계좌이체", "포인트"])
        
        if st.button("데이터 전송", use_container_width=True):
            if a_input > 0 and send_to_sheet(t_choice, c_main, c_sub, content, a_input, method_choice):
                st.cache_data.clear(); st.rerun()

# --- [5. 메인 화면: 투자 & 자산] ---
if menu == "투자 & 자산":
    df_assets = load_sheet_data(GID_MAP["Assets"])
    if not df_assets.empty:
        df_assets = df_assets.iloc[:, [0, 1]].copy()
        df_assets.columns = ["항목", "금액"]
        df_assets["val"] = df_assets["금액"].apply(to_numeric)
        
        a_df = df_assets[df_assets["val"] > 0].copy()
        l_df = df_assets[df_assets["val"] < 0].copy()
        
        sum_asset = a_df["val"].sum()
        sum_debt = l_df["val"].sum()
        net_worth = sum_asset + sum_debt

        # 원칙: 합계는 최상단 노출 (순자산, 자산총계, 부채총계)
        st.markdown(f"""
            <div class="net-box">
                <small style='color:#888;'>통합 순자산 (Net Worth)</small><br>
                <span style="font-size:2.8em; color:{COLOR_ASSET}; font-weight:bold;">{net_worth:,.0f} 원</span>
            </div>
        """, unsafe_allow_html=True)

        m1, m2 = st.columns(2)
        with m1:
            st.markdown(f"""<div class="stat-card"><small style='color:{COLOR_ASSET};'>자산 총계</small><br><h3 style='color:{COLOR_ASSET};'>{sum_asset:,.0f} 원</h3></div>""", unsafe_allow_html=True)
        with m2:
            st.markdown(f"""<div class="stat-card"><small style='color:{COLOR_DEBT};'>부채 총계</small><br><h3 style='color:{COLOR_DEBT};'>{abs(sum_debt):,.0f} 원</h3></div>""", unsafe_allow_html=True)

        st.divider()

        c1, c2 = st.columns(2)
        with c1:
            st.subheader("자산 세부 내역")
            st.table(a_df.assign(금액=a_df["val"].apply(format_krw))[["항목", "금액"]])
        with c2:
            st.subheader("부채 세부 내역")
            if not l_df.empty:
                st.table(l_df.assign(금액=l_df["val"].apply(lambda x: format_krw(abs(x))))[["항목", "금액"]])

elif menu == "식단 & 건강":
    st.header("건강 비서 대시보드")
    # 원칙 준수: 기존 기능 유지
    st.info("지방 → 콜레스테롤 → 나트륨 → 탄수화물 → 식이섬유 → 당 → 단백질 순서로 영양소를 관리합니다.")

elif menu == "재고 관리":
    st.header("창고 전수조사 리스트")
    # 원칙 준수: 기존 데이터 삭제 금지
    if 'inventory' not in st.session_state:
        st.session_state.inventory = pd.DataFrame([
            {"구분": "자산", "항목": "금(실물)", "수량": "16g", "비고": "금고"},
            {"구분": "상온", "항목": "올리브유/알룰로스/스테비아", "수량": "보유", "비고": "보유중"},
            {"구분": "냉동", "항목": "삼치/닭다리살/쉐이크", "수량": "보유", "비고": "냉동"}
        ])
    st.data_editor(st.session_state.inventory, num_rows="dynamic", use_container_width=True)

st.sidebar.button("새로고침", on_click=st.cache_data.clear)
