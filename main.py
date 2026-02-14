import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# --- [1. 마스터 데이터 및 주식 상세 정보] ---
FIXED_DATA = {
    "profile": {"항목": ["나이", "거주", "상태", "결혼예정일"], "내용": ["32세", "평택 원평동", "공무원 발령 대기 중", "2026-05-30"]},
    "health": {"항목": ["현재 체중", "목표 체중", "주요 관리", "식단 금기"], "내용": ["125.0kg", "90.0kg", "고지혈증/ADHD", "생굴/멍게"]},
    "stocks": {
        "동성화인텍": {"평단": 22701, "수량": 21, "코드": "033500"},
        "삼성중공업": {"평단": 16761, "수량": 88, "코드": "010140"},
        "SK하이닉스": {"평단": 473521, "수량": 6, "코드": "000660"},
        "삼성전자": {"평단": 78895, "수량": 46, "코드": "005930"}
    },
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

# --- [2. 실시간 가격 로드 함수] ---
def get_stock_prices():
    prices = {}
    for name, info in FIXED_DATA["stocks"].items():
        try:
            url = f"https://polling.finance.naver.com/api/realtime?query=SERVICE_ITEM:{info['코드']}"
            res = requests.get(url, timeout=1).json()
            prices[name] = int(res['result']['areas'][0]['datas'][0]['nv'])
        except: prices[name] = info['평단'] # 에러 시 평단가로 표시
    return prices

# --- [3. 초기화 및 스타일] ---
st.set_page_config(page_title="자비스 v9.0", layout="wide")
if 'consumed' not in st.session_state:
    st.session_state.consumed = {k: 0 for k in TARGET.keys()}

# FatSecret 스타일 하단 탭 모사 (Streamlit 탭 사용)
st.title("🛡️ JARVIS OS v9.0")
tabs = st.tabs(["🏠 홈", "🍎 영양/식단", "💰 자산/주식", "📦 재고/생활"])

# --- [탭 1: 홈 (기본 정보)] ---
with tabs[0]:
    st.subheader("📍 보스 프로필")
    st.table(pd.DataFrame(FIXED_DATA["profile"]))
    st.subheader("⚠️ 건강 주의사항")
    st.table(pd.DataFrame(FIXED_DATA["health"]))

# --- [탭 2: 영양/식단 (FatSecret 스타일)] ---
with tabs[1]:
    st.header("🥗 오늘 영양 섭취 정보")
    
    # 기록창을 상단에 배치
    with st.expander("➕ 식단 기록하기", expanded=True):
        col_in1, col_in2, col_in3 = st.columns(3)
        c_cal = col_in1.number_input("칼로리", 0)
        c_car = col_in2.number_input("탄수", 0)
        c_pro = col_in3.number_input("단백", 0)
        c_fat = col_in1.number_input("지방", 0)
        c_wat = col_in2.number_input("수분", 0)
        if st.button("기록 저장"):
            vals = [c_cal, c_car, c_pro, c_fat, c_wat]
            for k, v in zip(TARGET.keys(), vals):
                st.session_state.consumed[k] += v
            st.rerun()

    # 영양 현황 표
    nut_data = []
    for k, v in st.session_state.consumed.items():
        remain = TARGET[k] - v
        nut_data.append({"영양소": k, "현재": v, "목표": TARGET[k], "잔여": remain})
    st.table(pd.DataFrame(nut_data))

# --- [탭 3: 자산/주식 (수익률 포함)] ---
with tabs[2]:
    st.header("📈 실시간 투자 리포트")
    current_prices = get_stock_prices()
    
    stock_rows = []
    total_eval = 0
    for name, info in FIXED_DATA["stocks"].items():
        curr = current_prices.get(name, 0)
        eval_amt = curr * info['수량']
        profit = eval_amt - (info['평단'] * info['수량'])
        profit_rate = (profit / (info['평단'] * info['수량'])) * 100
        total_eval += eval_amt
        stock_rows.append({
            "종목명": name, "수량": info['수량'], "평단가": f"{info['평단']:,}원", 
            "현재가": f"{curr:,}원", "평가금액": f"{eval_amt:,}원", 
            "수익률": f"{profit_rate:.2f}%"
        })
    st.table(pd.DataFrame(stock_rows))
    
    st.subheader("🏦 금융 자산 및 부채")
    assets_df = pd.DataFrame([{"항목": k, "금액": f"{v:,.0f}원"} for k, v in FIXED_DATA["assets"]["savings"].items()])
    debts_df = pd.DataFrame([{"항목": k, "금액": f"{v:,.0f}원"} for k, v in FIXED_DATA["assets"]["liabilities"].items()])
    st.table(pd.concat([assets_df, debts_df], keys=['자산', '부채']))

# --- [탭 4: 재고/생활] ---
with tabs[3]:
    st.header("📦 시스템 재고 및 주기")
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.subheader("🍳 주방 재고")
        st.table(pd.DataFrame([{"카테고리": k, "내용": v} for k, v in FIXED_DATA["kitchen"].items()]))
    
    with col_b:
        st.subheader("🔄 교체 주기")
        l_rows = []
        for item, info in FIXED_DATA["lifecycle"].items():
            next_date = datetime.strptime(info["last"], "%Y-%m-%d") + timedelta(days=info["period"])
            days_left = (next_date - datetime.now()).days
            l_rows.append({"항목": item, "D-Day": f"D-{days_left}"})
        st.table(pd.DataFrame(l_rows))
