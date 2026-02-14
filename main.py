import streamlit as st
import pandas as pd
import datetime

# --- [시스템 설정] ---
st.set_page_config(page_title="JARVIS", layout="wide")

# 보스의 가계부 시트 ID 및 공개 URL 생성
SPREADSHEET_ID = '1X6ypXRLkHIMOSGuYdNLnzLkVB4xHfpRR'
# 이 주소는 구글 시트의 데이터를 직접 CSV로 추출하는 경로입니다.
SHEET_CSV_URL = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid=0"

# --- [데이터 로드 함수] ---
def load_finance_data():
    try:
        # pandas의 기본 기능을 활용해 가장 직접적으로 데이터를 가져옵니다.
        df = pd.read_csv(SHEET_CSV_URL)
        return df
    except Exception as e:
        # 에러 발생 시 사용자에게 친절하게 안내합니다.
        st.error(f"⚠️ 데이터를 불러오는 중 장애 발생: {e}")
        return None

# --- [세션 상태 관리] ---
# 식단 누적 데이터는 새로고침 전까지 유지됩니다.
if 'daily_nutri' not in st.session_state:
    st.session_state.daily_nutri = {'칼로리': 0, '탄수': 0, '단백': 0, '지방': 0}

# --- [사이드바: 보스 정보] ---
st.sidebar.title("🛡️ JARVIS OS")
st.sidebar.info("보스, 5월 30일 결혼식까지 최선을 다해 보좌하겠습니다.")
if st.sidebar.button("데이터 강제 새로고침"):
    st.cache_data.clear()
    st.rerun()

# --- [메인 화면 구성] ---
st.title("보스의 개인 비서 시스템")

tab1, tab2, tab3 = st.tabs(["💰 실시간 가계부", "🍽️ 식단 매니저", "📅 생활 관리"])

# --- 1. 가계부 탭 ---
with tab1:
    st.header("가계부 상세 내역")
    with st.spinner("구글 시트에서 최신 데이터를 동기화 중..."):
        df = load_finance_data()
        if df is not None:
            st.success("동기화 완료.")
            # 이자, 정수기, 난방비 등 모든 열을 그대로 노출합니다.
            st.dataframe(df, use_container_width=True)
            
            # 간단한 통계 (금액 열이 있는 경우)
            if '금액' in df.columns:
                try:
                    df['금액'] = pd.to_numeric(df['금액'].astype(str).str.replace(',', ''), errors='coerce')
                    total = df['금액'].sum()
                    st.metric("현재 지출 총액", f"{total:,.0f} 원")
                except:
                    pass
        else:
            st.warning("시트의 '공유'가 '링크가 있는 모든 사용자 - 뷰어'로 되어 있는지 다시 한번 확인 부탁드립니다.")

# --- 2. 식단 탭 ---
with tab2:
    st.header("영양소 누적 계산기")
    with st.container(border=True):
        col1, col2, col3, col4 = st.columns(4)
        k = col1.number_input("Kcal", 0)
        c = col2.number_input("탄수(g)", 0)
        p = col3.number_input("단백(g)", 0)
        f = col4.number_input("지방(g)", 0)
        
        if st.button("섭취 기록 추가"):
            st.session_state.daily_nutri['칼로리'] += k
            st.session_state.daily_nutri['탄수'] += c
            st.session_state.daily_nutri['단백'] += p
            st.session_state.daily_nutri['지방'] += f
            st.success("데이터가 반영되었습니다.")

    st.subheader("🔥 오늘 현재까지의 누적량")
    st.json(st.session_state.daily_nutri)

# --- 3. 생활 관리 탭 ---
with tab3:
    st.header("생활 주기 및 재고")
    c_a, c_b = st.columns(2)
    with c_a:
        st.subheader("🔄 주기적 교체 항목")
        st.table(pd.DataFrame({
            "항목": ["면도날", "칫솔", "베개커버"],
            "상태": ["교체완료(2월)", "사용 중", "관리 필요"]
        }))
    with c_b:
        st.subheader("🍳 주방 주요 재고")
        st.table(pd.DataFrame({
            "품목": ["닭가슴살", "계란", "양파"],
            "수량": ["5kg", "2판", "넉넉함"]
        }))

st.divider()
st.caption(f"시스템 가동 중 | {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
