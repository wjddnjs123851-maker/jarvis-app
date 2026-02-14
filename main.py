import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# --- [1. 시스템 설정 및 스타일] ---
st.set_page_config(page_title="자비스 v8.0", layout="wide")
st.markdown("""<style>
    [data-testid="stTable"] td { font-size: 18px !important; }
    th { background-color: #f0f2f6 !important; }
</style>""", unsafe_allow_html=True)

# --- [2. 마스터 데이터] ---
FIXED_DATA = {
    "profile": {"항목": ["나이", "거주", "상태", "결혼예정일"], "내용": ["32세", "평택 원평동", "공무원 발령 대기 중", "2026-05-30"]},
    "health": {"항목": ["현재 체중", "목표 체중", "주요 관리", "식단 금기"], "내용": ["125.0kg", "90.0kg", "고지혈증/ADHD", "생굴/멍게"]},
    "assets": {
        "savings": {"청년도약계좌": 14700000, "주택청약": 2540000, "전세보증금": 145850000},
        "liabilities": {"전세대출": 100000000, "마이너스통장": 3000000, "학자금대출": 1247270}
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

# --- [3. 데이터 로드 로직] ---
SPREADSHEET_ID = '1X6ypXRLkHIMOSGuYdNLnzLkVB4xHfpRR'
SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid=0"

@st.cache_data(ttl=60)
def get_finance():
    try: return pd.read_csv(SHEET_URL)
    except: return pd.DataFrame({"알림": ["시트 연결 대기 중..."]})

if 'consumed' not in st.session_state:
    st.session_state.consumed = {k: 0 for k in TARGET.keys()}

# --- [4. 메인 화면 구성] ---
st.title("🛡️ 자비스 통합 대시보드 v8.0")

# 사이드바 입력창
with st.sidebar:
    st.header("🥗 영양소 입력")
    with st.form("nutri_input"):
        c_cal = st.number_input("칼로리", 0)
        c_car = st.number_input("탄수", 0)
        c_pro = st.number_input("단백", 0)
        c_fat = st.number_input("지방", 0)
        c_wat = st.number_input("수분", 0)
        if st.form_submit_button("합산 및 저장"):
            for k, v in zip(TARGET.keys(), [c_cal, c_car, c_pro, c_fat, c_wat]):
                st.session_state.consumed[k] += v
            st.rerun()

# 메인 표 레이아웃
col1, col2 = st.columns(2)

with col1:
    st.subheader("📍 기본 정보")
    st.table(pd.DataFrame(FIXED_DATA["profile"]))
    
    st.subheader("🍎 건강 및 영양 섭취")
    nutri_df = pd.DataFrame({
        "항목": TARGET.keys(),
        "현재": [f"{v} / {TARGET[k]}" for k, v in st.session_state.consumed.items()]
    })
    st.table(nutri_df)

with col2:
    st.subheader("💰 자산 및 부채 현황")
    assets_list = [{"구분": "예적금/보증금", "상세": k, "금액": f"{v:,.0f}원"} for k, v in FIXED_DATA["assets"]["savings"].items()]
    debts_list = [{"구분": "부채", "상세": k, "금액": f"{v:,.0f}원"} for k, v in FIXED_DATA["assets"]["liabilities"].items()]
    st.table(pd.DataFrame(assets_list + debts_list))
    
    st.subheader("🍳 주방 재고 현황")
    st.table(pd.DataFrame([{"카테고리": k, "재고 내역": v} for k, v in FIXED_DATA["kitchen"].items()]))

st.divider()

st.subheader("💸 실시간 가계부 데이터 (구글 시트)")
st.table(get_finance().head(10)) # 가독성을 위해 상위 10개 항목 표출

st.subheader("🔄 생활 주기 관리")
l_rows = []
for item, info in FIXED_DATA["lifecycle"].items():
    next_date = datetime.strptime(info["last"], "%Y-%m-%d") + timedelta(days=info["period"])
    days_left = (next_date - datetime.now()).days
    l_rows.append({"항목": item, "마지막 교체일": info["last"], "상태": f"{days_left}일 남음"})
st.table(pd.DataFrame(l_rows))
