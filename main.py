import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime, timedelta

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

# --- [3. 메인 설정 및 상단 바] ---
st.set_page_config(page_title="JARVIS v37.0", layout="wide")

# CSS: 비서용 알림 스타일
st.markdown("""<style>
    .stTable td { text-align: right !important; }
    .status-card { background-color: #f0f2f6; padding: 20px; border-radius: 10px; border-left: 5px solid #1E90FF; margin-bottom: 20px; }
    .alert-text { color: #e03131; font-weight: bold; }
    .net-wealth { font-size: 2.5em !important; font-weight: bold; color: #1E90FF; border-top: 3px solid #1E90FF; padding-top: 10px; }
</style>""", unsafe_allow_html=True)

# [데이터 세션 초기화]
if 'inventory' not in st.session_state:
    st.session_state.inventory = pd.DataFrame([
        {"항목": "냉동 삼치", "수량": "4팩", "유통기한": "2026-05-10"}, {"항목": "냉동닭다리살", "수량": "3팩단위", "유통기한": "2026-06-01"},
        {"항목": "단백질 쉐이크", "수량": "9개", "유통기한": "2026-12-30"}, {"항목": "카무트/쌀 혼합", "수량": "2kg", "유통기한": "2026-10-20"},
        {"항목": "김치 4종", "수량": "보유", "유통기한": "-"}, {"항목": "당근", "수량": "보유", "유통기한": "-"}, {"항목": "감자", "수량": "보유", "유통기한": "-"}
    ])
if 'supplies' not in st.session_state:
    st.session_state.supplies = pd.DataFrame([
        {"품목": "칫솔(보스)", "최근교체일": "2026-01-15", "주기": 30},
        {"품목": "면도날", "최근교체일": "2026-02-01", "주기": 14},
        {"품목": "수세미", "최근교체일": "2026-02-15", "주기": 30},
        {"품목": "정수기필터", "최근교체일": "2025-12-10", "주기": 120}
    ])

# --- [지능형 비서 알림 로직] ---
today = datetime.now()
alerts = []
# 1. 생필품 주기 체크
for _, row in st.session_state.supplies.iterrows():
    last_date = datetime.strptime(row['최근교체일'], '%Y-%m-%d')
    if (today - last_date).days >= row['주기']:
        alerts.append(f"🔴 {row['품목']} 교체 시기 지남 (주기: {row['주기']}일)")

# 2. 유통기한 체크
for _, row in st.session_state.inventory.iterrows():
    if row['유통기한'] != "-":
        exp_date = datetime.strptime(row['유통기한'], '%Y-%m-%d')
        if (exp_date - today).days <= 7:
            alerts.append(f"🟡 {row['항목']} 유통기한 임박 ({(exp_date-today).days}일 남음)")

# 상단 알림창 출력
st.markdown('<div class="status-card">', unsafe_allow_html=True)
st.subheader("시스템 지능형 알림")
if alerts:
    for a in alerts: st.markdown(f'<p class="alert-text">{a}</p>', unsafe_allow_html=True)
else:
    st.write("모든 시스템 정상. 긴급히 관리할 항목이 없습니다.")
st.markdown('</div>', unsafe_allow_html=True)

# --- [사이드바 메뉴] ---
with st.sidebar:
    st.title("JARVIS v37.0")
    menu = st.radio("이동", ["투자 & 자산", "식단 & 건강", "재고 관리"])

# --- [4. 메인 화면 로직] ---
if menu == "투자 & 자산":
    st.header("종합 자산 현황")
    # (자산 테이블 로직 생략 없이 그대로 유지)
    inv_rows = []
    for cat, items in {"주식": FIXED_DATA["stocks"], "코인": FIXED_DATA["crypto"]}.items():
        for name, info in items.items(): inv_rows.append({"항목": name, "val": info['평단'] * info['수량']})
    df_total = pd.DataFrame(inv_rows)
    df_total.index = range(1, len(df_total)+1)
    st.table(df_total.assign(금액=df_total["val"].apply(format_krw))[["항목", "금액"]])
    st.markdown(f'<div class="net-wealth">투자 순자산: {format_krw(df_total["val"].sum())}</div>', unsafe_allow_html=True)

elif menu == "식단 & 건강":
    st.header("지능형 식단 가이드")
    d_day = (datetime(2026, 5, 30) - today).days
    st.warning(f"결혼식까지 {d_day}일 남음 | 현재 체중 기반 집중 관리 모드")

    st.subheader("식단 퀵 버튼 (1클릭 기록)")
    q_c1, q_c2, q_c3 = st.columns(3)
    with q_c1:
        if st.button("단백질 쉐이크 조합"):
            send_to_sheet("식단", "칼로리", 250); send_to_sheet("식단", "단백질", 30)
            st.success("쉐이크 기록 완료")
    with q_c2:
        if st.button("표준 집밥 (카무트)"):
            send_to_sheet("식단", "칼로리", 500); send_to_sheet("식단", "단백질", 25)
            st.success("집밥 기록 완료")
    with q_c3:
        if st.button("표준 외식/배달"):
            send_to_sheet("식단", "칼로리", 900); send_to_sheet("식단", "단백질", 40)
            st.success("외식 기록 완료")

elif menu == "재고 관리":
    st.header("재고 및 소모품 마스터")
    st.subheader("식재료 리스트 (1부터 시작)")
    inv_df = st.session_state.inventory.copy()
    inv_df.index = range(1, len(inv_df)+1)
    st.data_editor(inv_df, use_container_width=True)
    
    st.subheader("생활용품 교체 주기")
    sup_df = st.session_state.supplies.copy()
    sup_df.index = range(1, len(sup_df)+1)
    st.data_editor(sup_df, use_container_width=True)
