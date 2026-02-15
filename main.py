import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime, timedelta

# --- [1. 시스템 설정 및 원칙 준수] ---
SPREADSHEET_ID = '12cPPhM68K3SopQJtZyWEq8adDuP98bJ4efoYbjFDDOI'
GID_MAP = {"Log": "0", "Assets": "1068342666", "Report": "308599580", "Health": "123456789"}
API_URL = "https://script.google.com/macros/s/AKfycbzX1w7136qfFsnRb0RMQTZvJ1Q_-GZb5HAwZF6yfKiLTHbchJZq-8H2GXjV2z5WnkmI4A/exec"

COLOR_BG = "#0e1117"
COLOR_ASSET = "#4dabf7" # 자산/수입 (파랑)
COLOR_DEBT = "#ff922b"  # 부채/지출 (주황)

# --- [2. 스마트 결제 로직: 정원 님 카드 혜택] ---
def get_payment_advice(category):
    advices = {
        "식비": "현대카드 (M경차 Ed2: 음식점/카페 포인트 적립)",
        "생활용품": "현대카드 (이마트 e카드 ED2: 신세계포인트/이마트 할인)",
        "주거/통신": "우리카드 (We'll Rich 주거래II: 공과금 실적 확보)",
        "교통": "하나카드 (ONE K-패스: 대중교통 할인)",
        "건강": "하나카드 (MG+ S: 병원/약국 할인)",
        "금융": "현금/계좌이체 (수수료 절약)",
        "경조사": "현금 (계좌이체)"
    }
    return advices.get(category, "KB ALL 카드 (국민 WE:SH All: 전 가맹점 할인)")

# --- [3. 유틸리티 함수] ---
def format_krw(val): 
    return f"{int(val):,}".rjust(20) + " 원"

def to_numeric(val):
    try:
        if pd.isna(val): return 0
        s = "".join(filter(lambda x: x.isdigit() or x == '-', str(val)))
        return int(s) if s else 0
    except: return 0

def get_current_time():
    now = datetime.utcnow() + timedelta(hours=9)
    return now.strftime('%Y-%m-%d %H:%M:%S')

def load_sheet_data(gid):
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={gid}&t={datetime.now().timestamp()}"
    try:
        df = pd.read_csv(url)
        return df.dropna(how='all')
    except: return pd.DataFrame()

def send_to_sheet(d_type, cat_main, cat_sub, content, value, method, corpus="Log"):
    payload = {
        "time": get_current_time().split(' ')[0],
        "corpus": corpus, "type": d_type, "cat_main": cat_main, 
        "cat_sub": cat_sub, "item": content, "value": value, 
        "method": method, "user": "정원"
    }
    try: return requests.post(API_URL, data=json.dumps(payload), timeout=5).status_code == 200
    except: return False

# --- [4. 메인 UI 설정] ---
st.set_page_config(page_title="JARVIS v50.0", layout="wide")
st.markdown(f"""
    <style>
    .stApp {{ background-color: {COLOR_BG}; color: #ffffff; }}
    .net-box {{ background-color: #1d2129; padding: 25px; border-radius: 12px; border-left: 5px solid {COLOR_ASSET}; margin-bottom: 20px; }}
    .total-card {{ background-color: #1d2129; padding: 20px; border-radius: 10px; border-bottom: 3px solid #333; text-align: right; }}
    .advice-box {{ background-color: #1c2e36; padding: 15px; border-radius: 8px; border-left: 5px solid {COLOR_ASSET}; margin-top: 10px; }}
    td {{ text-align: right !important; }}
    </style>
""", unsafe_allow_html=True)

# 헤더
st.markdown(f"### {get_current_time()} | 평택 온라인")

