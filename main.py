import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta

# 1. 구글 시트 연동 설정 (보안 강화)
def get_gspread_client():
    try:
        creds_info = st.secrets["gcp_service_account"]
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(creds_info, scopes=scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"⚠️ Secrets 설정 오류: {e}")
        return None

# 2. 고정 데이터
FIXED_DATA = {
    "lifecycle": {"면도날": "2026-02-06", "칫솔": "2026-02-06", "이불세탁": "2026-02-04"},
    "kitchen": {"단백질": "냉동삼치, 닭다리, 북어채", "곡물": "파스타, 쿠스쿠스, 카무트"}
}

SHEET_ID = "1X6ypXRLkHIMOSGuYdNLnzLkVB4xHfpRR"

# 데이터 로드 로직
client = get_gspread_client()
df_sheet = pd.DataFrame()

if client:
    try:
        sh = client.open_by_key(SHEET_ID)
        # 보스, 여기서 시트 탭 이름을 꼭 확인하세요!
        ws = sh.get_worksheet(0) # 첫 번째 탭을 자동으로 가져옵니다.
        df_sheet = pd.DataFrame(ws.get_all_records())
    except Exception as e:
        st.warning(f"데이터를 가져오는 중입니다... (시트 이름 확인 요망)")

# 세션 초기화
if 'consumed' not in st.session_state:
    st.session_state.consumed = {"칼로리": 0, "단백질": 0, "나트륨": 0}

st.set_page_config(page_title="자비스 v9.1", layout="wide")

# CSS (보스 전용 50px 스타일)
st.markdown("""<style>
    [data-testid="stTable"] td:nth-child(1) { font-size: 50px !important; color: #FF4B4B !important; font-weight: 900; }
    [data-testid="stMetricValue"] { font-size: 45px !important; }
</style>""", unsafe_allow_html=True)

st.title("자비스 v9.1 : 연동 오류 수정본")

# --- 메인 화면 ---
if not df_sheet.empty:
    st.header("1. 실시간 자산 현황")
    latest = df_sheet.iloc[-1]
    rows = [{"항목": col, "내용": str(latest[col])} for col in df_sheet.columns]
    st.table(pd.DataFrame(rows).assign(순번=range(1, len(rows)+1)).set_index('순번'))
else:
    st.info("시트에 데이터를 채우거나 시트 공유 설정을 확인해주세요.")

# 2. 영양 (FatSecret 수동 동기화용)
st.header("2. 오늘 영양")
c1, c2 = st.columns(2)
c1.metric("칼로리", f"{st.session_state.consumed['칼로리']} kcal")
c2.metric("단백질", f"{st.session_state.consumed['단백질']} g")
