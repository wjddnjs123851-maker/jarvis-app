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

# --- [2. 유틸리티] ---
def format_krw(val):
    return f"{int(val):,}"

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
st.set_page_config(page_title="JARVIS v33.8", layout="wide")
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
    
    if menu == "식단 & 건강":
        st.subheader("데이터 입력 (정밀)")
        in_w = st.number_input("체중(kg)", 0.0, 200.0, 125.0, step=0.01, format="%.2f")
        in_fat = st.number_input("지방 (g)", 0.0, format="%.2f")
        in_carb = st.number_input("탄수화물 (g)", 0.0, format="%.2f")
        in_prot = st.number_input("단백질 (g)", 0.0, format="%.2f")
        in_kcal = st.number_input("칼로리 (kcal)", 0.0, format="%.2f")
        if st.button("식단 입력 완료 및 리셋"):
            send_to_sheet("건강", "체중", in_w)
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
            if a_input > 0 and send_to_sheet(t_choice, c_choice, a_input): st.success("완료!")
    st.markdown('</div>', unsafe_allow_html=True)
    st.info("자산 및 부채 목록이 표시되는 영역입니다. (v33.7과 동일)")

elif menu == "재고 관리":
    # A. 식자재 통합 관리 시스템 (편집 기능 강화)
    st.subheader("📦 식자재 통합 관리 시스템")
    if 'inventory' not in st.session_state:
        st.session_state.inventory = pd.DataFrame([
            {"항목": "닭다리살", "수량": "4팩", "보관": "냉동", "구매일": "2026-02-10", "유통기한": "2026-05-10"},
            {"항목": "냉동삼치", "수량": "4팩", "보관": "냉동", "구매일": "2026-02-12", "유통기한": "2026-04-12"}
        ])
    
    # 인덱스를 1부터 시작하도록 조정
    inv_display = st.session_state.inventory.copy()
    inv_display.index = range(1, len(inv_display) + 1)
    
    # st.data_editor의 수정 사항이 session_state에 즉시 반영되도록 설정
    edited_inv = st.data_editor(inv_display, num_rows="dynamic", use_container_width=True, key="inv_editor_v3")
    
    # 수정된 데이터를 다시 저장할 때는 인덱스 초기화
    if st.button("식자재 데이터 저장"):
        st.session_state.inventory = edited_inv.reset_index(drop=True)
        st.success("식자재 데이터가 업데이트되었습니다.")

    st.divider()

    # B. 생활용품 교체주기 (자동 계산 시스템)
    st.subheader("⏰ 생활용품 교체주기 자동 관리")
    if 'supplies' not in st.session_state:
        st.session_state.supplies = pd.DataFrame([
            {"품목": "칫솔", "최근교체일": "2026-01-15", "주기(일)": 30},
            {"품목": "면도날", "최근교체일": "2026-02-01", "주기(일)": 14},
            {"품목": "수건", "최근교체일": "2025-06-01", "주기(일)": 365}
        ])

    supplies_df = st.session_state.supplies.copy()
    
    # 차기 교체일 및 잔여일 계산
    def calculate_dates(row):
        last_date = datetime.strptime(row['최근교체일'], '%Y-%m-%d')
        next_date = last_date + timedelta(days=int(row['주기(일)']))
        remaining = (next_date - datetime.now()).days
        return next_date.strftime('%Y-%m-%d'), f"{remaining}일 남음" if remaining >= 0 else f"{abs(remaining)}일 지남"

    supplies_df[['차기교체일', '상태']] = supplies_df.apply(lambda r: pd.Series(calculate_dates(r)), axis=1)
    supplies_df.index = range(1, len(supplies_df) + 1)
    
    st.table(supplies_df)

    # 교체 완료 처리 영역
    c1, c2 = st.columns([2, 1])
    with c1:
        target_item = st.selectbox("교체 완료한 품목 선택", supplies_df['품목'].tolist())
    with c2:
        st.write(""); st.write("")
        if st.button("교체 완료 (오늘 날짜로 갱신)"):
            today_str = datetime.now().strftime('%Y-%m-%d')
            st.session_state.supplies.loc[st.session_state.supplies['품목'] == target_item, '최근교체일'] = today_str
            st.success(f"{target_item} 교체 완료! 다음 교체일이 재계산되었습니다.")
            st.rerun()

elif menu == "식단 & 건강":
    st.info("식단 분석 리포트 영역입니다. (v33.7과 동일)")