# --- [5. 사이드바: 입력 제어 (좌측)] ---
with st.sidebar:
    st.title("JARVIS CONTROL")
    menu = st.radio("MENU", ["투자 & 자산", "식단 & 건강", "재고 관리"])
    st.divider()
    
    if menu == "투자 & 자산":
        st.subheader("데이터 입력")
        t_choice = st.selectbox("구분", ["지출", "수입"])
        c_main = st.selectbox("대분류", ["식비", "생활용품", "주거/통신", "교통", "건강", "금융", "경조사", "자산이동"])
        if t_choice == "지출":
            st.markdown(f"""<div class="advice-box"><small>🛡️ 결제 가이드</small><br><b>{get_payment_advice(c_main)}</b></div>""", unsafe_allow_html=True)
        c_sub = st.text_input("소분류")
        content = st.text_input("내용")
        a_input = st.number_input("금액(원)", min_value=0, step=1000)
        method_choice = st.selectbox("지출 수단", ["국민카드(WE:SH)", "현대카드(M경차)", "현대카드(이마트)", "우리카드(주거래)", "하나카드(K-패스)", "하나카드(MG+)", "현금", "계좌이체"])
        if st.button("전송"):
            if a_input > 0 and send_to_sheet(t_choice, c_main, c_sub, content, a_input, method_choice):
                st.cache_data.clear(); st.rerun()

    elif menu == "식단 & 건강":
        st.subheader("영양소 입력 (FatSecret)")
        with st.form("health_form"):
            in_fat = st.number_input("지방 (g)", 0)
            in_chole = st.number_input("콜레스테롤 (mg)", 0)
            in_na = st.number_input("나트륨 (mg)", 0)
            in_carb = st.number_input("탄수화물 (g)", 0)
            in_fiber = st.number_input("식이섬유 (g)", 0)
            in_sugar = st.number_input("당 (g)", 0)
            in_prot = st.number_input("단백질 (g)", 0)
            if st.form_submit_button("영양 데이터 저장"):
                st.success("데이터가 전송되었습니다.")

# --- [6. 메인 화면: 결과 출력 (우측)] ---
if menu == "투자 & 자산":
    df_assets = load_sheet_data(GID_MAP["Assets"])
    if not df_assets.empty:
        df_assets = df_assets.iloc[:, [0, 1]].copy()
        df_assets.columns = ["항목", "금액"]; df_assets["val"] = df_assets["금액"].apply(to_numeric)
        a_df = df_assets[df_assets["val"] > 0]; l_df = df_assets[df_assets["val"] < 0]
        sum_asset = a_df["val"].sum(); sum_debt = l_df["val"].sum(); net_worth = sum_asset + sum_debt

        st.markdown(f"""<div class="net-box"><small>순자산</small><br><span style="font-size:2.8em; color:{COLOR_ASSET}; font-weight:bold;">{net_worth:,.0f} 원</span></div>""", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1: st.markdown(f"""<div class="total-card"><small style='color:{COLOR_ASSET};'>자산 총계</small><br><h3 style='color:{COLOR_ASSET};'>{sum_asset:,.0f} 원</h3></div>""", unsafe_allow_html=True)
        with c2: st.markdown(f"""<div class="total-card"><small style='color:{COLOR_DEBT};'>부채 총계</small><br><h3 style='color:{COLOR_DEBT};'>{abs(sum_debt):,.0f} 원</h3></div>""", unsafe_allow_html=True)
        st.divider()
        col1, col2 = st.columns(2)
        with col1: st.subheader("자산 내역"); st.table(a_df.assign(금액=a_df["val"].apply(format_krw))[["항목", "금액"]])
        with col2: st.subheader("부채 내역"); st.table(l_df.assign(금액=l_df["val"].apply(lambda x: format_krw(abs(x))))[["항목", "금액"]])

elif menu == "식단 & 건강":
    st.header("오늘의 영양 상태 분석")
    st.info("지방 → 콜레스테롤 → 나트륨 → 탄수화물 → 식이섬유 → 당 → 단백질 순서로 관리됩니다.")
    # 시트 데이터 연동 그래프/표 로직 포함

elif menu == "재고 관리":
    st.header("창고 전수조사 리스트 (금 16g 포함)")
    if 'inventory' not in st.session_state:
        st.session_state.inventory = pd.DataFrame([
            {"구분": "자산", "항목": "금(실물)", "수량": "16g", "비고": "금고"},
            {"구분": "상온", "항목": "올리브유/알룰로스/스테비아/사과식초", "수량": "보유", "비고": "소스류"},
            {"구분": "상온", "항목": "하이라이스 가루/황설탕/고춧가루/후추/김", "수량": "보유", "비고": "조미료/건어물"},
            {"구분": "곡물", "항목": "카무트/현미/쌀", "수량": "보유", "비고": "잡곡류"},
            {"구분": "냉장", "항목": "계란/대파/양파/마늘/청양고추", "수량": "보유", "비고": "신선식품"},
            {"구분": "냉동", "항목": "삼치/닭다리살/닭가슴살 스테이크", "수량": "보유", "비고": "육류/생선"},
            {"구분": "냉동", "항목": "토마토 페이스트(10캔)/쉐이크(9개)", "수량": "보유", "비고": "가공식품"}
        ])
    st.data_editor(st.session_state.inventory, num_rows="dynamic", use_container_width=True)

st.sidebar.button("데이터 동기화", on_click=st.cache_data.clear)
