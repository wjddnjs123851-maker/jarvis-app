import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# --- [1. 시스템 설정] ---
SPREADSHEET_ID = '12cPPhM68K3SopQJtZyWEq8adDuP98bJ4efoYbjFDDOI'
GID_MAP = {
    "Log": "0", 
    "Assets": "1068342666", 
    "Report": "308599580"
}

COLOR_ASSET = "#4dabf7"
COLOR_DEBT = "#ff922b"

# --- [2. 유틸리티] ---
def to_numeric(val):
    try:
        if pd.isna(val): return 0
        # 숫자와 마이너스 부호만 남기고 제거
        s = "".join(filter(lambda x: x.isdigit() or x == '-', str(val)))
        return int(s) if s else 0
    except: return 0

def get_current_time():
    # KST 오후 시간 보정
    now = datetime.utcnow() + timedelta(hours=9)
    return now.strftime('%Y-%m-%d %H:%M:%S')

def get_weather():
    try:
        w_url = "https://api.open-meteo.com/v1/forecast?latitude=36.99&longitude=127.11&current_weather=true&timezone=auto"
        res = requests.get(w_url, timeout=2).json()
        temp = res['current_weather']['temperature']
        return f"☀️ {temp}°C"
    except: return "날씨 로드 실패"

def load_sheet_data(gid):
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={gid}&t={datetime.now().timestamp()}"
    try:
        # 헤더를 읽어오되, 데이터가 없으면 빈 프레임 반환
        df = pd.read_csv(url)
        return df.dropna(how='all')
    except: return pd.DataFrame()

# --- [3. 메인 레이아웃] ---
st.set_page_config(page_title="JARVIS v45.0", layout="wide")
st.markdown(f"<style>.stApp {{ background-color: #ffffff; color: #212529; }} .net-box {{ background-color: #f8f9fa; padding: 20px; border-radius: 10px; border: 1px solid {COLOR_ASSET}; margin-bottom: 25px; }}</style>", unsafe_allow_html=True)

# 헤더
st.markdown(f"### {get_current_time()} | 평택 {get_weather()}")

# 사이드바 메뉴
menu = st.sidebar.radio("MENU", ["투자 & 자산", "식단 & 건강", "재고 관리"])

# --- [4. 투자 & 자산: 시트 기반 실시간 합산] ---
if menu == "투자 & 자산":
    st.header("종합 자산 관리 (시트 연동)")
    
    df_assets = load_sheet_data(GID_MAP["Assets"])
    
    if not df_assets.empty:
        # 정원님이 수정하신 시트 구조 반영 (A열: 항목, B열: 금액)
        df_assets = df_assets.iloc[:, [0, 1]]
        df_assets.columns = ["항목", "금액"]
        df_assets["val"] = df_assets["금액"].apply(to_numeric)
        
        # 자산과 부채 분류
        a_df = df_assets[df_assets["val"] > 0].copy()
        l_df = df_assets[df_assets["val"] < 0].copy()
        
        net_worth = df_assets["val"].sum()

        st.markdown(f"""<div class="net-box"><small>시트 기반 통합 순자산</small><br><span style="font-size:2.5em; color:{COLOR_ASSET}; font-weight:bold;">{net_worth:,.0f} 원</span></div>""", unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("보유 자산 내역")
            st.table(a_df[["항목", "금액"]])
        with c2:
            st.subheader("부채 및 카드값 내역")
            if not l_df.empty:
                # 부채는 보기 좋게 양수로 변환하여 표시
                l_display = l_df.copy()
                l_display["금액"] = l_display["val"].apply(lambda x: f"{abs(x):,}")
                st.table(l_display[["항목", "금액"]])
    else:
        st.error("Assets 시트 연동 실패. 공유 설정을 확인하세요.")

# --- [5. 식단 및 재고 섹션 (구조 유지)] ---
elif menu == "식단 & 건강":
    st.header("영양 분석")
    st.info("지방 → 콜레스테롤 → 나트륨 → 탄수화물 → 식이섬유 → 당 → 단백질 순서")

elif menu == "재고 관리":
    st.header("창고 재고 목록")
    st.write("금 16g 및 식재료 리스트가 관리됩니다.")

st.sidebar.button("새로고침", on_click=st.cache_data.clear)
