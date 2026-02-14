import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime

# --- [1. 시스템 설정] ---
SPREADSHEET_ID = '17kw1FMK50MUpAWA9VPSile8JZeeq6TZ9DWJqMRaBMUM'
# GID 설정 유지 (Log와 Assets 모두 활용)
GID_MAP = {"Log": "1716739583", "Finance": "1790876407", "Assets": "1666800532", "Health": "123456789"}
API_URL = "https://script.google.com/macros/s/AKfycbzX1w7136qfFsnRb0RMQTZvJ1Q_-GZb5HAwZF6yfKiLTHbchJZq-8H2GXjV2z5WnkmI4A/exec"

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
def format_krw(val): return f"{int(val):,}" + "원"

def to_numeric(val):
    try: return int(float(str(val).replace(',', '').replace('원', '').strip()))
    except: return 0

@st.cache_data(ttl=5)
def load_sheet_data(gid):
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={gid}"
    try: 
        df = pd.read_csv(url)
        return df.dropna(how='all').reset_index(drop=True)
    except: return pd.DataFrame()

# --- [3. 메인 설정] ---
st.set_page_config(page_title="JARVIS v35.7", layout="wide")

# --- [4. 실시간 자산 계산 로직] ---
def get_realtime_assets():
    # 1. 기초 자산 로드
    df_assets = load_sheet_data(GID_MAP["Assets"])
    if not df_assets.empty:
        df_assets.columns = ["항목", "금액"]
        df_assets["val"] = df_assets["금액"].apply(to_numeric)
    
    # 2. Log에서 추가 지출/수입 계산
    df_log = load_sheet_data(GID_MAP["Log"])
    log_diff = 0
    if not df_log.empty:
        # 시트 구조에 따라 열 이름 확인 필요 (날짜, 구분, 항목, 수치)
        df_log.columns = ["날짜", "구분", "항목", "수치"]
        incomes = df_log[df_log["구분"] == "수입"]["수치"].apply(to_numeric).sum()
        expenses = df_log[df_log["구분"] == "지출"]["수치"].apply(to_numeric).sum()
        log_diff = incomes - expenses
        
    return df_assets, log_diff

# --- [5. 투자 및 자산 화면] ---
st.header("종합 자산 관리 (실시간 연동)")

df_base, diff = get_realtime_assets()

# 주식/코인 계산
inv_rows = []
for cat, items in {"주식": FIXED_DATA["stocks"], "코인": FIXED_DATA["crypto"]}.items():
    for name, info in items.items():
        inv_rows.append({"항목": name, "val": info['평단'] * info['수량']})

# 전체 통합
df_total = pd.concat([df_base, pd.DataFrame(inv_rows)], ignore_index=True)

# 실시간 현금 잔고 조정 (첫 번째 자산 항목인 '현금' 혹은 '통장'에 Log 차액 반영)
if not df_total.empty:
    df_total.iloc[0, df_total.columns.get_loc("val")] += diff

a_df, l_df = df_total[df_total["val"] >= 0].copy(), df_total[df_total["val"] < 0].copy()

c1, c2 = st.columns(2)
with c1:
    st.subheader("자산 내역")
    a_df.index = range(1, len(a_df)+1)
    st.table(a_df.assign(금액=a_df["val"].apply(format_krw))[["항목", "금액"]])
with c2:
    st.subheader("부채 내역")
    l_df.index = range(1, len(l_df)+1)
    st.table(l_df.assign(금액=l_df["val"].apply(lambda x: format_krw(abs(x))))[["항목", "금액"]])

st.markdown(f"### 실시간 순자산: {format_krw(a_df['val'].sum() + l_df['val'].sum())}")
