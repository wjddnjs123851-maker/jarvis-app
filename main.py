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
    try: return pd.read_csv(url).dropna().reset_index(drop=True)
    except: return pd.DataFrame()

# --- [3. 메인 설정 및 상단 바] ---
st.set_page_config(page_title="JARVIS v36.2", layout="wide")
t_c1, t_c2 = st.columns([7, 3])
with t_c1: st.markdown(f"### {datetime.now().strftime('%Y-%m-%d')} | SYSTEM ONLINE")
with t_c2: st.markdown("<div style='text-align:right;'>STABLE RELEASE v36.2</div>", unsafe_allow_html=True)

st.markdown("""<style>
    .stTable td { text-align: right !important; }
    .total-display { text-align: right; font-size: 1.3em; font-weight: bold; padding: 15px; background: #f1f3f5; border-radius: 5px; margin-top: 5px; }
    .net-wealth { font-size: 2.5em !important; font-weight: bold; color: #1E90FF; text-align: left; margin-top: 25px; border-top: 3px solid #1E90FF; padding-top: 10px; }
</style>""", unsafe_allow_html=True)

with st.sidebar:
    st.title("JARVIS")
    menu = st.radio("메뉴", ["투자 & 자산", "식단 & 건강", "재고 관리"])
    if menu == "식단 & 건강":
        st.subheader("수동 기록")
        in_w = st.number_input("체중(kg)", 0.0, 200.0, 125.0, step=0.01)
        in_kcal = st.number_input("칼로리(kcal)", 0.0)
        in_prot = st.number_input("단백질(g)", 0.0)
        if st.button("전송"):
            send_to_sheet("식단", "칼로리", in_kcal, corpus="Health")
            send_to_sheet("식단", "단백질", in_prot, corpus="Health")
            send_to_sheet("건강", "체중", in_w, corpus="Health")
            st.rerun()

# --- [4. 메인 화면 로직] ---
if menu == "투자 & 자산":
    st.header("종합 자산 관리")
    df_sheet = load_sheet_data(GID_MAP["Assets"])
    if not df_sheet.empty: 
        df_sheet.columns = ["항목", "금액"]; df_sheet["val"] = df_sheet["금액"].apply(to_numeric)
    inv_rows = []
    for cat, items in {"주식": FIXED_DATA["stocks"], "코인": FIXED_DATA["crypto"]}.items():
        for name, info in items.items(): inv_rows.append({"항목": name, "val": info['평단'] * info['수량']})
    df_total = pd.concat([df_sheet, pd.DataFrame(inv_rows)], ignore_index=True)
    a_df, l_df = df_total[df_total["val"] >= 0].copy(), df_total[df_total["val"] < 0].copy()
    
    c_a, c_l = st.columns(2)
    with c_a:
        st.subheader("자산")
        a_df.index = range(1, len(a_df)+1)
        st.table(a_df.assign(금액=a_df["val"].apply(format_krw))[["항목", "금액"]])
    with c_l:
        st.subheader("부채")
        l_df.index = range(1, len(l_df)+1)
        st.table(l_df.assign(금액=l_df["val"].apply(lambda x: format_krw(abs(x))))[["항목", "금액"]])
    st.markdown(f'<div class="net-wealth">순자산: {format_krw(a_df["val"].sum() + l_df["val"].sum())}</div>', unsafe_allow_html=True)

elif menu == "식단 & 건강":
    st.header("영양 분석")
    st.info("결혼식 목표 체중 감량 관리 중")
    st.write("FatSecret 데이터 기반 분석 대기 중")

elif menu == "재고 관리":
    st.header("재고 및 소모품")
    if 'inventory' not in st.session_state:
        st.session_state.inventory = pd.DataFrame([
            {"항목": "냉동 삼치", "수량": "4팩", "유통기한": "2026-05-10"}, {"항목": "냉동닭다리살", "수량": "3팩단위", "유통기한": "2026-06-01"},
            {"항목": "단백질 쉐이크", "수량": "9개", "유통기한": "2026-12-30"}, {"항목": "카무트/쌀 혼합", "수량": "2kg", "유통기한": "2026-10-20"},
            {"항목": "파스타면", "수량": "대량", "유통기한": "-"}, {"항목": "소면", "수량": "1봉", "유통기한": "-"},
            {"항목": "쿠스쿠스", "수량": "500g", "유통기한": "2027-01-01"}, {"항목": "우동사리", "수량": "3봉", "유통기한": "-"},
            {"항목": "라면", "수량": "6봉", "유통기한": "-"}, {"항목": "토마토 페이스트", "수량": "10캔", "유통기한": "2027-05-15"},
            {"항목": "나시고랭 소스", "수량": "1팩", "유통기한": "2026-11-20"}, {"항목": "치아씨드/아사이베리", "수량": "보유", "유통기한": "-"},
            {"항목": "김치 4종", "수량": "보유", "유통기한": "-"}, {"항목": "당근", "수량": "보유", "유통기한": "-"}, {"항목": "감자", "수량": "보유", "유통기한": "-"}
        ])
    inv_df = st.session_state.inventory.copy()
    inv_df.index = range(1, len(inv_df)+1)
    st.subheader("식재료 현황")
    st.data_editor(inv_df, use_container_width=True, key="inv_editor")

    st.divider()
    
    st.subheader("생활용품 교체 주기")
    if 'supplies' not in st.session_state:
        st.session_state.supplies = pd.DataFrame([
            {"품목": "칫솔(보스)", "최근교체일": "2026-01-15", "주기": 30},
            {"품목": "칫솔(약혼녀)", "최근교체일": "2026-02-15", "주기": 30},
            {"품목": "면도날", "최근교체일": "2026-02-01", "주기": 14},
            {"품목": "수세미", "최근교체일": "2026-02-15", "주기": 30},
            {"품목": "정수기필터", "최근교체일": "2025-12-10", "주기": 120}
        ])
    sup_df = st.session_state.supplies.copy()
    sup_df.index = range(1, len(sup_df)+1)
    st.data_editor(sup_df, use_container_width=True, key="sup_editor")
