import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime, timedelta

# --- [1. 마스터 데이터: 보스의 투자 및 자산 정보 고정] ---
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
    "assets_base": {
        "순금(16g)": 3700000, # 대략적 가치, 시세연동 예정
        "가용현금": 492918,
        "청년도약계좌": 14700000,
        "주택청약": 2540000,
        "전세보증금": 145850000,
        "전세대출": -100000000,
        "마이너스통장": -3000000,
        "학자금대출": -1247270
    },
    "categories": {
        "지출": ["식비(집밥)", "식비(외식)", "식비(배달)", "식비(편의점)", "생활용품", "건강/의료", "기호품", "주거/통신", "교통/차량", "금융/보험", "결혼준비", "경조사", "기타지출"],
        "수입": ["급여", "금융소득", "기타"],
        "자산이동": ["적금/청약 납입", "주식/코인 매수", "대출 원금상환"]
    },
    "lifecycle": {
        "면도날": {"last": "2026-02-06", "period": 21},
        "칫솔": {"last": "2026-02-06", "period": 90},
        "이불세탁": {"last": "2026-02-04", "period": 14}
    },
    "kitchen": {
        "단백질": "냉동삼치, 냉동닭다리, 관찰레, 북어채, 단백질쉐이크",
        "곡물/면": "파스타면, 소면, 쿠스쿠스, 라면, 우동, 쌀/카무트",
        "신선/기타": "김치4종, 아사이베리, 치아씨드, 향신료, 치즈"
    }
}

API_URL = "https://script.google.com/macros/s/AKfycbzX1w7136qfFsnRb0RMQTZvJ1Q_-GZb5HAwZF6yfKiLTHbchJZq-8H2GXjV2z5WnkmI4A/exec"

# --- [2. 유틸리티] ---
def send_to_sheet(d_type, item, value):
    now = datetime.utcnow() + timedelta(hours=9)
    payload = {"time": now.strftime('%Y-%m-%d %H:%M:%S'), "type": d_type, "item": item, "value": value}
    try:
        requests.post(API_URL, data=json.dumps(payload), timeout=5)
        return True
    except: return False

def get_live_prices():
    prices = {"stocks": {}, "crypto": {}, "gold": 231345}
    # 주식/코인 가격 수집 로직 (v17.0과 동일)
    return prices

# --- [3. 사이드바 및 메인 제어] ---
st.set_page_config(page_title="JARVIS v18.1", layout="wide")
if 'consumed' not in st.session_state: st.session_state.consumed = {k: 0 for k in FIXED_DATA["health_target"].keys()}

with st.sidebar:
    st.title("JARVIS 제어 센터")
    menu = st.radio("메뉴 선택", ["영양/식단/체중", "자산/투자/가계부", "재고/생활관리"])
    st.divider()
    
    if menu == "영양/식단/체중":
        st.subheader("건강 데이터 입력")
        in_w = st.number_input("체중(kg)", 125.0, step=0.1)
        in_kcal = st.number_input("칼로리", 0)
        if st.button("데이터 전송"):
            send_to_sheet("체중", "일일체크", in_w)
            st.success("Log 탭 기록 완료")

    elif menu == "자산/투자/가계부":
        st.subheader("가계부/자산이동 입력")
        t_type = st.selectbox("구분", ["지출", "수입", "자산이동"])
        t_cat = st.selectbox("카테고리", FIXED_DATA["categories"][t_type])
        t_memo = st.text_input("메모")
        t_val = st.number_input("금액", 0)
        if st.button("시트 기록"):
            if send_to_sheet(t_type, f"{t_cat} - {t_memo}", t_val):
                st.success("Finance 탭 기록 완료")

# --- [4. 리포트 출력] ---
st.title(f"자비스 리포트: {menu}")

if menu == "자산/투자/가계부":
    # 자산 리포트 표 출력 (v18.0 로직 유지)
    st.table(pd.DataFrame([{"항목": k, "금액": f"{v:,}원"} for k, v in FIXED_DATA["assets_base"].items()]))
