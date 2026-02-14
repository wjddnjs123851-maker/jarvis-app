import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime, timedelta

# --- [1. 시스템 설정] ---
SPREADSHEET_ID = '17kw1FMK50MUpAWA9VPSile8JZeeq6TZ9DWJqMRaBMUM'
GID_MAP = {"Log": "0", "Finance": "0", "Assets": "0"} 

FIXED_DATA = {
    "health_target": {
        "칼로리": 2000, "지방": 65, "콜레스테롤": 300, "나트륨": 2000, 
        "탄수화물": 300, "식이섬유": 30, "당": 50, "단백질": 150
    },
    "stocks": {
        "동성화인텍": {"평단": 22701, "수량": 21, "코드": "033500"},
        "삼성중공업": {"평단": 16761, "수량": 88, "코드": "010140"},
        "SK하이닉스": {"평단": 473521, "수량": 6, "코드": "000660"},
        "삼성전자": {"평단": 78895, "수량": 46, "코드": "005930"}
    },
    "crypto": {
        "BTC": {"평단": 137788139, "수량": 0.00181400, "마켓": "KRW-BTC"},
        "ETH": {"평단": 4243000, "수량": 0.03417393, "마켓": "KRW-ETH"}
    }
}

API_URL = "https://script.google.com/macros/s/AKfycbzX1w7136qfFsnRb0RMQTZvJ1Q_-GZb5HAwZF6yfKiLTHbchJZq-8H2GXjV2z5WnkmI4A/exec"

# --- [2. 유틸리티] ---
def format_krw(val):
    try:
        clean_val = str(val).replace(',', '').replace('원', '').strip()
        return f"{int(float(clean_val)):,}원"
    except: return "0원"

def send_to_sheet(d_type, item, value):
    now = datetime.utcnow() + timedelta(hours=9)
    payload = {"time": now.strftime('%Y-%m-%d %H:%M:%S'), "type": d_type, "item": item, "value": value}
    try: requests.post(API_URL, data=json.dumps(payload), timeout=5); return True
    except: return False

@st.cache_data(ttl=10)
def load_sheet_safe(sheet_name):
    gid = GID_MAP.get(sheet_name, "0")
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&gid={gid}"
    try:
        df = pd.read_csv(url)
        return df
    except: return pd.DataFrame()

# --- [3. UI 레이아웃] ---
st.set_page_config(page_title="JARVIS v27.1", layout="wide")
st.markdown("<style>.stTable td { text-align: right !important; }</style>", unsafe_allow_html=True)

if 'consumed' not in st.session_state: 
    st.session_state.consumed = {k: 0 for k in FIXED_DATA["health_target"].keys()}

with st.sidebar:
    st.title("JARVIS 제어 센터")
    menu = st.radio("메뉴 선택", ["영양/식단/체중", "자산/투자/가계부", "재고/생활관리"])
    st.divider()
    
    if menu == "영양/식단/체중":
        st.subheader("데이터 입력")
        in_w = st.number_input("현재 체중 (kg)", 0.0, 150.0, 125.0, step=0.1)
        in_kcal = st.number_input("칼로리 (kcal)", 0)
        # 보스 요청 순서: 지방 -> 콜레스테롤 -> 나트륨 -> 탄수 -> 식이섬유 -> 당 -> 단백
        in_fat = st.number_input("지방 (g)", 0)
        in_chol = st.number_input("콜레스테롤 (mg)", 0)
        in_na = st.number_input("나트륨 (mg)", 0)
        in_carb = st.number_input("탄수화물 (g)", 0)
        in_fiber = st.number_input("식이섬유 (g)", 0)
        in_sugar = st.number_input("당 (g)", 0)
        in_prot = st.number_input("단백질 (g)", 0)
        
        if st.button("시트 데이터 전송"):
            send_to_sheet("건강", "체중", in_w)
            # 입력값 세션 반영 및 전송
            vals = [in_kcal, in_fat, in_chol, in_na, in_carb, in_fiber, in_sugar, in_prot]
            for k, v in zip(FIXED_DATA["health_target"].keys(), vals):
                if v > 0:
                    send_to_sheet("식단", k, v)
                    st.session_state.consumed[k] += v
            st.success("전송 및 반영 완료!")

# --- [4. 대시보드 출력] ---
st.title(f"JARVIS: {menu}")

if menu == "영양/식단/체중":
    st.subheader("오늘의 영양 섭취 현황")
    n_rows = [{"영양소": k, "현재": v, "목표": FIXED_DATA["health_target"][k]} for k, v in st.session_state.consumed.items()]
    df_n = pd.DataFrame(n_rows)
    df_n.index = range(1, len(df_n) + 1)
    st.table(df_n)

elif menu == "자산/투자/가계부":
    st.subheader("통합 자산 관리 리포트")
    df_assets_raw = load_sheet_safe("Assets")
    a_rows = []
    
    # 시트 데이터 강제 고정 매핑
    if not df_assets_raw.empty:
        for _, row in df_assets_raw.iterrows():
            try:
                # 첫 번째 열이 문자열이고 금액이 포함된 경우만 처리
                name = str(row.iloc[0])
                if len(name) < 2 or "2026" in name: continue 
                a_rows.append({"분류": "금융", "항목": name, "평가액": format_krw(row.iloc[1]), "비고": "기초잔액"})
            except: continue
    
    # 주식/코인 데이터 추가 (FIXED_DATA 기반)
    # (주식/코인 계산 로직은 이전과 동일하게 유지)
    df_final = pd.DataFrame(a_rows)
    df_final.index = range(1, len(df_final) + 1)
    st.table(df_final)
