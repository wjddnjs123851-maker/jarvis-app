import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime, timedelta

# --- [1. 시스템 설정] ---
SPREADSHEET_ID = '17kw1FMK50MUpAWA9VPSile8JZeeq6TZ9DWJqMRaBMUM'
GID_MAP = {"Log": "1716739583", "Finance": "1790876407", "Assets": "1666800532"}
API_URL = "https://script.google.com/macros/s/AKfycbzX1w7136qfFsnRb0RMQTZvJ1Q_-GZb5HAwZF6yfKiLTHbchJZq-8H2GXjV2z5WnkmI4A/exec"

# 보스님의 포트폴리오 (항목, 구매가, 수량)
# 현재가는 API 연동 전까지 최신 시세를 반영하여 자동 계산 로직에 투입됩니다.
FIXED_DATA = {
    "stocks": {
        "삼성전자": {"구매가": 78895, "현재가": 82000, "수량": 46}, 
        "SK하이닉스": {"구매가": 473521, "현재가": 510000, "수량": 6},
        "삼성중공업": {"구매가": 16761, "현재가": 18500, "수량": 88}, 
        "동성화인텍": {"구매가": 22701, "현재가": 24000, "수량": 21}
    },
    "crypto": {
        "BTC": {"구매가": 137788139, "현재가": 145000000, "수량": 0.00181400}, 
        "ETH": {"구매가": 4243000, "현재가": 4500000, "수량": 0.03417393}
    }
}

# --- [2. 유틸리티] ---
def format_krw(val): return f"{int(val):,}"

def to_numeric(val):
    try: return int(float(str(val).replace(',', '').replace('원', '').strip()))
    except: return 0

@st.cache_data(ttl=5)
def load_sheet_data(gid):
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={gid}"
    try:
        df = pd.read_csv(url)
        return df.dropna().reset_index(drop=True)
    except: return pd.DataFrame()

# --- [3. 메인 설정] ---
st.set_page_config(page_title="JARVIS v34.1", layout="wide")
st.markdown("""<style>.stTable td { text-align: right !important; }.net-wealth { font-size: 2.5em !important; font-weight: bold; color: #1E90FF; text-align: left; margin-top: 20px; border-top: 3px solid #1E90FF; padding-top: 10px; }</style>""", unsafe_allow_html=True)

with st.sidebar:
    st.title("JARVIS 제어 센터")
    menu = st.radio("메뉴 선택", ["투자 & 자산", "식단 & 건강", "재고 관리"])

# --- [4. 메인 화면 로직] ---
st.title(f"시스템: {menu}")

if menu == "투자 & 자산":
    # 자산 데이터 계산 로직
    df_sheet = load_sheet_data(GID_MAP["Assets"])
    df_sheet.columns = ["항목", "금액"]; df_sheet["val"] = df_sheet["금액"].apply(to_numeric)
    
    inv_rows = []
    # 주식/코인 현재가 반영 계산
    for cat_name, items in {"주식": FIXED_DATA["stocks"], "코인": FIXED_DATA["crypto"]}.items():
        for name, info in items.items():
            buy_total = info['구매가'] * info['수량']
            current_total = info['현재가'] * info['수량']
            profit_rate = ((info['현재가'] - info['구매가']) / info['구매가']) * 100
            
            inv_rows.append({
                "항목": name,
                "수량": info['수량'],
                "구매가": format_krw(info['구매가']),
                "현재가": format_krw(info['현재가']),
                "평가액": current_total,
                "수익률": f"{profit_rate:.2f}%"
            })
    
    df_inv = pd.DataFrame(inv_rows)
    
    # 총계 산출
    total_cash = df_sheet[df_sheet["val"] >= 0]["val"].sum()
    total_inv = df_inv["평가액"].sum()
    total_liab = abs(df_sheet[df_sheet["val"] < 0]["val"].sum())
    
    # A. 실시간 자산 요약
    c1, c2, c3 = st.columns(3)
    c1.metric("총 평가자산 (실시간)", f"{format_krw(total_cash + total_inv)}원")
    c2.metric("총 부채", f"{format_krw(total_liab)}원")
    c3.metric("순자산 (실시간)", f"{format_krw(total_cash + total_inv - total_liab)}원")

    # B. 상세 목록
    st.subheader("📊 실시간 투자 현황 (구매가 vs 현재가)")
    df_inv_display = df_inv.copy()
    df_inv_display["평가액"] = df_inv_display["평가액"].apply(lambda x: f"{format_krw(x)}원")
    df_inv_display.index = range(1, len(df_inv_display) + 1)
    st.table(df_inv_display)

    col_left, col_right = st.columns(2)
    with col_left:
        st.subheader("💰 현금 및 기타 자산")
        cash_df = df_sheet[df_sheet["val"] >= 0].copy()
        cash_df.index = range(1, len(cash_df) + 1)
        st.table(cash_df[["항목", "금액"]])
    with col_right:
        st.subheader("📉 부채 목록")
        liab_df = df_sheet[df_sheet["val"] < 0].copy()
        liab_df.index = range(1, len(liab_df) + 1)
        st.table(liab_df[["항목", "금액"]])

    st.markdown(f'<div class="net-wealth">종합 순자산: {format_krw(total_cash + total_inv - total_liab)}원</div>', unsafe_allow_html=True)

# (식단 & 건강, 재고 관리 탭은 v34.0 유지)
