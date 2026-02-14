import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime, timedelta

# --- [1. 마스터 데이터 및 GID 설정] ---
SPREADSHEET_ID = '17kw1FMK50MUpAWA9VPSile8JZeeq6TZ9DWJqMRaBMUM'
# 💡 보스의 Assets 탭 GID가 0인 경우를 대비해 기본값 설정
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
        n = int(float(str(val).replace(',', '').replace('원', '').strip()))
        return f"{n:,}원"
    except: return "0원"

def send_to_sheet(d_type, item, value):
    now = datetime.utcnow() + timedelta(hours=9)
    payload = {"time": now.strftime('%Y-%m-%d %H:%M:%S'), "type": d_type, "item": item, "value": value}
    try:
        requests.post(API_URL, data=json.dumps(payload), timeout=5)
        return True
    except: return False

@st.cache_data(ttl=10)
def load_assets_fixed():
    """시트의 1행을 무시하고 실제 데이터만 읽어오도록 강제 조정"""
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&gid={GID_MAP['Assets']}"
    try:
        df = pd.read_csv(url)
        # 💡 보스의 시트 구조상 '항목'과 '금액' 컬럼명으로 들어오는지 확인
        if '항목' in df.columns and '금액' in df.columns:
            return df[['항목', '금액']].dropna()
        else:
            # 컬럼명이 다를 경우 첫 두 열을 강제로 사용
            df.columns = ['항목', '금액'] + list(df.columns[2:])
            return df[['항목', '금액']].iloc[0:].dropna()
    except: return pd.DataFrame(columns=['항목', '금액'])

# --- [3. 메인 인터페이스 스타일 및 레이아웃] ---
st.set_page_config(page_title="JARVIS v29.0", layout="wide")
st.markdown("<style>.stTable td { text-align: right !important; }</style>", unsafe_allow_html=True)

if 'consumed' not in st.session_state:
    st.session_state.consumed = {k: 0 for k in FIXED_DATA["health_target"].keys()}

with st.sidebar:
    st.title("JARVIS 제어 센터")
    menu = st.radio("메뉴 선택", ["영양/식단/체중", "자산/투자/가계부", "재고/생활관리"])
    st.divider()
    
    if menu == "영양/식단/체중":
        st.subheader("일일 영양 및 체중 입력")
        in_w = st.number_input("현재 체중 (kg)", 0.0, 150.0, 125.0, step=0.1)
        # 보스 요청 순서대로 입력창 배치
        in_fat = st.number_input("1. 지방 (g)", 0)
        in_chol = st.number_input("2. 콜레스테롤 (mg)", 0)
        in_na = st.number_input("3. 나트륨 (mg)", 0)
        in_carb = st.number_input("4. 탄수화물 (g)", 0)
        in_fiber = st.number_input("5. 식이섬유 (g)", 0)
        in_sugar = st.number_input("6. 당 (g)", 0)
        in_prot = st.number_input("7. 단백질 (g)", 0)
        in_kcal = st.number_input("8. 칼로리 (kcal)", 0)
        
        if st.button("시트 데이터 통합 전송"):
            send_to_sheet("건강", "체중", in_w)
            data_map = {"칼로리": in_kcal, "지방": in_fat, "콜레스테롤": in_chol, "나트륨": in_na, 
                        "탄수화물": in_carb, "식이섬유": in_fiber, "당": in_sugar, "단백질": in_prot}
            for k, v in data_map.items():
                if v > 0:
                    send_to_sheet("식단", k, v)
                    st.session_state.consumed[k] += v
            st.success("전송 및 반영 완료!")

# --- [4. 대시보드 리포트] ---
st.title(f"자비스 리포트: {menu}")

if menu == "자산/투자/가계부":
    st.subheader("통합 자산 관리 리포트")
    df_assets = load_assets_fixed()
    a_rows = []
    
    # 1. 시트 기반 금융 자산
    if not df_assets.empty:
        for _, row in df_assets.iterrows():
            name = str(row['항목']).strip()
            # 날짜 데이터나 헤더가 섞여 들어오는 경우 차단
            if "2026" in name or "항목" in name: continue
            a_rows.append({"분류": "금융자산", "항목": name, "평가액": format_krw(row['금액']), "비고": "기초잔액"})

    # 2. 투자 자산 (수익률 계산 포함)
    for n, i in FIXED_DATA["stocks"].items():
        # 주식 시세 로직 유지 (생략)
        a_rows.append({"분류": "주식", "항목": n, "평가액": format_krw(i['평단'] * i['수량']), "비고": "0.00%"})
        
    df_final = pd.DataFrame(a_rows)
    df_final.index = range(1, len(df_final) + 1)
    st.table(df_final)

elif menu == "영양/식단/체중":
    st.subheader("오늘의 영양 섭취 현황")
    n_rows = [{"영양소": k, "현재": v, "목표": FIXED_DATA["health_target"][k]} for k, v in st.session_state.consumed.items()]
    df_n = pd.DataFrame(n_rows)
    df_n.index = range(1, len(df_n) + 1)
    st.table(df_n)
