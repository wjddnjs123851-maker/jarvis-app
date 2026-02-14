import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime, timedelta

# --- [1. 시스템 설정] ---
SPREADSHEET_ID = '17kw1FMK50MUpAWA9VPSile8JZeeq6TZ9DWJqMRaBMUM'
GID_MAP = {"Log": "1716739583", "Finance": "1790876407", "Assets": "1666800532"}
API_URL = "https://script.google.com/macros/s/AKfycbzX1w7136qfFsnRb0RMQTZvJ1Q_-GZb5HAwZF6yfKiLTHbchJZq-8H2GXjV2z5WnkmI4A/exec"

FIXED_DATA = {
    "stocks": {
        "삼성전자": {"평단": 78895, "수량": 46},
        "SK하이닉스": {"평단": 473521, "수량": 6},
        "삼성중공업": {"평단": 16761, "수량": 88},
        "동성화인텍": {"평단": 22701, "수량": 21}
    },
    "crypto": {
        "BTC": {"평단": 137788139, "수량": 0.00181400},
        "ETH": {"평단": 4243000, "수량": 0.03417393}
    },
    "precious_metals": {
        "금(Gold)": {"보유량(g)": 0, "평단": 0} # 필요시 업데이트
    }
}

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
        res = requests.post(API_URL, data=json.dumps(payload), timeout=5)
        return res.status_code == 200
    except: return False

@st.cache_data(ttl=10)
def load_assets():
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={GID_MAP['Assets']}"
    try:
        df = pd.read_csv(url)
        return df.dropna().reset_index(drop=True)
    except: return pd.DataFrame()

# --- [3. 메인 인터페이스 스타일] ---
st.set_page_config(page_title="JARVIS v32.6", layout="wide")
# 오른쪽 정렬 스타일 적용
st.markdown("<style>.stTable td { text-align: right !important; }</style>", unsafe_allow_html=True)

with st.sidebar:
    st.title("JARVIS 제어 센터")
    menu = st.radio("메뉴 선택", ["식단 & 건강", "투자 & 자산", "재고 관리"])
    st.divider()
    
    if menu == "식단 & 건강":
        st.subheader("데이터 입력")
        in_w = st.number_input("체중(kg)", 0.0, 150.0, 125.0)
        # 보스 요청 순서: 지방, 콜레스테롤, 나트륨, 탄수화물, 식이섬유, 당, 단백질
        in_fat = st.number_input("지방 (g)", 0)
        in_chol = st.number_input("콜레스테롤 (mg)", 0)
        in_na = st.number_input("나트륨 (mg)", 0)
        in_carb = st.number_input("탄수화물 (g)", 0)
        in_fiber = st.number_input("식이섬유 (g)", 0)
        in_sugar = st.number_input("당 (g)", 0)
        in_prot = st.number_input("단백질 (g)", 0)
        in_kcal = st.number_input("칼로리 (kcal)", 0)
        
        if st.button("시트로 전송", use_container_width=True):
            send_to_sheet("건강", "체중", in_w)
            d_map = {"지방": in_fat, "콜레스테롤": in_chol, "나트륨": in_na, "탄수화물": in_carb, 
                     "식이섬유": in_fiber, "당": in_sugar, "단백질": in_prot, "칼로리": in_kcal}
            for k, v in d_map.items():
                if v > 0: send_to_sheet("식단", k, v)
            st.success("완료")

# --- [4. 메인 화면] ---
st.title(f"시스템: {menu}")

if menu == "투자 & 자산":
    # 1. 시트 기반 자산 (현금, 금, 부채 등)
    df_raw = load_assets()
    st.subheader("현금 및 기타 자산 현황")
    if not df_raw.empty:
        df_display = df_raw.copy()
        df_display.columns = ["항목", "금액"]
        df_display["금액"] = df_display["금액"].apply(format_krw)
        st.table(df_display)
    
    # 2. 투자 자산 (주식/코인)
    st.subheader("주식 및 코인 현황")
    inv_data = []
    for category, items in {"주식": FIXED_DATA["stocks"], "코인": FIXED_DATA["crypto"]}.items():
        for name, info in items.items():
            value = info['평단'] * info['수량']
            inv_data.append({"분류": category, "항목": name, "평가액": format_krw(value)})
    
    st.table(pd.DataFrame(inv_data))

elif menu == "식단 & 건강":
    st.info("사이드바에서 데이터를 입력하면 시트에 기록됩니다.")
    # 향후 시트에서 최근 7일 데이터를 불러와 요약 표를 보여주는 기능을 추가할 수 있습니다.

elif menu == "재고 관리":
    st.subheader("생활용품 및 식자재 재고")
    # 기본 틀 구성
    stock_df = pd.DataFrame([
        {"카테고리": "주방", "품목": "쌀", "잔량": "적정", "메모": "-"},
        {"카테고리": "욕실", "품목": "샴푸", "잔량": "부족", "메모": "구매 필요"},
        {"카테고리": "건강", "품목": "닭가슴살", "잔량": "여유", "메모": "냉동실 확인"}
    ])
    st.table(stock_df)
    st.caption("※ 재고 데이터는 '재고' 시트와 연동하여 관리할 수 있도록 확장이 가능합니다.")
