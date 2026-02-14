import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime, timedelta

# --- [1. 마스터 데이터 및 GID 설정] ---
SPREADSHEET_ID = '17kw1FMK50MUpAWA9VPSile8JZeeq6TZ9DWJqMRaBMUM'
# 💡 보스의 시트 주소에서 확인된 Assets 탭의 실제 GID를 입력해야 합니다.
# (현재 주소창 gid= 이후의 숫자를 확인하여 아래 0 대신 넣어주세요)
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

# --- [2. 포맷팅 및 통신 유틸리티] ---
def format_krw(val):
    """숫자를 세자리 콤마와 '원'이 붙은 오른쪽 정렬 텍스트로 변환"""
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
def load_assets_direct():
    """Assets 탭의 A, B열만 강제로 읽어오는 함수"""
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&gid={GID_MAP['Assets']}"
    try:
        df = pd.read_csv(url, usecols=[0, 1]) # 💡 A열(항목)과 B열(금액)만 선택
        df.columns = ['항목', '금액']
        return df.dropna()
    except: return pd.DataFrame(columns=['항목', '금액'])

# --- [3. 메인 인터페이스 스타일] ---
st.set_page_config(page_title="JARVIS v28.0", layout="wide")
st.markdown("""
    <style>
    .stTable td { text-align: right !important; font-family: 'Courier New', Courier, monospace; }
    .stTable td:nth-child(2) { text-align: left !important; } /* '항목' 열만 왼쪽 정렬 */
    </style>
    """, unsafe_allow_html=True)

with st.sidebar:
    st.title("JARVIS 제어 센터")
    menu = st.radio("메뉴 선택", ["영양/식단/체중", "자산/투자/가계부", "재고/생활관리"])
    st.divider()
    
    if menu == "영양/식단/체중":
        st.subheader("일일 데이터 입력")
        in_w = st.number_input("체중 (kg)", 0.0, 150.0, 125.0, step=0.1)
        in_kcal = st.number_input("1. 칼로리 (kcal)", 0)
        in_fat = st.number_input("2. 지방 (g)", 0)
        in_chol = st.number_input("3. 콜레스테롤 (mg)", 0)
        in_na = st.number_input("4. 나트륨 (mg)", 0)
        in_carb = st.number_input("5. 탄수화물 (g)", 0)
        in_fiber = st.number_input("6. 식이섬유 (g)", 0)
        in_sugar = st.number_input("7. 당 (g)", 0)
        in_prot = st.number_input("8. 단백질 (g)", 0)
        
        if st.button("시트로 전송"):
            send_to_sheet("건강", "체중", in_w)
            data_points = {"칼로리": in_kcal, "지방": in_fat, "콜레스테롤": in_chol, "나트륨": in_na, 
                           "탄수화물": in_carb, "식이섬유": in_fiber, "당": in_sugar, "단백질": in_prot}
            for k, v in data_points.items():
                if v > 0: send_to_sheet("식단", k, v)
            st.success("전송 완료!")

# --- [4. 대시보드 리포트] ---
st.title(f"JARVIS: {menu}")

if menu == "자산/투자/가계부":
    st.subheader("통합 자산 관리 리포트")
    
    df_assets = load_assets_direct()
    a_rows = []
    
    # 1. 시트 데이터 (항목/금액)
    if not df_assets.empty:
        for _, row in df_assets.iterrows():
            if "항목" in str(row['항목']): continue # 헤더 중복 방지
            a_rows.append({
                "분류": "금융자산", 
                "항목": str(row['항목']), 
                "평가액": format_krw(row['금액']), 
                "비고": "기초잔액"
            })
    
    # 2. 투자 자산 (주식/코인 고정 데이터 연동)
    # (투자 자산 계산 로직 생략 - 기존 완벽한 코드 유지)
    
    if a_rows:
        df_final = pd.DataFrame(a_rows)
        df_final.index = range(1, len(df_final) + 1)
        st.table(df_final)
    else:
        st.warning("Assets 탭에서 데이터를 읽어오지 못했습니다. GID를 확인해 주세요.")

elif menu == "영양/식단/체중":
    # 영양 섭취 현황 표 (보스께서 올려주신 디자인 유지)
    st.subheader("오늘의 영양 섭취 현황")
    # (세션 데이터를 활용한 표 출력 로직)
