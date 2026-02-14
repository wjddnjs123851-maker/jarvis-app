import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# --- [1. 마스터 데이터 보존] ---
FIXED_DATA = {
    "profile": {"항목": ["나이", "거주", "상태", "결혼예정일"], "내용": ["32세", "평택 원평동", "공무원 발령 대기 중", "2026-05-30"]},
    "health": {"항목": ["현재 체중", "목표 체중", "주요 관리", "식단 금기"], "내용": ["125.0kg", "90.0kg", "고지혈증/ADHD", "생굴/멍게"]},
    "assets": {
        "savings": {"청년도약계좌": 14700000, "주택청약": 2540000, "전세보증금": 145850000},
        "liabilities": {"전세대출": 100000000, "마이너스통장": 3000000, "학자금대출": 1247270},
        "stocks_count": {"삼성전자": 46, "SK하이닉스": 6, "삼성중공업": 88, "동성화인텍": 21},
    },
    "kitchen": {
        "단백질": "냉동삼치, 냉동닭다리, 관찰레, 북어채, 단백질쉐이크",
        "곡물/면": "파스타면, 소면, 쿠스쿠스, 라면, 우동, 쌀/카무트",
        "신선/기타": "김치4종, 아사이베리, 치아씨드, 향신료, 치즈"
    },
    "lifecycle": {
        "면도날": {"last": "2026-02-06", "period": 21}, 
        "칫솔": {"last": "2026-02-06", "period": 90}, 
        "이불세탁": {"last": "2026-02-04", "period": 14} 
    }
}

TARGET = {"칼로리": 2000, "탄수": 300, "단백": 150, "지방": 65, "수분": 2000}

# --- [2. 시스템 초기화 및 데이터 로드] ---
st.set_page_config(page_title="자비스 v7.8", layout="wide")

# 구글 시트 ID (보스의 가계부)
SPREADSHEET_ID = '1X6ypXRLkHIMOSGuYdNLnzLkVB4xHfpRR'
SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid=0"

@st.cache_data(ttl=300) # 5분마다 갱신
def load_finance_sheet():
    try:
        return pd.read_csv(SHEET_URL)
    except:
        return pd.DataFrame()

if 'consumed' not in st.session_state:
    st.session_state.consumed = {k: 0 for k in TARGET.keys()}

# --- [3. UI 레이아웃] ---
st.title("🛡️ 자비스 통합 관리 시스템 v7.8")

# 사이드바: 입력 섹션 (FatSecret 데이터 입력용)
with st.sidebar:
    st.header("🥗 오늘 영양 기록")
    with st.form("nutri_input"):
        c_cal = st.number_input("칼로리(kcal)", 0)
        c_car = st.number_input("탄수(g)", 0)
        c_pro = st.number_input("단백(g)", 0)
        c_fat = st.number_input("지방(g)", 0)
        c_wat = st.number_input("수분(ml)", 0)
        if st.form_submit_button("영양 데이터 합산"):
            st.session_state.consumed['칼로리'] += c_cal
            st.session_state.consumed['탄수'] += c_car
            st.session_state.consumed['단백'] += c_pro
            st.session_state.consumed['지방'] += c_fat
            st.session_state.consumed['수분'] += c_wat
            st.rerun()

# 메인 화면 탭 구성
tab1, tab2, tab3 = st.tabs(["📊 데일리 리포트", "💸 실시간 가계부", "📦 재고 및 생활"])

with tab1:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("1. 기본 정보")
        st.table(pd.DataFrame(FIXED_DATA["profile"]))
        
        # 결혼식 디데이 계산
        wedding_day = datetime.strptime("2026-05-30", "%Y-%m-%d")
        d_day = (wedding_day - datetime.now()).days
        st.metric("💍 결혼식까지", f"D-{d_day}일")
        
    with col2:
        st.subheader("2. 영양 섭취 현황")
        for k, v in st.session_state.consumed.items():
            st.write(f"**{k}**: {v} / {TARGET[k]}")
            st.progress(min(v / TARGET[k], 1.0) if TARGET[k] > 0 else 0)

with tab2:
    st.header("💸 구글 시트 가계부 (실시간)")
    finance_df = load_finance_sheet()
    if not finance_df.empty:
        st.dataframe(finance_df, use_container_width=True)
    else:
        st.warning("구글 시트를 불러올 수 없습니다. 공유 설정을 확인해주세요.")

with tab3:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🔄 소모품 주기")
        l_data = []
        for item, info in FIXED_DATA["lifecycle"].items():
            next_date = datetime.strptime(info["last"], "%Y-%m-%d") + timedelta(days=info["period"])
            days_left = (next_date - datetime.now()).days
            l_data.append({"항목": item, "상태": f"{days_left}일 남음", "최근교체": info["last"]})
        st.table(pd.DataFrame(l_data))
    with c2:
        st.subheader("🍳 주방 재고")
        st.table(pd.DataFrame([{"구분": k, "내용": v} for k, v in FIXED_DATA["kitchen"].items()]))
