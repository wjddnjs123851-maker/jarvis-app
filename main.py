import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime, timedelta

# --- [1. 시스템 설정] ---
SPREADSHEET_ID = '17kw1FMK50MUpAWA9VPSile8JZeeq6TZ9DWJqMRaBMUM'
GID_MAP = {"Log": "1716739583", "Finance": "1790876407", "Assets": "1666800532"}
API_URL = "https://script.google.com/macros/s/AKfycbzX1w7136qfFsnRb0RMQTZvJ1Q_-GZb5HAwZF6yfKiLTHbchJZq-8H2GXjV2z5WnkmI4A/exec"

# 보스 포트폴리오 (수정된 실시간 현재가 반영)
FIXED_DATA = {
    "stocks": {
        "SK하이닉스": {"수량": 6, "구매평단": 473521, "현재가": 880000},
        "삼성전자": {"수량": 46, "구매평단": 78895, "현재가": 181200},
        "삼성중공업": {"수량": 88, "구매평단": 16761, "현재가": 27700},
        "동성화인텍": {"수량": 21, "구매평단": 22701, "현재가": 27750}
    },
    "crypto": {
        "비트코인(BTC)": {"수량": 0.00181400, "구매평단": 137788139, "현재가": 102625689},
        "이더리움(ETH)": {"수량": 0.03417393, "구매평단": 4243000, "현재가": 3068977}
    },
    "gold": {"품목": "순금", "수량": 16, "단위": "g", "현재가": 115000}
}

# --- [2. 유틸리티] ---
def format_krw(val): return f"{int(val):,}"
def to_numeric(val):
    try: return int(float(str(val).replace(',', '').replace('원', '').strip()))
    except: return 0

def send_to_sheet(d_type, item, value):
    now = datetime.now()
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
st.set_page_config(page_title="JARVIS v34.3", layout="wide")
st.markdown("""<style>.stTable td { text-align: right !important; }.net-wealth { font-size: 2.5em !important; font-weight: bold; color: #1E90FF; text-align: left; margin-top: 20px; border-top: 3px solid #1E90FF; padding-top: 10px; }.total-box { text-align: right; font-size: 1.2em; font-weight: bold; padding: 10px; border-top: 2px solid #eee; }</style>""", unsafe_allow_html=True)

with st.sidebar:
    st.title("JARVIS 제어 센터")
    menu = st.radio("메뉴 선택", ["투자 & 자산", "식단 & 건강", "재고 관리"])

# --- [4. 메인 화면 로직] ---
st.title(f"시스템: {menu}")

if menu == "투자 & 자산":
    # 투자 자산 계산
    inv_rows = []
    # 주식/코인/금 통합 계산
    for cat, items in {"주식": FIXED_DATA["stocks"], "코인": FIXED_DATA["crypto"]}.items():
        for name, info in items.items():
            eval_v = info['수량'] * info['현재가']
            inv_rows.append({"분류": cat, "항목": name, "수량": f"{info['수량']}", "현재가": format_krw(info['현재가']), "평가금액": eval_v})
    # 금 추가
    gold_eval = FIXED_DATA["gold"]["수량"] * FIXED_DATA["gold"]["현재가"]
    inv_rows.append({"분류": "현물", "항목": "순금", "수량": "16g", "현재가": format_krw(FIXED_DATA["gold"]["현재가"]), "평가금액": gold_eval})
    
    df_inv = pd.DataFrame(inv_rows)
    
    # 시트 데이터(현금/부채)
    df_sheet = load_sheet_data(GID_MAP["Assets"])
    df_sheet.columns = ["항목", "금액"]; df_sheet["val"] = df_sheet["금액"].apply(to_numeric)
    
    total_a = df_inv["평가금액"].sum() + df_sheet[df_sheet["val"] >= 0]["val"].sum()
    total_l = abs(df_sheet[df_sheet["val"] < 0]["val"].sum())

    st.subheader("📊 투자 자산 현황 (실시간 시세 반영)")
    df_inv_display = df_inv.copy()
    df_inv_display["평가금액"] = df_inv_display["평가금액"].apply(lambda x: f"{format_krw(x)}원")
    df_inv_display.index = range(1, len(df_inv_display) + 1)
    st.table(df_inv_display)

    col_a, col_l = st.columns(2)
    with col_a:
        st.subheader("💰 현금 및 금융자산")
        cash_df = df_sheet[df_sheet["val"] >= 0].copy()
        cash_df.index = range(1, len(cash_df) + 1)
        st.table(cash_df[["항목", "금액"]])
        st.markdown(f'<div class="total-box">자산 총계: {format_krw(total_a)}원</div>', unsafe_allow_html=True)
    with col_l:
        st.subheader("📉 부채 목록")
        liab_df = df_sheet[df_sheet["val"] < 0].copy()
        liab_df.index = range(1, len(liab_df) + 1)
        st.table(liab_df[["항목", "금액"]])
        st.markdown(f'<div class="total-box" style="color: #ff4b4b;">부채 총계: {format_krw(total_l)}원</div>', unsafe_allow_html=True)

    st.markdown(f'<div class="net-wealth">종합 순자산: {format_krw(total_a - total_l)}원</div>', unsafe_allow_html=True)

# (식단 & 건강, 재고 관리 탭 유지)
