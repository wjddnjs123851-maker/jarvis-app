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
COLOR_ASSET = "#4dabf7" # 자산 (파랑)
COLOR_DEBT = "#ff922b"  # 부채 (주황)

# --- [2. 정원 님 전용 스마트 결제 로직 (업데이트)] ---
def get_payment_advice(category):
    """
    정원 님이 보유하신 실제 카드 기반 혜택 로직
    """
    if category == "식비":
        return "현대카드 (M경차 Ed2 추천: 음식점/카페 포인트 적립 극대화)"
    elif category == "생활용품":
        return "현대카드 (이마트 e카드 ED2 추천: 신세계포인트 및 이마트 특화 할인)"
    elif category == "주거/통신":
        return "우리카드 (We'll Rich 주거래II 추천: 주거래 혜택 및 공과금 실적 확보)"
    elif category == "교통":
        return "하나카드 (ONE K-패스 추천: 대중교통 할인) 또는 국민카드 (하이패스 전용)"
    elif category == "건강":
        return "하나카드 (MG+ S 추천: 병원/약국 할인 혜택 확인)"
    elif category == "금융":
        return "현금/계좌이체 (수수료 절약)"
    else:
        return "KB ALL 카드 (국민 WE:SH All 추천: 전 가맹점 무난한 할인/적립)"

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
st.set_page_config(page_title="JARVIS v49.0", layout="wide")
st.markdown(f"""
    <style>
    .stApp {{ background-color: {COLOR_BG}; color: #ffffff; }}
    .net-box {{ background-color: #1d2129; padding: 25px; border-radius: 12px; border-left: 5px solid {COLOR_ASSET}; margin-bottom: 20px; }}
    .total-card {{ background-color: #1d2129; padding: 20px; border-radius: 10px; border-bottom: 3px solid #333; }}
    .advice-box {{ background-color: #1c2e36; padding: 15px; border-radius: 8px; border-left: 5px solid {COLOR_ASSET}; margin-top: 10px; }}
    td {{ text-align: right !important; }}
    </style>
""", unsafe_allow_html=True)

# 헤더
st.markdown(f"### {get_current_time()} | 평택 ONLINE")

# --- [5. 사이드바: 입력 제어] ---
with st.sidebar:
    st.title("JARVIS CONTROL")
    menu = st.radio("MENU", ["투자 & 자산", "식단 & 건강", "재고 관리"])
    st.divider()
    
    if menu == "투자 & 자산":
        st.subheader("데이터 입력")
        t_choice = st.selectbox("구분", ["지출", "수입"])
        c_main = st.selectbox("대분류", ["식비", "생활용품", "주거/통신", "교통", "건강", "금융", "경조사", "자산이동"])
        
        # [카드 맞춤 추천 가이드 노출]
        if t_choice == "지출":
            advice = get_payment_advice(c_main)
            st.markdown(f"""<div class="advice-box"><small>🛡️ JARVIS SMART GUIDE</small><br><b>{advice}</b></div>""", unsafe_allow_html=True)
            
        c_sub = st.text_input("소분류 (항목)")
        content = st.text_input("상세 내용")
        a_input = st.number_input("금액(원)", min_value=0, step=1000)
        
        # 정원 님 실제 보유 카드 리스트 (이미지 기반 업데이트)
        method_choice = st.selectbox("지출 수단", [
            "국민카드(WE:SH)", "현대카드(M경차)", "현대카드(이마트)", 
            "우리카드(주거래)", "하나카드(K-패스)", "하나카드(MG+)", "현금", "계좌이체"
        ])
        
        if st.button("데이터 전송", use_container_width=True):
            if a_input > 0 and send_to_sheet(t_choice, c_main, c_sub, content, a_input, method_choice):
                st.cache_data.clear(); st.rerun()

# --- [6. 메인 화면: 투자 & 자산 결과] ---
if menu == "투자 & 자산":
    df_assets = load_sheet_data(GID_MAP["Assets"])
    if not df_assets.empty:
        df_assets = df_assets.iloc[:, [0, 1]].copy()
        df_assets.columns = ["항목", "금액"]
        df_assets["val"] = df_assets["금액"].apply(to_numeric)
        
        a_df = df_assets[df_assets["val"] > 0].copy()
        l_df = df_assets[df_assets["val"] < 0].copy()
        
        sum_asset = a_df["val"].sum()
        sum_debt = l_df["val"].sum()
        net_worth = sum_asset + sum_debt

        # 최상단 순자산 및 총계 노출
        st.markdown(f"""
            <div class="net-box">
                <small style='color:#888;'>통합 순자산 (Net Worth)</small><br>
                <span style="font-size:2.8em; color:{COLOR_ASSET}; font-weight:bold;">{net_worth:,.0f} 원</span>
            </div>
        """, unsafe_allow_html=True)

        t_c1, t_c2 = st.columns(2)
        with t_c1:
            st.markdown(f"""<div class="total-card"><small style='color:{COLOR_ASSET};'>자산 총계 (Asset Total)</small><br><h3 style='color:{COLOR_ASSET};'>{sum_asset:,.0f} 원</h3></div>""", unsafe_allow_html=True)
        with t_c2:
            st.markdown(f"""<div class="total-card"><small style='color:{COLOR_DEBT};'>부채 총계 (Debt Total)</small><br><h3 style='color:{COLOR_DEBT};'>{abs(sum_debt):,.0f} 원</h3></div>""", unsafe_allow_html=True)

        st.divider()

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("세부 자산 내역")
            st.table(a_df.assign(금액=a_df["val"].apply(format_krw))[["항목", "금액"]])
        with col2:
            st.subheader("세부 부채 내역")
            if not l_df.empty:
                st.table(l_df.assign(금액=l_df["val"].apply(lambda x: format_krw(abs(x))))[["항목", "금액"]])

# ... (나머지 식단/재고 관리 로직은 원칙대로 유지됨) ...
