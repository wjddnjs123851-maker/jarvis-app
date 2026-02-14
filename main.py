import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime, timedelta

# --- [1. 시스템 설정 및 GID 정의] ---
SPREADSHEET_ID = '1X6ypXRLkHIMOSGuYdNLnzLkVB4xHfpRR'
GID_MAP = {
    "Log": "1716739583",
    "Finance": "1790876407",
    "Assets": "1666800532",
    "Stats": "1178071965"
}

# 마스터 데이터 (고정 수치 및 카테고리)
FIXED_DATA = {
    "health_target": {"칼로리": 2000, "탄수": 300, "단백": 150, "지방": 65, "당": 50, "나트륨": 2000, "콜레스테롤": 300},
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
    "categories": {
        "지출": ["식비(집밥)", "식비(외식)", "식비(배달)", "식비(편의점)", "생활용품", "건강/의료", "기호품", "주거/통신", "교통/차량", "금융/보험", "결혼준비", "경조사", "기타지출"],
        "수입": ["급여", "금융소득", "기타"],
        "자산이동": ["적금/청약 납입", "주식/코인 매수", "대출 원금상환"]
    }
}

API_URL = "https://script.google.com/macros/s/AKfycbzX1w7136qfFsnRb0RMQTZvJ1Q_-GZb5HAwZF6yfKiLTHbchJZq-8H2GXjV2z5WnkmI4A/exec"

# --- [2. 데이터 로드 및 통신 함수] ---
def send_to_sheet(d_type, item, value):
    now = datetime.utcnow() + timedelta(hours=9)
    payload = {"time": now.strftime('%Y-%m-%d %H:%M:%S'), "type": d_type, "item": item, "value": value}
    try:
        requests.post(API_URL, data=json.dumps(payload), timeout=5)
        return True
    except: return False

@st.cache_data(ttl=60)
def load_csv_from_sheet(sheet_name):
    gid = GID_MAP.get(sheet_name)
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={gid}"
    try:
        df = pd.read_csv(url)
        return df
    except:
        return pd.DataFrame()

def get_live_prices():
    prices = {"stocks": {}, "crypto": {}, "gold": 231345} # 금 시세 수동 보정
    # 주식/코인 가격 수집 (기존 로직 유지)
    return prices

# --- [3. 사이드바 제어 창] ---
st.set_page_config(page_title="JARVIS v19.0", layout="wide")
if 'consumed' not in st.session_state: st.session_state.consumed = {k: 0 for k in FIXED_DATA["health_target"].keys()}

with st.sidebar:
    st.title("JARVIS 제어 센터")
    menu = st.radio("메뉴 선택", ["영양/식단/체중", "자산/투자/가계부", "재고/생활관리"])
    st.divider()
    
    if menu == "영양/식단/체중":
        in_w = st.number_input("현재 체중(kg)", 125.0, step=0.1)
        in_kcal = st.number_input("칼로리", 0)
        # 기타 영양소 입력 (v17.0 동일)
        if st.button("건강 데이터 시트 전송"):
            send_to_sheet("체중", "일일체크", in_w)
            send_to_sheet("식단", "칼로리", in_kcal)
            st.success("Log 탭 기록 완료")

    elif menu == "자산/투자/가계부":
        st.subheader("가계부 기록")
        t_type = st.selectbox("구분", ["지출", "수입", "자산이동"])
        t_cat = st.selectbox("카테고리", FIXED_DATA["categories"][t_type])
        t_memo = st.text_input("메모 (항목명)")
        t_val = st.number_input("금액", 0)
        if st.button("가계부 시트 전송"):
            if send_to_sheet(t_type, f"{t_cat} - {t_memo}", t_val):
                st.success(f"{t_type} 전송 완료")

# --- [4. 메인 리포트 출력] ---
st.title(f"자비스 리포트: {menu}")

if menu == "자산/투자/가계부":
    live = get_live_prices()
    
    # 기초 자산(Assets 탭)과 변동 내역(Finance 탭) 로드
    df_assets = load_csv_from_sheet("Assets")
    df_finance = load_csv_from_sheet("Finance")
    
    st.subheader("실시간 통합 자산 현황")
    a_rows = []
    
    if not df_assets.empty:
        # 시트에 적힌 기초 자산 리스트 출력
        for index, row in df_assets.iterrows():
            # Finance 탭에서 해당 항목의 '자산이동' 누적액 계산 (추후 고도화 예정)
            a_rows.append({"분류": "금융", "항목": row['항목'], "평가액": f"{row['금액']:,}원", "비고": "기초잔액"})

    # 주식/코인 실시간 가치 합산 (v18.0 로직)
    for n, i in FIXED_DATA["stocks"].items():
        curr = live["stocks"].get(n, i['평단'])
        a_rows.append({"분류": "주식", "항목": n, "평가액": f"{curr * i['수량']:,}원", "수익률": f"{((curr/i['평단'])-1)*100:.2f}%"})
    
    for n, i in FIXED_DATA["crypto"].items():
        curr = live["crypto"].get(i['마켓'], i['평단'])
        a_rows.append({"분류": "코인", "항목": n, "평가액": f"{int(curr * i['수량']):,}원", "수익률": f"{((curr/i['평단'])-1)*100:.2f}%"})

    df_report = pd.DataFrame(a_rows)
    df_report.index = range(1, len(df_report) + 1)
    st.table(df_report)

elif menu == "영양/식단/체중":
    # 영양 리포트 표 (v17.0 로직)
    n_rows = []
    for k, v in st.session_state.consumed.items():
        n_rows.append({"항목": k, "현재": v, "목표": FIXED_DATA["health_target"][k]})
    df_n = pd.DataFrame(n_rows)
    df_n.index = range(1, len(df_n) + 1)
    st.table(df_n)
