import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# --- [1. 보스의 고정 마스터 데이터] ---
FIXED_DATA = {
    "profile": {"항목": ["나이", "거주", "상태", "결혼예정일"], "내용": ["32세", "평택 원평동", "공무원 발령 대기 중", "2026-05-30"]},
    "health": {"항목": ["체중", "목표", "관리"], "내용": ["125kg", "90kg", "고지혈증/ADHD"]},
    "assets": {
        "savings": {"청년도약계좌": 14700000, "주택청약": 2540000, "전세보증금": 145850000},
        "liabilities": {"전세대출": 100000000, "마이너스통장": 3000000}
    },
    "kitchen": {
        "단백질": "냉동삼치, 냉동닭다리, 관찰레, 북어채",
        "곡물/면": "파스타면, 소면, 쿠스쿠스, 라면",
        "신선": "김치4종, 아사이베리, 치아씨드"
    }
}

# --- [2. 시스템 초기화] ---
st.set_page_config(page_title="자비스 시스템 복구", layout="wide")

if 'consumed' not in st.session_state:
    st.session_state.consumed = {"칼로리": 0, "수분": 0}

# --- [3. UI 구성] ---
st.title("🛡️ JARVIS: 시스템 정상화 완료")
st.success("보스, 모든 외부 연결을 차단하고 내부 데이터로만 시스템을 복구했습니다.")

col1, col2 = st.columns(2)

with col1:
    st.header("1. 기본 정보")
    st.table(pd.DataFrame(FIXED_DATA["profile"]))
    
    st.header("🥗 오늘 영양")
    st.metric("섭취 칼로리", f"{st.session_state.consumed['칼로리']} kcal")
    st.metric("수분 섭취", f"{st.session_state.consumed['수분']} ml")

with col2:
    st.header("2. 자산 현황")
    savings_df = pd.DataFrame([{"항목": k, "금액": f"{v:,.0f}원"} for k, v in FIXED_DATA["assets"]["savings"].items()])
    st.table(savings_df)
    
    st.header("🍳 주방 재고")
    st.table(pd.DataFrame([{"구분": k, "내용": v} for k, v in FIXED_DATA["kitchen"].items()]))

# 입력창
with st.sidebar:
    st.header("기록")
    c = st.number_input("칼로리", 0)
    w = st.number_input("수분", 0)
    if st.button("저장"):
        st.session_state.consumed['칼로리'] += c
        st.session_state.consumed['수분'] += w
        st.rerun()
