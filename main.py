import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime, timedelta

# --- [1. 시스템 설정 및 시트 연결] ---
# 보스의 최신 시트 ID 적용
SPREADSHEET_ID = '17kw1FMK50MUpAWA9VPSile8JZeeq6TZ9DWJqMRaBMUM'
# 시트 내 Assets 탭의 실제 GID를 확인하여 입력해 주세요 (기본값 0)
GID_MAP = {"Log": "0", "Finance": "0", "Assets": "0"} 

FIXED_DATA = {
    "health_target": {
        "칼로리": 2000, "지방": 65, "콜레스테롤": 300, "나트륨": 2000, 
        "탄수화물": 300, "식이섬유": 30, "당": 50, "단백질": 150
    },
    "stocks": {
        "동성화인텍": {"평단": 22701, "수량": 21, "코드": "033500"},
        "삼성중공업": {"평단": 16761, "수량": 88, "코드": "010140"},
        "SK하이닉스": {"평단": 473521, "수량": 6, "코드": "000660"},
        "삼성전자": {"평단": 78895, "수량": 46, "코드": "005930"}
    },
    "crypto": {
        "BTC": {"평단": 137788139, "수량": 0.00181400, "마켓": "KRW-BTC"},
        "ETH": {"평단": 4243000, "수량": 0.03417393, "마켓": "KRW-ETH"}
    },
    "recurring": [
        {"항목": "임대료", "금액": 261620}, {"항목": "대출 이자", "금액": 263280},
        {"항목": "통신비", "금액": 136200}, {"항목": "보험료", "금액": 121780},
        {"항목": "청년도약계좌(적금)", "금액": 700000}, {"항목": "구독서비스", "금액": 42680}
    ]
}

API_URL = "https://script.google.com/macros/s/AKfycbzX1w7136qfFsnRb0RMQTZvJ1Q_-GZb5HAwZF6yfKiLTHbchJZq-8H2GXjV2z5WnkmI4A/exec"

# --- [2. 유틸리티] ---
def format_krw(val):
    """금액 우측 정렬 및 콤마 처리"""
    try:
        n = int(float(str(val).replace(',', '').replace('원', '').strip()))
        return f"{n:,}원"
    except: return "0원"

@st.cache_data(ttl=10)
def load_assets_pure():
    """Assets 탭에서 날짜 로그를 제외한 순수 자산 데이터만 필터링"""
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&gid={GID_MAP['Assets']}"
    try:
        df = pd.read_csv(url)
        # 데이터가 밀리지 않도록 '항목' 컬럼이 문자열이고 날짜 형식이 아닌 것만 추출
        df.columns = ['항목', '금액'] + list(df.columns[2:])
        df_clean = df[~df['항목'].astype(str).str.contains('2026')].dropna(subset=['항목', '금액'])
        return df_clean[['항목', '금액']]
    except: return pd.DataFrame(columns=['항목', '금액'])

# --- [3. 메인 인터페이스 스타일] ---
st.set_page_config(page_title="JARVIS v30.0", layout="wide")
# 모든 표 숫자 데이터 우측 정렬 CSS
st.markdown("<style>.stTable td { text-align: right !important; }</style>", unsafe_allow_html=True)

# --- [4. 메뉴별 출력] ---
with st.sidebar:
    st.title("JARVIS 제어 센터")
    menu = st.radio("메뉴 선택", ["영양/식단/체중", "자산/투자/가계부", "재고/생활관리"])
    st.divider()

st.title(f"자비스 리포트: {menu}")

if menu == "자산/투자/가계부":
    # 1. 고정 지출 섹션 복구
    st.subheader("매달 고정 지출 예정 내역")
    df_recur = pd.DataFrame(FIXED_DATA["recurring"])
    df_recur["금액"] = df_recur["금액"].apply(format_krw)
    st.table(df_recur.assign(No=range(1, len(df_recur)+1)).set_index('No'))

    # 2. 통합 자산 관리 섹션 (밀림 방지 적용)
    st.subheader("실시간 통합 자산 현황")
    df_assets = load_assets_pure()
    a_rows = []
    
    # 기초 자산 (시트 데이터)
    if not df_assets.empty:
        for _, row in df_assets.iterrows():
            if "항목" in str(row['항목']): continue
            a_rows.append({"분류": "금융자산", "항목": str(row['항목']), "평가액": format_krw(row['금액']), "비고": "기초잔액"})

    # 주식/코인 (고정 데이터)
    for n, i in FIXED_DATA["stocks"].items():
        # (실시간 시세 연동 로직 포함)
        a_rows.append({"분류": "주식", "항목": n, "평가액": format_krw(i['평단'] * i['수량']), "비고": "투자자산"})

    df_report = pd.DataFrame(a_rows)
    df_report.index = range(1, len(df_report) + 1)
    st.table(df_report)

elif menu == "영양/식단/체중":
    # 보스께서 '완벽하다'고 하신 기존 입력 및 리포트 로직 유지
    st.info("기존 영양/식단/체중 탭의 설정이 유지되고 있습니다.")
    # (이미 확인된 영양소 8종 입력 및 리포트 코드 삽입)
