import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime

# --- [1. 시스템 설정] ---
SPREADSHEET_ID = '17kw1FMK50MUpAWA9VPSile8JZeeq6TZ9DWJqMRaBMUM'
GID_MAP = {"Log": "1716739583", "Finance": "1790876407", "Assets": "1666800532", "Health": "123456789"}
API_URL = "https://script.google.com/macros/s/AKfycbzX1w7136qfFsnRb0RMQTZvJ1Q_-GZb5HAwZF6yfKiLTHbchJZq-8H2GXjV2z5WnkmI4A/exec"

DAILY_GUIDE = {
    "칼로리": {"val": 2900.0, "unit": "kcal"}, "지방": {"val": 90.0, "unit": "g"},
    "콜레스테롤": {"val": 300.0, "unit": "mg"}, "나트륨": {"val": 2300.0, "unit": "mg"},
    "탄수화물": {"val": 360.0, "unit": "g"}, "식이섬유": {"val": 30.0, "unit": "g"},
    "당": {"val": 50.0, "unit": "g"}, "단백질": {"val": 160.0, "unit": "g"}
}

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

def send_to_sheet(d_type, item, value, corpus="Log"):
    payload = {"time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'), "corpus": corpus, "type": d_type, "item": item, "value": value}
    try: return requests.post(API_URL, data=json.dumps(payload), timeout=5).status_code == 200
    except: return False

@st.cache_data(ttl=5)
def load_sheet_data(gid):
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={gid}"
    try: return pd.read_csv(url).dropna(how='all').reset_index(drop=True)
    except: return pd.DataFrame()

# --- [3. 메인 설정 및 상단 바] ---
st.set_page_config(page_title="JARVIS v35.9", layout="wide")
t_c1, t_c2 = st.columns([7, 3])
with t_c1: st.markdown(f"### {datetime.now().strftime('%Y-%m-%d')} | 🌡️ 8°C ☀️ 맑음")
with t_c2: st.markdown("<div style='text-align:right;'><b>SYSTEM STATUS: ONLINE</b></div>", unsafe_allow_html=True)

st.markdown("""<style>.stTable td { text-align: right !important; }.total-display { text-align: right; font-size: 1.3em; font-weight: bold; padding: 15px; background: #f1f3f5; border-radius: 5px; margin-top: 5px; }.net-wealth { font-size: 2.5em !important; font-weight: bold; color: #1E90FF; text-align: left; margin-top: 25px; border-top: 3px solid #1E90FF; padding-top: 10px; }.input-card { background-color: #f8f9fa; padding: 20px; border-radius: 10px; border: 1px solid #dee2e6; margin-bottom: 20px; }</style>""", unsafe_allow_html=True)

with st.sidebar:
    st.title("JARVIS 제어 센터")
    menu = st.radio("메뉴 선택", ["투자 & 자산", "식단 & 건강", "재고 관리"])

# --- [4. 메인 화면 로직] ---
if menu == "투자 & 자산":
    st.header("💰 투자 및 종합 자산 관리")
    st.markdown('<div class="input-card">', unsafe_allow_html=True)
    f_c1, f_c2, f_c3, f_c4 = st.columns([1, 2, 2, 1])
    with f_c1: t_choice = st.selectbox("구분", ["지출", "수입"])
    with f_c2:
        if t_choice == "지출":
            cats = ["식비(집밥)", "식비(외식)", "식비(배달)", "식비(편의점)", "생활용품", "건강/의료", "기호품", "주거/통신", "교통/차량", "금융/보험", "결혼준비", "경조사", "자산이동", "기타지출"]
        else:
            cats = ["급여", "금융소득", "자산이동", "기타"]
        c_choice = st.selectbox("카테고리", cats)
    with f_c3: a_input = st.number_input("금액(원)", min_value=0, step=1000)
    with f_c4: 
        st.write(""); st.write("")
        if st.button("기록"): 
            if a_input > 0 and send_to_sheet(t_choice, c_choice, a_input, corpus="Finance"): st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # 자산 및 로그 실시간 계산
    df_assets = load_sheet_data(GID_MAP["Assets"])
    df_log = load_sheet_data(GID_MAP["Log"])
    
    if not df_assets.empty:
        df_assets.columns = ["항목", "금액"]
        df_assets["val"] = df_assets["금액"].apply(to_numeric)
    
    cash_diff, card_debt = 0, 0
    if not df_log.empty:
        df_log.columns = ["날짜", "구분", "항목", "수치"]
        for _, row in df_log.iterrows():
            val = to_numeric(row["수치"])
            if row["구분"] == "지출":
                if row["항목"] == "자산이동": cash_diff -= val
                else: card_debt += val
            elif row["구분"] == "수입":
                if row["항목"] != "자산이동": cash_diff += val

    inv_rows = []
    for cat, items in {"주식": FIXED_DATA["stocks"], "코인": FIXED_DATA["crypto"]}.items():
        for name, info in items.items(): inv_rows.append({"항목": name, "val": info['평단'] * info['수량']})
    
    df_total = pd.concat([df_assets, pd.DataFrame(inv_rows)], ignore_index=True)
    if not df_total.empty: df_total.iloc[0, df_total.columns.get_loc("val")] += cash_diff
    if card_debt > 0: df_total = pd.concat([df_total, pd.DataFrame([{"항목": "카드값(미결제)", "val": -card_debt}])], ignore_index=True)

    a_df, l_df = df_total[df_total["val"] >= 0].copy(), df_total[df_total["val"] < 0].copy()
    sum_a, sum_l = a_df["val"].sum(), abs(l_df["val"].sum())
    
    col_a, col_l = st.columns(2)
    with col_a:
        st.subheader("자산 내역"); a_df.index = range(1, len(a_df)+1)
        st.table(a_df.assign(금액=a_df["val"].apply(format_krw))[["항목", "금액"]])
        st.markdown(f'<div class="total-display">자산총계: {format_krw(sum_a)}</div>', unsafe_allow_html=True)
    with col
