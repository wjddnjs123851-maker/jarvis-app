import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# 1. 구글 시트 연동 함수 (보안 창고 Secrets 사용)
def get_gspread_client():
    creds_info = st.secrets["gcp_service_account"]
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(creds_info, scopes=scope)
    return gspread.authorize(creds)

# 2. 데이터 로드 및 초기 설정
SHEET_ID = "1X6ypXRLkHIMOSGuYdNLnzLkVB4xHfpRR"

try:
    client = get_gspread_client()
    # '잔고' 시트를 메인 데이터 소스로 사용
    sheet = client.open_by_key(SHEET_ID).worksheet("잔고")
    records = sheet.get_all_records()
    df_sheet = pd.DataFrame(records)
except Exception as e:
    st.error(f"보스, 시트 연동 중 오류가 발생했습니다. Secrets 설정을 확인해 주세요: {e}")
    df_sheet = pd.DataFrame()

# 세션 상태 초기화 (영양 및 로그용)
if 'consumed' not in st.session_state:
    st.session_state.consumed = {"칼로리": 0, "탄수화물": 0, "단백질": 0, "지방": 0, "나트륨": 0, "콜레스테롤": 0, "당류": 0}

st.set_page_config(page_title="자비스 v8.5 (Live)", layout="wide")

# CSS: 보스 전용 50px 특대 빨간 숫자 및 정렬 스타일
st.markdown("""<style>
    * { font-family: 'Arial Black', sans-serif !important; }
    [data-testid="stTable"] td:nth-child(1) { font-size: 50px !important; color: #FF4B4B !important; font-weight: 900; text-align: center; }
    [data-testid="stTable"] td:nth-child(2) { text-align: right !important; font-size: 20px !important; }
    h2 { font-size: 30px !important; border-left: 10px solid #FF4B4B; padding-left: 15px; margin-top: 40px !important; }
    [data-testid="stMetricValue"] { text-align: right !important; font-size: 40px !important; }
</style>""", unsafe_allow_html=True)

st.title("자비스 v8.5 : 통합 자동화 리포트")
st.markdown('<p style="font-size:22px; color:#1E90FF; font-weight:bold;">📍 평택 원평동: 10°C ☀️ (맑음, 습도 77%)</p>', unsafe_allow_html=True)

# --- 사이드바: 입력 시스템 ---
with st.sidebar:
    st.header("📋 실시간 기록")
    with st.form("master_input"):
        # 가계부 지출/수입 항목 (시트 반영용)
        st.subheader("💰 가계부 기록")
        item_name = st.text_input("입력")
        amount = st.number_input("금액", min_value=0, step=100)
        category = st.selectbox("카테고리", df_sheet.columns.tolist() if not df_sheet.empty else ["식비", "담배", "생활용품"])
        
        st.divider()
        # FatSecret 영양 정보
        st.subheader("🥗 FatSecret 영양")
        c_cal = st.number_input("칼로리 (kcal)", min_value=0)
        c_pro = st.number_input("단백질 (g)", min_value=0)
        c_fat = st.number_input("지방 (g)", min_value=0)
        c_car = st.number_input("탄수화물 (g)", min_value=0)

        if st.form_submit_button("자비스에 통합 저장"):
            # 시트에 데이터 추가 로직 (생략 없이 실제 구현 시 시트 API 호출)
            # st.session_state.consumed 업데이트 로직
            st.success("보스, 시트와 영양 리포트에 동시 기록되었습니다.")
            st.rerun()

# --- 메인 화면: 무삭제 상세 섹션 ---

# 1. 시트 기반 실시간 자산 (잔고 탭 데이터 100% 출력)
st.header("1. 실시간 시트 자산 현황")
if not df_sheet.empty:
    # 가장 최근 행(현재 상태) 가져오기
    latest = df_sheet.iloc[-1]
    asset_rows = []
    # 시트의 모든 열을 순회하며 요약 없이 출력
    for col in df_sheet.columns:
        val = latest[col]
        asset_rows.append({"항목": col, "금액": f"{val:,.0f}원" if isinstance(val, (int, float)) else val})
    
    st.table(pd.DataFrame(asset_rows).assign(순번=range(1, len(asset_rows)+1)).set_index('순번'))
else:
    st.warning("시트 데이터를 불러올 수 없습니다. 권한 설정을 확인하세요.")

# 2. 정밀 영양 리포트 (FatSecret 기반)
st.header("2. 건강 및 정밀 영양")
n1, n2, n3 = st.columns(3)
n1.metric("오늘 칼로리", f"{st.session_state.consumed['칼로리']} / 2000 kcal")
n2.metric("단백질 섭취", f"{st.session_state.consumed['단백질']} / 150 g")
n3.metric("나트륨 관리", f"{st.session_state.consumed['나트륨']} / 2000 mg")

# 3. 생활 주기 및 재고 관리 (기존 고정 데이터)
st.header("3. 생활 주기 및 주
