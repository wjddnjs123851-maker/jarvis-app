import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# --- [1. 마스터 데이터: 보스의 데이터 원본 보존] ---
FIXED_DATA = {
    "profile": {"항목": ["나이", "거주", "상태", "결혼예정일"], "내용": ["32세", "평택 원평동", "공무원 발령 대기 중", "2026-05-30"]},
    "health": {"항목": ["현재 체중", "목표 체중", "주요 관리", "식단 금기"], "내용": ["125.0kg", "90.0kg", "고지혈증/ADHD", "생굴/멍게"]},
    "assets": {
        "savings": {"청년도약계좌": 14700000, "주택청약": 2540000, "전세보증금": 145850000},
        "liabilities": {"전세대출": 100000000, "마이너스통장": 3000000, "학자금대출": 1247270},
        "stocks": {"삼성전자": 46, "SK하이닉스": 6, "삼성중공업": 88, "동성화인텍": 21},
        "crypto": {"BTC": 0.00181400, "ETH": 0.03417393}
    },
    "lifecycle": {
        "면도날": {"last": "2026-02-06", "period": 21}, 
        "칫솔": {"last": "2026-02-06", "period": 90}, 
        "이불세탁": {"last": "2026-02-04", "period": 14} 
    },
    "kitchen": {
        "소스/캔": "토마토페이스트, 나시고랭, S&B카레, 뚝심, 땅콩버터",
        "단백질": "냉동삼치, 냉동닭다리, 관찰레, 북어채, 단백질쉐이크",
        "곡물/면": "파스타면, 소면, 쿠스쿠스, 라면, 우동, 쌀/카무트",
        "신선/기타": "김치4종, 아사이베리, 치아씨드, 향신료, 치즈"
    }
}

# --- [2. 시스템 초기 설정] ---
st.set_page_config(page_title="자비스 안전모드", layout="wide")

# 세션 상태 초기화 (데이터 휘발 방지)
if 'consumed' not in st.session_state:
    st.session_state.consumed = {"칼로리": 0, "수분": 0}
if 'cash' not in st.session_state:
    st.session_state.cash = 492918

# --- [3. 메인 리포트 UI] ---
st.title("🛡️ JARVIS OS (안전 모드 가동)")
st.info(f"📍 보스, 현재 평택은 {datetime.now().strftime('%H:%M')}입니다. 시스템을 안정화했습니다.")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("1. 기본 정보 및 건강")
    st.table(pd.DataFrame(FIXED_DATA["profile"]))
    
    st.subheader("📋 건강 지표")
    st.metric("오늘 섭취 칼로리", f"{st.session_state.consumed['칼로리']} / 2000 kcal")
    st.metric("수분 보충", f"{st.session_state.consumed['수분']} / 2000 ml")

with col2:
    st.subheader("2. 자산 현황 (안전 조회)")
    # 주식/코인 가격은 API 불안정 시 0원 처리 혹은 고정가로 표시하여 에러 방지
    asset_rows = []
    for k, v in FIXED_DATA["assets"]["savings"].items():
        asset_rows.append({"항목": k, "금액": f"{v:,.0f}원"})
    
    st.table(pd.DataFrame(asset_rows))
    
    # 순자산 요약 (부채 차감)
    total_savings = sum(FIXED_DATA["assets"]["savings"].values())
    total_debt = sum(FIXED_DATA["assets"]["liabilities"].values())
    net_worth = total_savings + st.session_state.cash - total_debt
    st.warning(f"예상 통합 순자산: 약 {net_worth:,.0f} 원")

st.divider()

# 3. 생활 및 주방 관리
st.subheader("3. 생활 주기 및 주방 재고")
c_l, c_k = st.columns(2)

with c_l:
    st.write("**🔄 소모품 주기**")
    l_rows = []
    for item, info in FIXED_DATA["lifecycle"].items():
        rem = (datetime.strptime(info["last"], "%Y-%m-%d") + timedelta(days=info["period"]) - datetime.now()).days
        l_rows.append({"항목": item, "잔여": f"{rem}일"})
    st.table(pd.DataFrame(l_rows))

with c_k:
    st.write("**🍳 주방 재고 현황**")
    st.table(pd.DataFrame([{"구분": k, "리스트": v} for k, v in FIXED_DATA["kitchen"].items()]))

# 사이드바: 입력 기능
with st.sidebar:
    st.header("⚡ 퀵 커맨드")
    with st.form("quick_input"):
        cal = st.number_input("칼로리 추가", 0)
        water = st.number_input("수분 추가(ml)", 0)
        if st.form_submit_button("기록"):
            st.session_state.consumed['칼로리'] += cal
            st.session_state.consumed['수분'] += water
            st.rerun()
