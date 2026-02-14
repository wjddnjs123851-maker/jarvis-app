import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime, timedelta

# --- [1. 시스템 설정] ---
SPREADSHEET_ID = '17kw1FMK50MUpAWA9VPSile8JZeeq6TZ9DWJqMRaBMUM'
GID_MAP = {"Log": "1716739583", "Finance": "1790876407", "Assets": "1666800532"}
API_URL = "https://script.google.com/macros/s/AKfycbzX1w7136qfFsnRb0RMQTZvJ1Q_-GZb5HAwZF6yfKiLTHbchJZq-8H2GXjV2z5WnkmI4A/exec"

EXPENSE_CATS = ["식비(집밥)", "식비(외식)", "식비(배달)", "식비(편의점)", "생활용품", "건강/의료", "기호품", "주거/통신", "교통/차량", "금융/보험", "결혼준비", "경조사", "기타지출"]
INCOME_CATS = ["급여", "금융소득", "기타"]

FIXED_DATA = {
    "stocks": {
        "삼성전자": {"평단": 78895, "수량": 46}, "SK하이닉스": {"평단": 473521, "수량": 6},
        "삼성중공업": {"평단": 16761, "수량": 88}, "동성화인텍": {"평단": 22701, "수량": 21}
    },
    "crypto": {
        "BTC": {"평단": 137788139, "수량": 0.00181400}, "ETH": {"평단": 4243000, "수량": 0.03417393}
    }
}

# --- [2. 유틸리티] ---
def format_krw(val):
    return f"{int(val):,}"

def to_numeric(val):
    try: return int(float(str(val).replace(',', '').replace('원', '').strip()))
    except: return 0

def send_to_sheet(d_type, item, value):
    now = datetime.utcnow() + timedelta(hours=9)
    payload = {"time": now.strftime('%Y-%m-%d %H:%M:%S'), "type": d_type, "item": item, "value": value}
    try:
        res = requests.post(API_URL, data=json.dumps(payload), timeout=5)
        return res.status_code == 200
    except: return False

@st.cache_data(ttl=5)
def load_sheet_data(gid):
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={gid}"
    try:
        df = pd.read_csv(url)
        return df.dropna().reset_index(drop=True)
    except: return pd.DataFrame()

# --- [3. 메인 설정] ---
st.set_page_config(page_title="JARVIS v33.6", layout="wide")
st.markdown("""
    <style>
    .stTable td { text-align: right !important; }
    .total-box { text-align: right; font-size: 1.2em; font-weight: bold; padding: 10px; border-top: 2px solid #eee; }
    .net-wealth { font-size: 2.5em !important; font-weight: bold; color: #1E90FF; text-align: left; margin-top: 20px; border-top: 3px solid #1E90FF; padding-top: 10px; }
    .input-card { background-color: #f8f9fa; padding: 20px; border-radius: 10px; border: 1px solid #dee2e6; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

with st.sidebar:
    st.title("JARVIS 제어 센터")
    menu = st.radio("메뉴 선택", ["투자 & 자산", "식단 & 건강", "재고 관리"])

# --- [4. 메인 화면 로직] ---
st.title(f"시스템: {menu}")

if menu == "투자 & 자산":
    # A. 가계부 입력 영역 (상단 배치)
    st.markdown('<div class="input-card">', unsafe_allow_html=True)
    st.subheader("📝 오늘의 재무 활동 기록")
    i_col1, i_col2, i_col3, i_col4 = st.columns([1, 2, 2, 1])
    
    with i_col1:
        type_choice = st.selectbox("구분", ["지출", "수입"], key="fin_type")
    with i_col2:
        cats = EXPENSE_CATS if type_choice == "지출" else INCOME_CATS
        cat_choice = st.selectbox("카테고리", cats, key="fin_cat")
    with i_col3:
        amount_input = st.number_input("금액(원)", min_value=0, step=1000, key="fin_amt")
    with i_col4:
        st.write("") # 간격 맞춤용
        st.write("") 
        if st.button("기록하기", use_container_width=True):
            if amount_input > 0:
                if send_to_sheet(type_choice, cat_choice, amount_input):
                    st.success(f"기록 완료!")
                else:
                    st.error("전송 실패")
    st.markdown('</div>', unsafe_allow_html=True)

    # B. 자산 현황 테이블
    df_sheet = load_sheet_data(GID_MAP["Assets"])
    df_sheet.columns = ["항목", "금액"]
    df_sheet["val"] = df_sheet["금액"].apply(to_numeric)
    
    inv_rows = []
    for cat_name, items in {"주식": FIXED_DATA["stocks"], "코인": FIXED_DATA["crypto"]}.items():
        for name, info in items.items():
            val = info['평단'] * info['수량']
            inv_rows.append({"항목": name, "val": val})
    
    df_total = pd.concat([df_sheet, pd.DataFrame(inv_rows)], ignore_index=True)
    assets_df = df_total[df_total["val"] >= 0].copy()
    liabs_df = df_total[df_total["val"] < 0].copy()

    col_a, col_l = st.columns(2)
    with col_a:
        st.subheader("💰 자산 목록")
        assets_df["금액"] = assets_df["val"].apply(lambda x: f"{format_krw(x)}원")
        assets_df.index = range(1, len(assets_df) + 1)
        st.table(assets_df[["항목", "금액"]])
        st.markdown(f'<div class="total-box">자산 총계: {format_krw(assets_df["val"].sum())}원</div>', unsafe_allow_html=True)
        
    with col_l:
        st.subheader("📉 부채 목록")
        liabs_df["금액"] = liabs_df["val"].apply(lambda x: f"{format_krw(abs(x))}원")
        liabs_df.index = range(1, len(liabs_df) + 1)
        st.table(liabs_df[["항목", "금액"]])
        st.markdown(f'<div class="total-box" style="color: #ff4b4b;">부채 총계: {format_krw(abs(liabs_df["val"].sum()))}원</div>', unsafe_allow_html=True)

    net_wealth = assets_df["val"].sum() + liabs_df["val"].sum()
    st.markdown(f'<div class="net-wealth">종합 순자산: {format_krw(net_wealth)}원</div>', unsafe_allow_html=True)

# (식단 & 건강, 재고 관리 탭은 v33.5 코드 유지)
