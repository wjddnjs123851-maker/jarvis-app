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

DAILY_GUIDE = {
    "지방": {"val": 65.0, "unit": "g"}, "콜레스테롤": {"val": 300.0, "unit": "mg"},
    "나트륨": {"val": 2000.0, "unit": "mg"}, "탄수화물": {"val": 300.0, "unit": "g"},
    "식이섬유": {"val": 30.0, "unit": "g"}, "당": {"val": 50.0, "unit": "g"},
    "단백질": {"val": 150.0, "unit": "g"}, "칼로리": {"val": 2000.0, "unit": "kcal"}
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
    try: return pd.read_csv(url).dropna().reset_index(drop=True)
    except: return pd.DataFrame()

# --- [3. 메인 설정 및 스타일] ---
st.set_page_config(page_title="JARVIS v34.9", layout="wide")
st.markdown("""<style>.stTable td { text-align: right !important; }.total-box { text-align: right; font-size: 1.2em; font-weight: bold; padding: 10px; border-top: 2px solid #eee; }.net-wealth { font-size: 2.2em !important; font-weight: bold; color: #1E90FF; text-align: left; margin-top: 20px; border-top: 3px solid #1E90FF; padding-top: 10px; }.input-card { background-color: #f8f9fa; padding: 20px; border-radius: 10px; border: 1px solid #dee2e6; margin-bottom: 20px; }</style>""", unsafe_allow_html=True)

with st.sidebar:
    st.title("JARVIS 제어 센터")
    menu = st.radio("메뉴 선택", ["투자 & 자산", "식단 & 건강", "재고 관리"])
    
    if menu == "식단 & 건강":
        st.subheader("데이터 입력 (정밀)")
        in_w = st.number_input("체중(kg)", 0.0, 200.0, 125.0, step=0.01, format="%.2f")
        in_kcal = st.number_input("칼로리 (kcal)", 0.0, format="%.2f")
        in_prot = st.number_input("단백질 (g)", 0.0, format="%.2f")
        # 추가 영양소 입력 (v34.0 복구)
        in_fat = st.number_input("지방 (g)", 0.0, format="%.2f")
        in_carb = st.number_input("탄수화물 (g)", 0.0, format="%.2f")
        if st.button("식단 데이터 전송"):
            send_to_sheet("건강", "체중", in_w)
            send_to_sheet("식단", "칼로리", in_kcal)
            send_to_sheet("식단", "단백질", in_prot)
            st.success("전송 완료!"); st.rerun()

# --- [4. 메인 화면 로직] ---
st.title(f"시스템: {menu}")

if menu == "투자 & 자산":
    st.markdown('<div class="input-card">', unsafe_allow_html=True)
    st.subheader("📝 오늘의 재무 활동 기록")
    i_c1, i_c2, i_c3, i_c4 = st.columns([1, 2, 2, 1])
    with i_c1: t_choice = st.selectbox("구분", ["지출", "수입"])
    with i_c2: cats = EXPENSE_CATS if t_choice == "지출" else INCOME_CATS; c_choice = st.selectbox("카테고리", cats)
    with i_c3: a_input = st.number_input("금액(원)", min_value=0, step=1000)
    with i_c4: 
        st.write(""); st.write("")
        if st.button("기록하기"):
            if a_input > 0 and send_to_sheet(t_choice, c_choice, a_input): st.success("기록 완료!")
    st.markdown('</div>', unsafe_allow_html=True)

    df_assets_sheet = load_sheet_data(GID_MAP["Assets"])
    if not df_assets_sheet.empty:
        df_assets_sheet.columns = ["항목", "금액"]; df_assets_sheet["val"] = df_assets_sheet["금액"].apply(to_numeric)
    
    inv_rows = []
    for cat_name, items in {"주식": FIXED_DATA["stocks"], "코인": FIXED_DATA["crypto"]}.items():
        for name, info in items.items():
            val = info['평단'] * info['수량']; inv_rows.append({"항목": name, "val": val})
    
    df_total = pd.concat([df_assets_sheet, pd.DataFrame(inv_rows)], ignore_index=True)
    a_df = df_total[df_total["val"] >= 0].copy(); l_df = df_total[df_total["val"] < 0].copy()
    
    col_a, col_l = st.columns(2)
    with col_a:
        st.subheader("💰 자산 목록"); a_df["금액표기"] = a_df["val"].apply(lambda x: f"{format_krw(x)}원")
        a_df.index = range(1, len(a_df) + 1); st.table(a_df[["항목", "금액표기"]])
        st.markdown(f'<div class="total-box">자산 총계: {format_krw(a_df["val"].sum())}원</div>', unsafe_allow_html=True)
    with col_l:
        st.subheader("📉 부채 목록"); l_df["금액표기"] = l_df["val"].apply(lambda x: f"{format_krw(abs(x))}원")
        l_df.index = range(1, len(l_df) + 1); st.table(l_df[["항목", "금액표기"]])
        st.markdown(f'<div class="total-box" style="color: #ff4b4b;">부채 총계: {format_krw(abs(l_df["val"].sum()))}원</div>', unsafe_allow_html=True)
    
    net_val = a_df["val"].sum() + l_df["val"].sum()
    st.markdown(f'<div class="net-wealth">종합 순자산: {format_krw(net_val)}원</div>', unsafe_allow_html=True)

elif menu == "식단 & 건강":
    st.subheader("🥗 실시간 영양 분석 리포트")
    st.warning(f"🎯 목표: 5월 30일 결혼식 전 체중 감량 (현재 체중: {in_w:.2f}kg)")
    
    # [복구] 대시보드 메트릭 (스크린샷의 빈 공간을 채움)
    cur_nutri = {"단백질": in_prot, "칼로리": in_kcal, "지방": in_fat, "탄수화물": in_carb}
    m_cols = st.columns(len(cur_nutri))
    for i, (name, val) in enumerate(cur_nutri.items()):
        guide = DAILY_GUIDE.get(name, {"val": 100, "unit": ""})
        ratio = min(val / guide["val"], 1.0) if val > 0 else 0
        with m_cols[i]:
            st.metric(name, f"{val:.2f}{guide['unit']}", f"{int(ratio*100)}%")
            st.progress(ratio)

elif menu == "재고 관리":
    st.subheader("📦 식자재 및 생활용품 통합 관리")
    tab1, tab2 = st.tabs(["🛒 식재료 현황", "⏰ 교체주기 관리"])
    
    with tab1:
        if 'inventory' not in st.session_state:
            st.session_state.inventory = pd.DataFrame([
                {"분류": "Protein", "항목": "냉동 삼치", "수량": "4팩"},
                {"분류": "Protein", "항목": "냉동닭다리살", "수량": "3팩단위"},
                {"분류": "Protein", "항목": "단백질 쉐이크", "수량": "9개"},
                {"분류": "Grains", "항목": "카무트/쌀 혼합", "수량": "2kg"},
                {"분류": "Grains", "항목": "파스타면", "수량": "대량"},
                {"분류": "Grains", "항목": "쿠스쿠스", "수량": "500g"},
                {"분류": "Others", "항목": "토마토 페이스트", "수량": "10캔"},
                {"분류": "Others", "항목": "나시고랭 소스", "수량": "1팩"}
            ])
        edited_inv = st.data_editor(st.session_state.inventory, num_rows="dynamic", use_container_width=True, key="inv_v2")
        if st.button("식자재 데이터 저장"):
            st.session_state.inventory = edited_inv.reset_index(drop=True); st.success("저장 완료")

    with tab2:
        if 'supplies' not in st.session_state:
            st.session_state.supplies = pd.DataFrame([
                {"품목": "칫솔", "최근교체": "2026-01-15", "주기(일)": 30},
                {"품목": "면도날", "최근교체": "2026-02-01", "주기(일)": 14}
            ])
        edited_supp = st.data_editor(st.session_state.supplies, num_rows="dynamic", use_container_width=True, key="supp_v2")
        if st.button("교체주기 저장"):
            st.session_state.supplies = edited_supp.reset_index(drop=True); st.success("저장 완료")
