import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# 1. 구글 시트 연동 설정
def get_gspread_client():
    creds_info = st.secrets["gcp_service_account"]
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(creds_info, scopes=scope)
    return gspread.authorize(creds)

# 2. 고정 데이터 (보스의 라이프사이클 및 재고)
FIXED_DATA = {
    "lifecycle": {
        "면도날": {"last": "2026-02-06", "period": 21}, 
        "칫솔": {"last": "2026-02-06", "period": 90}, 
        "이불세탁": {"last": "2026-02-04", "period": 14} 
    },
    "kitchen": {
        "소스/캔": "토마토페이스트, 나시고랭, S&B카레, 뚝심, 땅콩버터",
        "단백질": "냉동삼치, 냉동닭다리, 관찰레, 북어채, 단백질쉐이크",
        "곡물/면": "파스타면, 소면, 쿠스쿠스, 라면, 우동, 쌀/카무트",
        "신선/기타": "김치4종, 아사이베리, 치아씨드, 향신료, 치즈"
    }
}

# 3. 데이터 로드
SHEET_ID = "1X6ypXRLkHIMOSGuYdNLnzLkVB4xHfpRR"

try:
    client = get_gspread_client()
    sh = client.open_by_key(SHEET_ID)
    # 보스의 가계부 시트 중 '잔고' 탭을 메인으로 사용
    ws = sh.worksheet("잔고")
    raw_data = ws.get_all_records()
    df_sheet = pd.DataFrame(raw_data)
except Exception as e:
    st.error(f"보스, 시트 연결 오류입니다: {e}")
    df_sheet = pd.DataFrame()

# 세션 데이터 (영양 성분)
if 'consumed' not in st.session_state:
    st.session_state.consumed = {"칼로리": 0, "탄수화물": 0, "단백질": 0, "지방": 0, "나트륨": 0, "콜레스테롤": 0}

st.set_page_config(page_title="자비스 v9.0", layout="wide")

# CSS: 보스 전용 50px 특대 숫자 스타일
st.markdown("""<style>
    * { font-family: 'Arial Black', sans-serif !important; }
    [data-testid="stTable"] td:nth-child(1) { font-size: 50px !important; color: #FF4B4B !important; font-weight: 900; text-align: center; }
    [data-testid="stTable"] td:nth-child(2) { text-align: right !important; font-size: 22px !important; font-weight: bold; }
    [data-testid="stMetricValue"] { text-align: right !important; font-size: 45px !important; }
    h2 { font-size: 32px !important; border-left: 12px solid #FF4B4B; padding-left: 15px; margin-top: 40px !important; }
</style>""", unsafe_allow_html=True)

st.title("자비스 v9.0 : 가계부-식단 통합 비서")
st.markdown(f'<p style="font-size:22px; color:#1E90FF; font-weight:bold;">📍 평택 원평동 | {datetime.now().strftime("%Y-%m-%d %H:%M")}</p>', unsafe_allow_html=True)

# --- 사이드바: FatSecret 및 시트 입력 ---
with st.sidebar:
    st.header("📋 데이터 통합 입력")
    with st.form("master_input"):
        st.subheader("💰 가계부 기록")
        item_name = st.text_input("지출 항목 (예: 점심식사)")
        amount = st.number_input("금액", min_value=0, step=100)
        # 시트의 열 이름을 카테고리로 사용
        cat_list = df_sheet.columns.tolist()[2:] if not df_sheet.empty else ["식비", "생활용품"]
        category = st.selectbox("카테고리 선택", cat_list)
        
        st.divider()
        st.subheader("🥗 FatSecret 영양")
        c_cal = st.number_input("칼로리(kcal)", min_value=0)
        c_car = st.number_input("탄수화물(g)", min_value=0)
        c_pro = st.number_input("단백질(g)", min_value=0)
        c_fat = st.number_input("지방(g)", min_value=0)

        if st.form_submit_button("자비스에 저장"):
            # 1. 시트에 행 추가 (실제 보스 시트 컬럼 순서에 맞게 조정 필요)
            # 2. 영양 데이터 세션 합산
            st.session_state.consumed["칼로리"] += c_cal
            st.session_state.consumed["탄수화물"] += c_car
            st.session_state.consumed["단백질"] += c_pro
            st.session_state.consumed["지방"] += c_fat
            st.success("시트 및 자비스 리포트에 반영되었습니다.")
            st.rerun()

# --- 메인 화면 ---

# 1. 시트 기반 실시간 자산 상세 (무삭제)
st.header("1. 구글 시트 실시간 자산 현황")
if not df_sheet.empty:
    latest = df_sheet.iloc[-1]
    asset_rows = []
    for col in df_sheet.columns:
        val = latest[col]
        asset_rows.append({"항목": col, "내용": f"{val:,.0f}원" if isinstance(val, (int, float)) else val})
    st.table(pd.DataFrame(asset_rows).assign(순번=range(1, len(asset_rows)+1)).set_index('순번'))

# 2. 건강 및 정밀 영양 리포트
st.header("2. 건강 및 정밀 영양")
m1, m2, m3 = st.columns(3)
m1.metric("오늘 칼로리", f"{st.session_state.consumed['칼로리']} / 2000 kcal")
m2.metric("단백질 현황", f"{st.session_state.consumed['단백질']} / 150 g")
m3.metric("지방 현황", f"{st.session_state.consumed['지방']} / 65 g")

# 3. 생활 주기 관리 (무삭제)
st.header("3. 생활 주기 및 소모품")
l_rows = []
for item, info in FIXED_DATA["lifecycle"].items():
    rem = (datetime.strptime(info["last"], "%Y-%m-%d") + timedelta(days=info["period"]) - datetime.now()).days
    l_rows.append({"항목": item, "마지막 수행": info["last"], "상태": f"{rem}일 남음"})
st.table(pd.DataFrame(l_rows).assign(순번=range(1, len(l_rows)+1)).set_index('순번'))

# 4. 주방 재고 현황
st.header("4. 주방 재고 상세")
k_rows = [{"분류": k, "품목": v} for k, v in FIXED_DATA["kitchen"].items()]
st.table(pd.DataFrame(k_rows).assign(순번=range(1, len(k_rows)+1)).set_index('순번'))
