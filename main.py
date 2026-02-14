import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime

# --- [1. 시스템 설정] ---
# 데이터 무결성 유지: 기존 식자재 15종 및 자산 내역 전체 포함
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

# --- [3. 메인 설정 및 스타일] ---
st.set_page_config(page_title="JARVIS v37.1", layout="wide")
st.markdown("""<style>
    .stTable td { text-align: right !important; }
    .status-card { background-color: #f0f2f6; padding: 20px; border-radius: 10px; border-left: 5px solid #1E90FF; margin-bottom: 20px; }
    .alert-text { color: #e03131; font-weight: bold; }
    .net-wealth { font-size: 2.2em !important; font-weight: bold; color: #1E90FF; text-align: left; margin-top: 10px; border-top: 2px solid #eee; padding-top: 10px; }
</style>""", unsafe_allow_html=True)

# [데이터 세션 초기화 - 사용자 최신 데이터 반영]
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

if 'supplies' not in st.session_state:
    st.session_state.supplies = pd.DataFrame([
        {"품목": "칫솔(보스)", "최근교체일": "2026-02-15", "주기": 30}, # 오늘로 업데이트 반영
        {"품목": "칫솔(약혼녀)", "최근교체일": "2026-02-15", "주기": 30},
        {"품목": "면도날", "최근교체일": "2026-02-01", "주기": 14},
        {"품목": "수세미", "최근교체일": "2026-02-15", "주기": 30},
        {"품목": "정수기필터", "최근교체일": "2025-12-10", "주기": 120}
    ])

# --- [4. 상단 알림 및 대시보드] ---
today = datetime.now()
st.markdown(f"### {today.strftime('%Y-%m-%d')} | SYSTEM ONLINE")

# 지능형 알림 로직 (주기 도달 시에만 노출)
alerts = []
for _, row in st.session_state.supplies.iterrows():
    last_date = datetime.strptime(row['최근교체일'], '%Y-%m-%d')
    days_passed = (today - last_date).days
    if days_passed >= row['주기']:
        alerts.append(f"🔴 {row['품목']} 교체 시기 지남 ({(days_passed - row['주기'])}일 초과)")

if alerts:
    with st.container():
        st.markdown('<div class="status-card">', unsafe_allow_html=True)
        for a in alerts: st.markdown(f'<p class="alert-text">{a}</p>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

# --- [5. 사이드바 및 메뉴] ---
with st.sidebar:
    st.title("JARVIS v37.1")
    menu = st.radio("메뉴", ["투자 & 자산", "식단 & 건강", "재고 관리"])
    
    st.divider()
    st.subheader("수동 기록 (식단/체중)")
    in_w = st.number_input("체중(kg)", 0.0, 200.0, 125.0, step=0.01)
    in_kcal = st.number_input("칼로리(kcal)", 0.0)
    in_prot = st.number_input("단백질(g)", 0.0)
    if st.button("기록 전송"):
        send_to_sheet("건강", "체중", in_w, corpus="Health")
        if in_kcal > 0: send_to_sheet("식단", "칼로리", in_kcal, corpus="Health")
        if in_prot > 0: send_to_sheet("식단", "단백질", in_prot, corpus="Health")
        st.rerun()

# --- [6. 메인 로직] ---
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
    
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("자산 리스트")
        a_df.index = range(1, len(a_df)+1)
        st.table(a_df.assign(금액=a_df["val"].apply(format_krw))[["항목", "금액"]])
    with c2:
        st.subheader("부채 리스트")
        l_df.index = range(1, len(l_df)+1)
        st.table(l_df.assign(금액=l_df["val"].apply(lambda x: format_krw(abs(x))))[["항목", "금액"]])
    
    net_val = a_df["val"].sum() + l_df["val"].sum()
    st.markdown(f'<div class="net-wealth">현재 순자산 합계: {format_krw(net_val)}</div>', unsafe_allow_html=True)

elif menu == "식단 & 건강":
    st.header("영양 섭취 및 건강 관리")
    d_day = (datetime(2026, 5, 30) - today).days
    st.info(f"결혼식까지 D-{d_day} | 현재 체중 125kg 기준 감량 모드")
    
    # 영양 성분 수치 확인 대시보드 (복구)
    st.subheader("오늘의 영양 달성도")
    cols = st.columns(4)
    for i, (name, target) in enumerate(list(DAILY_GUIDE.items())[:4]):
        with cols[i]:
            st.metric(name, f"0 {target['unit']}", f"목표: {target['val']}")
            st.progress(0.0) # 실제 데이터 연동 전 0% 표시

    st.subheader("식단 퀵 입력")
    q_c1, q_c2, q_c3 = st.columns(3)
    with q_c1:
        if st.button("🥤 단백질 쉐이크"):
            send_to_sheet("식단", "칼로리", 250); send_to_sheet("식단", "단백질", 30)
            st.success("쉐이크 전송됨")
    with q_c2:
        if st.button("🍚 카무트 집밥"):
            send_to_sheet("식단", "칼로리", 550); send_to_sheet("식단", "단백질", 25)
            st.success("집밥 전송됨")
    with q_c3:
        if st.button("🍗 외식/배달"):
            send_to_sheet("식단", "칼로리", 950); send_to_sheet("식단", "단백질", 45)
            st.success("외식 전송됨")

elif menu == "재고 관리":
    st.header("식재료 및 소모품 관리")
    
    st.subheader("1. 식재료 재고 (15종 전체)")
    inv_df = st.session_state.inventory.copy()
    inv_df.index = range(1, len(inv_df)+1)
    st.data_editor(inv_df, use_container_width=True, key="inv_editor")

    st.divider()
    
    st.subheader("2. 소모품 교체 주기")
    sup_df = st.session_state.supplies.copy()
    sup_df.index = range(1, len(sup_df)+1)
    st.data_editor(sup_df, use_container_width=True, key="sup_editor")
