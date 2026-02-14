import streamlit as st
import pandas as pd
import datetime
import urllib.request
import json

# --- 1. 기본 설정 및 데이터 로드 ---
# 보스의 가계부 시트 ID
SPREADSHEET_ID = '1X6ypXRLkHIMOSGuYdNLnzLkVB4xHfpRR'

# 라이브러리 없이 시트를 읽기 위해 CSV 내보내기 링크를 생성합니다.
# (이 방식은 시트가 '링크가 있는 모든 사용자에게 공개'되어 있거나 서비스 계정 권한이 필요할 수 있으나, 
# 가장 충돌이 적은 방식인 공개 CSV 읽기 방식으로 먼저 시도합니다.)
SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv"

@st.cache_data(ttl=600) # 10분마다 데이터 갱신
def load_data():
    try:
        df = pd.read_csv(SHEET_URL)
        return df
    except Exception as e:
        return None

# --- 2. 세션 상태 (식단 관리용) ---
if 'nutri' not in st.session_state:
    st.session_state.nutri = {'kcal': 0, 'carb': 0, 'prot': 0, 'fat': 0}

# --- 3. UI 레이아웃 ---
st.set_page_config(page_title="JARVIS", layout="wide")
st.title("🛡️ JARVIS: 보스의 전용 비서")

tab1, tab2, tab3 = st.tabs(["💸 가계부 리포트", "🥗 식단 관리", "📦 재고 및 일정"])

# --- TAB 1: 가계부 ---
with tab1:
    st.header("실시간 가계부 현황")
    data = load_data()
    if data is not None:
        st.success("보스의 가계부 데이터를 성공적으로 불러왔습니다.")
        # 모든 항목(이자, 정수기, 난방비 등) 상세 출력
        st.dataframe(data, use_container_width=True)
    else:
        st.error("데이터를 불러오지 못했습니다. 구글 시트의 [공유] 설정에서 '링크가 있는 모든 사용자에게 뷰어' 권한이 있는지 확인해 주십시오.")

# --- TAB 2: 식단 ---
with tab2:
    st.header("오늘의 식단 합산")
    with st.form("food"):
        c1, c2, c3, c4 = st.columns(4)
        k = c1.number_input("칼로리", 0)
        c = c2.number_input("탄수", 0)
        p = c3.number_input("단백", 0)
        f = c4.number_input("지방", 0)
        if st.form_submit_button("영양소 합산"):
            st.session_state.nutri['kcal'] += k
            st.session_state.nutri['carb'] += c
            st.session_state.nutri['prot'] += p
            st.session_state.nutri['fat'] += f
            st.toast("기록 완료!")

    st.subheader("🔥 누적 섭취량")
    st.write(st.session_state.nutri)

# --- TAB 3: 재고 ---
with tab3:
    st.header("생활 주기 및 재고 관리")
    col_left, col_right = st.columns(2)
    with col_left:
        st.subheader("🔄 교체 주기")
        st.table(pd.DataFrame({"항목": ["면도날", "칫솔", "수건"], "상태": ["양호", "교체필요", "양호"]}))
    with col_right:
        st.subheader("🍳 주방 재고")
        st.table(pd.DataFrame({"품목": ["닭가슴살", "계란"], "수량": ["5kg", "2판"]}))

st.divider()
st.caption(f"최종 동기화 시각: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
